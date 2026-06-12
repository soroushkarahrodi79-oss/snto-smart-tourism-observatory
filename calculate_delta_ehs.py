"""
SNTO — Delta EHS Calculator
============================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Computes the seasonal Environmental Stress Score for each hiking trail using
spring and summer Sentinel-2 composite rasters, then writes the degradation
delta back to the PostGIS production table.

Naming note: the legacy database columns are still named ehs_spring,
ehs_summer, and delta_ehs for compatibility, but their convention is STRESS:
0 = no stress, 100 = maximum degradation. Dashboard health scores are derived
as health = 100 - stress in src.metrics.semantics.

Workflow:
   1. Verify GeoTIFF inputs (spring_raster.tif, summer_raster.tif)
   2. Connect to PostGIS
   3. Ensure output columns exist (ehs_spring, ehs_summer, delta_ehs)
   4. Load hiking trails from production_hiking_trails
   5. Buffer each trail 50 m in UTM (EPSG:25830)
   6. Compute scene-level baselines per season and per index (NDVI, NDMI):
        baseline_sano = P_BASE percentile of valid scene pixels
        suelo         = P_FLOOR percentile of valid scene pixels
      Pixels excluded from this computation:
        (a) SCL-classified non-vegetation pixels (if spring_scl.tif /
            summer_scl.tif are present in clean_assets/):
              3 = cloud shadows, 5 = bare soil / rock, 6 = water,
              8 = cloud medium probability, 9 = cloud high probability,
              10 = thin cirrus.
            Sentinel-2 L2A SCL (Sen2Cor) has no explicit "urban/built-up"
            class; class 7 (Unclassified) is intentionally retained to avoid
            masking legitimate vegetation pixels.
        (b) Pixels inside the 50 m buffer of any hiking trail — these are
            the very pixels whose stress we measure; including them in the
            reference distribution would pull the baseline down.
   7. Extract mean NDVI (band 1) + mean NDMI (band 2) per trail buffer,
      both seasons.
   8. Compute per-trail EHS for each season:
        D = clamp((baseline_sano − observed) / (baseline_sano − suelo), 0, 1)
        EHS = 100 × (W_NDVI × D_ndvi + W_NDMI × D_ndmi)
      EHS = 0 → observation at or above baseline_sano (no stress).
      EHS = 100 → observation at or below suelo (maximum degradation).
   9. Compute delta_ehs = EHS_summer − EHS_spring
      (positive = ecosystem degrading from spring to summer)
  10. Write ehs_spring, ehs_summer, delta_ehs to PostGIS
  11. Print top-5 fastest-degrading trails

Configuration (src/config/constants.py — change values there, not here):
  EHS_P_BASE            = 90     # percentile for healthy reference
  EHS_P_FLOOR           = 10     # percentile for degraded floor
  EHS_W_NDVI            = 0.5    # NDVI deficit weight
  EHS_W_NDMI            = 0.5    # NDMI deficit weight
  EHS_SEASON_FOR_BUDGET = "summer"  # season feeding tis_engine.py

Raster convention:
  Each seasonal GeoTIFF must contain exactly two bands:
    Band 1 → NDVI  (float, [-1, 1])
    Band 2 → NDMI  (float, [-1, 1])
  Optional SCL GeoTIFFs (spring_scl.tif, summer_scl.tif) in clean_assets/:
    single-band, integer class raster, aligned to the same Sentinel-2 tile.
    If absent, SCL masking is skipped and a warning is printed.

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

# Allow `from src.config.constants import ...` when the script is run directly
# from the project root (project root is always the parent of this file).
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np
import geopandas as gpd
import psycopg2
import rasterio
import rasterio.enums
from dotenv import load_dotenv
from pyproj import CRS as ProjCRS
from rasterio.features import geometry_mask
from rasterstats import zonal_stats
from shapely.ops import unary_union
from sqlalchemy import create_engine

from src.config.constants import (
    EHS_P_BASE,
    EHS_P_FLOOR,
    EHS_W_NDVI,
    EHS_W_NDMI,
    EHS_SEASON_FOR_BUDGET,
    EHS_DENSE_CANOPY_NDVI_THRESHOLD,
    EHS_W_NDVI_DENSE,
    EHS_W_NDMI_DENSE,
)

load_dotenv()  # carga .env antes de os.getenv() a nivel de módulo

SEP = "=" * 72
DIV = "-" * 72

# SCL classes that indicate non-vegetated or obscured pixels.
# Excluded so that bare rock, water, and clouds do not pull the healthy
# reference percentile downward.
_SCL_EXCLUDE: frozenset[int] = frozenset({3, 5, 6, 8, 9, 10})

PROJECT_ROOT = Path(__file__).parent
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean_assets"

SPRING_PATH     = CLEAN_DIR / "spring_raster.tif"
SUMMER_PATH     = CLEAN_DIR / "summer_raster.tif"
SPRING_SCL_PATH = CLEAN_DIR / "spring_scl.tif"   # optional — skipped if absent
SUMMER_SCL_PATH = CLEAN_DIR / "summer_scl.tif"   # optional — skipped if absent

BUFFER_M   = 50
BUFFER_CRS = "EPSG:25830"   # UTM zone 30N — covers mainland Spain

DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
DB_USER = os.getenv("SNTO_DB_USER", "postgres")
DB_PASS = os.getenv("SNTO_DB_PASS", "")


# ── EHS math ──────────────────────────────────────────────────────────────────

def _deficit(observed: float, baseline: float, floor: float) -> float:
    """
    D = clamp((baseline − observed) / (baseline − floor), 0, 1)

    Measures how far the observed value has dropped below the scene's healthy
    reference, scaled to the full degradation range (baseline → floor).

    D = 0  → observation at or above baseline_sano (no stress).
    D = 1  → observation at or below suelo (maximally degraded).

    The denominator (baseline − floor) is derived from the real pixel
    distribution of each scene, so D is always relative to what healthy
    vegetation looks like in this specific territory and season — never to an
    external universal constant.

    Returns 0.0 when baseline ≤ floor (degenerate / flat distribution).
    """
    if baseline <= floor:
        return 0.0
    return max(0.0, min(1.0, (baseline - observed) / (baseline - floor)))


def _trail_stress_score(
    ndvi_obs: float | None,
    ndmi_obs: float | None,
    ndvi_baseline: float,
    ndvi_floor: float,
    ndmi_baseline: float,
    ndmi_floor: float,
    w_ndvi: float = EHS_W_NDVI,
    w_ndmi: float = EHS_W_NDMI,
) -> float | None:
    """
    stress = 100 x (W_NDVI x D_ndvi + W_NDMI x D_ndmi)

    The baselines passed in are the scene-level P_BASE / P_FLOOR percentiles
    for the season being evaluated (spring or summer), computed exclusively
    from pixels that are neither SCL-masked nor inside trail buffers.

    stress = 0   -> both indices at their season's healthy reference.
    stress = 100 -> both indices at their season's degraded floor.

    Dense-canopy dynamic weight rule:
    When the trail buffer's mean NDVI exceeds EHS_DENSE_CANOPY_NDVI_THRESHOLD
    (default 0.80), NDVI saturates and loses sensitivity to sub-canopy stress.
    The weights are automatically switched to EHS_W_NDVI_DENSE / EHS_W_NDMI_DENSE
    so that NDMI (moisture stress) dominates in this regime.

    Returns None when both inputs are missing.
    When only one index is available, it carries full weight so the result
    stays in [0, 100] rather than collapsing to half-scale.
    """
    if ndvi_obs is None and ndmi_obs is None:
        return None

    # Dense-canopy saturation guard: upweight NDMI when NDVI is in saturation zone
    if ndvi_obs is not None and ndvi_obs > EHS_DENSE_CANOPY_NDVI_THRESHOLD:
        w_ndvi = EHS_W_NDVI_DENSE
        w_ndmi = EHS_W_NDMI_DENSE

    d_ndvi = _deficit(ndvi_obs, ndvi_baseline, ndvi_floor) if ndvi_obs is not None else None
    d_ndmi = _deficit(ndmi_obs, ndmi_baseline, ndmi_floor) if ndmi_obs is not None else None

    if d_ndvi is not None and d_ndmi is not None:
        raw = w_ndvi * d_ndvi + w_ndmi * d_ndmi
    elif d_ndvi is not None:
        raw = d_ndvi   # single index — rescaled to maintain [0, 1]
    else:
        raw = d_ndmi   # type: ignore[assignment]

    return round(raw * 100.0, 4)


def _trail_ehs(*args, **kwargs) -> float | None:
    """Backward-compatible alias for the Pipeline A stress score.

    Historical tests and scripts import ``_trail_ehs``. Keep that API stable,
    but route all new code through ``_trail_stress_score`` so the score
    direction is explicit at the call site.
    """
    return _trail_stress_score(*args, **kwargs)


# ── Scene baseline computation ────────────────────────────────────────────────

def _compute_scene_baselines(
    raster_path: Path,
    band: int,
    trail_buffers_gdf: gpd.GeoDataFrame,
    scl_path: Path | None,
    p_base: int = EHS_P_BASE,
    p_floor: int = EHS_P_FLOOR,
) -> tuple[float, float]:
    """
    Derive the per-scene healthy reference (baseline_sano) and degraded floor
    (suelo) percentiles for one spectral band, using only pixels that represent
    undisturbed background vegetation.

    Exclusion pipeline (applied in this order):
      1. Raster NoData: pixels tagged with the band's NoData value, or
         non-finite values when no NoData tag exists.
      2. SCL classification: classes 3 (cloud shadows), 5 (bare soil / rock),
         6 (water), 8 (cloud medium probability), 9 (cloud high probability),
         10 (thin cirrus).  Skipped when scl_path is None or file is absent.
         Class 7 (Unclassified) is intentionally retained — it sometimes
         contains valid vegetation, and Sentinel-2 L2A SCL has no explicit
         "urban/built-up" class that would make exclusion unambiguous.
      3. Trail buffers: pixels inside the 50 m buffer around any hiking trail.
         These are the pixels whose health we are trying to measure; leaving
         them in the reference pool would artificially depress the baseline
         when trails are already degraded.

    Parameters
    ----------
    p_base  : scene percentile that defines baseline_sano (e.g. 90 → P90).
              P90 captures the upper end of vegetation vigour present in this
              specific scene and season without being skewed by outliers.
    p_floor : scene percentile that defines suelo (e.g. 10 → P10).
              P10 captures the lower end of the valid vegetation distribution,
              representing the worst background condition in this scene.

    Returns
    -------
    (baseline_sano, suelo) — both as float, in the native index units.

    Raises
    ------
    ValueError if fewer than 100 valid pixels remain after masking — this
    signals that the raster does not cover the study area or that the SCL
    mask is too aggressive.
    """
    with rasterio.open(raster_path) as src:
        data      = src.read(band).astype(np.float32)
        transform = src.transform
        crs       = src.crs
        nodata    = src.nodata
        height, width = data.shape

    # mask 1: NoData
    invalid = (data == nodata) if nodata is not None else ~np.isfinite(data)

    # mask 2: SCL
    if scl_path is not None:
        if scl_path.exists():
            with rasterio.open(scl_path) as scl_src:
                # Read SCL resampled to the target band's grid so both arrays
                # share the same (height, width).  Nearest-neighbour is correct
                # for a classification raster (no interpolation of class codes).
                scl_data = scl_src.read(
                    1,
                    out_shape=(height, width),
                    resampling=rasterio.enums.Resampling.nearest,
                )
            invalid |= np.isin(scl_data, list(_SCL_EXCLUDE))
        else:
            print(
                f"    WARNING: SCL file not found at {scl_path.name} — "
                "SCL masking skipped for this season."
            )

    # mask 3: trail buffers — pixels that overlap any 50 m buffer are excluded
    # so that degraded trail corridors do not contaminate the reference pool.
    raster_wkt = crs.to_wkt()
    if "LOCAL_CS" in raster_wkt:
        # Malformed LOCAL_CS metadata from some Sentinel-2 tile processors;
        # the raster is confirmed to share the same UTM 30N space as the buffers.
        buffers_aligned = trail_buffers_gdf
    else:
        try:
            raster_crs_obj = ProjCRS.from_user_input(crs)
            buffers_aligned = (
                trail_buffers_gdf
                if trail_buffers_gdf.crs.equals(raster_crs_obj)
                else trail_buffers_gdf.to_crs(raster_wkt)
            )
        except Exception:
            buffers_aligned = trail_buffers_gdf

    buffer_union = unary_union(buffers_aligned.geometry.values)
    if buffer_union is not None and not buffer_union.is_empty:
        trail_px_mask = geometry_mask(
            [buffer_union],
            out_shape=(height, width),
            transform=transform,
            invert=True,    # True inside buffer → pixels to exclude
            all_touched=False,
        )
        invalid |= trail_px_mask

    valid_pixels = data[~invalid].ravel()
    n_valid = int(valid_pixels.size)
    n_total = int(data.size)
    pct = 100.0 * n_valid / n_total if n_total else 0.0
    print(
        f"    Band {band}: {n_valid:,} valid pixels "
        f"({pct:.1f}% of scene, after SCL + buffer exclusion)"
    )

    if n_valid < 100:
        raise ValueError(
            f"Too few valid pixels ({n_valid}) to compute reliable baselines "
            f"for band {band} of '{raster_path.name}'. "
            "Verify the raster covers the study area and check SCL masks."
        )

    baseline_sano = float(np.percentile(valid_pixels, p_base))
    suelo         = float(np.percentile(valid_pixels, p_floor))
    print(f"      P{p_base}  baseline_sano = {baseline_sano:.4f}")
    print(f"      P{p_floor}  suelo         = {suelo:.4f}")

    return baseline_sano, suelo


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
    """Add ehs_spring / ehs_summer / delta_ehs FLOAT columns if not present."""
    with conn.cursor() as cur:
        for col in ("ehs_spring", "ehs_summer", "delta_ehs"):
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
        print(
            f"           Bounds = ({src.bounds.left:.4f}, {src.bounds.bottom:.4f}, "
            f"{src.bounds.right:.4f}, {src.bounds.top:.4f})"
        )


def _extract_band(
    buffers_gdf: gpd.GeoDataFrame,
    raster_path: Path,
    band: int,
    label: str,
) -> list[float | None]:
    """
    Reproject buffers to the raster's CRS if needed, then run zonal_stats on
    a single band. Returns mean values aligned to buffers_gdf rows.
    Geometries entirely outside the raster extent return None.
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
            crs_match = buffers_gdf.crs.equals(raster_crs_obj)
        except Exception:
            crs_match = True

    aligned = buffers_gdf if crs_match else buffers_gdf.to_crs(raster_wkt)

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
        print(
            f"    [{label}] {n_null} trail(s) outside raster extent — "
            "will contribute None to EHS (excluded from formula)."
        )
    return means


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(SEP)
    print("  SNTO — Delta EHS Calculator")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Target: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print(
        f"  Config: P_BASE={EHS_P_BASE}  P_FLOOR={EHS_P_FLOOR}  "
        f"W_NDVI={EHS_W_NDVI}  W_NDMI={EHS_W_NDMI}  "
        f"SEASON_FOR_BUDGET={EHS_SEASON_FOR_BUDGET!r}"
    )
    print()

    # ── [1/10] Verify raster inputs ───────────────────────────────────────────
    print("  [1/10] Verifying seasonal raster inputs ...")
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
    for scl_p, lbl in [
        (SPRING_SCL_PATH, "Spring SCL"),
        (SUMMER_SCL_PATH, "Summer SCL"),
    ]:
        if scl_p.exists():
            _inspect_raster(scl_p, lbl)
        else:
            print(
                f"    {lbl}: not found ({scl_p.name}) — "
                "SCL masking will be skipped for this season."
            )
    print()

    # ── [2/10] Connect to PostGIS ─────────────────────────────────────────────
    print("  [2/10] Connecting to PostGIS ...")
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

    # ── [3/10] Ensure output columns ──────────────────────────────────────────
    print("  [3/10] Ensuring ehs_spring / ehs_summer / delta_ehs columns exist ...")
    _ensure_columns(conn)
    print()

    # ── [4/10] Load hiking trails ─────────────────────────────────────────────
    print("  [4/10] Loading hiking trails from PostGIS ...")
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
    print(f"    Native CRS: {trails_gdf.crs.to_string()}")
    print()

    # ── [5/10] Project to UTM and buffer ──────────────────────────────────────
    print(f"  [5/10] Projecting to {BUFFER_CRS} and creating {BUFFER_M} m buffers ...")
    projected   = trails_gdf.to_crs(BUFFER_CRS)
    buffers_gdf = projected.copy()
    buffers_gdf["geometry"] = projected.geometry.buffer(BUFFER_M)

    n_empty = buffers_gdf.geometry.is_empty.sum()
    if n_empty:
        print(f"    WARNING: {n_empty} buffer(s) are unexpectedly empty.")
    print(f"    Buffers created: {len(buffers_gdf)}")
    print()

    # ── [6/10] Scene baselines — spring ───────────────────────────────────────
    print("  [6/10] Computing scene baselines for spring raster ...")
    spring_ndvi_baseline, spring_ndvi_floor = _compute_scene_baselines(
        SPRING_PATH, band=1, trail_buffers_gdf=buffers_gdf,
        scl_path=SPRING_SCL_PATH,
    )
    spring_ndmi_baseline, spring_ndmi_floor = _compute_scene_baselines(
        SPRING_PATH, band=2, trail_buffers_gdf=buffers_gdf,
        scl_path=SPRING_SCL_PATH,
    )
    print()

    # ── [7/10] Scene baselines — summer ───────────────────────────────────────
    print("  [7/10] Computing scene baselines for summer raster ...")
    summer_ndvi_baseline, summer_ndvi_floor = _compute_scene_baselines(
        SUMMER_PATH, band=1, trail_buffers_gdf=buffers_gdf,
        scl_path=SUMMER_SCL_PATH,
    )
    summer_ndmi_baseline, summer_ndmi_floor = _compute_scene_baselines(
        SUMMER_PATH, band=2, trail_buffers_gdf=buffers_gdf,
        scl_path=SUMMER_SCL_PATH,
    )
    print()

    # ── [8/10] Zonal statistics per trail buffer ──────────────────────────────
    print("  [8/10] Extracting zonal means per trail buffer ...")
    spring_ndvi = _extract_band(buffers_gdf, SPRING_PATH, band=1, label="Spring NDVI")
    spring_ndmi = _extract_band(buffers_gdf, SPRING_PATH, band=2, label="Spring NDMI")
    summer_ndvi = _extract_band(buffers_gdf, SUMMER_PATH, band=1, label="Summer NDVI")
    summer_ndmi = _extract_band(buffers_gdf, SUMMER_PATH, band=2, label="Summer NDMI")
    print(f"    Spring NDVI non-null: {sum(v is not None for v in spring_ndvi)} / {len(spring_ndvi)}")
    print(f"    Spring NDMI non-null: {sum(v is not None for v in spring_ndmi)} / {len(spring_ndmi)}")
    print(f"    Summer NDVI non-null: {sum(v is not None for v in summer_ndvi)} / {len(summer_ndvi)}")
    print(f"    Summer NDMI non-null: {sum(v is not None for v in summer_ndmi)} / {len(summer_ndmi)}")
    print()

    # ── [9/10] Compute EHS and write to PostGIS ───────────────────────────────
    print(
        "  [9/10] Computing EHS_spring, EHS_summer, delta_ehs "
        "and writing to PostGIS ..."
    )

    ids   = trails_gdf["id"].tolist()
    names = trails_gdf["name"].tolist()

    stress_spring_vals = [
        _trail_stress_score(
            n, m,
            spring_ndvi_baseline, spring_ndvi_floor,
            spring_ndmi_baseline, spring_ndmi_floor,
        )
        for n, m in zip(spring_ndvi, spring_ndmi)
    ]
    stress_summer_vals = [
        _trail_stress_score(
            n, m,
            summer_ndvi_baseline, summer_ndvi_floor,
            summer_ndmi_baseline, summer_ndmi_floor,
        )
        for n, m in zip(summer_ndvi, summer_ndmi)
    ]
    delta_vals = [
        round(su - sp, 4) if su is not None and sp is not None else None
        for sp, su in zip(stress_spring_vals, stress_summer_vals)
    ]

    updated = 0
    with conn.cursor() as cur:
        for trail_id, stress_sp, stress_su, d_ehs in zip(
            ids, stress_spring_vals, stress_summer_vals, delta_vals
        ):
            cur.execute(
                """
                UPDATE production_hiking_trails
                   SET ehs_spring = %s,
                       ehs_summer = %s,
                       delta_ehs  = %s
                 WHERE id = %s
                """,
                (stress_sp, stress_su, d_ehs, int(trail_id)),
            )
            updated += cur.rowcount
    conn.commit()
    print(f"    Rows updated: {updated}")
    print()

    # ── [10/10] Top-5 degradation summary ─────────────────────────────────────
    print(DIV)
    print("  [10/10] TOP-5 TRAILS DEGRADING FASTEST  (highest delta_ehs)")
    print(DIV)

    sortable = [
        (tid, name, sp, su, d)
        for tid, name, sp, su, d
        in zip(ids, names, stress_spring_vals, stress_summer_vals, delta_vals)
        if d is not None
    ]
    ranked = sorted(sortable, key=lambda r: r[4], reverse=True)

    col_w = 34
    print(
        f"  {'#':<3}  {'ID':<6}  {'Trail Name':<{col_w}}  "
        f"{'EHS_spring':>10}  {'EHS_summer':>10}  {'Δ_EHS':>8}"
    )
    print(f"  {'-' * (3 + 2 + 6 + 2 + col_w + 2 + 10 + 2 + 10 + 2 + 8)}")
    for rank, (tid, name, sp, su, d) in enumerate(ranked[:5], 1):
        trail_name = (str(name) if name else "—")[:col_w]
        sp_str = f"{sp:.2f}" if sp is not None else "N/A"
        su_str = f"{su:.2f}" if su is not None else "N/A"
        print(
            f"  {rank:<3}  {tid:<6}  {trail_name:<{col_w}}  "
            f"{sp_str:>10}  {su_str:>10}  {d:>+8.2f}"
        )
    print()

    valid_deltas = [d for d in delta_vals if d is not None]
    if valid_deltas:
        n_degrading = sum(1 for d in valid_deltas if d > 0)
        mean_delta  = sum(valid_deltas) / len(valid_deltas)
        print(
            f"  Trails degrading into summer (positive Δ): "
            f"{n_degrading} / {len(valid_deltas)}"
        )
        print(f"  Mean delta_ehs across all trails: {mean_delta:+.2f}")
    print()

    conn.close()

    print(SEP)
    print("  Delta EHS calculation complete.")
    print(SEP)
    print()


if __name__ == "__main__":
    main()
