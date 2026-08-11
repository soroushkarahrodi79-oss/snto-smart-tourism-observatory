"""
scripts/paper1/generate_plot_plan.py
====================================
Paper-1 Backlog B-01: generate a field plot plan with **real, distinct**
impact/control coordinates, replacing the shipped template's void-contrast bug
(impact and control at identical coordinates → same satellite pixel).

Pipeline:
  1. Filter the 218 OAPN trails to the Madrid-administered sector, using a
     **pluggable** administrative boundary (``--boundary``) buffered inward by a
     safety margin (``--margin-m``). Full containment only — trails crossing or
     near the boundary are conservatively excluded.
  2. Stratify eligible trails by satellite-stress (``ehs_summer``) tercile and
     select segments spanning the range (deterministic given ``--seed``).
  3. Place impact plots along each segment and one stratum-matched control per
     impact, each snapped to the 20 m support grid (B-04) and validated:
       * SM-1 impact/control cells ≥ 40 m apart (non-adjacent),
       * SM-2 no two plots share a 20 m cell,
       * SM-3 control ≥ 100 m from *every* mapped trail.
  4. Emit the field CSV (distinct coords, measurement columns blank), GPX
     waypoints, and a provenance sidecar (seed, commit, boundary SHA-256, per-
     plot cell id + distance to boundary).

⚠️ Jurisdiction is PROVISIONAL unless ``--boundary-authoritative`` is passed.
The committed reference boundary is Natural Earth 10m (non-authoritative,
crest-inaccurate — see clean_assets/field_validation/reference/README.md); it
misclassifies sierra trails and must be replaced with the IGN Líneas Límite
before the campaign. The output filename carries ``_PROVISIONAL`` until then.

``--boundary`` has no default: choosing the jurisdiction layer is a conscious act.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pyproj import Transformer  # noqa: E402

from scripts.paper1._figutil import (  # noqa: E402
    build_provenance,
    git_commit_hash,
    require_inputs,
    sha256_file,
    write_sidecar,
)
from src.validation.io import write_template  # noqa: E402
from src.validation.spatial_match import (  # noqa: E402
    check_pair_independence,
    control_trail_clearance_m,
    snap_to_support_grid,
)

_TRAILS = _ROOT / "data" / "outputs" / "pnsg" / "pipeline_a_results.geojson"
_OUT_DIR = _ROOT / "clean_assets" / "field_validation"
_STRESS_COL = "ehs_summer"
_GRID_EPSG = 25830

_TO_UTM = Transformer.from_crs(4326, _GRID_EPSG, always_xy=True)
_TO_WGS = Transformer.from_crs(_GRID_EPSG, 4326, always_xy=True)

# Control placement candidates: perpendicular offsets (m), both sides.
_CONTROL_OFFSETS_M = (140.0, 180.0, 220.0, 260.0)
_MIN_CONTROL_CLEARANCE_M = 100.0


def _tercile_label(value: float, q1: float, q2: float) -> str:
    if value <= q1:
        return "low"
    if value <= q2:
        return "mid"
    return "high"


def _merged_line(geom):
    """A single LineString to interpolate along (longest part of a Multi)."""
    from shapely.ops import linemerge

    if geom.geom_type == "MultiLineString":
        merged = linemerge(geom)
        if merged.geom_type == "MultiLineString":
            return max(merged.geoms, key=lambda g: g.length)
        return merged
    return geom


def _perp_unit(line, f: float) -> tuple[float, float]:
    p1 = line.interpolate(f, normalized=True)
    p2 = line.interpolate(min(f + 0.02, 1.0), normalized=True)
    dx, dy = (p2.x - p1.x), (p2.y - p1.y)
    n = math.hypot(dx, dy) or 1.0
    return (-dy / n, dx / n)  # left-perpendicular unit vector


def _place_control(impact_utm, perp, trails_utm, used_cells, impact_cell):
    """First control offset that satisfies SM-1, SM-2 and SM-3; else None."""
    for off in _CONTROL_OFFSETS_M:
        for sign in (1.0, -1.0):
            cx = impact_utm.x + sign * perp[0] * off
            cy = impact_utm.y + sign * perp[1] * off
            lon, lat = _TO_WGS.transform(cx, cy)
            clearance = control_trail_clearance_m(lon, lat, trails_utm)
            if clearance < _MIN_CONTROL_CLEARANCE_M:
                continue
            cell = snap_to_support_grid(lon, lat)
            if cell.cell_id in used_cells:
                continue
            if not check_pair_independence(impact_cell, cell).independent:
                continue
            return lon, lat, cell, round(clearance, 1)
    return None


def build_plan(trails_gdf, trails_utm, *, n_segments: int, impacts_per_segment: int,
               seed: int):
    """Return (rows, plot_meta) — deterministic given seed."""
    from shapely.geometry import Point  # noqa: F401

    stress = trails_gdf[_STRESS_COL].astype(float)
    q1, q2 = stress.quantile(1 / 3), stress.quantile(2 / 3)

    # Bucket eligible trails by tercile, then select spanning the range.
    buckets: dict[str, list] = {"low": [], "mid": [], "high": []}
    for idx, row in trails_gdf.iterrows():
        buckets[_tercile_label(float(row[_STRESS_COL]), q1, q2)].append(idx)
    rng = random.Random(seed)
    for b in buckets.values():
        rng.shuffle(b)

    selected: list = []
    order = ["low", "mid", "high"]
    while len(selected) < n_segments and any(buckets[k] for k in order):
        for k in order:
            if buckets[k] and len(selected) < n_segments:
                selected.append((k, buckets[k].pop()))

    rows: list[dict] = []
    meta: list[dict] = []
    used_cells: set[str] = set()

    for tercile, idx in selected:
        row = trails_gdf.loc[idx]
        sid = int(row.get("id", idx))
        line = _merged_line(row.geometry)
        if line.length < 40:  # too short to host separated plots
            continue
        stratum = f"sat_stress_{tercile}"
        # Even fractions avoiding the endpoints.
        fracs = [(k + 1) / (impacts_per_segment + 1)
                 for k in range(impacts_per_segment)]
        for k, f in enumerate(fracs, start=1):
            ip = line.interpolate(f, normalized=True)
            ilon, ilat = _TO_WGS.transform(ip.x, ip.y)
            icell = snap_to_support_grid(ilon, ilat)
            if icell.cell_id in used_cells:
                continue
            perp = _perp_unit(line, f)
            placed = _place_control(ip, perp, trails_utm, used_cells | {icell.cell_id},
                                    icell)
            if placed is None:
                meta.append({"segment": sid, "impact_k": k, "status": "control_unplaceable"})
                continue
            clon, clat, ccell, clearance = placed
            used_cells.add(icell.cell_id)
            used_cells.add(ccell.cell_id)

            base = f"seg{sid}_{k}"
            rows.append({"plot_id": f"{base}_impact", "asset_id": f"pnsg_trail_{sid}",
                         "lat": round(ilat, 6), "lon": round(ilon, 6),
                         "distance_to_trail_m": 0, "is_control": "false",
                         "stratum": stratum})
            rows.append({"plot_id": f"{base}_control", "asset_id": f"pnsg_trail_{sid}",
                         "lat": round(clat, 6), "lon": round(clon, 6),
                         "distance_to_trail_m": clearance, "is_control": "true",
                         "stratum": stratum})
            meta.append({"segment": sid, "impact_k": k, "status": "placed",
                         "stratum": stratum,
                         "impact_cell": icell.cell_id, "control_cell": ccell.cell_id,
                         "control_clearance_m": clearance})
    return rows, meta


def _write_gpx(rows: list[dict], path: Path) -> None:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<gpx version="1.1" creator="SNTO generate_plot_plan">']
    for r in rows:
        lines.append(f'  <wpt lat="{r["lat"]}" lon="{r["lon"]}">'
                     f'<name>{r["plot_id"]}</name></wpt>')
    lines.append("</gpx>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render(boundary: Path, *, margin_m: float, seed: int, n_segments: int,
           impacts_per_segment: int, authoritative: bool, out_dir: Path = _OUT_DIR):
    import geopandas as gpd
    import warnings
    warnings.filterwarnings("ignore")

    require_inputs({"trails": _TRAILS, "boundary": boundary})

    trails = gpd.read_file(_TRAILS)
    if trails.crs is None:
        trails = trails.set_crs(4326)
    trails = trails.to_crs(_GRID_EPSG)
    bnd = gpd.read_file(boundary)
    if bnd.crs is None:
        bnd = bnd.set_crs(4326)
    bnd_geom = bnd.to_crs(_GRID_EPSG).union_all()

    # Madrid filter: full containment inside the inward-buffered boundary.
    inner = bnd_geom.buffer(-margin_m)
    dist_to_boundary = trails.geometry.apply(lambda g: g.distance(bnd_geom.boundary))
    eligible_mask = trails.geometry.apply(lambda g: g.within(inner))
    eligible = trails[eligible_mask].copy()

    # Full 218-trail network (UTM) for SM-3 clearance — controls must clear ALL trails.
    trails_utm = list(trails.geometry.values)

    rows, meta = build_plan(
        eligible, trails_utm, n_segments=n_segments,
        impacts_per_segment=impacts_per_segment, seed=seed)

    tag = "" if authoritative else "_PROVISIONAL"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"pnsg_plot_plan{tag}.csv"
    gpx_path = out_dir / f"pnsg_plot_plan{tag}.gpx"
    write_template(csv_path, rows)
    _write_gpx(rows, gpx_path)

    prov = build_provenance(
        {"trails": _TRAILS, "boundary": boundary},
        params={
            "seed": seed, "margin_m": margin_m, "n_segments_requested": n_segments,
            "impacts_per_segment": impacts_per_segment,
            "boundary_authoritative": authoritative,
            "boundary_sha256": sha256_file(boundary),
            "n_trails_total": len(trails),
            "n_eligible_madrid": int(eligible_mask.sum()),
            "n_plots": len(rows),
            "n_pairs_placed": sum(1 for m in meta if m["status"] == "placed"),
            "n_controls_unplaceable": sum(1 for m in meta
                                          if m["status"] == "control_unplaceable"),
            "commit_hash": git_commit_hash(),
        },
    )
    prov["plot_meta"] = meta
    write_sidecar(csv_path, prov)
    return csv_path, prov


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--boundary", type=Path, required=True,
                   help="Administrative boundary GeoJSON (no default — choose consciously).")
    p.add_argument("--boundary-authoritative", action="store_true",
                   help="Assert the boundary is authoritative (e.g. IGN); drops the "
                        "PROVISIONAL marking. Do NOT pass for Natural Earth.")
    p.add_argument("--margin-m", type=float, default=1000.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-segments", type=int, default=12)
    p.add_argument("--impacts-per-segment", type=int, default=2)
    args = p.parse_args()

    csv_path, prov = render(
        args.boundary, margin_m=args.margin_m, seed=args.seed,
        n_segments=args.n_segments, impacts_per_segment=args.impacts_per_segment,
        authoritative=args.boundary_authoritative)

    pr = prov["params"]
    if not pr["boundary_authoritative"]:
        print("⚠️  PROVISIONAL PLAN — boundary is NOT authoritative. Jurisdiction "
              "must be verified against IGN Líneas Límite before the campaign.")
    print(f"Plot plan → {csv_path}")
    print(f"  eligible Madrid-side trails: {pr['n_eligible_madrid']}/{pr['n_trails_total']} "
          f"(margin {pr['margin_m']:.0f} m) · pairs placed: {pr['n_pairs_placed']} · "
          f"plots: {pr['n_plots']}")


if __name__ == "__main__":
    main()
