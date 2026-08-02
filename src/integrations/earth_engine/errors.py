"""
SNTO — Earth Engine typed error hierarchy (ADR-015)
===================================================

A small, typed exception hierarchy for the shared Earth Engine foundation so
callers (the future Visual Change Explorer service and UI) can map failure
*categories* to understandable states without inspecting raw SDK exceptions.

Design notes
------------
* ``EarthEngineError`` subclasses :class:`RuntimeError` on purpose: the existing
  ``src/ingestion/gee_adapter.py`` documented a ``RuntimeError`` contract on a
  missing ``earthengine-api`` install, and callers may still ``except
  RuntimeError``. Keeping the base as ``RuntimeError`` preserves that behaviour
  while adding precise subtypes.
* **No credential material** (service-account emails, key-file paths, tokens)
  is ever placed in these messages. :func:`map_ee_exception` classifies by
  keyword but never re-emits the original text; the original is retained only
  via exception chaining (``raise ... from exc``) for local debugging.
"""
from __future__ import annotations


class EarthEngineError(RuntimeError):
    """Base class for all Earth Engine foundation errors."""


class EarthEngineDisabledError(EarthEngineError):
    """The Visual Change Explorer feature flag is off (SNTO_ENABLE_CHANGE_EXPLORER)."""


class EarthEngineConfigError(EarthEngineError):
    """Required Earth Engine configuration is missing or invalid (e.g. project id)."""


class EarthEngineAuthError(EarthEngineError):
    """Authentication with Earth Engine failed (bad credentials / permission)."""


class EarthEngineUnavailableError(EarthEngineError):
    """Earth Engine could not be initialised or is otherwise unavailable.

    Also raised when the ``earthengine-api`` package is not installed.
    """


class EarthEngineQuotaError(EarthEngineError):
    """Earth Engine rejected the call due to quota or rate limiting."""


# ── Safe classification ───────────────────────────────────────────────────────

# Keyword buckets used to classify an opaque SDK exception. Matching is done on a
# lower-cased copy of the message; the message itself is never re-emitted.
_QUOTA_HINTS = ("quota", "rate limit", "rate-limit", "too many requests", "429")
_AUTH_HINTS = (
    "auth",
    "credential",
    "permission",
    "forbidden",
    "unauthorized",
    "unauthenticated",
    "401",
    "403",
)


def map_ee_exception(exc: BaseException) -> EarthEngineError:
    """Classify an arbitrary Earth Engine SDK exception into a typed error.

    The returned exception carries a *fixed, credential-free* message per
    category and chains ``exc`` as its cause. This is the single place the
    foundation converts opaque ``ee``/Google API failures into the SNTO
    hierarchy, so error handling stays uniform and leak-free.
    """
    text = str(exc).lower()
    if any(hint in text for hint in _QUOTA_HINTS):
        return EarthEngineQuotaError(
            "Earth Engine quota or rate limit exceeded."
        )
    if any(hint in text for hint in _AUTH_HINTS):
        return EarthEngineAuthError(
            "Earth Engine authentication failed."
        )
    return EarthEngineUnavailableError(
        "Earth Engine initialization failed or is unavailable."
    )
