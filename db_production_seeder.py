"""
SNTO ETL Phase 0 -- Production Database Seeder
================================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Connects to PostgreSQL/PostGIS, creates the three production tables with
proper schema and GIST spatial indexes, streams records from the clean
GeoJSON assets, and prints a row-count + index verification report.

Tables created:
  production_hiking_trails     (osm_id, name, type, geometry EPSG:4326)
  production_viewpoints        (osm_id, name, geometry EPSG:4326)
  production_protected_areas   (site_code, name, category, area_ha, geometry EPSG:4326)

Credentials (env vars with fallbacks):
  SNTO_DB_HOST  localhost
  SNTO_DB_PORT  5432
  SNTO_DB_NAME  snto
  SNTO_DB_USER  postgres
  SNTO_DB_PASS  secret
"""
from __future__ import annotations

import io
import math
import os
import sys

# Ensure UTF-8 output regardless of terminal code page
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values

SEP = "=" * 72
DIV = "-" * 72

PROJECT_ROOT = Path(__file__).parent
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean_assets"

# ── Credentials (override via environment variables) ──────────────────────────
DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
DB_USER = os.getenv("SNTO_DB_USER", "postgres")
DB_PASS = os.getenv("SNTO_DB_PASS", "")

SRID = 4326

# ── DDL: one statement per element so each step is auditable ──────────────────

_DDL_POSTGIS = "CREATE EXTENSION IF NOT EXISTS postgis"

