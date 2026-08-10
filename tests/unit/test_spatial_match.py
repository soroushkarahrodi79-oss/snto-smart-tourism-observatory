"""Plot ↔ satellite support-cell matching (Paper 1, Backlog B-04)."""
from __future__ import annotations

import json

import numpy as np
import pytest
import rasterio
from pyproj import Transformer
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from shapely.geometry import LineString

from src.validation import (
    CRSMismatch,
    GridMisalignment,
    InsufficientCoverage,
    SupportCell,
    cell_inside_footprint,
    cell_separation_m,
    check_pair_independence,
    control_clearance_ok,
    control_trail_clearance_m,
    extract_plot_value,
    find_cell_collisions,
    load_trail_network_utm,
    plot_stress_from_baselines,
    snap_to_support_grid,
)
from src.validation.spatial_match import _snap_xy

# EPSG:25830 → WGS84 to build lon/lat inputs from controlled UTM coordinates.
_TO_LL = Transformer.from_crs(25830, 4326, always_xy=True)

# A grid-aligned base point in PNSG-ish UTM (both multiples of 20 m).
_BASE_X, _BASE_Y = 420010.0, 4520010.0  # a 20 m cell centre


def _ll(x: float, y: float) -> tuple[float, float]:
    """(lon, lat) for an EPSG:25830 (x, y)."""
    lon, lat = _TO_LL.transform(x, y)
    return lon, lat


# ── snap_to_support_grid — determinism & grid math ──────────────────────────

def test_snap_xy_is_deterministic_and_centres_correctly():
    c = _snap_xy(420015.0, 4520003.0)  # inside the cell [420000,420020)×[4520000,4520020)
    assert c.centre_x == 420010.0
    assert c.centre_y == 4520010.0
    assert c.cell_size_m == 20.0
    assert c.epsg == 25830


def test_cell_id_is_stable_string():
    c = _snap_xy(_BASE_X, _BASE_Y)
    assert c.cell_id == f"25830:20:{c.col}:{c.row}"


def test_points_5m_apart_share_a_cell_25m_apart_do_not():
    # Acceptance: 5 m → same cell; 25 m → different cell. Via the real lon/lat API.
    a = snap_to_support_grid(*_ll(_BASE_X, _BASE_Y))
    near = snap_to_support_grid(*_ll(_BASE_X + 5.0, _BASE_Y))
    far = snap_to_support_grid(*_ll(_BASE_X + 25.0, _BASE_Y))
    assert a.cell_id == near.cell_id
    assert a.cell_id != far.cell_id


def test_cell_bounds_are_the_20m_footprint():
    c = _snap_xy(_BASE_X, _BASE_Y)
    left, bottom, right, top = c.bounds
    assert (right - left) == 20.0 and (top - bottom) == 20.0
    assert left == 420000.0 and top == 4520020.0


# ── SM-1 / SM-2 ─────────────────────────────────────────────────────────────

def test_sm1_adjacent_cells_not_independent():
    impact = _snap_xy(_BASE_X, _BASE_Y)
    adjacent = _snap_xy(_BASE_X + 20.0, _BASE_Y)  # one cell east → 20 m centres
    r = check_pair_independence(impact, adjacent)
    assert r.independent is False
    assert "SM-1" in r.reason


def test_sm1_two_cells_apart_independent():
    impact = _snap_xy(_BASE_X, _BASE_Y)
    control = _snap_xy(_BASE_X + 40.0, _BASE_Y)  # two cells east → 40 m centres
    r = check_pair_independence(impact, control)
    assert r.independent is True
    assert r.separation_m == pytest.approx(40.0)


def test_sm2_same_cell_flagged_within_pair():
    impact = _snap_xy(_BASE_X, _BASE_Y)
    control = _snap_xy(_BASE_X + 3.0, _BASE_Y)  # same cell
    r = check_pair_independence(impact, control)
    assert r.same_cell is True
    assert r.independent is False
    assert "SM-2" in r.reason


def test_sm2_collision_detection_keeps_earlier_index():
    cells = [
        _snap_xy(_BASE_X, _BASE_Y),
        _snap_xy(_BASE_X + 200.0, _BASE_Y),
        _snap_xy(_BASE_X + 4.0, _BASE_Y),   # collides with index 0
    ]
    assert find_cell_collisions(cells) == [(0, 2)]


def test_cell_separation_matches_geometry():
    a = _snap_xy(_BASE_X, _BASE_Y)
    b = _snap_xy(_BASE_X + 60.0, _BASE_Y + 80.0)
    assert cell_separation_m(a, b) == pytest.approx(100.0)


# ── SM-3: control clearance from trails ─────────────────────────────────────

def test_sm3_control_too_close_to_trail_fails():
    # A trail running N–S through x=_BASE_X; control 50 m east is < 100 m.
    trail = LineString([(_BASE_X, _BASE_Y - 500), (_BASE_X, _BASE_Y + 500)])
    lon, lat = _ll(_BASE_X + 50.0, _BASE_Y)
    assert control_trail_clearance_m(lon, lat, [trail]) == pytest.approx(50.0, abs=1.0)
    assert control_clearance_ok(lon, lat, [trail]) is False


