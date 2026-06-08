"""
SNTO — Operational Spatial Causality Module (SCM)
===================================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Classifies each hiking trail as LOCALIZED_IMPACT, LANDSCAPE_DRIVEN, or MIXED
by computing the Spatial Impact Gradient (SIG) directly from the real
Sentinel-2 seasonal rasters — no simulated or synthetic data.

SCIENTIFIC BASIS
================
The SIG diagnostic rests on a spatial autocorrelation principle:

  Climate forcing (drought, regional temperature anomaly) acts uniformly
  across the landscape — all buffer rings around a trail show similar NDVI.
  Human impact (trampling, path clearing, compaction) is localised — the
  trail corridor (core zone) is significantly more degraded than the
  undisturbed regional background (landscape zone), producing a gradient.

  Reference: Marion & Leung (2001), Journal of Park and Recreation
    Administration 19(3):17-37. Core impact zone for hiking trails: 0-50 m.

SIG FORMULA
===========
  SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)

  SIG > 0.15 → LOCALIZED_IMPACT   (core substantially worse than landscape)
  SIG < 0.07 → LANDSCAPE_DRIVEN   (core and landscape indistinguishable)
  else       → MIXED

  Only NDVI (band 1) is used for SIG — NDVI is the primary spatial
  discriminator for trampling impact (Pickering et al. 2011). NDMI is not
  used here; it feeds the EHS deficit formula in calculate_delta_ehs.py.

SPATIAL ZONES (in EPSG:25830, UTM zone 30N)
============================================
  Core      (0–50 m)     : direct trail footprint; captures trampling signal.
  Near      (50–200 m)   : transition zone; created for the spatial framework
                           but not used in the SIG formula.
  Landscape (200–1000 m) : regional background; assumed unaffected by trail use.

RASTERS
=======
  The same two GeoTIFFs used by calculate_delta_ehs.py:
    data/clean_assets/spring_raster.tif  (Band 1 = NDVI, Band 2 = NDMI)
    data/clean_assets/summer_raster.tif  (Band 1 = NDVI, Band 2 = NDMI)

  SIG is computed independently for each season. Classification uses
  SIG_summer because summer represents the highest-stress state and is
  the season that drives the tis_engine.py budget (EHS_SEASON_FOR_BUDGET).

  SIG_spring is written to the DB for audit and seasonal comparison only.

NULL HANDLING
=============
  Trails without raster coverage in either zone receive NULL for SIG and NULL
  for scm_classification. tis_engine.py treats NULL as MIXED (causal_factor=0.5)
  to apply a conservative budget reduction rather than zero-ing the budget for
  trails that happen to sit outside the current raster extent.

OUTPUT COLUMNS (production_hiking_trails)
==========================================
  scm_classification  TEXT   — LOCALIZED_IMPACT | MIXED | LANDSCAPE_DRIVEN | NULL
  scm_sig_spring      FLOAT  — SIG computed from spring raster (audit)
  scm_sig_summer      FLOAT  — SIG computed from summer raster (classification input)

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
from pathlib import Path

# Allow `from src.config.constants import ...` when the script is run directly.
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import geopandas as gpd
import psycopg2
import rasterio
from dotenv import load_dotenv
from pyproj import CRS as ProjCRS
from rasterstats import zonal_stats
from sqlalchemy import create_engine

from src.config.constants import (
    SCM_SIG_LOCALIZED_THRESHOLD,
    SCM_SIG_LANDSCAPE_THRESHOLD,
)

load_dotenv()

SEP = "=" * 72
DIV = "-" * 72

# ── Zone radii — match src/spatial_causality/analyzer.py ─────────────────────
CORE_OUTER_M: int = 50
NEAR_OUTER_M: int = 200
LANDSCAPE_OUTER_M: int = 1_000

BUFFER_CRS = "EPSG:25830"   # UTM zone 30N — covers mainland Spain

PROJECT_ROOT = Path(__file__).parent
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean_assets"
SPRING_PATH  = CLEAN_DIR / "spring_raster.tif"
SUMMER_PATH  = CLEAN_DIR / "summer_raster.tif"

DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
DB_USER = os.getenv("SNTO_DB_USER", "postgres")
DB_PASS = os.getenv("SNTO_DB_PASS", "")


# ── SIG math ──────────────────────────────────────────────────────────────────

def _sig(
    ndvi_landscape: float | None,
    ndvi_core: float | None,
) -> float | None:
    """
    SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)

    Measures the relative NDVI deficit of the trail corridor compared to the
    undisturbed regional background.

    SIG > 0: landscape is healthier than core (localised degradation pattern).
    SIG ≤ 0: core is at least as healthy as landscape (no localised impact).

    The denominator is floored at 0.01 to prevent division by near-zero on
    bare-soil or drought-collapsed scenes. Formula taken from
    src/spatial_causality/analyzer.py (_compute_gradient).

    Returns None when either zone lacks raster coverage.
    """
    if ndvi_landscape is None or ndvi_core is None:
        return None
    return (ndvi_landscape - ndvi_core) / max(ndvi_landscape, 0.01)


def _classify_sig(sig: float | None) -> str | None:
    """
    Single-criterion SIG threshold classifier.

    SIG > SCM_SIG_LOCALIZED_THRESHOLD (0.15) → LOCALIZED_IMPACT
        Core NDVI is substantially below landscape. The spatial gradient is
        consistent with localised vegetation disturbance from trail use
        (trampling, path clearing). The restoration budget is fully attributable
        to human pressure. Causal factor in tis_engine.py = 1.0.

    SIG < SCM_SIG_LANDSCAPE_THRESHOLD (0.07) → LANDSCAPE_DRIVEN
        All zones show similar NDVI. The degradation is regional — most likely
        climate-driven (drought, phenological suppression). Local restoration
        cannot address the root cause; investing the full budget here would be
        ineffective. Causal factor = 0.0.

    Between thresholds → MIXED
        Both localized and landscape-scale processes may be operating.
        Causal factor = 0.5 (conservative split).

    Returns None (not "MIXED") when SIG is None — preserving the distinction
    between "the SIG was computed and fell in the mixed range" and "we could
    not compute the SIG at all". tis_engine.py treats NULL as MIXED.
    """
    if sig is None:
        return None
    if sig > SCM_SIG_LOCALIZED_THRESHOLD:
        return "LOCALIZED_IMPACT"
    if sig < SCM_SIG_LANDSCAPE_THRESHOLD:
        return "LANDSCAPE_DRIVEN"
    return "MIXED"


# ── Raster extraction ─────────────────────────────────────────────────────────

def _extract_zone_ndvi(
    zone_gdf: gpd.GeoDataFrame,
    raster_path: Path,
    label: str,
) -> list[float | None]:
    """
    Extract mean NDVI (band 1) for each zone geometry via zonal statistics.

    Reprojects zone geometries to the raster CRS when needed, with the same
    LOCAL_CS guard used in calculate_delta_ehs.py: rasters with malformed
    LOCAL_CS metadata (produced by some Sentinel-2 tile processors) are
    assumed to share the same UTM 30N space as the EPSG:25830 buffers.

    Returns a list of mean values aligned to zone_gdf rows.
    Geometries with no raster overlap return None.
    """
    with rasterio.open(raster_path) as src:
        raster_crs_raw = src.crs
        raster_nodata  = src.nodata

    raster_wkt = raster_crs_raw.to_wkt()
    if "LOCAL_CS" in raster_wkt:
        crs_match = True
    else:
        try:
            raster_crs_obj = ProjCRS.from_user_input(raster_crs_raw)
            crs_match = zone_gdf.crs.equals(raster_crs_obj)
        except Exception:
            crs_match = True

    aligned = zone_gdf if crs_match else zone_gdf.to_crs(raster_wkt)

    stats = zonal_stats(
        aligned,
        str(raster_path),
        band=1,   # NDVI
        stats=["mean"],
        nodata=raster_nodata,
        all_touched=False,
    )

    means = [s.get("mean") for s in stats]
    n_null = sum(1 for v in means if v is None)
    if n_null:
        print(
            f"    [{label}] {n_null} trail(s) have no raster coverage "
            "— SIG will be NULL for those trails."
        )
    return means


# ── Raster inspector ──────────────────────────────────────────────────────────

def _inspect_raster(path: Path, label: str) -> None:
    with rasterio.open(path) as src:
        print(f"    {label}: {path.name}")
        print(f"           CRS    = {src.crs.to_string()}")
        print(f"           Size   = {src.width} px × {src.height} px")
        print(f"           Bands  = {src.count}")
        print(f"           NoData = {src.nodata}")
        print(
            f"           Bounds = ({src.bounds.left:.4f}, {src.bounds.bottom:.4f}, "
            f"{src.bounds.right:.4f}, {src.bounds.top:.4f})"
        )


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
    """Add SCM output columns if not already present."""
    cols = [
        ("scm_classification", "TEXT"),
        ("scm_sig_spring",     "FLOAT"),
        ("scm_sig_summer",     "FLOAT"),
    ]
    with conn.cursor() as cur:
        for col, col_type in cols:
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
                print(f"    Adding column '{col}' {col_type} ...")
                cur.execute(
                    f"ALTER TABLE production_hiking_trails ADD COLUMN {col} {col_type}"
                )
            else:
                print(f"    Column '{col}' already exists — will overwrite values.")
    conn.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print(SEP)
    print("  SNTO — Operational Spatial Causality Module (SCM)")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Target: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print(
        f"  Config: SIG_LOCALIZED>{SCM_SIG_LOCALIZED_THRESHOLD}  "
        f"SIG_LANDSCAPE<{SCM_SIG_LANDSCAPE_THRESHOLD}"
    )
    print(
        f"  Zones: core=0–{CORE_OUTER_M}m  "
        f"near={CORE_OUTER_M}–{NEAR_OUTER_M}m  "
        f"landscape={NEAR_OUTER_M}–{LANDSCAPE_OUTER_M}m  (EPSG:25830)"
    )
    print()

    # ── [1/9] Verify rasters ──────────────────────────────────────────────────
    print("  [1/9] Verifying seasonal raster inputs ...")
    missing = [
        (lbl, p)
        for lbl, p in [("Spring", SPRING_PATH), ("Summer", SUMMER_PATH)]
        if not p.exists()
    ]
    if missing:
        for lbl, p in missing:
            print(f"  ERROR: {lbl} raster not found at: {p}")
        print(f"  Expected location: {CLEAN_DIR}")
        print("  Run etl_raster_processor.py / prepare_raster.py first.")
        sys.exit(1)

    _inspect_raster(SPRING_PATH, "Spring")
    _inspect_raster(SUMMER_PATH, "Summer")
    print()

    # ── [2/9] Connect ─────────────────────────────────────────────────────────
    print("  [2/9] Connecting to PostGIS ...")
    try:
        conn = _connect()
    except (psycopg2.OperationalError, UnicodeDecodeError) as exc:
        print(f"  ERROR: Cannot connect — {type(exc).__name__}")
        print("  Ensure PostgreSQL is running and credentials are correct.")
        print("  Override via env vars: SNTO_DB_HOST / PORT / NAME / USER / PASS")
        sys.exit(1)

    major, minor = divmod(conn.server_version, 10000)
    print(f"  Connected. PostgreSQL {major}.{minor}")
    print()

    # ── [3/9] Ensure columns ──────────────────────────────────────────────────
    print("  [3/9] Ensuring scm_classification / scm_sig_spring / scm_sig_summer ...")
    _ensure_columns(conn)
    print()

    # ── [4/9] Load trails ─────────────────────────────────────────────────────
    print("  [4/9] Loading hiking trails from PostGIS ...")
    engine = _engine()
    try:
        trails_gdf = gpd.read_postgis(
            "SELECT id, name, geometry FROM production_hiking_trails ORDER BY id",
            con=engine,
            geom_col="geometry",
            crs="EPSG:4326",
        )
    finally:
        engine.dispose()

    n_total = len(trails_gdf)
    valid_mask = trails_gdf.geometry.notna() & ~trails_gdf.geometry.is_empty
    trails_gdf = trails_gdf[valid_mask].copy()
    n_valid = len(trails_gdf)
    if n_total != n_valid:
        print(f"    Dropped {n_total - n_valid} null/empty geometries. {n_valid} remain.")
    else:
        print(f"    Loaded {n_valid} features from production_hiking_trails")
    print()

    # ── [5/9] Build zone buffers in EPSG:25830 ────────────────────────────────
    print(
        f"  [5/9] Building core (0–{CORE_OUTER_M} m) and "
        f"landscape ({NEAR_OUTER_M}–{LANDSCAPE_OUTER_M} m) buffers ..."
    )
    utm = trails_gdf.to_crs(BUFFER_CRS)

    # Core: simple buffer to CORE_OUTER_M
    core_gdf = utm.copy()
    core_gdf["geometry"] = utm.geometry.buffer(CORE_OUTER_M)

    # Landscape: annular ring from NEAR_OUTER_M to LANDSCAPE_OUTER_M.
    # The inner hole removes the near zone so that only the true regional
    # background pixels (200–1000 m from the trail axis) feed the SIG.
    outer_ring = utm.geometry.buffer(LANDSCAPE_OUTER_M)
    inner_hole = utm.geometry.buffer(NEAR_OUTER_M)
    landscape_gdf = utm.copy()
    landscape_gdf["geometry"] = outer_ring.difference(inner_hole)

    n_core_empty = core_gdf.geometry.is_empty.sum()
    n_land_empty = landscape_gdf.geometry.is_empty.sum()
    if n_core_empty or n_land_empty:
        print(
            f"    WARNING: {n_core_empty} empty core, {n_land_empty} empty landscape "
            "buffer(s) — those trails will produce NULL SIG."
        )
    print(f"    Zone geometries built for {len(core_gdf)} trails.")
    print()

    # ── [6/9] Extract NDVI by zone and season ─────────────────────────────────
    print("  [6/9] Extracting zonal mean NDVI (band 1) for all zones and seasons ...")
    spring_core_ndvi = _extract_zone_ndvi(core_gdf,      SPRING_PATH, "Spring core")
    spring_land_ndvi = _extract_zone_ndvi(landscape_gdf, SPRING_PATH, "Spring landscape")
    summer_core_ndvi = _extract_zone_ndvi(core_gdf,      SUMMER_PATH, "Summer core")
    summer_land_ndvi = _extract_zone_ndvi(landscape_gdf, SUMMER_PATH, "Summer landscape")
    print(
        f"    Spring core    non-null: {sum(v is not None for v in spring_core_ndvi)}"
        f" / {len(spring_core_ndvi)}"
    )
    print(
        f"    Spring landscape non-null: {sum(v is not None for v in spring_land_ndvi)}"
        f" / {len(spring_land_ndvi)}"
    )
    print(
        f"    Summer core    non-null: {sum(v is not None for v in summer_core_ndvi)}"
        f" / {len(summer_core_ndvi)}"
    )
    print(
        f"    Summer landscape non-null: {sum(v is not None for v in summer_land_ndvi)}"
        f" / {len(summer_land_ndvi)}"
    )
    print()

    # ── [7/9] Compute SIG per trail ───────────────────────────────────────────
    print("  [7/9] Computing SIG_spring and SIG_summer per trail ...")
    sig_spring_vals = [
        _sig(land, core)
        for land, core in zip(spring_land_ndvi, spring_core_ndvi)
    ]
    sig_summer_vals = [
        _sig(land, core)
        for land, core in zip(summer_land_ndvi, summer_core_ndvi)
    ]
    n_sig_ok = sum(1 for s in sig_summer_vals if s is not None)
    print(f"    SIG_summer computed: {n_sig_ok} / {len(sig_summer_vals)}")
    print()

    # ── [8/9] Classify and write to PostGIS ───────────────────────────────────
    print("  [8/9] Classifying by SIG_summer and writing to PostGIS ...")
    classifications = [_classify_sig(s) for s in sig_summer_vals]

    ids   = trails_gdf["id"].tolist()
    names = trails_gdf["name"].tolist()

    updated = 0
    with conn.cursor() as cur:
        for trail_id, cls, sig_sp, sig_su in zip(
            ids, classifications, sig_spring_vals, sig_summer_vals
        ):
            cur.execute(
                """
                UPDATE production_hiking_trails
                   SET scm_classification = %s,
                       scm_sig_spring     = %s,
                       scm_sig_summer     = %s
                 WHERE id = %s
                """,
                (cls, sig_sp, sig_su, int(trail_id)),
            )
            updated += cur.rowcount
    conn.commit()
    print(f"    Rows updated: {updated}")
    print()

    # ── [9/9] Summary ─────────────────────────────────────────────────────────
    counts: dict[str, int] = {
        "LOCALIZED_IMPACT":  0,
        "MIXED":             0,
        "LANDSCAPE_DRIVEN":  0,
        "NULL":              0,
    }
    for c in classifications:
        counts[c if c is not None else "NULL"] += 1

    print(DIV)
    print("  [9/9] SCM CLASSIFICATION SUMMARY")
    print(DIV)
    print(f"  LOCALIZED_IMPACT  : {counts['LOCALIZED_IMPACT']:>4}  "
          "(human pressure — full causal budget)")
    print(f"  MIXED             : {counts['MIXED']:>4}  "
          "(ambiguous — half causal budget)")
    print(f"  LANDSCAPE_DRIVEN  : {counts['LANDSCAPE_DRIVEN']:>4}  "
          "(climate forcing — zero causal budget)")
    print(f"  NULL (no data)    : {counts['NULL']:>4}  "
          "(treated as MIXED by tis_engine.py)")
    print()

    # Top-5 by SIG_summer (most localized impact)
    sortable = [
        (tid, name, sig_su, cls)
        for tid, name, sig_su, cls
        in zip(ids, names, sig_summer_vals, classifications)
        if sig_su is not None
    ]
    ranked = sorted(sortable, key=lambda r: r[2], reverse=True)

    if ranked:
        col_w = 36
        print(f"  TOP-5 TRAILS BY SIG_SUMMER  (highest localized impact signal)")
        print(
            f"  {'#':<3}  {'ID':<6}  {'Trail Name':<{col_w}}  "
            f"{'SIG_summer':>10}  {'Classification':<18}"
        )
        print(f"  {'-' * (3 + 2 + 6 + 2 + col_w + 2 + 10 + 2 + 18)}")
        for rank, (tid, name, sig_su, cls) in enumerate(ranked[:5], 1):
            trail_name = (str(name) if name else "—")[:col_w]
            cls_str = cls if cls is not None else "NULL"
            print(
                f"  {rank:<3}  {tid:<6}  {trail_name:<{col_w}}  "
                f"{sig_su:>10.5f}  {cls_str:<18}"
            )
    print()

    conn.close()

    print(SEP)
    print("  SCM operational classification complete.")
    print("  Run tis_engine.py next to apply causal budget factors.")
    print(SEP)
    print()


if __name__ == "__main__":
    main()
