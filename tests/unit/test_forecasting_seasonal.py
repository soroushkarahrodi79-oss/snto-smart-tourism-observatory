"""
Tests for the v2.2 seasonal projection.

Covers the seasonal shape (peaks land where the cycle says), the trend-driven
band still widening, and the same evidence-honesty gate as the plain trend
forecast.
"""
from __future__ import annotations

import dataclasses
import math

import pytest

from src.forecasting.projection import FORECAST_EVIDENCE_CLASS
from src.forecasting.seasonal import SeasonalForecast, project_seasonal
from src.platform.evidence import DecisionUse, EvidenceClass, supports

_PERIOD = 12


def _seasonal_series(
    n_years: int = 4, trend: float = 0.5, amp: float = 10.0
) -> list[float]:
    """A clean trend + annual sine wave: base + trend·t + amp·sin(2πt/12)."""
    out: list[float] = []
    for t in range(n_years * _PERIOD):
        out.append(50.0 + trend * t + amp * math.sin(2 * math.pi * t / _PERIOD))
    return out


def test_band_contains_point_and_widens() -> None:
    fc = project_seasonal(_seasonal_series(), horizon=24)
    for lo, p, hi in zip(fc.lower, fc.point, fc.upper):
        assert lo <= p <= hi
    widths = [hi - lo for lo, hi in zip(fc.lower, fc.upper)]
    assert all(b >= a - 1e-9 for a, b in zip(widths, widths[1:]))


def test_seasonal_component_is_periodic() -> None:
    fc = project_seasonal(_seasonal_series(), horizon=24, period=_PERIOD)
    # The applied seasonal offsets must repeat every `period` steps.
    for i in range(_PERIOD):
        assert fc.seasonal[i] == pytest.approx(fc.seasonal[i + _PERIOD], abs=1e-6)


def test_seasonal_forecast_beats_flat_trend_on_seasonal_data() -> None:
    # On a strongly seasonal series, the projected path must actually oscillate —
    # its peak-to-trough spread should be close to the true amplitude (2*amp),
    # not flattened to ~0 as a pure trend projection would be.
    amp = 10.0
    fc = project_seasonal(_seasonal_series(amp=amp), horizon=24, period=_PERIOD)
    spread = max(fc.seasonal) - min(fc.seasonal)
    assert spread > amp  # clearly retains the cycle (true peak-to-trough ≈ 2*amp)


def test_seasonality_strength_high_for_seasonal_series() -> None:
    fc = project_seasonal(_seasonal_series(amp=10.0), horizon=12)
    assert fc.seasonality_strength > 0.5


def test_clamp_bounds_all_paths() -> None:
    fc = project_seasonal(_seasonal_series(), horizon=36, clamp=(0.0, 100.0))
    for lo, p, hi in zip(fc.lower, fc.point, fc.upper):
        assert 0.0 <= lo <= 100.0
        assert 0.0 <= p <= 100.0
        assert 0.0 <= hi <= 100.0
        assert lo <= p <= hi


# ── Evidence honesty ──────────────────────────────────────────────────────


def test_seasonal_forecast_is_simulated_never_real() -> None:
    fc = project_seasonal(_seasonal_series(), horizon=6)
    assert fc.evidence_class is EvidenceClass.SIMULATED
    assert fc.evidence_class is FORECAST_EVIDENCE_CLASS
    for use in DecisionUse:
        assert supports(fc.evidence_class, use) is False


def test_construction_rejects_real_evidence_class() -> None:
    with pytest.raises(ValueError, match="never carry"):
        SeasonalForecast(
            horizon=1, period=12, point=[1.0], lower=[0.0], upper=[2.0],
            seasonal=[0.0], trend_point=[1.0], seasonality_strength=0.5,
            n_obs=12, alpha=0.05, evidence_class=EvidenceClass.REAL,
        )


def test_to_dict_reports_evidence_and_period() -> None:
    fc = project_seasonal(_seasonal_series(), horizon=3, period=_PERIOD)
    d = fc.to_dict()
    assert d["evidence_class"] == "simulated"
    assert d["period"] == _PERIOD
    assert d["caveat"]


# ── Guards ────────────────────────────────────────────────────────────────


def test_rejects_series_shorter_than_period() -> None:
    with pytest.raises(ValueError, match="one full period"):
        project_seasonal([1.0] * 6, horizon=3, period=12)


def test_rejects_nonpositive_horizon() -> None:
    with pytest.raises(ValueError, match="horizon"):
        project_seasonal(_seasonal_series(), horizon=0)


def test_seasonal_forecast_is_frozen() -> None:
    fc = project_seasonal(_seasonal_series(), horizon=2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        fc.horizon = 5  # type: ignore[misc]
