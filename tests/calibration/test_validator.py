from __future__ import annotations

import pytest

from src.assets.models import AssetObservation, SpatialStats
from src.calibration.validator import CalibrationReport, CalibrationValidator
from src.ingestion.calibrated_adapter import (
    ANNUAL_MEAN_NDMI,
    ANNUAL_MEAN_NDVI,
    CalibratedAdapter,
)
from src.ingestion.mock_generator import MockDataGenerator


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mock_obs(masatrigo_asset):
    return MockDataGenerator().fetch_time_series(masatrigo_asset, year=2024)


@pytest.fixture
def ref_obs(masatrigo_asset):
    return CalibratedAdapter().fetch_time_series(masatrigo_asset, year=2024)


@pytest.fixture
def cal_report(mock_obs, ref_obs):
    return CalibrationValidator().validate(mock_obs, ref_obs, elevation_m=420.0)


# ── CalibratedAdapter tests ────────────────────────────────────────────────

def test_calibrated_adapter_returns_12_months(masatrigo_asset):
    obs = CalibratedAdapter().fetch_time_series(masatrigo_asset, year=2024)
    assert len(obs) == 12


def test_calibrated_adapter_ndvi_range(masatrigo_asset):
    obs = CalibratedAdapter().fetch_time_series(masatrigo_asset, year=2024)
    for o in obs:
        assert 0.0 < o.ndvi < 1.0, f"NDVI {o.ndvi} out of range at month {o.month}"


def test_calibrated_adapter_ndmi_range(masatrigo_asset):
    obs = CalibratedAdapter().fetch_time_series(masatrigo_asset, year=2024)
    for o in obs:
        assert 0.0 < o.ndmi < 1.0, f"NDMI {o.ndmi} out of range at month {o.month}"


def test_calibrated_adapter_has_spatial_stats(masatrigo_asset):
    obs = CalibratedAdapter().fetch_time_series(masatrigo_asset, year=2024)
    for o in obs:
        assert o.ndvi_stats is not None
        assert o.ndmi_stats is not None


def test_calibrated_annual_mean_matches_constant():
    from src.ingestion.calibrated_adapter import _NDVI_CLIMATOLOGY
    computed = sum(v["mean"] for v in _NDVI_CLIMATOLOGY.values()) / 12
    assert abs(computed - ANNUAL_MEAN_NDVI) < 1e-10


def test_calibrated_summer_ndvi_lower_than_spring(masatrigo_asset):
    obs = CalibratedAdapter().fetch_time_series(masatrigo_asset, year=2024)
    by_month = {o.month: o for o in obs}
    # Mediterranean: spring (Apr) NDVI >> summer (Jul) NDVI
    assert by_month[4].ndvi > by_month[7].ndvi


def test_calibrated_spatial_stats_p75_gt_p25(masatrigo_asset):
    obs = CalibratedAdapter().fetch_time_series(masatrigo_asset, year=2024)
    for o in obs:
        assert o.ndvi_stats.p75 > o.ndvi_stats.p25


# ── CalibrationValidator tests ─────────────────────────────────────────────

def test_calibration_report_has_12_months(cal_report):
    assert len(cal_report.monthly_deviations) == 12


def test_mock_ndvi_overestimates_reference_summer(cal_report):
    # Mock is known to overestimate in summer months (Jul-Aug)
    summer = [d for d in cal_report.monthly_deviations if d.month in [7, 8]]
    for d in summer:
        assert d.mock_ndvi > d.ref_ndvi, (
            f"Month {d.month}: expected mock > ref, got mock={d.mock_ndvi}, ref={d.ref_ndvi}"
        )


def test_ndvi_bias_direction_is_optimistic(cal_report):
    assert cal_report.ndvi_bias_direction == "optimistic"


def test_ndmi_bias_direction_is_optimistic(cal_report):
    assert cal_report.ndmi_bias_direction == "optimistic"


def test_reference_risk_score_higher_than_mock(cal_report):
    # Real data reveals more degradation than the optimistic mock
    assert cal_report.ref_risk_score > cal_report.mock_risk_score


def test_reference_risk_score_above_mock_regardless_of_level(cal_report):
    # Reference shows meaningfully more ecological stress than mock.
    # Alert level may or may not change depending on geo proxy context —
    # what matters is that reference score is higher (more degraded).
    delta_pct = cal_report.risk_score_pct_change
    assert delta_pct > 50.0, (
        f"Expected reference risk at least 50% higher than mock, got {delta_pct:.1f}%"
    )


def test_cal_report_rmse_positive(cal_report):
    assert cal_report.ndvi_rmse > 0
    assert cal_report.ndmi_rmse > 0


def test_cal_report_to_dict_has_required_sections(cal_report):
    d = cal_report.to_dict()
    assert "ndvi" in d
    assert "ndmi" in d
    assert "risk_model" in d
    assert "spatial_quality" in d
    assert "monthly_detail" in d
    assert len(d["monthly_detail"]) == 12


def test_validator_raises_on_empty_observations():
    with pytest.raises(ValueError, match="non-empty"):
        CalibrationValidator().validate([], [])


def test_validator_raises_on_no_overlapping_months(masatrigo_asset):
    obs_a = [AssetObservation(asset_id="x", year=2024, month=1, ndvi=0.4, ndmi=0.1)]
    obs_b = [AssetObservation(asset_id="x", year=2024, month=7, ndvi=0.3, ndmi=0.08)]
    # month 1 in A vs month 7 in B — no overlap
    with pytest.raises(ValueError, match="overlapping"):
        CalibrationValidator().validate(obs_a, obs_b)


# ── SpatialStats model tests ───────────────────────────────────────────────

def test_spatial_stats_validation():
    ss = SpatialStats(
        mean=0.42, median=0.41, p25=0.36, p75=0.48,
        std=0.05, pixel_count=1200, valid_pixel_pct=0.85,
    )
    assert ss.p75 > ss.p25
    assert 0 < ss.valid_pixel_pct <= 1.0


def test_observation_spatial_stats_optional():
    obs = AssetObservation(asset_id="x", year=2024, month=1, ndvi=0.4, ndmi=0.1)
    assert obs.ndvi_stats is None
    assert obs.ndmi_stats is None
