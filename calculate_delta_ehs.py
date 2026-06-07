"""
SNTO — Delta EHS Calculator
============================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Computes the seasonal Environmental Health Score (EHS) for each hiking trail
using spring and summer Sentinel-2 composite rasters, then writes the
degradation delta back to the PostGIS production table.

Workflow:
  1. Verify GeoTIFF inputs (spring_raster.tif, summer_raster.tif)
  2. Connect to PostGIS
  3. Ensure output columns exist (ehs_spring, delta_ehs)
  4. Load hiking trails from production_hiking_trails
  5. Buffer each trail 50 m in UTM (EPSG:25830)
  6. Extract mean NDVI (band 1) + mean NDMI (band 2) — spring raster
  7. Extract mean NDVI (band 1) + mean NDMI (band 2) — summer raster
  8. Compute EHS values and delta; write to PostGIS
  9. Print top-5 fastest-degrading trails

EHS formula (simplified per-season):
  EHS = 100 − (NDVI × 50 + NDMI × 50)
  delta_ehs = ehs_summer − ehs_spring   (positive = degrading into summer)

Raster convention:
  Each seasonal GeoTIFF must contain exactly two bands:
    Band 1 → NDVI
    Band 2 → NDMI
  If a trail does not overlap the raster extent, its NDVI/NDMI default to 0.0.

Credentials (override via environment variables):
  SNTO_DB_HOST  localhost
  SNTO_DB_PORT  5432
  SNTO_DB_NAME  snto
  SNTO_DB_USER  postgres
  SNTO_DB_PASS  secret
"""
from __future__ import annotations

import io
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

import geopandas as gpd
import psycopg2
import rasterio
from rasterstats import zonal_stats
from sqlalchemy import create_engine

SEP = "=" * 72
DIV = "-" * 72

PROJECT_ROOT = Path(__file__).parent
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean_assets"

SPRING_PATH = CLEAN_DIR / "spring_raster.tif"
SUMMER_PATH = CLEAN_DIR / "summer_raster.tif"

BUFFER_M   = 50
BUFFER_CRS = "EPSG:25830"   # UTM zone 30N — covers mainland Spain

DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
DB_USER = os.getenv("SNTO_DB_USER", "postgres")
DB_PASS = os.getenv("SNTO_DB_PASS", "Navidesalehin_1379")


# ── EHS ───────────────────────────────────────────────────────────────────────

def _ehs(ndvi: float | None, ndmi: float | None) -> float:
    """EHS = 100 − (NDVI × 50 + NDMI × 50). None values default to 0.0."""
    v = ndvi if ndvi is not None else 0.0
    m = ndmi if ndmi is not None else 0.0
    return round(100.0 - (v * 50.0 + m * 50.0), 4)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS, connect_timeout=10,
    )


def _engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


