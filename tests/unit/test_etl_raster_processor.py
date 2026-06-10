"""Unit tests for etl_raster_processor (STAC / COG edition).

All STAC catalogue calls and rasterio file I/O are mocked so the suite runs
fully offline without any cloud credentials or local raster files.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from affine import Affine
from pyproj import CRS  # pyproj bundles its own PROJ data — avoids PG/PostGIS PROJ conflict
from rasterio.enums import Resampling

from etl_raster_processor import (
    bbox_to_native_crs,
    compute_normalised_index,
    read_cog_window,
    resolve_asset_href,
    search_best_item,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_stac_item(cloud_pct: float, asset_keys: list[str]) -> MagicMock:
    """Build a minimal mock STAC Item."""
    item = MagicMock()
    item.id = f"S2_MOCK_{int(cloud_pct):02d}"
    item.datetime = "2023-08-15T00:00:00Z"
    item.properties = {"eo:cloud_cover": cloud_pct}
    item.assets = {
        key: SimpleNamespace(href=f"https://example.com/{key}.tif")
        for key in asset_keys
    }
    return item


def _make_rasterio_ds(shape: tuple[int, int] = (100, 120)) -> MagicMock:
    """Build a minimal mock rasterio DatasetReader."""
    h, w = shape
    ds = MagicMock()
    ds.crs = CRS.from_epsg(32630)
    ds.transform = Affine(10.0, 0.0, 450000.0, 0.0, -10.0, 4560000.0)
    # read() returns a uint16 array matching out_shape when provided
    ds.read = MagicMock(
        side_effect=lambda band, window=None, out_shape=None, resampling=None: (
            np.ones(out_shape[1:], dtype=np.uint16) * 1000
            if out_shape is not None
            else np.ones((h, w), dtype=np.uint16) * 1000
        )
    )
    # window_bounds returns geographic bounds for the mock window
    return ds


# ── bbox_to_native_crs ───────────────────────────────────────────────────────

class TestBboxToNativeCrs:
    def test_identity_roundtrip(self):
        """Reprojecting from WGS84 to WGS84 must return the original coords."""
        crs = CRS.from_epsg(4326)
        bbox = (-3.65, 41.05, -3.30, 41.20)
        xmin, ymin, xmax, ymax = bbox_to_native_crs(bbox, crs)
        assert abs(xmin - bbox[0]) < 1e-6
        assert abs(ymin - bbox[1]) < 1e-6
        assert abs(xmax - bbox[2]) < 1e-6
        assert abs(ymax - bbox[3]) < 1e-6

    def test_utm_easting_range(self):
        """Reprojected UTM30N x-coords for Sierra del Rincón must be ~400–450 km."""
        crs = CRS.from_epsg(32630)
        bbox = (-3.65, 41.05, -3.30, 41.20)
        xmin, ymin, xmax, ymax = bbox_to_native_crs(bbox, crs)
        assert 380_000 < xmin < 450_000
        assert xmax > xmin

    def test_ordering_preserved(self):
        """min coords must remain less than max coords after reprojection."""
        crs = CRS.from_epsg(32630)
        bbox = (-3.65, 41.05, -3.30, 41.20)
        xmin, ymin, xmax, ymax = bbox_to_native_crs(bbox, crs)
        assert xmin < xmax
        assert ymin < ymax


# ── compute_normalised_index ─────────────────────────────────────────────────

class TestComputeNormalisedIndex:
    def test_known_value(self):
        a = np.array([[0.8]], dtype=np.float32)
        b = np.array([[0.2]], dtype=np.float32)
        result = compute_normalised_index(a, b)
        assert abs(float(result[0, 0]) - 0.6) < 1e-6

    def test_zero_denominator_returns_zero(self):
        a = np.zeros((3, 3), dtype=np.float32)
        b = np.zeros((3, 3), dtype=np.float32)
        result = compute_normalised_index(a, b)
        np.testing.assert_array_equal(result, 0.0)

    def test_output_dtype_is_float32(self):
        a = np.ones((4, 4), dtype=np.uint16) * 3000
        b = np.ones((4, 4), dtype=np.uint16) * 1000
        result = compute_normalised_index(a, b)
        assert result.dtype == np.float32

    def test_symmetry(self):
        """Swapping A and B must negate the result."""
        a = np.array([[3000.0]], dtype=np.float32)
        b = np.array([[1000.0]], dtype=np.float32)
        pos = compute_normalised_index(a, b)
        neg = compute_normalised_index(b, a)
        np.testing.assert_allclose(pos, -neg, atol=1e-6)

    def test_bounds_always_in_minus_one_to_one(self):
        rng = np.random.default_rng(42)
        a = rng.integers(0, 10000, size=(50, 50)).astype(np.float32)
        b = rng.integers(0, 10000, size=(50, 50)).astype(np.float32)
        result = compute_normalised_index(a, b)
        assert result.min() >= -1.0
        assert result.max() <= 1.0


# ── resolve_asset_href ───────────────────────────────────────────────────────

class TestResolveAssetHref:
    def test_first_key_wins(self):
        item = _make_stac_item(5.0, ["red", "B04"])
        href = resolve_asset_href(item, "red", "B04")
        assert href == "https://example.com/red.tif"

    def test_fallback_key_used(self):
        item = _make_stac_item(5.0, ["B04"])
        href = resolve_asset_href(item, "red", "B04")
        assert href == "https://example.com/B04.tif"

    def test_missing_key_raises_key_error(self):
        item = _make_stac_item(5.0, ["blue"])
        with pytest.raises(KeyError, match="red"):
            resolve_asset_href(item, "red", "B04")

    def test_error_lists_available_assets(self):
        item = _make_stac_item(5.0, ["blue", "green"])
        with pytest.raises(KeyError, match="blue"):
            resolve_asset_href(item, "red")


# ── search_best_item ─────────────────────────────────────────────────────────

class TestSearchBestItem:
    def _mock_catalog(self, items: list) -> MagicMock:
        search = MagicMock()
        search.items.return_value = items
        catalog = MagicMock()
        catalog.search.return_value = search
        return catalog

    def test_returns_least_cloudy_item(self):
        items = [
            _make_stac_item(15.0, ["red"]),
            _make_stac_item(3.0,  ["red"]),
            _make_stac_item(8.0,  ["red"]),
        ]
        catalog = self._mock_catalog(items)
        with patch("etl_raster_processor.Client") as MockClient:
            MockClient.open.return_value = catalog
            result = search_best_item((-3.65, 41.05, -3.30, 41.20), "2023-07-01/2023-09-30", 20.0)
        assert result.properties["eo:cloud_cover"] == 3.0

    def test_no_items_raises_runtime_error(self):
        catalog = self._mock_catalog([])
        with patch("etl_raster_processor.Client") as MockClient:
            MockClient.open.return_value = catalog
            with pytest.raises(RuntimeError, match="No S2 L2A scene found"):
                search_best_item((-3.65, 41.05, -3.30, 41.20), "2023-07-01/2023-09-30", 20.0)

    def test_search_called_with_correct_bbox(self):
        items = [_make_stac_item(5.0, ["red"])]
        catalog = self._mock_catalog(items)
        bbox = (-3.65, 41.05, -3.30, 41.20)
        with patch("etl_raster_processor.Client") as MockClient:
            MockClient.open.return_value = catalog
            search_best_item(bbox, "2023-07-01/2023-09-30", 20.0)
        call_kwargs = catalog.search.call_args.kwargs
        assert call_kwargs["bbox"] == list(bbox)


# ── read_cog_window ──────────────────────────────────────────────────────────

class TestReadCogWindow:
    _BBOX = (-3.65, 41.05, -3.30, 41.20)
    _HREF = "https://example.com/B04.tif"

    def _patch_rasterio(self, ds: MagicMock):
        """Context-manager patch for rasterio.open used inside read_cog_window."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ds)
        ctx.__exit__ = MagicMock(return_value=False)
        return patch("rasterio.open", return_value=ctx)

    def test_returns_tuple_of_three(self):
        ds = _make_rasterio_ds((100, 120))
        # window_from_bounds and window_bounds need a real-ish window
        with patch("etl_raster_processor.window_from_bounds") as mock_wfb, \
             patch("etl_raster_processor.window_bounds", return_value=(450000, 4550000, 451200, 4551000)), \
             self._patch_rasterio(ds):
            mock_wfb.return_value = MagicMock()
            arr, transform, crs = read_cog_window(self._HREF, self._BBOX)
        assert isinstance(arr, np.ndarray)
        assert arr.ndim == 2
        assert transform is not None
        assert crs is not None

    def test_out_shape_passed_to_read(self):
        ds = _make_rasterio_ds((50, 60))
        with patch("etl_raster_processor.window_from_bounds") as mock_wfb, \
             patch("etl_raster_processor.window_bounds", return_value=(450000, 4550000, 451200, 4551000)), \
             self._patch_rasterio(ds):
            mock_wfb.return_value = MagicMock()
            arr, _, _ = read_cog_window(self._HREF, self._BBOX, out_shape=(100, 120))
        # The mock returns shape matching out_shape when provided
        assert arr.shape == (100, 120)

    def test_native_resolution_when_no_out_shape(self):
        ds = _make_rasterio_ds((100, 120))
        with patch("etl_raster_processor.window_from_bounds") as mock_wfb, \
             patch("etl_raster_processor.window_bounds", return_value=(450000, 4550000, 451200, 4551000)), \
             self._patch_rasterio(ds):
            mock_wfb.return_value = MagicMock()
            arr, _, _ = read_cog_window(self._HREF, self._BBOX)
        assert arr.shape == (100, 120)
