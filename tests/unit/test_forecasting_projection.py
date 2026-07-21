"""
Tests for the v2.2 trend-projection layer.

Two axes are pinned: the projection is analytically sound (direction, band
ordering, horizon-widening), and it is evidence-honest (always SIMULATED, never
REAL, and gated out of every decision use).
"""
from __future__ import annotations

import dataclasses

import pytest

from src.forecasting.projection import (
    FORECAST_EVIDENCE_CLASS,
    Forecast,
    ThresholdDirection,
    project_trend,
    threshold_crossing,
)
from src.platform.evidence import DecisionUse, EvidenceClass, supports

# A clean declining series (degradation): slope ≈ -1 per period.
_DECLINING = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0]
# A clean rising series.
_RISING = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0]


def test_point_path_follows_slope_direction() -> None:
    fc = project_trend(_DECLINING, horizon=6)
    assert fc.slope < 0
    # Declining series → each projected point below the previous.
    assert all(b < a for a, b in zip(fc.point, fc.point[1:]))

    up = project_trend(_RISING, horizon=6)
    assert up.slope > 0
    assert all(b > a for a, b in zip(up.point, up.point[1:]))


def test_band_contains_point_at_every_step() -> None:
    fc = project_trend(_DECLINING, horizon=8)
    for lo, p, hi in zip(fc.lower, fc.point, fc.upper):
        assert lo <= p <= hi


def test_band_widens_with_horizon() -> None:
    fc = project_trend(_DECLINING, horizon=10)
    widths = [hi - lo for lo, hi in zip(fc.lower, fc.upper)]
    # Uncertainty must not shrink as we project further out.
    assert all(b >= a - 1e-9 for a, b in zip(widths, widths[1:]))


def test_horizon_length_and_indexing() -> None:
    fc = project_trend(_RISING, horizon=5)
    assert fc.horizon == 5
    assert len(fc.point) == len(fc.lower) == len(fc.upper) == 5
    assert fc.n_obs == len(_RISING)


def test_clamp_bounds_all_paths() -> None:
    fc = project_trend(_DECLINING, horizon=200, clamp=(0.0, 100.0))
    assert all(0.0 <= v <= 100.0 for v in fc.lower)
    assert all(0.0 <= v <= 100.0 for v in fc.point)
    assert all(0.0 <= v <= 100.0 for v in fc.upper)
    # Band ordering survives clamping.
    for lo, p, hi in zip(fc.lower, fc.point, fc.upper):
        assert lo <= p <= hi


# ── Evidence honesty ──────────────────────────────────────────────────────


def test_forecast_is_always_simulated_never_real() -> None:
    fc = project_trend(_DECLINING, horizon=3)
    assert fc.evidence_class is EvidenceClass.SIMULATED
    assert fc.evidence_class is FORECAST_EVIDENCE_CLASS
    assert fc.evidence_class is not EvidenceClass.REAL


def test_forecast_supports_no_decision_use() -> None:
    fc = project_trend(_DECLINING, horizon=3)
    # A projection may back NO decision — the built-in gate (empty allowed_uses).
    for use in DecisionUse:
        assert supports(fc.evidence_class, use) is False


def test_construction_rejects_real_evidence_class() -> None:
    with pytest.raises(ValueError, match="never carry"):
        Forecast(
            horizon=1, point=[1.0], lower=[0.0], upper=[2.0],
            slope=0.0, slope_lower=0.0, slope_upper=0.0, anchor=1.0,
            n_obs=3, alpha=0.05, evidence_class=EvidenceClass.REAL,
        )


def test_to_dict_reports_evidence_class() -> None:
    fc = project_trend(_DECLINING, horizon=2)
    d = fc.to_dict()
    assert d["evidence_class"] == "simulated"
    assert d["slope_ci"] == [fc.slope_lower, fc.slope_upper]
    assert d["caveat"]


# ── Threshold crossing ────────────────────────────────────────────────────


def test_threshold_crossing_below_orders_edges() -> None:
    # Declining from ~93 at slope ~-1; an EHS floor of 85 is reached within ~8-10.
    fc = project_trend(_DECLINING, horizon=20)
    cross = threshold_crossing(fc, threshold=85.0, direction=ThresholdDirection.BELOW)
    assert cross.point_step is not None
    # The pessimistic edge (lower) reaches the floor no later than the point path,
    # which reaches it no later than the optimistic edge.
    assert cross.lower_step is not None and cross.lower_step <= cross.point_step


def test_threshold_never_reached_returns_none() -> None:
    fc = project_trend(_RISING, horizon=5)
    # Rising series never falls below a floor far beneath it.
    cross = threshold_crossing(fc, threshold=-100.0, direction=ThresholdDirection.BELOW)
    assert cross.point_step is None
    assert cross.lower_step is None
    assert cross.upper_step is None


# ── Guards ────────────────────────────────────────────────────────────────


def test_rejects_short_series() -> None:
    with pytest.raises(ValueError, match="at least"):
        project_trend([1.0, 2.0], horizon=3)


def test_rejects_nonpositive_horizon() -> None:
    with pytest.raises(ValueError, match="horizon"):
        project_trend(_RISING, horizon=0)


def test_forecast_is_frozen() -> None:
    fc = project_trend(_RISING, horizon=2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        fc.slope = 1.0  # type: ignore[misc]
