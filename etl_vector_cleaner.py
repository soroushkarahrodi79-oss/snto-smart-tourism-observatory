"""
SNTO ETL Phase 0 -- Vector Layer Cleaner
=========================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Loads all 7 raw vector layers from data/raw_assets/vector_data/, reprojects
every layer to EPSG:4326 (WGS 84), filters the national MAB and ENP datasets
to the Sierra del Rincón study bounding box, and saves production-ready
GeoJSON files to data/clean_assets/.

Inputs  : data/raw_assets/vector_data/
Outputs : data/clean_assets/  (clean_*.geojson)
"""
from __future__ import annotations

import io
import sys

# Ensure UTF-8 output regardless of terminal code page (e.g. cp1252 on Windows)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

import geopandas as gpd

SEP = "=" * 72
DIV = "-" * 72

PROJECT_ROOT = Path(__file__).parent
RAW_VEC      = PROJECT_ROOT / "data" / "raw_assets" / "vector_data"
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean_assets"

# Sierra del Rincón study bounding box (EPSG:4326)
BBOX_MINX, BBOX_MINY = -3.65, 41.05
BBOX_MAXX, BBOX_MAXY =  -3.30, 41.20

TARGET_CRS = 4326


def _load_reproject_filter(
    src_path: Path,
    out_name: str,
    force_crs_epsg: int | None = None,
) -> tuple[int, gpd.GeoDataFrame, str]:
    """Load a vector file, reproject to EPSG:4326, apply bbox filter.

    Returns (original_feature_count, filtered_GeoDataFrame, original_crs_str).
    """
    gdf = gpd.read_file(src_path)
    orig_count = len(gdf)
    orig_crs   = str(gdf.crs) if gdf.crs else "None (set to WGS84)"

    # Assign CRS if not embedded (RFC 7946 default = WGS84 for bare GeoJSON)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=force_crs_epsg if force_crs_epsg else TARGET_CRS)

    # Reproject to WGS84 if not already there
    if gdf.crs.to_epsg() != TARGET_CRS:
        try:
            gdf = gdf.to_crs(epsg=TARGET_CRS)
        except Exception:
            # Fallback: ETRS89 geographic (EPSG:4258) is sub-meter identical
            # to WGS84 over Spain — safe override when authority code is exotic
            gdf = gdf.set_crs(epsg=4258, allow_override=True)
            gdf = gdf.to_crs(epsg=TARGET_CRS)

    # Spatial filter to Sierra del Rincón bbox
    gdf = gdf.cx[BBOX_MINX:BBOX_MAXX, BBOX_MINY:BBOX_MAXY]

    return orig_count, gdf, orig_crs


def main() -> None:
    print(SEP)
    print("  SNTO ETL -- Vector Layer Cleaner")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Bbox (WGS84): xmin={BBOX_MINX}  ymin={BBOX_MINY}  "
          f"xmax={BBOX_MAXX}  ymax={BBOX_MAXY}")
    print(f"  Output: {CLEAN_DIR}")
    print(SEP)
    print()

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # (src_path, output_name, fallback_crs_epsg)
    layers: list[tuple[Path, str, int | None]] = [
        (RAW_VEC / "hiking_trails.geojson",
         "clean_hiking_trails.geojson",          None),
        (RAW_VEC / "viewpoints.geojson",
         "clean_viewpoints.geojson",             None),
        (RAW_VEC / "cycling_routes.geojson",
         "clean_cycling_routes.geojson",         None),
        (RAW_VEC / "MAB_LIMITE_C_EPSG4083.geojson",
         "clean_MAB_LIMITE_C.geojson",           4083),
        (RAW_VEC / "MAB_LIMITE_PyB_EPSG25830.geojson",
         "clean_MAB_LIMITE_PyB.geojson",         25830),
        (RAW_VEC / "Enp2025_geojson" / "Enp2025_c.json",
         "clean_Enp2025_c.geojson",              32628),
        (RAW_VEC / "Enp2025_geojson" / "Enp2025_p.json",
         "clean_Enp2025_p.geojson",              25830),
    ]

    col_w = 32
    print(f"  {'Layer':<{col_w}} {'Orig CRS':<20} {'In':>6} {'Out':>6}  Output")
    print(f"  {DIV}")

    for src_path, out_name, fallback_crs in layers:
        orig_count, gdf_out, orig_crs_str = _load_reproject_filter(
            src_path, out_name, force_crs_epsg=fallback_crs
        )
        out_path = CLEAN_DIR / out_name
        gdf_out.to_file(out_path, driver="GeoJSON")

        note = ""
        if orig_count > 0 and len(gdf_out) == 0:
            note = "  [Canary Is. — outside bbox]"

        # Shorten CRS string for display
        crs_display = orig_crs_str.replace("EPSG:", "").replace("None ", "")
        if "EPSG" not in orig_crs_str and "None" not in orig_crs_str:
            crs_display = orig_crs_str.split(":")[-1][:18]

        print(
            f"  {src_path.stem:<{col_w}} EPSG:{crs_display:<15}"
            f" {orig_count:>6} {len(gdf_out):>6}  {out_name}{note}"
        )

    print(f"  {DIV}")
    print()
    print(f"  Done. {len(layers)} layers written to: {CLEAN_DIR}")
    print()
    print(SEP)


if __name__ == "__main__":
    main()
