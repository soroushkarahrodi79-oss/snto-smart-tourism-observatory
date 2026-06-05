from __future__ import annotations

import pytest
from src.assets.models import AssetObservation
from src.time_series.climatology import (
    MonthlyClimatology,
    AnomalyEvent,
    build_climatology,
    detect_anomaly_events,
)


def _make_obs(year, month, ndvi, ndmi=0.12):
    return AssetObservation(
        asset_id="test", year=year, month=month, ndvi=ndvi, ndmi=ndmi
    )


def _make_multiyear_obs():
    observations = []
    base = {1: 0.32, 2: 0.37, 3: 0.45, 4: 0.52, 5: 0.47, 6: 0.28,
            7: 0.18, 8: 0.17, 9: 0.20, 10: 0.28, 11: 0.32, 12: 0.30}
    for year in range(2021, 2025):
        for month, ndvi in base.items():
            # 2022: drought year — NDVI depressed
            delta = -0.08 if year == 2022 and month in [4, 5, 6, 7, 8] else 0.0
            observations.append(_make_obs(year, month, ndvi + delta))
    return observations


def test_build_climatology_returns_12_months():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    assert len(clim) == 12


def test_climatology_mean_close_to_expected():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    # April mean should be (0.52 * 3 + 0.44) / 4 = 0.50
    expected_apr_mean = (0.52 * 3 + (0.52 - 0.08)) / 4
    assert abs(clim[4].mean - expected_apr_mean) < 0.01


def test_z_score_normal_value_near_zero():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    z = clim[7].z_score(0.18)  # near climatological mean for July
    assert abs(z) < 1.5


def test_z_score_drought_value_negative():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    z = clim[4].z_score(0.30)  # 0.08 below April mean
    assert z < -1.0


def test_climatology_p75_gt_p25():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    for month, c in clim.items():
        assert c.p75 >= c.p25, f"Month {month}: p75 < p25"


def test_classify_anomaly_returns_valid_category():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    categories = {
        "anomaly_low_severe", "anomaly_low", "below_normal",
        "normal", "above_normal", "anomaly_high", "anomaly_high_severe",
    }
    for month, c in clim.items():
        cat = c.classify_anomaly(c.mean)
        assert cat in categories


def test_detect_anomaly_events_finds_drought():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    events = detect_anomaly_events(obs, clim, z_threshold=1.5)
    # 2022 drought months should be flagged (z <= -1.5 because delta=-0.08 vs small std)
    drought_years = {e.year for e in events if e.z_score <= -1.5}
    assert 2022 in drought_years


def test_anomaly_events_sorted_by_severity():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    events = detect_anomaly_events(obs, clim, z_threshold=1.5)
    z_scores = [abs(e.z_score) for e in events]
    assert z_scores == sorted(z_scores, reverse=True)


def test_no_events_when_threshold_too_high():
    obs = _make_multiyear_obs()
    clim = build_climatology(obs)
    events = detect_anomaly_events(obs, clim, z_threshold=10.0)
    assert events == []
