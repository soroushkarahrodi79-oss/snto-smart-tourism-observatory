from __future__ import annotations

import pytest
from src.assets.models import AssetObservation
from src.spatial_causality.analyzer import (
    CORE_OUTER_M,
    LANDSCAPE_OUTER_M,
    NEAR_OUTER_M,
    SpatialCausalityAnalyzer,
    SpatialCausalityResult,
    ZoneSignal,
    _pearson,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_obs(year, month, ndvi, ndmi=0.12, asset_id="test"):
    return AssetObservation(
        asset_id=asset_id, year=year, month=month, ndvi=ndvi, ndmi=ndmi
    )


def _make_series(n=48, base_ndvi=0.32, base_ndmi=0.12):
    """Synthetic 48-month series (Jan 2021 – Dec 2024)."""
    import math
    obs = []
    for i in range(n):
        month = (i % 12) + 1
        year = 2021 + i // 12
        # Simple seasonal
        ndvi = base_ndvi + 0.12 * math.sin(2 * math.pi * (month - 4) / 12)
        ndmi = base_ndmi + 0.05 * math.sin(2 * math.pi * (month - 4) / 12)
        obs.append(_make_obs(year, month, max(0.05, ndvi), max(0.0, ndmi)))
    return obs


# ── Zone simulation tests ──────────────────────────────────────────────────

class TestSimulateZones:
    def test_returns_three_zones(self):
        obs = _make_series()
        scm = SpatialCausalityAnalyzer(human_pressure=0.31)
        zones = scm.simulate_zones(obs)
        assert set(zones.keys()) == {"core", "near", "landscape"}

    def test_each_zone_has_same_length(self):
        obs = _make_series(n=48)
        zones = SpatialCausalityAnalyzer(0.31).simulate_zones(obs)
        lengths = {k: len(v) for k, v in zones.items()}
        assert len(set(lengths.values())) == 1  # all equal

    def test_landscape_ndvi_above_core(self):
        obs = _make_series()
        zones = SpatialCausalityAnalyzer(0.60).simulate_zones(obs)
        core_mean = sum(o.ndvi for o in zones["core"]) / len(zones["core"])
        land_mean = sum(o.ndvi for o in zones["landscape"]) / len(zones["landscape"])
        assert land_mean > core_mean

    def test_zero_pressure_all_zones_similar(self):
        obs = _make_series()
        zones = SpatialCausalityAnalyzer(0.0).simulate_zones(obs)
        core_mean = sum(o.ndvi for o in zones["core"]) / len(zones["core"])
        land_mean = sum(o.ndvi for o in zones["landscape"]) / len(zones["landscape"])
        # With HP=0, core should only differ by the landscape uplift factor
        assert abs(land_mean - core_mean) / land_mean < 0.04

    def test_high_pressure_strong_core_deficit(self):
        obs = _make_series()
        zones = SpatialCausalityAnalyzer(0.90).simulate_zones(obs)
        core_mean = sum(o.ndvi for o in zones["core"]) / len(zones["core"])
        land_mean = sum(o.ndvi for o in zones["landscape"]) / len(zones["landscape"])
        assert (land_mean - core_mean) / land_mean > 0.08

    def test_invalid_pressure_raises(self):
        with pytest.raises(ValueError, match="human_pressure"):
            SpatialCausalityAnalyzer(human_pressure=-0.1)

        with pytest.raises(ValueError, match="human_pressure"):
            SpatialCausalityAnalyzer(human_pressure=1.5)


# ── Analysis tests ─────────────────────────────────────────────────────────

class TestAnalysis:
    def _run_scm(self, hp, n=48):
        obs = _make_series(n=n)
        scm = SpatialCausalityAnalyzer(hp)
        zones = scm.simulate_zones(obs)
        return scm.analyse("test-asset", zones)

    def test_low_pressure_landscape_driven(self):
        result = self._run_scm(hp=0.00)
        assert result.classification == "LANDSCAPE_DRIVEN"

    def test_result_has_three_zones(self):
        result = self._run_scm(hp=0.31)
        assert set(result.zones.keys()) == {"core", "near", "landscape"}

    def test_sig_in_range(self):
        result = self._run_scm(hp=0.50)
        assert 0.0 <= result.gradient.spatial_impact_gradient <= 1.0

    def test_correlation_in_range(self):
        result = self._run_scm(hp=0.31)
        assert -1.0 <= result.gradient.cross_zone_correlation <= 1.0

    def test_confidence_is_valid(self):
        result = self._run_scm(hp=0.31)
        assert result.confidence in {"HIGH", "MODERATE", "LOW"}

    def test_classification_is_valid(self):
        for hp in [0.0, 0.31, 0.60, 0.90]:
            result = self._run_scm(hp=hp)
            assert result.classification in {
                "LOCALIZED_IMPACT", "LANDSCAPE_DRIVEN", "MIXED"
            }

    def test_plain_language_not_empty(self):
        result = self._run_scm(hp=0.31)
        assert len(result.plain_language) > 50

    def test_management_not_empty(self):
        result = self._run_scm(hp=0.31)
        assert len(result.management_implication) > 20

    def test_requires_all_three_zones(self):
        obs = _make_series()
        scm = SpatialCausalityAnalyzer(0.31)
        zones = scm.simulate_zones(obs)
        del zones["landscape"]
        with pytest.raises(ValueError, match="zone_observations"):
            scm.analyse("test", zones)


# ── Zone signal tests ──────────────────────────────────────────────────────

class TestZoneSignalStructure:
    def test_zone_radii_correct(self):
        obs = _make_series()
        scm = SpatialCausalityAnalyzer(0.31)
        zones = scm.simulate_zones(obs)
        result = scm.analyse("test", zones)
        assert result.zones["core"].inner_radius_m == 0
        assert result.zones["core"].outer_radius_m == CORE_OUTER_M
        assert result.zones["near"].inner_radius_m == CORE_OUTER_M
        assert result.zones["near"].outer_radius_m == NEAR_OUTER_M
        assert result.zones["landscape"].inner_radius_m == NEAR_OUTER_M
        assert result.zones["landscape"].outer_radius_m == LANDSCAPE_OUTER_M

    def test_zone_ndvi_in_range(self):
        obs = _make_series()
        scm = SpatialCausalityAnalyzer(0.60)
        zones = scm.simulate_zones(obs)
        result = scm.analyse("test", zones)
        for zs in result.zones.values():
            assert 0.0 <= zs.mean_ndvi <= 1.0


# ── Gradient / SIG tests ───────────────────────────────────────────────────

class TestGradient:
    def test_sig_higher_for_higher_pressure(self):
        obs = _make_series()
        scm_lo = SpatialCausalityAnalyzer(0.10)
        scm_hi = SpatialCausalityAnalyzer(0.80)

        def get_sig(scm):
            zones = scm.simulate_zones(obs)
            result = scm.analyse("test", zones)
            return result.gradient.spatial_impact_gradient

        assert get_sig(scm_hi) > get_sig(scm_lo)

    def test_core_landscape_delta_negative_when_pressure_present(self):
        obs = _make_series()
        scm = SpatialCausalityAnalyzer(0.50)
        zones = scm.simulate_zones(obs)
        result = scm.analyse("test", zones)
        assert result.gradient.core_landscape_delta < 0


# ── Pearson helper tests ───────────────────────────────────────────────────

class TestPearson:
    def test_identical_series_r_one(self):
        x = [0.1 * i for i in range(20)]
        assert abs(_pearson(x, x) - 1.0) < 1e-6

    def test_opposite_series_r_neg_one(self):
        x = [float(i) for i in range(20)]
        y = [float(20 - i) for i in range(20)]
        assert _pearson(x, y) < -0.95

    def test_constant_series_returns_zero(self):
        x = [0.5] * 20
        y = [0.3 + 0.01 * i for i in range(20)]
        assert _pearson(x, y) == 0.0

    def test_short_series_returns_zero(self):
        assert _pearson([0.3, 0.4], [0.3, 0.4]) == 0.0
