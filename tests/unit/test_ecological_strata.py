"""Ecological strata engine (Backlog A-4).

The pure elevation×aspect → S1–S4 mapping is the scientific core and is tested
exhaustively at the band/aspect boundaries. DEM sampling is verified against a
synthetic in-memory DEM (no network — every real DEM source is blocked here).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.paper1._figutil import MissingInput
from scripts.paper1.build_ecological_strata import (
    FOREST_MAX_M,
    SHRUB_MAX_M,
    _is_north_facing,
    render,
    stratum_for,
)

_ROOT = Path(__file__).resolve().parents[2]
_TRAILS = _ROOT / "data" / "outputs" / "pnsg" / "pipeline_a_results.geojson"


# ── pure mapping ────────────────────────────────────────────────────────────

def test_stratum_alpine_above_shrub_max():
    assert stratum_for(SHRUB_MAX_M + 0.1, 10) == "S4_alpine_grassland"


def test_stratum_shrubland_band():
    assert stratum_for(SHRUB_MAX_M, 10) == "S3_shrubland"          # 2100 → S3
    assert stratum_for(FOREST_MAX_M + 0.1, 200) == "S3_shrubland"


def test_stratum_forest_split_by_aspect():
    assert stratum_for(1500, 0) == "S1_forest_N"        # due north
    assert stratum_for(1500, 180) == "S2_forest_S"      # due south
    assert stratum_for(FOREST_MAX_M, 350) == "S1_forest_N"   # 1800 boundary → forest


def test_stratum_unknown_aspect_is_conservative_south():
    # Never fabricate a north exposure; unknown aspect → S2.
    assert stratum_for(1500, None) == "S2_forest_S"


@pytest.mark.parametrize("aspect,expected", [
    (0, True), (45, True), (45.01, False), (315, True), (314.99, False),
    (180, False), (360, True),
])
def test_is_north_facing_boundaries(aspect, expected):
    assert _is_north_facing(aspect) is expected


# ── engine on a synthetic DEM ───────────────────────────────────────────────

def _write_dem(path: Path, ulx, uly, res, W, H, elev):
    tr = from_origin(ulx, uly, res, res)
    with rasterio.open(path, "w", driver="GTiff", height=H, width=W, count=1,
                       dtype="float32", crs="EPSG:25830", transform=tr) as d:
        d.write(elev.astype("float32"), 1)


@pytest.mark.skipif(not _TRAILS.exists(), reason="committed trails absent")
def test_render_classifies_all_trails(tmp_path):
    # DEM covering the trail area, elevation rising to the north.
    W = H = 450
    yy, xx = np.mgrid[0:H, 0:W]
    elev = 1000.0 + (H - yy) * 3.0 + xx * 1.0
    dem = tmp_path / "dem.tif"
    _write_dem(dem, 395000.0, 4550000.0, 100.0, W, H, elev)

    out, prov = render(dem, out=tmp_path / "strata.csv")
    assert out.exists()
    pr = prov["params"]
    assert pr["n_trails"] == 218
    assert sum(pr["stratum_distribution"].values()) == 218
    assert pr["dem_sha256"]
    assert pr["dem_authoritative"] is False


@pytest.mark.skipif(not _TRAILS.exists(), reason="committed trails absent")
def test_render_marks_unresolved_when_dem_misses_trails(tmp_path):
    # A DEM far from the trails → no coverage → every trail 'unresolved'.
    W = H = 50
    elev = np.full((H, W), 1500.0)
    dem = tmp_path / "far.tif"
    _write_dem(dem, 200000.0, 4200000.0, 100.0, W, H, elev)
    out, prov = render(dem, out=tmp_path / "s.csv")
    assert prov["params"]["stratum_distribution"].get("unresolved") == 218


def test_missing_dem_fails_loudly(tmp_path):
    with pytest.raises(MissingInput):
        render(tmp_path / "nope.tif", out=tmp_path / "s.csv")


# ── B-01 wiring: the plan carries S1–S4 when strata are supplied ────────────

@pytest.mark.skipif(not _TRAILS.exists(), reason="committed trails absent")
def test_plot_plan_uses_ecological_stratum_when_strata_supplied(tmp_path):
    import csv

    from scripts.paper1.generate_plot_plan import render as plan_render

    boundary = (_ROOT / "clean_assets" / "field_validation" / "reference"
                / "madrid_boundary_naturalearth10m.geojson")
    if not boundary.exists():
        pytest.skip("reference boundary absent")

    # Build a strata table for the whole network from a synthetic DEM.
    W = H = 450
    yy, xx = np.mgrid[0:H, 0:W]
    elev = 1000.0 + (H - yy) * 3.0 + xx * 1.0
    dem = tmp_path / "dem.tif"
    _write_dem(dem, 395000.0, 4550000.0, 100.0, W, H, elev)
    strata_csv, _ = render(dem, out=tmp_path / "strata.csv")

    csv_path, prov = plan_render(
        boundary, margin_m=1000.0, seed=42, n_segments=8, impacts_per_segment=2,
        authoritative=False, out_dir=tmp_path, strata_path=strata_csv)

    assert prov["params"]["stratum_axis"] == "ecological_S1_S4"
    strata_vals = {r["stratum"] for r in csv.DictReader(csv_path.open(encoding="utf-8"))}
    assert strata_vals and all(s.startswith("S") for s in strata_vals)
    assert not any(s.startswith("sat_stress") for s in strata_vals)
