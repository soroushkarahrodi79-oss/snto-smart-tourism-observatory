"""
Integration test — SCM Spatial Impact Gradient computation.

Builds a synthetic NDVI GeoTIFF in EPSG:25830 where the core zone
(0–50 m buffer around a point) is deliberately degraded (NDVI = 0.20)
and the landscape zone (annular ring 200–1000 m) is healthy (NDVI = 0.70).
Expected SIG ≈ (0.70 − 0.20) / 0.70 ≈ 0.71, well above the 0.15 threshold.

No database connection required — tests the raster extraction and SIG
classification logic in isolation using in-memory fixtures.
"""
from __future__ import annotations

import numpy as np
import geopandas as gpd
import pyproj
import pytest
import rasterio
import rasterio.env
from rasterio.transform import from_bounds
from shapely.geometry import Point

from run_scm_operational import (
    BUFFER_CRS,
    CORE_OUTER_M,
    LANDSCAPE_OUTER_M,
    NEAR_OUTER_M,
    _classify_sig,
    _extract_zone_ndvi,
    _sig,
)

# ── Synthetic raster parameters ───────────────────────────────────────────────
# 300 × 300 pixels at 10 m → 3 km × 3 km tile placed in UTM 30N.
# The center sits 1 500 m from every edge, so the full 1 000 m landscape ring
# is well inside the raster and never truncated.
_RES     = 10.0          # metres per pixel
_WIDTH   = 300
_HEIGHT  = 300
_LEFT    = 500_000.0     # UTM easting  — Sierra del Rincón area
_TOP     = 4_550_000.0   # UTM northing

_CX = _LEFT + (_WIDTH  / 2) * _RES   # 501 500 m E
_CY = _TOP  - (_HEIGHT / 2) * _RES   # 4 548 500 m N

_NDVI_LANDSCAPE = 0.70   # healthy background
_NDVI_CORE      = 0.20   # degraded trail corridor


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def synthetic_raster(tmp_path_factory):
    """
    Write a one-band NDVI GeoTIFF (EPSG:25830) to a temporary directory.

    Pixel values:
      NDVI_CORE      (0.20) inside a circle of radius CORE_OUTER_M (50 m)
      NDVI_LANDSCAPE (0.70) everywhere else

    The raster has a single band so that _extract_zone_ndvi(band=1) works
    identically to how it operates on the real two-band seasonal rasters.
    """
    right  = _LEFT  + _WIDTH  * _RES
    bottom = _TOP   - _HEIGHT * _RES
    transform = from_bounds(_LEFT, bottom, right, _TOP, _WIDTH, _HEIGHT)

    data = np.full((_HEIGHT, _WIDTH), _NDVI_LANDSCAPE, dtype=np.float32)

    # Mark pixels whose centre falls within CORE_OUTER_M of the trail point.
    rows_idx, cols_idx = np.indices((_HEIGHT, _WIDTH))
    px_x = _LEFT + (cols_idx + 0.5) * _RES
    px_y = _TOP  - (rows_idx + 0.5) * _RES
    dist = np.sqrt((px_x - _CX) ** 2 + (px_y - _CY) ** 2)
    data[dist <= CORE_OUTER_M] = _NDVI_CORE

    # Use rasterio.Env to pin PROJ_DATA to pyproj's bundled database.
    # On Windows, PostgreSQL adds its own (older) proj.db to the PROJ search
    # path, causing "DATABASE.LAYOUT.VERSION.MINOR" mismatch errors when
    # rasterio tries to look up EPSG codes. Overriding PROJ_DATA here routes
    # the GDAL/PROJ lookup to pyproj's compatible database for this scope only.
    proj_data_dir = pyproj.datadir.get_data_dir()

    path = tmp_path_factory.mktemp("rasters") / "ndvi_localized.tif"
    with rasterio.env.Env(PROJ_DATA=proj_data_dir):
        with rasterio.open(
            path, "w",
            driver="GTiff",
            height=_HEIGHT, width=_WIDTH,
            count=1,
            dtype="float32",
            crs=BUFFER_CRS,
            transform=transform,
            nodata=-9999.0,
        ) as dst:
            dst.write(data, 1)

    return path


