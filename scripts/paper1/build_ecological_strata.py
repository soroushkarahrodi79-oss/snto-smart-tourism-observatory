"""
scripts/paper1/build_ecological_strata.py
=========================================
Paper-1 Backlog A-4: derive the ecological strata (S1–S4) for the PNSG trails
from a Digital Elevation Model (elevation + aspect), per the definitions in
``docs/paper1/FIELD_CAMPAIGN_EXECUTION_PLAN.md`` §3:

  S1  Pinus sylvestris montane forest, N-facing   (≤ 1800 m, aspect N)
  S2  Pinus sylvestris montane forest, S-facing   (≤ 1800 m, aspect not N)
  S3  High-mountain shrubland (Cytisus/Juniperus)  (1800–2100 m)
  S4  Alpine/subalpine grassland                    (> 2100 m)

The strata are **topographic** (elevation + aspect from a DEM) — cartography-
derived, not satellite-signal-derived, as the sampling design requires. An
optional OAPN vegetation layer can be supplied to cross-check the elevation-
derived class against real habitat polygons (refinement), but elevation +
aspect is the primary, defensible first-order stratification for Guadarrama,
where vegetation zonation is strongly elevation-driven.

⚠️ DEM PROVENANCE. ``--dem`` has **no default**: a real DEM (e.g. Copernicus
GLO-30 or IGN MDT05, both free) must be supplied. None is committed because
every DEM source (Copernicus/earth-search STAC, OpenTopography, USGS/CGIAR
SRTM, IGN) is unreachable from this build environment's proxy — the same
constraint that made B-01's Madrid boundary provisional. The pure
``stratum_for`` mapping is fully tested against a synthetic DEM; the real
per-trail layer is produced once a DEM is supplied.

Output: a per-trail strata CSV + provenance sidecar. B-01's plot planner reads
it via ``--strata`` so the ``stratum`` column carries S1–S4 instead of the
interim satellite-stress tercile.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.paper1._figutil import (  # noqa: E402
    build_provenance,
    require_inputs,
    sha256_file,
    write_sidecar,
)

_TRAILS = _ROOT / "data" / "outputs" / "pnsg" / "pipeline_a_results.geojson"
_OUT = _ROOT / "clean_assets" / "field_validation" / "reference" / "pnsg_trail_strata.csv"

# Elevation band thresholds (m), FIELD_CAMPAIGN_EXECUTION_PLAN.md §3.
FOREST_MAX_M = 1800.0    # ≤ this → montane forest (S1/S2)
SHRUB_MAX_M = 2100.0     # ≤ this (and > FOREST_MAX_M) → shrubland (S3); above → S4
# North-facing half-window (deg from N) for the S1/S2 split.
NORTH_HALF_WINDOW_DEG = 45.0

STRATA = {
    "S1": "S1_forest_N",
    "S2": "S2_forest_S",
    "S3": "S3_shrubland",
    "S4": "S4_alpine_grassland",
}


def _is_north_facing(aspect_deg: float) -> bool:
    """True when aspect is within ±45° of North (0/360)."""
    return aspect_deg >= (360.0 - NORTH_HALF_WINDOW_DEG) or aspect_deg <= NORTH_HALF_WINDOW_DEG


def stratum_for(elevation_m: float, aspect_deg: Optional[float]) -> str:
    """Map (elevation, aspect) → ecological stratum code. Pure, testable.

    Aspect only splits the forest band. When aspect is unknown the plot is
    assigned to S2 (S-facing) rather than fabricating a north exposure — the
    conservative choice, since N-facing is the cooler/moister refugium.
    """
    if elevation_m > SHRUB_MAX_M:
        return STRATA["S4"]
    if elevation_m > FOREST_MAX_M:
        return STRATA["S3"]
    if aspect_deg is not None and _is_north_facing(aspect_deg):
        return STRATA["S1"]
    return STRATA["S2"]


def _sample_trail(line, elev, aspect, transform, n: int = 20):
    """Mean elevation and circular-mean aspect sampled along a trail line
    (already in the DEM CRS). Returns (elev_mean, aspect_mean|None)."""
    import numpy as np

    h, w = elev.shape
    a, e_, c, f = transform.a, transform.e, transform.c, transform.f
    elevs: list[float] = []
    sin_s = cos_s = 0.0
    n_asp = 0
    length = line.length or 1.0
    for i in range(n):
        pt = line.interpolate(i / max(n - 1, 1), normalized=True)
        col = int(round((pt.x - c) / a))
        row = int(round((pt.y - f) / e_))
        if 0 <= row < h and 0 <= col < w:
            ev = float(elev[row, col])
            if math.isfinite(ev):
                elevs.append(ev)
            av = float(aspect[row, col])
            if math.isfinite(av):
                rad = math.radians(av)
                sin_s += math.sin(rad)
                cos_s += math.cos(rad)
                n_asp += 1
    if not elevs:
        return None, None
    elev_mean = sum(elevs) / len(elevs)
    aspect_mean = ((math.degrees(math.atan2(sin_s / n_asp, cos_s / n_asp)) + 360.0) % 360.0
                   if n_asp else None)
    return elev_mean, aspect_mean


def build_rows(trails_gdf, elev, aspect, transform) -> list[dict]:
    rows = []
    for idx, row in trails_gdf.iterrows():
        geom = row.geometry
        if geom.geom_type == "MultiLineString":
            geom = max(geom.geoms, key=lambda g: g.length)
        elev_mean, aspect_mean = _sample_trail(geom, elev, aspect, transform)
        sid = int(row.get("id", idx))
        if elev_mean is None:
            rows.append({"trail_id": sid, "stratum": "unresolved",
                         "elevation_m": "", "aspect_deg": "",
                         "reason": "no DEM coverage"})
            continue
        rows.append({
            "trail_id": sid,
            "stratum": stratum_for(elev_mean, aspect_mean),
            "elevation_m": round(elev_mean, 1),
            "aspect_deg": round(aspect_mean, 1) if aspect_mean is not None else "",
            "reason": "",
        })
    return rows


def render(dem_path: Path, *, trails_path: Path = _TRAILS, out: Path = _OUT,
           dem_authoritative: bool = False):
    import geopandas as gpd
    import numpy as np
    import rasterio
    import warnings
    warnings.filterwarnings("ignore")

    from src.geospatial.geometry import compute_slope_aspect

    require_inputs({"trails": trails_path, "dem": dem_path})

    with rasterio.open(dem_path) as ds:
        elev = ds.read(1).astype("float64")
        if ds.nodata is not None:
            elev = np.where(elev == ds.nodata, np.nan, elev)
        transform = ds.transform
        dem_crs = ds.crs.to_epsg() if ds.crs else None

    _, aspect = compute_slope_aspect(elev, transform)

    trails = gpd.read_file(trails_path)
    if trails.crs is None:
        trails = trails.set_crs(4326)
    if dem_crs is not None:
        trails = trails.to_crs(dem_crs)

    rows = build_rows(trails, elev, aspect, transform)

    out.parent.mkdir(parents=True, exist_ok=True)
    import csv
    fieldnames = ["trail_id", "stratum", "elevation_m", "aspect_deg", "reason"]
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    dist = Counter(r["stratum"] for r in rows)
    prov = build_provenance(
        {"trails": trails_path, "dem": dem_path},
        params={"dem_authoritative": dem_authoritative,
                "dem_sha256": sha256_file(dem_path),
                "dem_crs_epsg": dem_crs,
                "n_trails": len(rows),
                "forest_max_m": FOREST_MAX_M, "shrub_max_m": SHRUB_MAX_M,
                "north_half_window_deg": NORTH_HALF_WINDOW_DEG,
                "stratum_distribution": dict(dist)},
    )
    write_sidecar(out, prov)
    return out, prov


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dem", type=Path, required=True,
                   help="DEM raster (no default — supply Copernicus GLO-30 or IGN MDT).")
    p.add_argument("--dem-authoritative", action="store_true",
                   help="Assert the DEM is an authoritative source (drops the "
                        "provisional note in provenance).")
    p.add_argument("--trails", type=Path, default=_TRAILS)
    p.add_argument("--out", type=Path, default=_OUT)
    args = p.parse_args()

    out, prov = render(args.dem, trails_path=args.trails, out=args.out,
                       dem_authoritative=args.dem_authoritative)
    pr = prov["params"]
    if not pr["dem_authoritative"]:
        print("⚠️  DEM not marked authoritative — verify the source before relying "
              "on the strata for the campaign.")
    print(f"Ecological strata → {out}  ({pr['n_trails']} trails)")
    print(f"  distribution: {pr['stratum_distribution']}")


if __name__ == "__main__":
    main()
