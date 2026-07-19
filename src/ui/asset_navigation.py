"""Session-state routing contract for the central asset page.

Fase 6.5 keeps the in-page Streamlit architecture selected in roadmap option
2.1-A.  An asset identifier in ``st.session_state`` therefore acts as the
route: when present, the dashboard shell renders the asset page instead of the
four analytical layers.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from typing import Any

SELECTED_ASSET_SESSION_KEY = "_snto_selected_asset_id"


def selected_asset_id(state: Mapping[str, Any]) -> str | None:
    """Return the normalized selected asset id, or ``None`` for no route."""
    value = state.get(SELECTED_ASSET_SESSION_KEY)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def select_asset(state: MutableMapping[str, Any], asset_id: str) -> None:
    """Open the asset-page route for ``asset_id`` in a mutable state mapping."""
    normalized = str(asset_id).strip()
    if not normalized:
        raise ValueError("asset_id must not be empty")
    state[SELECTED_ASSET_SESSION_KEY] = normalized


def clear_asset_selection(state: MutableMapping[str, Any]) -> None:
    """Return to the dashboard layers without disturbing other session state."""
    state.pop(SELECTED_ASSET_SESSION_KEY, None)


def find_asset(assets: Iterable[Any], asset_id: str | None) -> Any | None:
    """Resolve one asset by id; stale or absent routes resolve to ``None``."""
    if asset_id is None:
        return None
    return next(
        (asset for asset in assets if str(asset.asset_id) == str(asset_id)),
        None,
    )
