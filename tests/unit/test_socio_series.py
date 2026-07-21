"""
Tests for the v2.2 socioeconomic SVI time-series.

Pins the honest gate (single snapshot → insufficient_history, never a fabricated
slope) and the trend direction across multiple synthetic-but-schema-real dated
snapshots.
"""
from __future__ import annotations

from src.socioeconomic.loader import SocioeconomicSnapshot
from src.socioeconomic.models import DataCompleteness, Municipality
from src.socioeconomic.series import (
    STATUS_INSUFFICIENT,
    SVITrend,
    _DatedSnapshot,
    compute_svi_trends,
    svi_history_available,
)


def _muni(
    ine: str, over65: float, decline: float, second_homes: float
) -> Municipality:
    return Municipality(
        ine_code=ine, name=f"M{ine}", province="Madrid", pnsg_zone="PN",
        population=1000, population_year=2026, pop_change_5y_pct=decline,
        pct_over_65=over65, pct_second_homes=second_homes, tourism_employment=50,
        completeness=DataCompleteness.FULL,
    )


def _snap(
    date: str, over65: float, decline: float, second_homes: float
) -> _DatedSnapshot:
    # Two municipalities so min-max normalisation has a cohort.
    munis = {
        "28001": _muni("28001", over65, decline, second_homes),
        "28002": _muni("28002", 10.0, 1.0, 5.0),  # a stable low-vulnerability peer
    }
    snap = SocioeconomicSnapshot(
        schema_version="1.0", source_snapshot_date=date, n_municipalities=2,
        n_full=2, n_demographic_only=0, sources={}, municipalities=munis,
    )
    return _DatedSnapshot(date, snap)


def test_single_snapshot_is_insufficient_history() -> None:
    trends = compute_svi_trends([_snap("2026-06", 30.0, -5.0, 40.0)])
    t = trends["28001"]
    assert t.status == STATUS_INSUFFICIENT
    assert t.slope_per_period is None
    assert t.n_points == 1


def test_worsening_municipality_trends_rising() -> None:
    # 28001 gets older, more depopulated, more second homes over three periods →
    # its socioeconomic vulnerability (DEP+DEM) should rise.
    hist = [
        _snap("2024-06", 20.0, -2.0, 20.0),
        _snap("2025-06", 30.0, -5.0, 35.0),
        _snap("2026-06", 40.0, -9.0, 55.0),
    ]
    trends = compute_svi_trends(hist)
    t = trends["28001"]
    assert t.status == ""
    assert t.n_points == 3
    assert t.slope_per_period is not None and t.slope_per_period > 0
    assert t.direction == "rising"
    assert t.svi_series[0] < t.svi_series[-1]


def test_trend_evidence_stays_calibrated() -> None:
    hist = [_snap("2025-06", 20.0, -2.0, 20.0), _snap("2026-06", 40.0, -9.0, 55.0)]
    t = compute_svi_trends(hist)["28001"]
    assert t.data_status == "calibrated"  # never REAL — INE + normalisation


def test_to_dict_roundtrips_fields() -> None:
    t = compute_svi_trends([_snap("2026-06", 30.0, -5.0, 40.0)])["28001"]
    d = t.to_dict()
    assert d["status"] == STATUS_INSUFFICIENT
    assert d["data_status"] == "calibrated"
    assert d["ine_code"] == "28001"


def test_history_gate_reflects_shipped_single_snapshot() -> None:
    # The repo ships exactly one dated snapshot (2026-06), so no trend yet — the
    # gate must say so honestly rather than inventing history.
    assert svi_history_available() is False


def test_svitrend_is_frozen() -> None:
    import dataclasses

    t = SVITrend(
        ine_code="x", name="X", periods=["2026-06"], svi_series=[50.0],
        slope_per_period=None, direction="stable", n_points=1,
        status=STATUS_INSUFFICIENT,
    )
    try:
        t.slope_per_period = 1.0  # type: ignore[misc]
        raise AssertionError("SVITrend should be frozen")
    except dataclasses.FrozenInstanceError:
        pass
