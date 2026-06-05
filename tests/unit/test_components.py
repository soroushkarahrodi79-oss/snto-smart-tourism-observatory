from __future__ import annotations

from src.features.spectral import SpectralFeatures
from src.risk_engine.components import (
    compute_ecological_degradation,
    compute_human_pressure_proxy,
    compute_vulnerability_index,
)
from src.time_series.anomaly import AnomalyResult
from src.time_series.trend import TrendResult


def _make_features(mean_ndvi: float = 0.55, mean_ndmi: float = 0.20) -> SpectralFeatures:
    return SpectralFeatures(
        asset_id="test",
        mean_ndvi=mean_ndvi,
        mean_ndmi=mean_ndmi,
        mean_nbr=None,
        ndvi_series=[mean_ndvi] * 12,
        ndmi_series=[mean_ndmi] * 12,
    )


def _flat_trend(slope: float = 0.0) -> TrendResult:
    return TrendResult(slope=slope, intercept=0.5, r_squared=0.0)


def _no_anomaly() -> AnomalyResult:
    return AnomalyResult(z_score=0.0, is_anomaly=False, direction="none")


# ── Ecological degradation ─────────────────────────────────────────────────

def test_ecological_in_range():
    features = _make_features()
    result = compute_ecological_degradation(features, _flat_trend())
    assert 0.0 <= result <= 1.0


def test_ecological_higher_when_ndvi_below_baseline():
    healthy = _make_features(mean_ndvi=0.55)
    degraded = _make_features(mean_ndvi=0.15)
    trend = _flat_trend()
    assert compute_ecological_degradation(degraded, trend) > compute_ecological_degradation(healthy, trend)


def test_ecological_negative_trend_increases_score():
    features = _make_features()
    good_trend = _flat_trend(slope=0.01)
    bad_trend = _flat_trend(slope=-0.04)
    assert compute_ecological_degradation(features, bad_trend) > compute_ecological_degradation(features, good_trend)


# ── Human pressure proxy ───────────────────────────────────────────────────

def test_human_pressure_in_range():
    features = _make_features()
    result = compute_human_pressure_proxy(features, volatility=0.05, asset_metadata={})
    assert 0.0 <= result <= 1.0


def test_disturbed_series_higher_pressure_than_smooth():
    import math
    # Smooth seasonal series — very low deseasonalized residual
    smooth_series = [0.5 + 0.2 * math.sin(2 * math.pi * (t - 4) / 12) for t in range(1, 13)]
    # Same series with a sharp disturbance spike (e.g. fire scar, construction)
    disturbed_series = smooth_series[:]
    disturbed_series[5] -= 0.15
    disturbed_series[6] -= 0.12

    smooth_feat = SpectralFeatures(
        asset_id="test", mean_ndvi=0.5, mean_ndmi=0.3, mean_nbr=None,
        ndvi_series=smooth_series, ndmi_series=[0.3] * 12,
    )
    disturbed_feat = SpectralFeatures(
        asset_id="test", mean_ndvi=0.5, mean_ndmi=0.3, mean_nbr=None,
        ndvi_series=disturbed_series, ndmi_series=[0.3] * 12,
    )
    low = compute_human_pressure_proxy(smooth_feat, volatility=0.0, asset_metadata={})
    high = compute_human_pressure_proxy(disturbed_feat, volatility=0.0, asset_metadata={})
    assert high > low


def test_visitor_count_increases_pressure():
    features = _make_features()
    no_visitors = compute_human_pressure_proxy(features, volatility=0.02, asset_metadata={})
    with_visitors = compute_human_pressure_proxy(
        features, volatility=0.02, asset_metadata={"visitor_count_annual": 40_000}
    )
    assert with_visitors > no_visitors


# ── Vulnerability index ────────────────────────────────────────────────────

def test_vulnerability_in_range():
    features = _make_features()
    result = compute_vulnerability_index(features, _no_anomaly(), elevation_m=420.0)
    assert 0.0 <= result <= 1.0


def test_anomaly_increases_vulnerability():
    features = _make_features()
    baseline = compute_vulnerability_index(features, _no_anomaly(), elevation_m=None)
    anomaly = AnomalyResult(z_score=-3.0, is_anomaly=True, direction="low")
    elevated = compute_vulnerability_index(features, anomaly, elevation_m=None)
    assert elevated > baseline
