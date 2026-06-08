"""
SNTO TIS Engine -- Environmental Health Stress & Investment Simulator
======================================================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

For each hiking trail in production_hiking_trails this script:
  1. Reads avg_ndvi, avg_ndmi, annual_visitors and precise trail length
     (PostGIS ST_Length)
  2. Computes Environmental Health Stress (EHS) index  [0–100]
       EHS = ((1 - norm_ndvi) + (1 - norm_ndmi)) / 2 * 100
       norm_ndvi = clamp(avg_ndvi, 0, 1)
       norm_ndmi = clamp((avg_ndmi + 1) / 2, 0, 1)   [maps -1…1 → 0…1]
       Trails missing both spectral values receive NULL EHS.
  3. Computes traffic_index by normalising annual_visitors to [0, 100]
       traffic_index = (visitors - min) / (max - min) * 100
       NULL annual_visitors are treated as 0.
  4. Computes priority_score = (EHS × 0.60) + (traffic_index × 0.40)
       Trails with NULL EHS receive NULL priority_score.
  5. Sets needs_intervention = True when priority_score > 60
  6. Computes tis_budget_eur = length_m × 15.50 EUR/m × (priority_score / 100)
       Non-critical trails receive a budget of 0.
  7. Writes results back to the database and prints a management report.

Credentials (env vars with fallbacks):
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

import psycopg2
from psycopg2.extras import execute_values

SEP = "=" * 72
DIV = "-" * 72

# ── Thresholds, weights & cost constants ──────────────────────────────────────
PRIORITY_CRITICAL_THRESHOLD: float = 60.0
EHS_WEIGHT: float = 0.60
TRAFFIC_WEIGHT: float = 0.40
BASE_RESTORATION_COST_EUR_PER_M: float = 15.50

# ── Credentials (override via environment variables) ──────────────────────────
DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
DB_USER = os.getenv("SNTO_DB_USER", "postgres")
DB_PASS = os.getenv("SNTO_DB_PASS", "")


# ── Connection helper ─────────────────────────────────────────────────────────

def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        connect_timeout=10,
    )


# ── Schema helper ─────────────────────────────────────────────────────────────

def _ensure_columns(conn: psycopg2.extensions.connection) -> None:
    """Add output columns to production_hiking_trails if not already present."""
    new_cols = [
        ("ehs_index",          "FLOAT"),
        ("needs_intervention", "BOOLEAN"),
        ("tis_budget_eur",     "FLOAT"),
        ("priority_score",     "FLOAT"),
    ]
    with conn.cursor() as cur:
        for col, col_type in new_cols:
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


# ── EHS algorithm ─────────────────────────────────────────────────────────────

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _compute_ehs(avg_ndvi: float | None, avg_ndmi: float | None) -> float | None:
    """
    Returns EHS in [0, 100] — higher means more environmental stress.
    Returns None when both spectral inputs are absent.

    Normalisation:
      NDVI is already in [0, 1] for vegetated surfaces — clamp to [0, 1].
      NDMI lives in [-1, 1] — shift/scale to [0, 1] via (ndmi + 1) / 2.
    """
    if avg_ndvi is None and avg_ndmi is None:
        return None

    if avg_ndvi is not None:
        norm_ndvi   = _clamp(avg_ndvi)
        stress_ndvi: float | None = 1.0 - norm_ndvi
    else:
        stress_ndvi = None

    if avg_ndmi is not None:
        norm_ndmi   = _clamp((avg_ndmi + 1.0) / 2.0)
        stress_ndmi: float | None = 1.0 - norm_ndmi
    else:
        stress_ndmi = None

    if stress_ndvi is not None and stress_ndmi is not None:
        raw_stress = (stress_ndvi + stress_ndmi) / 2.0
    elif stress_ndvi is not None:
        raw_stress = stress_ndvi
    else:
        raw_stress = stress_ndmi  # type: ignore[assignment]

    return round(raw_stress * 100.0, 2)


# ── Demand normalisation ──────────────────────────────────────────────────────

def _traffic_index(visitors: int | None, min_v: int, max_v: int) -> float:
    """
    Normalise annual_visitors to [0, 100].
    NULL visitors → 0.  Flat distribution (all equal) → 0.
    """
    if visitors is None or max_v == min_v:
        return 0.0
    return round((visitors - min_v) / (max_v - min_v) * 100.0, 2)


# ── Priority & TIS algorithm ──────────────────────────────────────────────────

def _compute_priority(ehs: float | None, ti: float) -> float | None:
    """
    priority_score = (EHS × 0.60) + (traffic_index × 0.40)
    Returns None when EHS is unavailable (no spectral data).
    """
    if ehs is None:
        return None
    return round(ehs * EHS_WEIGHT + ti * TRAFFIC_WEIGHT, 2)


def _compute_tis(priority_score: float | None, length_m: float) -> tuple[bool, float]:
    """Returns (needs_intervention, tis_budget_eur) using priority_score as severity."""
    if priority_score is None or priority_score <= PRIORITY_CRITICAL_THRESHOLD:
        return False, 0.0
    budget = length_m * BASE_RESTORATION_COST_EUR_PER_M * (priority_score / 100.0)
    return True, round(budget, 2)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("  SNTO TIS Engine -- Environmental Health Stress & Investment Simulator")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Target: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print()

    # ── [1/5] Connect ─────────────────────────────────────────────────────────
    print("  [1/5] Connecting to PostgreSQL ...")
    try:
        conn = _connect()
    except (psycopg2.OperationalError, UnicodeDecodeError) as exc:
        print()
        print("  ERROR: Cannot reach the PostgreSQL server.")
        print(f"  Detail: {type(exc).__name__} — server may not be running.")
        print()
        print("  To resolve:")
        print("    1. Start PostgreSQL via pgAdmin or Windows Services")
        print("    2. Override credentials via env vars if needed:")
        print("         SNTO_DB_HOST  SNTO_DB_PORT  SNTO_DB_NAME  SNTO_DB_USER  SNTO_DB_PASS")
        print("    3. Run etl_tourist_traffic.py, then re-run this script.")
        sys.exit(1)

    major, minor = divmod(conn.server_version, 10000)
    print(f"  Connected to '{DB_NAME}'. PostgreSQL {major}.{minor}")
    print()

    try:
        # ── [2/5] Ensure output columns ───────────────────────────────────────
        print("  [2/5] Ensuring output columns exist ...")
        _ensure_columns(conn)
        print()

        # ── [3/5] Fetch trail data ─────────────────────────────────────────────
        print(
            "  [3/5] Fetching trails with spectral indices, "
            "visitor counts and PostGIS lengths ..."
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    name,
                    avg_ndvi,
                    avg_ndmi,
                    annual_visitors,
                    ST_Length(geometry::geography) AS length_m
                FROM production_hiking_trails
                ORDER BY id
                """
            )
            rows = cur.fetchall()

        n_total    = len(rows)
        n_ndvi     = sum(1 for r in rows if r[2] is not None)
        n_ndmi     = sum(1 for r in rows if r[3] is not None)
        n_visitors = sum(1 for r in rows if r[4] is not None)
        print(f"    Trails fetched       : {n_total}")
        print(f"    With avg_ndvi        : {n_ndvi}")
        print(f"    With avg_ndmi        : {n_ndmi}")
        print(f"    With annual_visitors : {n_visitors}")
        print()

        if n_total == 0:
            print("  WARNING: No trails found. Run db_production_seeder.py,")
            print("  etl_raster_intersection.py and etl_tourist_traffic.py first.")
            sys.exit(0)

        # Visitor bounds for dataset-level normalisation
        visitor_values = [r[4] for r in rows if r[4] is not None]
        min_v = min(visitor_values) if visitor_values else 0
        max_v = max(visitor_values) if visitor_values else 0

        # ── [4/5] Compute and batch-update ────────────────────────────────────
        print("  [4/5] Computing EHS, traffic index, priority score and TIS ...")
        update_rows: list[tuple] = []

        for trail_id, name, avg_ndvi, avg_ndmi, annual_visitors, length_m in rows:
            ehs      = _compute_ehs(avg_ndvi, avg_ndmi)
            ti       = _traffic_index(annual_visitors, min_v, max_v)
            priority = _compute_priority(ehs, ti)
            needs_intervention, tis_budget = _compute_tis(priority, float(length_m or 0.0))
            update_rows.append((ehs, priority, needs_intervention, tis_budget, trail_id))

        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                UPDATE production_hiking_trails AS t SET
                    ehs_index          = v.ehs_index,
                    priority_score     = v.priority_score,
                    needs_intervention = v.needs_intervention,
                    tis_budget_eur     = v.tis_budget_eur
                FROM (VALUES %s) AS v(ehs_index, priority_score, needs_intervention, tis_budget_eur, id)
                WHERE t.id = v.id
                """,
                update_rows,
                template="(%s::FLOAT, %s::FLOAT, %s::BOOLEAN, %s::FLOAT, %s::INT)",
            )

        conn.commit()
        print(f"    Rows updated: {len(update_rows)}")
        print()

        # ── [5/5] Management report ───────────────────────────────────────────
        print("  [5/5] Fetching final figures for management report ...")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)                                              AS total_trails,
                    COUNT(ehs_index)                                      AS ehs_computed,
                    COUNT(priority_score)                                 AS priority_computed,
                    COUNT(*) FILTER (WHERE needs_intervention = TRUE)     AS critical_trails,
                    COALESCE(SUM(tis_budget_eur), 0)                      AS total_budget,
                    ROUND(AVG(priority_score)::NUMERIC, 2)                AS mean_priority,
                    ROUND(MIN(priority_score)::NUMERIC, 2)                AS min_priority,
                    ROUND(MAX(priority_score)::NUMERIC, 2)                AS max_priority
                FROM production_hiking_trails
                """
            )
            stats = cur.fetchone()
            (
                total_trails, ehs_computed, priority_computed, critical_trails,
                total_budget, mean_priority, min_priority, max_priority,
            ) = stats

            cur.execute(
                """
                SELECT
                    name,
                    ehs_index,
                    priority_score,
                    annual_visitors,
                    tis_budget_eur,
                    ST_Length(geometry::geography) AS length_m
                FROM   production_hiking_trails
                WHERE  needs_intervention = TRUE
                ORDER  BY priority_score DESC NULLS LAST
                """
            )
            critical_rows = cur.fetchall()

        print()
        print(SEP)
        print("  SNTO MANAGEMENT REPORT — Priority Score & Investment Budget")
        print("  Demand Layer: Tourist Pressure integrated (CETS Phase I)")
        print(SEP)
        print()
        print(f"  Total trails analysed        : {total_trails}")
        print(f"  Trails with EHS computed     : {ehs_computed}")
        print(f"  Trails with priority score   : {priority_computed}")
        print(f"  Priority score range         : {min_priority}  –  {max_priority}  (mean: {mean_priority})")
        print(f"  Critical threshold (score>60): {PRIORITY_CRITICAL_THRESHOLD:.0f}")
        print(f"  Visitor range (annual)       : {min_v:,}  –  {max_v:,}")
        print()
        print(DIV)
        print(f"  Trails requiring intervention : {critical_trails} / {total_trails}")
        print(f"  Total Estimated Budget        : EUR {total_budget:,.2f}")
        print(DIV)
        print()

        if critical_rows:
            print(
                f"  {'Trail name':<36} "
                f"{'EHS':>6}  {'Priority':>8}  {'Visitors':>9}  {'Budget(EUR)':>12}"
            )
            print(
                f"  {'-'*36} "
                f"{'-'*6}  {'-'*8}  {'-'*9}  {'-'*12}"
            )
            for name, ehs, priority, visitors, budget, length_m in critical_rows:
                label   = (name or "—")[:35]
                ehs_str = f"{ehs:.1f}"      if ehs      is not None else "N/A"
                pri_str = f"{priority:.1f}" if priority is not None else "N/A"
                vis_str = f"{visitors:,}"   if visitors is not None else "N/A"
                print(
                    f"  {label:<36} "
                    f"{ehs_str:>6}  {pri_str:>8}  {vis_str:>9}  {budget:>12,.2f}"
                )
            print()
        else:
            print("  No trails exceed the critical priority threshold.")
            print()

        cost_km = BASE_RESTORATION_COST_EUR_PER_M * 1000
        print("  Assumptions:")
        print(
            f"    Base restoration cost  : EUR {BASE_RESTORATION_COST_EUR_PER_M:.2f}/m  "
            f"(EUR {cost_km:,.0f}/km)"
        )
        print(
            f"    Priority formula       : "
            f"(EHS × {EHS_WEIGHT:.2f}) + (traffic_index × {TRAFFIC_WEIGHT:.2f})"
        )
        print(f"    Severity multiplier    : priority_score / 100")
        print(
            f"    Budget formula         : "
            f"length_m × {BASE_RESTORATION_COST_EUR_PER_M} × (priority_score / 100)"
        )
        print()
        print(SEP)

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
