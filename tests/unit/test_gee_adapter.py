"""Unit tests for GEEAdapter (STAC/COG-free, fully mocked).

All GEE API calls are mocked at the `ee` module level so the suite runs
offline without earthengine-api installed.
"""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest

# ── Minimal ee stub so gee_adapter.py can be imported without the SDK ─────────

def _make_ee_stub() -> types.ModuleType:
    ee = types.ModuleType("ee")
    ee.ServiceAccountCredentials = MagicMock()
    ee.Initialize = MagicMock()
    ee.Date = MagicMock()
    ee.Reducer = MagicMock()
    ee.ImageCollection = MagicMock()
    ee.Geometry = MagicMock()
    return ee

# Inject the stub before importing the adapter
_ee_stub = _make_ee_stub()
sys.modules.setdefault("ee", _ee_stub)

from src.assets.models import AssetObservation, AssetType, GeoJSONGeometry, GeometryType, TourismAsset  # noqa: E402
from src.ingestion.gee_adapter import GEEAdapter, _gee_retry  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _trail_asset(asset_id: str = "trail_01") -> TourismAsset:
    return TourismAsset(
        asset_id=asset_id,
        name="Sendero Test",
        asset_type=AssetType.TRAIL,
        geometry=GeoJSONGeometry(
            type=GeometryType.LINESTRING,
            coordinates=[[-3.55, 41.10], [-3.52, 41.12]],
        ),
        region="Sierra del Rincón",
    )


def _make_adapter(project: str = "test-project") -> GEEAdapter:
    adapter = GEEAdapter(project_id=project)
    adapter._initialized = True  # skip ee.Initialize() in unit tests
    return adapter


def _raw_stats(ndvi: float = 0.45, ndmi: float = 0.15, evi: float = 0.30) -> dict:
    """Simulate the dict returned by GEE reduceRegion().getInfo()."""
    return {
        "NDVI_mean": ndvi, "NDVI_median": ndvi, "NDVI_p25": ndvi - 0.05,
        "NDVI_p75": ndvi + 0.05, "NDVI_stdDev": 0.03, "NDVI_count": 800,
        "NDMI_mean": ndmi, "NDMI_median": ndmi, "NDMI_p25": ndmi - 0.03,
        "NDMI_p75": ndmi + 0.03, "NDMI_stdDev": 0.02, "NDMI_count": 800,
        "EVI_mean": evi,  "EVI_median": evi,  "EVI_p25": evi - 0.04,
        "EVI_p75": evi + 0.04,  "EVI_stdDev": 0.025, "EVI_count": 800,
    }


# ── _gee_retry tests ──────────────────────────────────────────────────────────

class TestGeeRetry:
    def test_succeeds_on_first_try(self):
        fn = MagicMock(return_value=42)
        assert _gee_retry(fn) == 42
        fn.assert_called_once()

    def test_retries_and_succeeds(self):
        fn = MagicMock(side_effect=[RuntimeError("quota"), RuntimeError("timeout"), 99])
        with patch("src.ingestion.gee_adapter.time.sleep"):
            result = _gee_retry(fn)
        assert result == 99
        assert fn.call_count == 3

    def test_raises_after_all_retries(self):
        fn = MagicMock(side_effect=RuntimeError("persistent"))
        with patch("src.ingestion.gee_adapter.time.sleep"), \
             pytest.raises(RuntimeError, match="persistent"):
            _gee_retry(fn)

    def test_exponential_backoff_delays(self):
        fn = MagicMock(side_effect=[RuntimeError(), RuntimeError(), "ok"])
        sleep_calls = []
        with patch("src.ingestion.gee_adapter.time.sleep", side_effect=sleep_calls.append):
            _gee_retry(fn)
        assert len(sleep_calls) == 2
        assert sleep_calls[1] > sleep_calls[0]   # delay doubles


# ── GEEAdapter._fetch_monthly_observation ────────────────────────────────────