_DDL_TABLES = [
    # ── Hiking Trails ─────────────────────────────────────────────────────────
    "DROP TABLE IF EXISTS production_hiking_trails CASCADE",
    """CREATE TABLE production_hiking_trails (
        id       SERIAL PRIMARY KEY,
        osm_id   TEXT,
        name     TEXT,
        type     TEXT,
        geometry GEOMETRY(GEOMETRY, 4326)
    )""",
    """CREATE INDEX idx_hiking_trails_geom
           ON production_hiking_trails USING GIST (geometry)""",

    # ── Viewpoints ────────────────────────────────────────────────────────────
    "DROP TABLE IF EXISTS production_viewpoints CASCADE",
    """CREATE TABLE production_viewpoints (
        id       SERIAL PRIMARY KEY,
        osm_id   TEXT,
        name     TEXT,
        geometry GEOMETRY(POINT, 4326)
    )""",
    """CREATE INDEX idx_viewpoints_geom
           ON production_viewpoints USING GIST (geometry)""",

    # ── Protected Areas ───────────────────────────────────────────────────────
    "DROP TABLE IF EXISTS production_protected_areas CASCADE",
    """CREATE TABLE production_protected_areas (
        id        SERIAL PRIMARY KEY,
        site_code TEXT,
        name      TEXT,
        category  TEXT,
        area_ha   DOUBLE PRECISION,
        geometry  GEOMETRY(POLYGON, 4326)
    )""",
    """CREATE INDEX idx_protected_areas_geom
           ON production_protected_areas USING GIST (geometry)""",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _s(val: object) -> str | None:
    """Coerce a pandas/numpy value to str or None (never inserts NaN)."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return str(val)


def _connect(dbname: str = DB_NAME) -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=dbname,
        user=DB_USER,
        password=DB_PASS,
        connect_timeout=10,
    )


def _ensure_database() -> None:
    """Connect to the maintenance 'postgres' DB and CREATE DATABASE if missing.

    CREATE DATABASE cannot run inside a transaction, so autocommit must be on.
    """
    boot = _connect(dbname="postgres")
    boot.autocommit = True
    try:
        with boot.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            exists = cur.fetchone() is not None
            if exists:
                print(f"  Database '{DB_NAME}' already exists.")
            else:
                print(f"  Database '{DB_NAME}' not found — creating ...")
                cur.execute(f'CREATE DATABASE "{DB_NAME}"')
                print(f"  Database '{DB_NAME}' created successfully.")
    finally:
        boot.close()


# ── Data preparation ──────────────────────────────────────────────────────────

def _prepare_hiking_trails(gdf: gpd.GeoDataFrame) -> list[tuple]:
    """Filter to linear geometries; derive trail type from route → highway."""
    linear_types = {"LineString", "MultiLineString"}
    gdf = gdf[
        gdf.geometry.geom_type.isin(linear_types) & gdf.geometry.notna()
    ].copy()

    rows: list[tuple] = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        # route (hiking/mtb) is most meaningful; fall back to highway (path/track)
        trail_type = _s(row.get("route")) or _s(row.get("highway")) or _s(row.get("type"))
        rows.append((_s(row.get("id")), _s(row.get("name")), trail_type, geom.wkt))
    return rows


def _prepare_viewpoints(gdf: gpd.GeoDataFrame) -> list[tuple]:
    rows: list[tuple] = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        rows.append((_s(row.get("id")), _s(row.get("name")), geom.wkt))
    return rows


def _prepare_protected_areas(gdf: gpd.GeoDataFrame) -> list[tuple]:
    # Resolve column names once via case-insensitive lookup before iterating.
    # The ENP GeoJSON column case varies by GDAL driver version (Sup_ha / SUP_HA).
    _lower = {c.lower(): c for c in gdf.columns}
    area_col      = _lower.get("sup_ha")
    site_code_col = _lower.get("site_code_")
    site_name_col = _lower.get("site_name")
    odesig_col    = _lower.get("odesignate")

    if area_col is None:
        print(f"    WARNING: area column 'Sup_ha' not found. "
              f"Available columns: {list(gdf.columns)}")

    rows: list[tuple] = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        area = row[area_col] if area_col is not None else None
        area_ha = (
            float(area)
            if area is not None and not (isinstance(area, float) and math.isnan(area))
            else 0.0
        )
        rows.append((
            _s(row[site_code_col] if site_code_col else None),
            _s(row[site_name_col] if site_name_col else None),
            _s(row[odesig_col]    if odesig_col    else None),
            area_ha,
            geom.wkt,
        ))
    return rows


# ── Insert helpers ─────────────────────────────────────────────────────────────

def _insert_hiking_trails(cur: psycopg2.extensions.cursor, rows: list[tuple]) -> None:
    execute_values(
        cur,
        "INSERT INTO production_hiking_trails (osm_id, name, type, geometry) VALUES %s",
        rows,
        template="(%s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))",
    )


def _insert_viewpoints(cur: psycopg2.extensions.cursor, rows: list[tuple]) -> None:
    execute_values(
        cur,
        "INSERT INTO production_viewpoints (osm_id, name, geometry) VALUES %s",
        rows,
        template="(%s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))",
    )


def _insert_protected_areas(cur: psycopg2.extensions.cursor, rows: list[tuple]) -> None:
    execute_values(
        cur,
        "INSERT INTO production_protected_areas "
        "(site_code, name, category, area_ha, geometry) VALUES %s",
        rows,
        template="(%s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))",
    )


# ── Verification ──────────────────────────────────────────────────────────────

_COUNT_SQL = """
SELECT table_name, row_count FROM (
    SELECT 'production_hiking_trails'    AS table_name,
           COUNT(*)                      AS row_count
    FROM   production_hiking_trails
    UNION ALL
    SELECT 'production_viewpoints',      COUNT(*)
    FROM   production_viewpoints
    UNION ALL
    SELECT 'production_protected_areas', COUNT(*)
    FROM   production_protected_areas
) t
ORDER BY table_name;
"""

_IDX_SQL = """
SELECT tablename, indexname
FROM   pg_indexes
WHERE  schemaname = 'public'
  AND  tablename  IN (
           'production_hiking_trails',
           'production_viewpoints',
           'production_protected_areas'
       )
  AND  indexdef ILIKE '%gist%'
ORDER BY tablename;
"""

_SAMPLE_ENP_SQL = """
SELECT name, category, area_ha
FROM   production_protected_areas
ORDER  BY area_ha DESC;
"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("  SNTO ETL -- Production Database Seeder")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Target: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print()

    # ── Step 1: Bootstrap — ensure the target database exists ────────────────
    print("  [1/5] Connecting to PostgreSQL ...")
    try:
        _ensure_database()
        conn = _connect()
    except (psycopg2.OperationalError, UnicodeDecodeError) as exc:
        # UnicodeDecodeError: psycopg2 on Windows can fail to decode the OS
        # socket error message (cp1252 locale) before raising OperationalError.
        print()
        print("  ERROR: Cannot reach the PostgreSQL server.")
        print(f"  Detail: {type(exc).__name__} — server is likely not running.")
        print()
        print("  To resolve:")
        print("    1. Start PostgreSQL via pgAdmin or Windows Services")
        print("    2. Override credentials via env vars if needed:")
        print("         SNTO_DB_HOST  SNTO_DB_PORT  SNTO_DB_NAME  SNTO_DB_USER  SNTO_DB_PASS")
        print("    3. Re-run this script.")
        sys.exit(1)

    ver = conn.server_version
    major, minor = divmod(ver, 10000)
    print(f"  Connected to '{DB_NAME}'. PostgreSQL {major}.{minor}")
    print()

    try:
        with conn.cursor() as cur:
            # ── Step 2: Enable PostGIS ─────────────────────────────────────
            print("  [2/5] Enabling PostGIS extension ...")
            cur.execute(_DDL_POSTGIS)
            conn.commit()
            cur.execute("SELECT PostGIS_Full_Version()")
            postgis_ver = cur.fetchone()[0].split('"')[0].strip()
            print(f"  {postgis_ver}")
            print()

            # ── Step 3: Create schema ─────────────────────────────────────
            print("  [3/5] Creating production tables and GIST indexes ...")
            for stmt in _DDL_TABLES:
                cur.execute(stmt)
            conn.commit()
            print("  Tables created:")
            for tbl in ("production_hiking_trails", "production_viewpoints",
                        "production_protected_areas"):
                print(f"    {tbl}")
            print()

            # ── Step 4: Load and seed ─────────────────────────────────────
            print("  [4/5] Loading clean GeoJSON files ...")
            trails_gdf = gpd.read_file(CLEAN_DIR / "clean_hiking_trails.geojson")
            viewpts_gdf = gpd.read_file(CLEAN_DIR / "clean_viewpoints.geojson")
            enp_gdf     = gpd.read_file(CLEAN_DIR / "clean_Enp2025_p.geojson")

            trail_rows  = _prepare_hiking_trails(trails_gdf)
            viewpt_rows = _prepare_viewpoints(viewpts_gdf)
            enp_rows    = _prepare_protected_areas(enp_gdf)

            print(f"  Seeding rows:")
            _insert_hiking_trails(cur, trail_rows)
            print(f"    production_hiking_trails     -> {len(trail_rows):>4} rows"
                  f"  (filtered from {len(trails_gdf)} raw features; "
                  f"{len(trails_gdf) - len(trail_rows)} Point geometries excluded)")

            _insert_viewpoints(cur, viewpt_rows)
            print(f"    production_viewpoints        -> {len(viewpt_rows):>4} rows")

            _insert_protected_areas(cur, enp_rows)
            print(f"    production_protected_areas   -> {len(enp_rows):>4} rows")
            conn.commit()
            print()

            # ── Step 5: Verify ────────────────────────────────────────────
            print(DIV)
            print("  [5/5] VERIFICATION REPORT")
            print(DIV)
            print()

            # Row counts
            cur.execute(_COUNT_SQL)
            counts = cur.fetchall()
            print(f"  {'Table':<38} {'Rows':>6}  Status")
            print(f"  {'-'*55}")
            all_ok = True
            for table_name, row_count in counts:
                status = "OK" if row_count > 0 else "EMPTY — check input file"
                if row_count == 0:
                    all_ok = False
                print(f"  {table_name:<38} {row_count:>6}  [{status}]")
            print()

            # GIST index verification
            cur.execute(_IDX_SQL)
            indexes = cur.fetchall()
            print(f"  GIST spatial indexes ({len(indexes)} confirmed):")
            for tablename, indexname in indexes:
                print(f"    {tablename:<38}  {indexname}")
            print()

            # Spatial sanity: ST_IsValid on each table
            for tbl in ("production_hiking_trails", "production_viewpoints",
                        "production_protected_areas"):
                cur.execute(
                    f"SELECT COUNT(*) FROM {tbl} WHERE NOT ST_IsValid(geometry)"
                )
                invalid = cur.fetchone()[0]
                flag = "CLEAN" if invalid == 0 else f"{invalid} INVALID GEOMETRIES"
                print(f"  Geometry validity  {tbl:<30}  [{flag}]")
            print()

            # Protected areas detail
            cur.execute(_SAMPLE_ENP_SQL)
            print("  Protected areas detail:")
            for name, category, area_ha in cur.fetchall():
                cat = (category or "")[:45]
                print(f"    {name}  ({area_ha:,.0f} ha)")
                print(f"      designation: {cat}")
            print()

            print(DIV)
            overall = "ALL TABLES POPULATED AND SPATIALLY INDEXED" if all_ok else "WARNING: some tables are empty"
            print(f"  {overall}")
            print(DIV)
            print()
            print(f"  Database '{DB_NAME}' is production-ready.")
            print()
            print(SEP)

    except Exception as exc:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
