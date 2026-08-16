"""DEM reprojection utility (A-4 support, Backlog scripts/paper1/reproject_dem_to_utm.py).

Verifies the geographic->UTM reprojection is deterministic and that the
anisotropy it exists to fix (unequal real-world pixel size on lon vs lat axes
at PNSG's latitude) is actually removed.
"""
from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.paper1.reproject_dem_to_utm import reproject_dem


def _write_geographic_dem(path, *, ulx=-4.0, uly=41.0, res_deg=0.0002778, W=200, H=200):
    # A simple north-south ramp so aspect should point ~north after reprojection.
    yy, xx = np.mgrid[0:H, 0:W]
    elev = (1000.0 + (H - yy) * 2.0).astype("float32")
    transform = from_origin(ulx, uly, res_deg, res_deg)
    with rasterio.open(path, "w", driver="GTiff", height=H, width=W, count=1,
                       dtype="float32", crs="EPSG:4326", transform=transform) as ds:
        ds.write(elev, 1)


def test_reprojection_is_deterministic(tmp_path):
    src = tmp_path / "src.tif"
    _write_geographic_dem(src)
    dst_a = tmp_path / "a.tif"
    dst_b = tmp_path / "b.tif"
    reproject_dem(src, dst_a)
    reproject_dem(src, dst_b)
    assert dst_a.read_bytes() == dst_b.read_bytes()


def test_output_crs_and_nodata_are_metric_and_explicit(tmp_path):
    src = tmp_path / "src.tif"
    _write_geographic_dem(src)
    dst = tmp_path / "out.tif"
    info = reproject_dem(src, dst, dst_crs="EPSG:25830", resolution=30.0)
    assert info["crs"] == "EPSG:25830"
    with rasterio.open(dst) as ds:
        assert ds.crs.to_epsg() == 25830
        assert ds.nodata is not None and np.isnan(ds.nodata)
        # pixel size is now ~30 m on both axes (not degrees).
        assert abs(ds.res[0] - 30.0) < 1e-6
        assert abs(ds.res[1] - 30.0) < 1e-6


def test_corner_gaps_are_nan_not_zero(tmp_path):
    src = tmp_path / "src.tif"
    _write_geographic_dem(src)
    dst = tmp_path / "out.tif"
    reproject_dem(src, dst)
    with rasterio.open(dst) as ds:
        arr = ds.read(1)
        # A rotated-footprint reprojection of a rectangle always leaves some
        # nodata corners; they must be NaN, never a spurious 0 elevation.
        assert np.isnan(arr).any()
        assert not np.any(arr == 0.0)


def test_elevation_values_preserved_within_tolerance(tmp_path):
    src = tmp_path / "src.tif"
    _write_geographic_dem(src)
    dst = tmp_path / "out.tif"
    reproject_dem(src, dst)
    with rasterio.open(dst) as ds:
        arr = ds.read(1)
    valid = arr[~np.isnan(arr)]
    # Bilinear resampling to a different grid should stay within the source range.
    assert 990.0 <= float(valid.min()) <= 1010.0
    assert 990.0 <= float(valid.max()) <= 1410.0
