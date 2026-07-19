"""Contracts for the Fase 6.5 session-state asset route."""

from dataclasses import dataclass

import pytest

from src.ui.asset_navigation import (
    SELECTED_ASSET_SESSION_KEY,
    clear_asset_selection,
    find_asset,
    select_asset,
    selected_asset_id,
)


@dataclass(frozen=True)
class _Asset:
    asset_id: str


def test_asset_route_round_trip_preserves_unrelated_session_state() -> None:
    state = {"view": "manager"}

    select_asset(state, "pnsg-01")

    assert selected_asset_id(state) == "pnsg-01"
    assert state[SELECTED_ASSET_SESSION_KEY] == "pnsg-01"
    assert find_asset([_Asset("pnsg-01"), _Asset("pnsg-02")], "pnsg-01") == _Asset(
        "pnsg-01"
    )

    clear_asset_selection(state)

    assert selected_asset_id(state) is None
    assert state == {"view": "manager"}


def test_stale_asset_route_does_not_resolve_to_another_asset() -> None:
    assert find_asset([_Asset("pnsg-01")], "missing") is None
    assert find_asset([_Asset("pnsg-01")], None) is None


def test_asset_ids_are_normalized_at_the_state_boundary() -> None:
    state = {}
    select_asset(state, "  pnsg-01  ")
    assert selected_asset_id(state) == "pnsg-01"

    with pytest.raises(ValueError, match="must not be empty"):
        select_asset(state, "   ")
