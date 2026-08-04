"""Unit tests for the shared Sentinel-2 collection foundation (ADR-015).

Fully offline: Earth Engine objects are MagicMocks; no module imports ``ee`` and
no test contacts Earth Engine or needs credentials.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.integrations.earth_engine import collections as col
from src.integrations.earth_engine.collections import (
    S2_COLLECTION_ID,
    SCL_BAD_VALUES,
    add_ndvi,
    build_sentinel2_collection,
    mask_scl,
)

# ── mask_scl ──────────────────────────────────────────────────────────────────

class TestMaskScl:
    def test_selects_scl_band(self):
        img = MagicMock()
        mask_scl(img)
        img.select.assert_called_once_with("SCL")

    def test_excludes_all_bad_classes_in_order(self):
        img = MagicMock()
        mask_scl(img)
        scl = img.select.return_value
        neq_args = [c.args[0] for c in scl.neq.call_args_list]
        assert neq_args == [0, 1, 3, 8, 9, 10, 11]
        assert tuple(neq_args) == SCL_BAD_VALUES

    def test_returns_updatemask_result(self):
        img = MagicMock()
        out = mask_scl(img)
        img.updateMask.assert_called_once()
        assert out is img.updateMask.return_value


# ── add_ndvi ──────────────────────────────────────────────────────────────────

class TestAddNdvi:
    def test_normalized_difference_nir_red(self):
        img = MagicMock()
        add_ndvi(img)
        img.normalizedDifference.assert_called_once_with(["B8", "B4"])
        img.normalizedDifference.return_value.rename.assert_called_once_with("NDVI")

    def test_appends_band(self):
        img = MagicMock()
        out = add_ndvi(img)
        ndvi_band = img.normalizedDifference.return_value.rename.return_value
        img.addBands.assert_called_once_with(ndvi_band)
        assert out is img.addBands.return_value


# ── build_sentinel2_collection ────────────────────────────────────────────────

class TestBuildCollection:
    def _build(self, cloud=20):
        ee = MagicMock()
        geom = MagicMock()
        out = build_sentinel2_collection(
            ee_module=ee,
            geometry=geom,
            start_date="2024-06-01",
            end_date="2024-07-01",
            max_cloud_percentage=cloud,
        )
        return ee, geom, out

    def test_uses_harmonized_dataset(self):
        ee, _, _ = self._build()
        ee.ImageCollection.assert_called_once_with(S2_COLLECTION_ID)
        assert S2_COLLECTION_ID == "COPERNICUS/S2_SR_HARMONIZED"

    def test_filter_bounds(self):
        ee, geom, _ = self._build()
        ee.ImageCollection.return_value.filterBounds.assert_called_once_with(geom)

    def test_filter_date_end_exclusive_strings(self):
        ee, _, _ = self._build()
        fb = ee.ImageCollection.return_value.filterBounds.return_value
        fb.filterDate.assert_called_once_with("2024-06-01", "2024-07-01")

    def test_scene_cloud_threshold(self):
        ee, _, _ = self._build(cloud=35)
        ee.Filter.lte.assert_called_once_with("CLOUDY_PIXEL_PERCENTAGE", 35)
        fd = (
            ee.ImageCollection.return_value.filterBounds.return_value
            .filterDate.return_value
        )
        fd.filter.assert_called_once_with(ee.Filter.lte.return_value)

    def test_applies_scl_pixel_mask(self):
        ee, _, out = self._build()
        filt = (
            ee.ImageCollection.return_value.filterBounds.return_value
            .filterDate.return_value.filter.return_value
        )
        filt.map.assert_called_once_with(mask_scl)
        assert out is filt.map.return_value

    def test_retains_all_bands_no_select(self):
        ee, _, _ = self._build()
        # The builder must not narrow bands: true colour (B4/B3/B2) and NDVI
        # (B8/B4) must remain available downstream.
        assert "select" not in repr(ee.ImageCollection.return_value.mock_calls)

    def test_no_getinfo_during_construction(self):
        ee, _, _ = self._build()
        assert "getInfo" not in repr(ee.mock_calls)


# ── GEEAdapter now consumes the shared helpers (regression) ───────────────────

class TestAdapterUsesSharedHelpers:
    def test_adapter_shares_collection_constants(self):
        from src.ingestion import gee_adapter

        # The adapter imports the shared constants (one source of truth). The
        # interned collection id shows object identity; the numeric constants are
        # compared by value (float identity is implementation-fragile).
        assert gee_adapter._S2_COLLECTION is S2_COLLECTION_ID
        assert gee_adapter._SR_SCALE == col.SR_SCALE
        assert gee_adapter._MIN_VALID_PIX_PCT == col.MIN_VALID_PIXEL_FRACTION

    def test_no_duplicate_scl_list_in_adapter(self):
        from src.ingestion import gee_adapter

        # The legacy in-adapter SCL bad-class list / band constant are gone.
        assert not hasattr(gee_adapter, "_SCL_BAD_VALUES")
        assert not hasattr(gee_adapter, "_BAND_SCL")

    def test_cloud_mask_delegates_to_shared(self):
        from src.ingestion.gee_adapter import GEEAdapter

        img = MagicMock()
        with patch("src.ingestion.gee_adapter._shared_mask_scl") as m:
            GEEAdapter._cloud_mask_scl(img)
        m.assert_called_once_with(img)

    def test_indices_delegate_ndvi_to_shared(self):
        from src.ingestion.gee_adapter import GEEAdapter

        img = MagicMock()
        with patch("src.ingestion.gee_adapter._shared_add_ndvi") as m:
            GEEAdapter._compute_scaled_indices(img)
        # NDVI comes from the shared definition, not a re-implemented formula.
        m.assert_called_once_with(img)
