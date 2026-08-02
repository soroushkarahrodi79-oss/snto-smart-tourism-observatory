"""
SNTO — Shared Earth Engine initialization foundation (ADR-015)
==============================================================

One idempotent Earth Engine initialization path for the whole project. Both the
offline ingestion adapter (``src/ingestion/gee_adapter.py``) and the future
in-process Visual Change Explorer share it, so ``ee.Initialize`` is called at
most once per process/credential set — critical under Streamlit's rerun model.

Layers
------
* :func:`initialize_earth_engine` — **low-level, framework-free.** Reuses the
  existing personal-auth / service-account modes, is idempotent via a process
  guard, imports ``ee`` lazily (so the module stays importable without the SDK),
  and maps SDK failures to the typed hierarchy in :mod:`.errors`. Takes explicit
  credentials so non-``Settings`` callers (the adapter) can keep their own.
* :func:`get_change_explorer_client` — **application-facing.** Enforces the
  ``SNTO_ENABLE_CHANGE_EXPLORER`` feature flag and required config, then delegates
  to :func:`initialize_earth_engine` using :class:`Settings`.
* :func:`cached_earth_engine_client` — the same accessor memoised with
  ``st.cache_resource`` (the only Streamlit touch-point). Importable without a
  Streamlit *run context*; non-UI callers should use
  :func:`get_change_explorer_client` directly.

Nothing here authenticates interactively: service-account mode uses a key file,
personal mode relies on a prior ``earthengine authenticate`` (dev only). There is
no ``ee.Authenticate()`` call anywhere in this module.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Callable

from src.config.settings import Settings
from src.config.settings import settings as _default_settings
from src.integrations.earth_engine.errors import (
    EarthEngineConfigError,
    EarthEngineDisabledError,
    EarthEngineUnavailableError,
    map_ee_exception,
)

logger = logging.getLogger(__name__)

# Process-wide initialization guard. The tuple identifies the credential set that
# was initialised; a repeat request with the same set is a no-op. Guarded by a
# lock so concurrent Streamlit script threads cannot double-initialise.
_init_lock = threading.Lock()
_initialized_key: tuple[str, str, str] | None = None


@dataclass(frozen=True)
class EarthEngineClient:
    """Small, typed handle returned once Earth Engine is initialised.

    Intentionally minimal: it records the initialised ``project_id`` and exposes
    the live ``ee`` module via :meth:`module`. It holds no credential material.
    """

    project_id: str

    def module(self) -> Any:
        """Return the initialised ``ee`` module (import is lazy)."""
        return _import_ee()


def _import_ee() -> Any:
    """Import ``earthengine-api`` lazily, mapping absence to a typed error."""
    try:
        import ee
    except ImportError as exc:  # pragma: no cover - exercised via monkeypatch
        raise EarthEngineUnavailableError(
            "earthengine-api is not installed."
        ) from exc
    return ee


def initialize_earth_engine(
    project_id: str,
    *,
    service_account: str = "",
    key_file: str = "",
) -> EarthEngineClient:
    """Idempotently initialise Earth Engine for *project_id*.

    * ``key_file`` set  → service-account mode
      (``ee.ServiceAccountCredentials`` + ``ee.Initialize(credentials=…)``).
    * ``key_file`` empty → personal mode (``ee.Initialize(project=…)``); requires
      a prior ``earthengine authenticate`` on the machine (dev only).

    Repeated calls with the same ``(project_id, service_account, key_file)`` do
    not call ``ee.Initialize`` again. SDK failures are mapped to the typed
    hierarchy and never leak credential material.
    """
    if not project_id:
        raise EarthEngineConfigError(
            "Earth Engine project id is not configured."
        )

    key = (project_id, service_account, key_file)
    global _initialized_key
    with _init_lock:
        if _initialized_key == key:
            return EarthEngineClient(project_id=project_id)

        ee = _import_ee()
        try:
            if key_file:
                credentials = ee.ServiceAccountCredentials(service_account, key_file)
                ee.Initialize(credentials=credentials, project=project_id)
            else:
                ee.Initialize(project=project_id)
        except Exception as exc:  # noqa: BLE001 - re-raised as typed, cause chained
            # Log the category only; never the exception text (may hold paths).
            logger.warning("Earth Engine initialization failed (project set).")
            raise map_ee_exception(exc) from exc

        _initialized_key = key
        logger.info("Earth Engine initialized for the configured project.")
        return EarthEngineClient(project_id=project_id)


def get_change_explorer_client(
    app_settings: Settings | None = None,
) -> EarthEngineClient:
    """Application-facing accessor gated by the Visual Change Explorer flag.

    Raises :class:`EarthEngineDisabledError` when the feature flag is off and
    :class:`EarthEngineConfigError` when the project id is missing, before any
    Earth Engine import or network call.
    """
    s = app_settings if app_settings is not None else _default_settings
    if not s.snto_enable_change_explorer:
        raise EarthEngineDisabledError(
            "The Visual Change Explorer is disabled. "
            "Set SNTO_ENABLE_CHANGE_EXPLORER=true to enable it."
        )
    if not s.gee_project_id:
        raise EarthEngineConfigError(
            "Earth Engine is enabled but GEE_PROJECT_ID is not configured."
        )
    return initialize_earth_engine(
        s.gee_project_id,
        service_account=s.gee_service_account,
        key_file=s.gee_key_file,
    )


def reset_earth_engine_state() -> None:
    """Clear the process init guard so the next call re-initialises.

    Intended for tests and long-running ops that rotate credentials; not part of
    the normal request path.
    """
    global _initialized_key
    with _init_lock:
        _initialized_key = None


# ── Application-facing cached boundary (only Streamlit touch-point) ────────────
# The process-level guard above already guarantees single initialisation;
# st.cache_resource simply memoises the returned handle per Streamlit session and
# is the sole Streamlit dependency in this module. The wrapper is built once at
# import so the memo is stable across reruns, and it degrades to a plain delegate
# when Streamlit is absent — so the module stays importable without a Streamlit
# run context.
def _build_cached_accessor() -> Callable[[], EarthEngineClient]:
    try:
        import streamlit as st
    except ModuleNotFoundError:  # pragma: no cover - streamlit is a declared dep
        return get_change_explorer_client

    return st.cache_resource(show_spinner=False)(get_change_explorer_client)


cached_earth_engine_client: Callable[[], EarthEngineClient] = _build_cached_accessor()
"""Application-facing accessor for the Visual Change Explorer, memoised via
``st.cache_resource`` when Streamlit is present. Non-UI callers should prefer
:func:`get_change_explorer_client`."""