class TestFetchMonthlyObservation:
    def _run(self, raw: dict | None, image_count: int = 5, area_m2: float = 50_000.0):
        adapter = _make_adapter()
        asset = _trail_asset()

        # Mock GEE objects
        ee_geom = MagicMock()
        collection = MagicMock()

        monthly = MagicMock()
        collection.filterDate.return_value = monthly

        # size().getInfo() → image_count
        monthly.size.return_value.getInfo.return_value = image_count

        if raw is not None:
            composite = MagicMock()
            monthly.median.return_value = composite
            reducer_chain = MagicMock()
            # Reducer chain mock
            _ee_stub.Reducer.mean.return_value = MagicMock(
                combine=MagicMock(return_value=MagicMock(
                    combine=MagicMock(return_value=MagicMock(
                        combine=MagicMock(return_value=MagicMock(
                            combine=MagicMock(return_value=reducer_chain)
                        ))
                    ))
                ))
            )
            composite.select.return_value.reduceRegion.return_value.getInfo.return_value = raw
            ee_geom.area.return_value.getInfo.return_value = area_m2

        return adapter._fetch_monthly_observation(
            asset=asset,
            collection=collection,
            ee_geom=ee_geom,
            year=2023,
            month=7,
        )

    def test_returns_none_when_no_images(self):
        result = self._run(raw=None, image_count=0)
        assert result is None

    def test_returns_observation_with_all_indices(self):
        raw = _raw_stats(ndvi=0.45, ndmi=0.18, evi=0.32)
        obs = self._run(raw=raw)
        assert obs is not None
        assert isinstance(obs, AssetObservation)
        assert abs(obs.ndvi - 0.45) < 1e-9
        assert abs(obs.ndmi - 0.18) < 1e-9
        assert obs.evi is not None
        assert abs(obs.evi - 0.32) < 1e-9

    def test_evi_field_populated(self):
        raw = _raw_stats(evi=0.40)
        obs = self._run(raw=raw)
        assert obs is not None
        assert obs.evi == pytest.approx(0.40, abs=1e-9)

    def test_data_source_is_gee(self):
        obs = self._run(raw=_raw_stats())
        assert obs is not None
        assert "GEE" in obs.data_source

    def test_returns_none_when_ndvi_missing_from_raw(self):
        raw = {"NDMI_mean": 0.10}   # NDVI absent
        obs = self._run(raw=raw)
        assert obs is None

    def test_returns_none_when_valid_pixel_pct_too_low(self):
        # area_m2 = 1_000_000 → total_pixels = 10_000 at 10 m scale
        # NDVI_count = 800 → valid_pct = 0.08 < 0.30 → should be rejected
        raw = _raw_stats()
        raw["NDVI_count"] = 800
        obs = self._run(raw=raw, area_m2=1_000_000.0)
        assert obs is None

    def test_ndvi_stats_populated(self):
        obs = self._run(raw=_raw_stats())
        assert obs is not None
        assert obs.ndvi_stats is not None
        assert obs.ndvi_stats.pixel_count == 800


# ── GEEAdapter.fetch_multiyear_time_series ────────────────────────────────────