def test_sm3_control_far_enough_passes():
    trail = LineString([(_BASE_X, _BASE_Y - 500), (_BASE_X, _BASE_Y + 500)])
    lon, lat = _ll(_BASE_X + 150.0, _BASE_Y)
    assert control_clearance_ok(lon, lat, [trail]) is True


def test_sm3_empty_network_is_infinite_clearance():
    lon, lat = _ll(_BASE_X, _BASE_Y)
    assert control_trail_clearance_m(lon, lat, []) == float("inf")


def test_load_trail_network_reprojects_to_utm(tmp_path):
    lon, lat = _ll(_BASE_X, _BASE_Y)
    lon2, lat2 = _ll(_BASE_X, _BASE_Y + 100.0)
    fc = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "properties": {},
            "geometry": {"type": "LineString",
                         "coordinates": [[lon, lat], [lon2, lat2]]},
        }],
    }
    p = tmp_path / "trails.geojson"
    p.write_text(json.dumps(fc), encoding="utf-8")
    geoms = load_trail_network_utm(p)
    assert len(geoms) == 1
    # Reprojected back near the original UTM easting.
    assert geoms[0].coords[0][0] == pytest.approx(_BASE_X, abs=1.0)


# ── SM-4: edge of footprint ─────────────────────────────────────────────────

def test_sm4_interior_cell_inside_edge_cell_excluded():
    bounds = (420000.0, 4520000.0, 420200.0, 4520200.0)  # 200 m square
    interior = _snap_xy(420100.0, 4520100.0)
    assert cell_inside_footprint(interior, bounds) is True
    edge = _snap_xy(420005.0, 4520100.0)  # touches the western margin
    assert cell_inside_footprint(edge, bounds) is False


# ── extraction against a synthetic composite ────────────────────────────────

def _make_raster(ndvi: np.ndarray, ndmi: np.ndarray, *,
                 ulx=420000.0, uly=4520200.0, res=10.0, epsg=25830, nodata=-9999.0):
    """Open an in-memory 2-band (NDVI, NDMI) raster with a north-up transform."""
    transform = from_origin(ulx, uly, res, res)
    mem = MemoryFile()
    ds = mem.open(driver="GTiff", height=ndvi.shape[0], width=ndvi.shape[1],
                  count=2, dtype="float32", crs=f"EPSG:{epsg}",
                  transform=transform, nodata=nodata)
    ds.write(ndvi.astype("float32"), 1)
    ds.write(ndmi.astype("float32"), 2)
    return ds


def test_extract_returns_means_and_full_provenance():
    ndvi = np.full((20, 20), 0.70, dtype="float32")
    ndmi = np.full((20, 20), 0.20, dtype="float32")
    ds = _make_raster(ndvi, ndmi)
    lon, lat = _ll(420100.0, 4520100.0)
    ext = extract_plot_value("plot_1", lon, lat, ds, scene_ids=["S2B_X", "S2A_Y"])
    assert ext.ndvi == pytest.approx(0.70, abs=1e-4)
    assert ext.ndmi == pytest.approx(0.20, abs=1e-4)
    assert ext.valid_pixel_fraction == 1.0
    assert ext.scene_ids == ("S2B_X", "S2A_Y")
    assert ext.cell_id.startswith("25830:20:")
    assert ext.gps_to_cell_centre_m >= 0.0


def test_extract_excludes_when_coverage_below_threshold():
    ndvi = np.full((20, 20), 0.70, dtype="float32")
    ndmi = np.full((20, 20), 0.20, dtype="float32")
    # Knock out 2 of the 4 pixels in the target cell → 50 % valid < 70 %.
    cell = snap_to_support_grid(*_ll(420100.0, 4520100.0))
    from src.validation.spatial_match import _cell_pixel_window
    ds0 = _make_raster(ndvi, ndmi)
    r0, c0, nr, nc = _cell_pixel_window(cell, ds0.transform)
    ndvi[r0, c0] = -9999.0
    ndvi[r0, c0 + 1] = -9999.0
    ds = _make_raster(ndvi, ndmi)
    lon, lat = _ll(420100.0, 4520100.0)
    with pytest.raises(InsufficientCoverage):
        extract_plot_value("plot_bad", lon, lat, ds, scene_ids=["S2B_X"])


def test_extract_passes_at_75_percent_coverage():
    ndvi = np.full((20, 20), 0.70, dtype="float32")
    ndmi = np.full((20, 20), 0.20, dtype="float32")
    cell = snap_to_support_grid(*_ll(420100.0, 4520100.0))
    from src.validation.spatial_match import _cell_pixel_window
    ds0 = _make_raster(ndvi, ndmi)
    r0, c0, nr, nc = _cell_pixel_window(cell, ds0.transform)
    ndvi[r0, c0] = -9999.0  # 1 of 4 → 75 % valid ≥ 70 %
    ds = _make_raster(ndvi, ndmi)
    lon, lat = _ll(420100.0, 4520100.0)
    ext = extract_plot_value("plot_ok", lon, lat, ds, scene_ids=["S2B_X"])
    assert ext.valid_pixel_fraction == pytest.approx(0.75)