def _ensure_columns(conn: psycopg2.extensions.connection) -> None:
    """Add ehs_spring / delta_ehs FLOAT columns if they do not already exist."""
    with conn.cursor() as cur:
        for col in ("ehs_spring", "delta_ehs"):
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE  table_schema = 'public'
                  AND  table_name   = 'production_hiking_trails'
                  AND  column_name  = %s
                """,
                (col,),
            )
            if cur.fetchone() is None:
                print(f"    Adding column '{col}' FLOAT to production_hiking_trails ...")
                cur.execute(
                    f"ALTER TABLE production_hiking_trails ADD COLUMN {col} FLOAT"
                )
            else:
                print(f"    Column '{col}' already exists — will overwrite values.")
    conn.commit()


# ── Raster helpers ────────────────────────────────────────────────────────────

def _inspect_raster(path: Path, label: str) -> None:
    with rasterio.open(path) as src:
        print(f"    {label}: {path.name}")
        print(f"           CRS    = {src.crs.to_string()}")
        print(f"           Size   = {src.width} px × {src.height} px")
        print(f"           Bands  = {src.count}")
        print(f"           NoData = {src.nodata}")
        print(f"           Bounds = ({src.bounds.left:.4f}, {src.bounds.bottom:.4f}, "
              f"{src.bounds.right:.4f}, {src.bounds.top:.4f})")


def _extract_band(
    buffers_gdf: gpd.GeoDataFrame,
    raster_path: Path,
    band: int,
    label: str,
) -> list[float | None]:
    """
    Reproject buffers to the raster's CRS if needed, then run zonal_stats on
    a single band. Returns a list of mean values aligned to buffers_gdf.
    Geometries that fall entirely outside the raster extent return None.
    """
    with rasterio.open(raster_path) as src:
        raster_crs    = src.crs.to_string()
        raster_nodata = src.nodata

    if buffers_gdf.crs.to_string() != raster_crs:
        aligned = buffers_gdf.to_crs(raster_crs)
    else:
        aligned = buffers_gdf

    stats_list = zonal_stats(
        aligned,
        str(raster_path),
        band=band,
        stats=["mean"],
        nodata=raster_nodata,
        all_touched=False,
    )

    means = [s.get("mean") for s in stats_list]
    n_null = sum(1 for v in means if v is None)
    if n_null:
        print(f"    [{label}] {n_null} trail(s) outside raster extent — "
              "will default to 0 in EHS calculation.")
    return means


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("  SNTO — Delta EHS Calculator")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Target: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print()

    # ── [1/9] Verify raster inputs ────────────────────────────────────────────
    print("  [1/9] Verifying seasonal raster inputs ...")
    missing = [
        (lbl, p)
        for lbl, p in [("Spring", SPRING_PATH), ("Summer", SUMMER_PATH)]
        if not p.exists()
    ]
    if missing:
        for lbl, p in missing:
            print(f"  ERROR: {lbl} raster not found at: {p}")
        print()
        print("  Place spring_raster.tif and summer_raster.tif in:")
        print(f"    {CLEAN_DIR}")
        print("  Each file must have two bands: Band 1 = NDVI, Band 2 = NDMI.")
        sys.exit(1)

    _inspect_raster(SPRING_PATH, "Spring")
    _inspect_raster(SUMMER_PATH, "Summer")
    print()

    # ── [2/9] Connect to PostGIS ──────────────────────────────────────────────
    print("  [2/9] Connecting to PostGIS ...")
    try:
        conn = _connect()
    except (psycopg2.OperationalError, UnicodeDecodeError) as exc:
        print(f"  ERROR: Cannot connect — {type(exc).__name__}")
        print("  Ensure PostgreSQL is running and credentials are correct.")
        print("  Override via env vars: SNTO_DB_HOST / PORT / NAME / USER / PASS")
        sys.exit(1)

    major, minor = divmod(conn.server_version, 10000)
    print(f"  Connected. PostgreSQL {major}.{minor // 100}")
    print()

    # ── [3/9] Ensure output columns ───────────────────────────────────────────
    print("  [3/9] Ensuring ehs_spring / delta_ehs columns exist ...")
    _ensure_columns(conn)
    print()

    # ── [4/9] Load hiking trails ──────────────────────────────────────────────
    print("  [4/9] Loading hiking trails from PostGIS ...")
    engine = _engine()
    trails_gdf = gpd.read_postgis(
        "SELECT id, name, geometry FROM production_hiking_trails ORDER BY id",
        con=engine,
        geom_col="geometry",
        crs="EPSG:4326",
    )
    n_total = len(trails_gdf)
    valid_mask = trails_gdf.geometry.notna() & ~trails_gdf.geometry.is_empty
    trails_gdf = trails_gdf[valid_mask].copy()
    n_valid = len(trails_gdf)
    if n_total != n_valid:
        print(f"    Dropped {n_total - n_valid} null/empty geometries. {n_valid} remain.")
    else:
        print(f"    Loaded {n_valid} features from production_hiking_trails")
    print(f"    Native CRS: {trails_gdf.crs.to_string()}")
    print()

    # ── [5/9] Project to UTM and buffer ──────────────────────────────────────
    print(f"  [5/9] Projecting to {BUFFER_CRS} and creating {BUFFER_M} m buffers ...")
    projected   = trails_gdf.to_crs(BUFFER_CRS)
    buffers_gdf = projected.copy()
    buffers_gdf["geometry"] = projected.geometry.buffer(BUFFER_M)

    n_empty = buffers_gdf.geometry.is_empty.sum()
    if n_empty:
        print(f"    WARNING: {n_empty} buffer(s) are unexpectedly empty — "
              "they will produce NULL stats.")
    print(f"    Buffers created: {len(buffers_gdf)}")
    print()

    # ── [6/9] Zonal stats — spring ────────────────────────────────────────────
    print("  [6/9] Extracting spring NDVI / NDMI ...")
    spring_ndvi = _extract_band(buffers_gdf, SPRING_PATH, band=1, label="Spring NDVI")
    spring_ndmi = _extract_band(buffers_gdf, SPRING_PATH, band=2, label="Spring NDMI")
    s_ndvi_ok = sum(1 for v in spring_ndvi if v is not None)
    print(f"    Spring NDVI non-null: {s_ndvi_ok} / {len(spring_ndvi)}")
    print(f"    Spring NDMI non-null: {sum(1 for v in spring_ndmi if v is not None)} / {len(spring_ndmi)}")
    print()

    # ── [7/9] Zonal stats — summer ────────────────────────────────────────────
    print("  [7/9] Extracting summer NDVI / NDMI ...")
    summer_ndvi = _extract_band(buffers_gdf, SUMMER_PATH, band=1, label="Summer NDVI")
    summer_ndmi = _extract_band(buffers_gdf, SUMMER_PATH, band=2, label="Summer NDMI")
    print(f"    Summer NDVI non-null: {sum(1 for v in summer_ndvi if v is not None)} / {len(summer_ndvi)}")
    print(f"    Summer NDMI non-null: {sum(1 for v in summer_ndmi if v is not None)} / {len(summer_ndmi)}")
    print()

    # ── [8/9] Compute EHS values and write to PostGIS ────────────────────────
    print("  [8/9] Computing EHS_spring, EHS_summer, delta_ehs and writing to PostGIS ...")

    ids   = trails_gdf["id"].tolist()
    names = trails_gdf["name"].tolist()

    ehs_spring_vals = [_ehs(n, m) for n, m in zip(spring_ndvi, spring_ndmi)]
    ehs_summer_vals = [_ehs(n, m) for n, m in zip(summer_ndvi, summer_ndmi)]
    delta_vals      = [round(su - sp, 4) for sp, su in zip(ehs_spring_vals, ehs_summer_vals)]

    n_spring_fb = sum(1 for n, m in zip(spring_ndvi, spring_ndmi) if n is None or m is None)
    n_summer_fb = sum(1 for n, m in zip(summer_ndvi, summer_ndmi) if n is None or m is None)
    if n_spring_fb:
        print(f"    NOTE: {n_spring_fb} trail(s) used 0-fallback for spring EHS.")
    if n_summer_fb:
        print(f"    NOTE: {n_summer_fb} trail(s) used 0-fallback for summer EHS.")

    updated = 0
    with conn.cursor() as cur:
        for trail_id, ehs_sp, d_ehs in zip(ids, ehs_spring_vals, delta_vals):
            cur.execute(
                """
                UPDATE production_hiking_trails
                   SET ehs_spring = %s,
                       delta_ehs  = %s
                 WHERE id = %s
                """,
                (ehs_sp, d_ehs, int(trail_id)),
            )
            updated += cur.rowcount
    conn.commit()
    print(f"    Rows updated: {updated}")
    print()

    # ── [9/9] Top-5 degradation summary ──────────────────────────────────────
    print(DIV)
    print("  [9/9] TOP-5 TRAILS DEGRADING FASTEST  (highest delta_ehs)")
    print(DIV)

    ranked = sorted(
        zip(ids, names, ehs_spring_vals, ehs_summer_vals, delta_vals),
        key=lambda r: r[4],
        reverse=True,
    )

    col_w = 34
    print(f"  {'#':<3}  {'ID':<6}  {'Trail Name':<{col_w}}  "
          f"{'EHS_spring':>10}  {'EHS_summer':>10}  {'Δ_EHS':>8}")
    print(f"  {'-' * (3 + 2 + 6 + 2 + col_w + 2 + 10 + 2 + 10 + 2 + 8)}")
    for rank, (tid, name, sp, su, d) in enumerate(ranked[:5], 1):
        trail_name = (str(name) if name else "—")[:col_w]
        print(f"  {rank:<3}  {tid:<6}  {trail_name:<{col_w}}  "
              f"{sp:>10.2f}  {su:>10.2f}  {d:>+8.2f}")
    print()

    overall_mean_delta = sum(delta_vals) / len(delta_vals) if delta_vals else 0.0
    n_degrading = sum(1 for d in delta_vals if d > 0)
    print(f"  Trails with positive delta (degrading into summer): "
          f"{n_degrading} / {len(delta_vals)}")
    print(f"  Mean delta_ehs across all trails: {overall_mean_delta:+.2f}")
    print()

    conn.close()

    print(SEP)
    print("  Delta EHS calculation complete.")
    print(SEP)
    print()


if __name__ == "__main__":
    main()
