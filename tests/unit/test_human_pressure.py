from __future__ import annotations

import math

import pytest

from src.risk_engine.human_pressure import (
    GeoProximityFactors,
    compute_geo_human_pressure,
    compute_poi_density,
    compute_road_accessibility,
    compute_settlement_proximity,
    compute_slope_accessibility,
    compute_trail_connectivity,
)


# ── Individual factor tests ────────────────────────────────────────────────

class TestRoadAccessibility:
    def test_at_road_edge(self):
        assert compute_road_accessibility(0.0) == 1.0

    def test_decay_at_1km(self):
        result = compute_road_accessibility(1.0)
        expected = math.exp(-1.5)
        assert abs(result - expected) < 1e-10

    def test_high_distance_near_zero(self):
        assert compute_road_accessibility(10.0) < 0.05

    def test_negative_distance_clamped(self):
        # Negative distance treated as 0 — returns 1.0
        assert compute_road_accessibility(-1.0) == 1.0

    def test_monotone_decreasing(self):
        assert compute_road_accessibility(0.5) > compute_road_accessibility(1.5) \
            > compute_road_accessibility(3.0)


class TestSettlementProximity:
    def test_at_settlement_edge(self):
        assert compute_settlement_proximity(0.0) == 1.0

    def test_decay_at_5km(self):
        result = compute_settlement_proximity(5.0)
        expected = math.exp(-0.4 * 5.0)
        assert abs(result - expected) < 1e-10

    def test_monotone_decreasing(self):
        assert (compute_settlement_proximity(1.0)
                > compute_settlement_proximity(3.0)
                > compute_settlement_proximity(8.0))


class TestPoiDensity:
    def test_zero_pois(self):
        assert compute_poi_density(0) == 0.0

    def test_saturated_at_threshold(self):
        assert compute_poi_density(15) == 1.0

    def test_above_threshold_clamped(self):
        assert compute_poi_density(100) == 1.0

    def test_partial_density(self):
        result = compute_poi_density(5)
        assert abs(result - 5 / 15) < 1e-10


class TestTrailConnectivity:
    def test_isolated_trail(self):
        assert compute_trail_connectivity(0.0) == 0.0

    def test_saturated_at_threshold(self):
        assert compute_trail_connectivity(8.0) == 1.0

    def test_above_threshold_clamped(self):
        assert compute_trail_connectivity(20.0) == 1.0

    def test_partial_connectivity(self):
        result = compute_trail_connectivity(4.0)
        assert abs(result - 0.5) < 1e-10


class TestSlopeAccessibility:
    def test_flat_terrain(self):
        assert compute_slope_accessibility(0.0) == 1.0

    def test_at_max_slope(self):
        assert compute_slope_accessibility(30.0) == 0.0

    def test_above_max_clamped(self):
        assert compute_slope_accessibility(45.0) == 0.0

    def test_moderate_slope(self):
        result = compute_slope_accessibility(15.0)
        assert abs(result - 0.5) < 1e-10


# ── GeoProximityFactors ────────────────────────────────────────────────────

class TestGeoProximityFactors:
    MASATRIGO_CONTEXT = {
        "geo_proximity": {
            "road_km": 0.8,
            "settlement_km": 4.5,
            "poi_count_5km": 4,
            "trail_network_km": 2.8,
            "mean_slope_deg": 7.5,
        }
    }

    def test_from_metadata_valid(self):
        factors = GeoProximityFactors.from_metadata(self.MASATRIGO_CONTEXT)
        assert factors is not None
        assert factors.road_km == 0.8
        assert factors.poi_count_5km == 4

    def test_from_metadata_missing_key_returns_none(self):
        assert GeoProximityFactors.from_metadata({}) is None
        assert GeoProximityFactors.from_metadata({"other_key": 1}) is None

    def test_from_metadata_incomplete_returns_none(self):
        incomplete = {"geo_proximity": {"road_km": 0.8}}  # missing required keys
        assert GeoProximityFactors.from_metadata(incomplete) is None

    def test_masatrigo_pressure_in_range(self):
        factors = GeoProximityFactors.from_metadata(self.MASATRIGO_CONTEXT)
        result = compute_geo_human_pressure(factors)
        assert 0.0 < result < 1.0

    def test_masatrigo_pressure_is_low_moderate(self):
        # Rural trail in Extremadura should yield low-moderate pressure (< 0.50)
        factors = GeoProximityFactors.from_metadata(self.MASATRIGO_CONTEXT)
        result = compute_geo_human_pressure(factors)
        assert result < 0.50, f"Expected low-moderate pressure, got {result:.3f}"


# ── Combined proxy test ────────────────────────────────────────────────────

class TestCombinedProxy:
    def test_road_adjacent_urban_site_high_pressure(self):
        factors = GeoProximityFactors(
            road_km=0.05,
            settlement_km=0.5,
            poi_count_5km=20,
            trail_network_km=10.0,
            mean_slope_deg=3.0,
        )
        assert compute_geo_human_pressure(factors) > 0.70

    def test_remote_steep_site_low_pressure(self):
        factors = GeoProximityFactors(
            road_km=5.0,
            settlement_km=15.0,
            poi_count_5km=0,
            trail_network_km=0.0,
            mean_slope_deg=25.0,
        )
        assert compute_geo_human_pressure(factors) < 0.15

    def test_pressure_output_in_unit_range(self):
        for road, settle, pois, trail, slope in [
            (0.1, 0.2, 30, 12.0, 2.0),
            (10.0, 20.0, 0, 0.0, 35.0),
            (1.5, 3.0, 7, 4.0, 12.0),
        ]:
            factors = GeoProximityFactors(
                road_km=road, settlement_km=settle,
                poi_count_5km=pois, trail_network_km=trail,
                mean_slope_deg=slope,
            )
            result = compute_geo_human_pressure(factors)
            assert 0.0 <= result <= 1.0, f"Out of range: {result}"