def test_extract_raises_on_grid_misalignment():
    ndvi = np.full((20, 20), 0.70, dtype="float32")
    ndmi = np.full((20, 20), 0.20, dtype="float32")
    ds = _make_raster(ndvi, ndmi, ulx=420005.0)  # 5 m off the 20 m grid
    lon, lat = _ll(420100.0, 4520100.0)
    with pytest.raises(GridMisalignment):
        extract_plot_value("plot_x", lon, lat, ds, scene_ids=["S2B_X"])


def test_extract_raises_on_crs_mismatch():
    ndvi = np.full((20, 20), 0.70, dtype="float32")
    ndmi = np.full((20, 20), 0.20, dtype="float32")
    ds = _make_raster(ndvi, ndmi, epsg=25829)  # wrong UTM zone
    lon, lat = _ll(420100.0, 4520100.0)
    with pytest.raises(CRSMismatch):
        extract_plot_value("plot_x", lon, lat, ds, scene_ids=["S2B_X"])


def test_extract_masks_scl_excluded_classes():
    ndvi = np.full((20, 20), 0.70, dtype="float32")
    ndmi = np.full((20, 20), 0.20, dtype="float32")
    ds = _make_raster(ndvi, ndmi)
    # SCL raster: class 4 (vegetation) everywhere except the target cell's pixels,
    # set to class 9 (cloud high prob., excluded) enough to drop below 70 %.
    cell = snap_to_support_grid(*_ll(420100.0, 4520100.0))
    from src.validation.spatial_match import _cell_pixel_window
    r0, c0, nr, nc = _cell_pixel_window(cell, ds.transform)
    scl = np.full((20, 20), 4, dtype="float32")
    scl[r0, c0] = 9
    scl[r0, c0 + 1] = 9
    scl[r0 + 1, c0] = 9  # 3 of 4 → 25 % valid
    scl_ds = _make_scl_raster(scl)
    lon, lat = _ll(420100.0, 4520100.0)
    with pytest.raises(InsufficientCoverage):
        extract_plot_value("plot_scl", lon, lat, ds, scene_ids=["S2B_X"],
                           scl_raster=scl_ds)


def test_extract_scl_class_5_retained_not_masked():
    # The matching-plan asymmetry: bare/rock (SCL 5) is real signal at a plot,
    # so a cell full of class 5 must NOT be excluded.
    ndvi = np.full((20, 20), 0.30, dtype="float32")
    ndmi = np.full((20, 20), 0.05, dtype="float32")
    ds = _make_raster(ndvi, ndmi)
    scl = np.full((20, 20), 5, dtype="float32")  # all bare/rock
    scl_ds = _make_scl_raster(scl)
    lon, lat = _ll(420100.0, 4520100.0)
    ext = extract_plot_value("plot_bare", lon, lat, ds, scene_ids=["S2B_X"],
                             scl_raster=scl_ds)
    assert ext.valid_pixel_fraction == 1.0
    assert 5 in ext.scl_classes_present


def _make_scl_raster(scl: np.ndarray, *, ulx=420000.0, uly=4520200.0, res=10.0):
    transform = from_origin(ulx, uly, res, res)
    mem = MemoryFile()
    ds = mem.open(driver="GTiff", height=scl.shape[0], width=scl.shape[1],
                  count=1, dtype="float32", crs="EPSG:25830", transform=transform)
    ds.write(scl.astype("float32"), 1)
    return ds


# ── EHS reuse (operational formula, not a fork) ─────────────────────────────

def test_plot_stress_reuses_operational_formula():
    # NDVI at floor, NDMI at baseline, equal weights → D_ndvi=1, D_ndmi=0 → 50.
    stress = plot_stress_from_baselines(
        ndvi=0.2, ndmi=0.5,
        ndvi_baseline=0.8, ndvi_floor=0.2,
        ndmi_baseline=0.5, ndmi_floor=0.1,
    )
    assert stress == pytest.approx(50.0, abs=1e-6)


def test_plot_stress_zero_at_baseline():
    stress = plot_stress_from_baselines(
        ndvi=0.8, ndmi=0.5,
        ndvi_baseline=0.8, ndvi_floor=0.2,
        ndmi_baseline=0.5, ndmi_floor=0.1,
    )
    assert stress == pytest.approx(0.0, abs=1e-6)


# ── the existing asset-level service is untouched (regression guard) ────────

def test_existing_field_agreement_service_still_imports():
    # B-04 must not disturb the product's asset-level path.
    from src.ui.services import field_agreement  # noqa: F401
    assert hasattr(field_agreement, "compute_field_agreement")