@pytest.fixture(scope="module")
def zone_gdfs():
    """
    Return (core_gdf, landscape_gdf) built from the synthetic trail point.

    core      — simple disk buffer 0–CORE_OUTER_M m.
    landscape — annular ring NEAR_OUTER_M–LANDSCAPE_OUTER_M m.
                The inner hole is necessary so that only the regional
                background pixels (200–1000 m) feed the SIG denominator,
                keeping the near-field transition zone (50–200 m) out of
                both measurements.
    """
    pt = Point(_CX, _CY)

    core_geom      = pt.buffer(CORE_OUTER_M)
    landscape_geom = pt.buffer(LANDSCAPE_OUTER_M).difference(pt.buffer(NEAR_OUTER_M))

    core_gdf      = gpd.GeoDataFrame({"id": [1]}, geometry=[core_geom],      crs=BUFFER_CRS)
    landscape_gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[landscape_geom], crs=BUFFER_CRS)

    return core_gdf, landscape_gdf


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_zonal_extraction_returns_expected_ndvi(synthetic_raster, zone_gdfs):
    """
    Core zone should average near NDVI_CORE; landscape zone near NDVI_LANDSCAPE.
    Allow ±10 % tolerance to absorb boundary pixels.
    """
    core_gdf, landscape_gdf = zone_gdfs

    core_means      = _extract_zone_ndvi(core_gdf,      synthetic_raster, "core")
    landscape_means = _extract_zone_ndvi(landscape_gdf, synthetic_raster, "landscape")

    assert core_means[0]      is not None, "Core zone returned None — no raster overlap"
    assert landscape_means[0] is not None, "Landscape zone returned None — no raster overlap"

    assert abs(core_means[0]      - _NDVI_CORE)      < 0.10, (
        f"Core NDVI {core_means[0]:.4f} too far from expected {_NDVI_CORE}"
    )
    assert abs(landscape_means[0] - _NDVI_LANDSCAPE) < 0.10, (
        f"Landscape NDVI {landscape_means[0]:.4f} too far from expected {_NDVI_LANDSCAPE}"
    )


def test_sig_exceeds_localized_threshold(synthetic_raster, zone_gdfs):
    """
    With core NDVI deliberately below landscape NDVI, SIG must exceed 0.15.
    """
    core_gdf, landscape_gdf = zone_gdfs

    core_ndvi      = _extract_zone_ndvi(core_gdf,      synthetic_raster, "core")
    landscape_ndvi = _extract_zone_ndvi(landscape_gdf, synthetic_raster, "landscape")

    sig_val = _sig(landscape_ndvi[0], core_ndvi[0])

    assert sig_val is not None
    assert sig_val > 0.15, f"SIG = {sig_val:.4f}, expected > 0.15"


def test_classification_is_localized_impact(synthetic_raster, zone_gdfs):
    """
    End-to-end: synthetic raster with degraded core → LOCALIZED_IMPACT.
    This is the primary integration assertion for the SCM pipeline.
    """
    core_gdf, landscape_gdf = zone_gdfs

    core_ndvi      = _extract_zone_ndvi(core_gdf,      synthetic_raster, "core")
    landscape_ndvi = _extract_zone_ndvi(landscape_gdf, synthetic_raster, "landscape")

    sig_val        = _sig(landscape_ndvi[0], core_ndvi[0])
    classification = _classify_sig(sig_val)

    assert classification == "LOCALIZED_IMPACT", (
        f"Expected LOCALIZED_IMPACT, got {classification!r}  (SIG = {sig_val})"
    )


# ── Unit helpers (no raster needed) ──────────────────────────────────────────

def test_sig_formula_symmetric_degradation():
    """Known values: landscape=0.7, core=0.2 → SIG ≈ 0.714."""
    result = _sig(ndvi_landscape=0.70, ndvi_core=0.20)
    assert result == pytest.approx(0.714, abs=0.001)


def test_sig_none_when_core_missing():
    assert _sig(ndvi_landscape=0.70, ndvi_core=None) is None


def test_sig_none_when_landscape_missing():
    assert _sig(ndvi_landscape=None, ndvi_core=0.20) is None


def test_landscape_driven_when_zones_equal():
    """Equal zones → SIG = 0 → LANDSCAPE_DRIVEN."""
    sig_val = _sig(ndvi_landscape=0.60, ndvi_core=0.60)
    assert _classify_sig(sig_val) == "LANDSCAPE_DRIVEN"


def test_mixed_between_thresholds():
    """SIG = 0.10 is between 0.07 and 0.15 → MIXED."""
    assert _classify_sig(0.10) == "MIXED"
