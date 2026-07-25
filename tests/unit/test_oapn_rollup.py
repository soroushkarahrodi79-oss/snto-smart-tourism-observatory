"""Contracts for the OAPN cross-park benchmarking roll-up (v3.0, A15).

The non-negotiable under test: the roll-up includes ONLY parks with real,
committed satellite-trend data — never the 13 unvalidated GEE templates, which
would fabricate a network-wide claim the evidence doesn't support (ADR-004).
Runs against the repo's real committed trend fixtures (the existing
satellite_trends test convention), not mocks.
"""
from __future__ import annotations

from src.benchmarking.oapn_rollup import ParkBenchmark, build_rollup
from src.platform.territory_registry import ValidationState


def test_rollup_includes_exactly_the_three_real_parks() -> None:
    rollup = build_rollup()
    keys = {p.trend_park_key for p in rollup.parks}
    assert keys == {"pnsg", "pn_monfrague", "pn_tablas_daimiel"}
    assert rollup.n_parks_included == 3


def test_no_unvalidated_template_park_enters_the_rollup() -> None:
    rollup = build_rollup()
    for park in rollup.parks:
        assert park.validation_state is not ValidationState.TEMPLATE_UNVALIDATED


def test_pending_templates_are_counted_not_folded_into_totals() -> None:
    rollup = build_rollup()
    # 15 GEE templates - 2 real trend pilots = 13 still pending.
    assert rollup.n_parks_pending_validation == 13
    # the pending count must not silently inflate total_assets/degrading
    assert rollup.total_assets == sum(p.n_assets for p in rollup.parks)


def test_pnsg_maps_to_its_active_pilot_validation_state() -> None:
    rollup = build_rollup()
    pnsg = next(p for p in rollup.parks if p.trend_park_key == "pnsg")
    assert pnsg.registry_slug == "pnsg"
    assert pnsg.validation_state is ValidationState.ACTIVE_PILOT


def test_trend_pilots_map_to_trend_pilot_validation_state() -> None:
    rollup = build_rollup()
    by_key = {p.trend_park_key: p for p in rollup.parks}
    for key in ("pn_monfrague", "pn_tablas_daimiel"):
        assert by_key[key].validation_state is ValidationState.TREND_PILOT
        assert by_key[key].registry_slug is not None


def test_pct_degrading_is_consistent_with_counts() -> None:
    rollup = build_rollup()
    for p in rollup.parks:
        assert 0.0 <= p.pct_degrading <= 100.0
        if p.n_assets:
            expected = round(100.0 * p.n_degrading / p.n_assets, 1)
            assert p.pct_degrading == expected


def test_parks_sorted_worst_first_by_pct_degrading() -> None:
    rollup = build_rollup()
    pcts = [p.pct_degrading for p in rollup.parks]
    assert pcts == sorted(pcts, reverse=True)


def test_park_benchmark_is_frozen() -> None:
    rollup = build_rollup()
    park = rollup.parks[0]
    assert isinstance(park, ParkBenchmark)
    try:
        park.n_assets = 999  # type: ignore[misc]
        raised = False
    except Exception:
        raised = True
    assert raised