class TestFetchMultiyearTimeSeries:
    def test_returns_empty_for_no_years(self):
        adapter = _make_adapter()
        result = adapter.fetch_multiyear_time_series(_trail_asset(), years=[])
        assert result == []

    def test_observations_sorted_chronologically(self):
        adapter = _make_adapter()
        asset = _trail_asset()

        # Patch _build_masked_collection and _fetch_monthly_observation
        mock_obs_counter = [0]
        def fake_fetch(asset, collection, ee_geom, year, month):
            mock_obs_counter[0] += 1
            return AssetObservation(
                asset_id=asset.asset_id, year=year, month=month,
                ndvi=0.4, ndmi=0.1, data_source="mock",
            )

        with patch.object(adapter, "_build_masked_collection", return_value=MagicMock()), \
             patch.object(adapter, "_to_ee_geometry", return_value=MagicMock()), \
             patch.object(adapter, "_fetch_monthly_observation", side_effect=fake_fetch):
            result = adapter.fetch_multiyear_time_series(asset, years=[2022, 2021])

        # Must be sorted: 2021 before 2022
        years_months = [(o.year, o.month) for o in result]
        assert years_months == sorted(years_months)

    def test_none_months_are_excluded(self):
        adapter = _make_adapter()
        asset = _trail_asset()

        call_count = [0]
        def fake_fetch(asset, collection, ee_geom, year, month):
            call_count[0] += 1
            # Only return observations for even months
            if month % 2 == 0:
                return AssetObservation(
                    asset_id=asset.asset_id, year=year, month=month,
                    ndvi=0.4, ndmi=0.1, data_source="mock",
                )
            return None

        with patch.object(adapter, "_build_masked_collection", return_value=MagicMock()), \
             patch.object(adapter, "_to_ee_geometry", return_value=MagicMock()), \
             patch.object(adapter, "_fetch_monthly_observation", side_effect=fake_fetch):
            result = adapter.fetch_multiyear_time_series(asset, years=[2023])

        assert call_count[0] == 12        # all months attempted
        assert len(result) == 6           # only even months returned


# ── run_pipeline_a_timeseries: analyse_trail ──────────────────────────────────

class TestAnalyseTrail:
    def _make_obs(self, n: int = 48) -> list[AssetObservation]:
        """Generate n synthetic observations with a mild declining trend."""
        import math
        obs = []
        for t in range(n):
            year, month = 2021 + t // 12, (t % 12) + 1
            ndvi = 0.50 - 0.001 * t + 0.05 * math.sin(2 * math.pi * t / 12)
            obs.append(AssetObservation(
                asset_id="t1", year=year, month=month,
                ndvi=round(ndvi, 4), ndmi=0.15, evi=0.30,
                data_source="mock",
            ))
        return obs

    def test_returns_dict_with_ehs(self):
        from run_pipeline_a_timeseries import analyse_trail
        asset = _trail_asset("t1")
        result = analyse_trail(asset, self._make_obs())
        assert "ehs" in result
        assert 0.0 <= result["ehs"] <= 100.0

    def test_mk_fields_present(self):
        from run_pipeline_a_timeseries import analyse_trail
        asset = _trail_asset("t1")
        result = analyse_trail(asset, self._make_obs())
        for field in ("mk_ndvi_direction", "mk_ndvi_slope", "mk_ndvi_p", "mk_ndvi_significant"):
            assert field in result

    def test_evi_reported_when_present(self):
        from run_pipeline_a_timeseries import analyse_trail
        asset = _trail_asset("t1")
        result = analyse_trail(asset, self._make_obs())
        assert result["mean_evi"] == pytest.approx(0.30, abs=0.01)

    def test_insufficient_observations_returns_error(self):
        from run_pipeline_a_timeseries import analyse_trail
        asset = _trail_asset("t1")
        obs = self._make_obs(3)   # only 3 — below the 4-observation minimum
        result = analyse_trail(asset, obs)
        assert result.get("error") == "insufficient_observations"

    def test_declining_trend_captured(self):
        from run_pipeline_a_timeseries import analyse_trail
        # Strong declining trend: NDVI drops 0.01/month for 48 months
        obs = []
        for t in range(48):
            yr, mo = 2021 + t // 12, (t % 12) + 1
            obs.append(AssetObservation(
                asset_id="t1", year=yr, month=mo,
                ndvi=round(0.70 - 0.01 * t, 4), ndmi=0.20,
                data_source="mock",
            ))
        result = analyse_trail(_trail_asset("t1"), obs)
        assert result["mk_ndvi_direction"] == "decreasing"
        assert result["mk_ndvi_significant"] is True
