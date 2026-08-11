"""Field plot-plan generator (Backlog B-01).

Validates the plot-placement engine against the committed (non-authoritative)
reference boundary: distinct coordinates, 1:1 stratum-matched pairing, and
independent re-verification of SM-1/SM-2/SM-3 on the emitted plan. The Madrid
*jurisdiction* is provisional (coarse boundary); these tests check plot
GEOMETRY, which is boundary-independent-correct.
"""
from __future__ import annotations

import collections
import csv
from pathlib import Path

import pytest

from scripts.paper1._figutil import MissingInput
from scripts.paper1.generate_plot_plan import render
from src.validation.spatial_match import (
    check_pair_independence,
    control_trail_clearance_m,
    find_cell_collisions,
    load_trail_network_utm,
    snap_to_support_grid,
)

_ROOT = Path(__file__).resolve().parents[2]
_BOUNDARY = (_ROOT / "clean_assets" / "field_validation" / "reference"
             / "madrid_boundary_naturalearth10m.geojson")
_TRAILS = _ROOT / "data" / "outputs" / "pnsg" / "pipeline_a_results.geojson"

pytestmark = pytest.mark.skipif(
    not (_BOUNDARY.exists() and _TRAILS.exists()),
    reason="committed boundary/trail inputs absent in this checkout")


def _render(tmp_path, **kw):
    params = dict(margin_m=1000.0, seed=42, n_segments=12,
                  impacts_per_segment=2, authoritative=False, out_dir=tmp_path)
    params.update(kw)
    return render(_BOUNDARY, **params)


def _rows(csv_path):
    return list(csv.DictReader(csv_path.open(encoding="utf-8")))


def test_plan_produces_distinct_coordinates(tmp_path):
    csv_path, _ = _render(tmp_path)
    rows = _rows(csv_path)
    coords = [(r["lat"], r["lon"]) for r in rows]
    assert len(rows) > 0
    assert len(set(coords)) == len(coords)  # no two plots share a coordinate


def test_no_two_plots_share_a_support_cell(tmp_path):
    csv_path, _ = _render(tmp_path)
    cells = [snap_to_support_grid(float(r["lon"]), float(r["lat"]))
             for r in _rows(csv_path)]
    assert find_cell_collisions(cells) == []  # SM-2


def test_every_impact_has_one_control_in_same_stratum(tmp_path):
    csv_path, _ = _render(tmp_path)
    pairs: dict[str, dict] = collections.defaultdict(dict)
    for r in _rows(csv_path):
        base = r["plot_id"].rsplit("_", 1)[0]
        role = "control" if r["is_control"] == "true" else "impact"
        pairs[base][role] = r
    assert pairs
    for base, d in pairs.items():
        assert "impact" in d and "control" in d, f"{base} not 1:1 paired"
        assert d["impact"]["stratum"] == d["control"]["stratum"]


def test_pairs_satisfy_sm1_non_adjacent(tmp_path):
    csv_path, _ = _render(tmp_path)
    pairs: dict[str, dict] = collections.defaultdict(dict)
    for r in _rows(csv_path):
        base = r["plot_id"].rsplit("_", 1)[0]
        cell = snap_to_support_grid(float(r["lon"]), float(r["lat"]))
        pairs[base]["C" if r["is_control"] == "true" else "I"] = cell
    for d in pairs.values():
        assert check_pair_independence(d["I"], d["C"]).independent  # SM-1


def test_controls_clear_every_trail_by_100m(tmp_path):
    csv_path, _ = _render(tmp_path)
    trails = load_trail_network_utm(_TRAILS)
    for r in _rows(csv_path):
        if r["is_control"] == "true":
            d = control_trail_clearance_m(float(r["lon"]), float(r["lat"]), trails)
            assert d >= 100.0, f"{r['plot_id']} only {d:.0f} m from a trail"  # SM-3


def test_generation_is_deterministic_given_seed(tmp_path):
    a, _ = _render(tmp_path / "a")
    b, _ = _render(tmp_path / "b")
    assert a.read_bytes() == b.read_bytes()


def test_provisional_marking_in_filename_and_provenance(tmp_path):
    csv_path, prov = _render(tmp_path, authoritative=False)
    assert "_PROVISIONAL" in csv_path.name
    assert prov["params"]["boundary_authoritative"] is False
    assert prov["params"]["boundary_sha256"]


def test_authoritative_flag_drops_provisional_marking(tmp_path):
    csv_path, prov = _render(tmp_path, authoritative=True)
    assert "_PROVISIONAL" not in csv_path.name
    assert prov["params"]["boundary_authoritative"] is True


def test_sidecar_records_boundary_distance_meta(tmp_path):
    csv_path, prov = _render(tmp_path)
    assert prov["params"]["n_eligible_madrid"] <= prov["params"]["n_trails_total"]
    placed = [m for m in prov["plot_meta"] if m["status"] == "placed"]
    assert placed and all("control_clearance_m" in m for m in placed)


def test_gpx_written_alongside_csv(tmp_path):
    csv_path, _ = _render(tmp_path)
    gpx = csv_path.with_suffix(".gpx")
    assert gpx.exists()
    body = gpx.read_text(encoding="utf-8")
    assert body.startswith("<?xml") and "<wpt" in body


def test_missing_boundary_fails_loudly(tmp_path):
    with pytest.raises(MissingInput):
        render(tmp_path / "nope.geojson", margin_m=1000.0, seed=1,
               n_segments=3, impacts_per_segment=1, authoritative=False,
               out_dir=tmp_path)
