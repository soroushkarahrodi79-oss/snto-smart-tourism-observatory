"""
SNTO Utility -- Bounding Box & Trail Length Report
===================================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Queries the production_hiking_trails table in the snto PostGIS database and
reports the combined spatial extent (EPSG:4326) plus total trail length (km).
Output is formatted for direct use in Copernicus / EO Browser / STAC downloads.

Credentials (env vars with fallbacks):
  SNTO_DB_HOST  localhost
  SNTO_DB_PORT  5432
  SNTO_DB_NAME  snto
  SNTO_DB_USER  postgres
  SNTO_DB_PASS  secret
"""
from __future__ import annotations

import io
import json
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import psycopg2

SEP = "=" * 72
DIV = "-" * 72

DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
DB_USER = os.getenv("SNTO_DB_USER", "postgres")
DB_PASS = os.getenv("SNTO_DB_PASS", "Navidesalehin_1379")

# ── SQL ───────────────────────────────────────────────────────────────────────

_BBOX_SQL = """
SELECT
    ST_XMin(ST_Extent(geometry)) AS west,
    ST_YMin(ST_Extent(geometry)) AS south,
    ST_XMax(ST_Extent(geometry)) AS east,
    ST_YMax(ST_Extent(geometry)) AS north,
    COUNT(*)                     AS trail_count
FROM production_hiking_trails;
"""

# ST_Length on a geography cast gives metres on the ellipsoid — no reprojection needed.
_LENGTH_SQL = """
SELECT
    SUM(ST_Length(geometry::geography)) / 1000.0 AS total_km
FROM production_hiking_trails;
"""


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        connect_timeout=10,
    )


def main() -> None:
    print(SEP)
    print("  SNTO Utility -- Bounding Box & Trail Length Report")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Target: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print()

    try:
        conn = _connect()
    except (psycopg2.OperationalError, UnicodeDecodeError) as exc:
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
    print(f"  Connected to '{DB_NAME}'. PostgreSQL {major}.{minor // 100}")
    print()

    try:
        with conn.cursor() as cur:
            # ── Bounding box ──────────────────────────────────────────────────
            cur.execute(_BBOX_SQL)
            row = cur.fetchone()
            if row is None or row[0] is None:
                print("  ERROR: production_hiking_trails is empty or missing.")
                sys.exit(1)

            west, south, east, north, trail_count = row
            west  = float(west)
            south = float(south)
            east  = float(east)
            north = float(north)

            # ── Total length ──────────────────────────────────────────────────
            cur.execute(_LENGTH_SQL)
            total_km = float(cur.fetchone()[0] or 0.0)

    finally:
        conn.close()

    # ── GeoJSON bounding-box polygon (closed ring, counter-clockwise) ─────────
    geojson_bbox = {
        "type": "Polygon",
        "coordinates": [[
            [west,  south],
            [east,  south],
            [east,  north],
            [west,  north],
            [west,  south],   # closed
        ]],
    }
    geojson_str = json.dumps(geojson_bbox, separators=(",", ":"))

    # ── Output ────────────────────────────────────────────────────────────────
    print(DIV)
    print("  SPATIAL EXTENT  —  production_hiking_trails")
    print(f"  Trails included : {trail_count} features  (EPSG:4326)")
    print(DIV)
    print()
    print(f"  Minimum Longitude  (West)  :  {west:.6f}")
    print(f"  Minimum Latitude   (South) :  {south:.6f}")
    print(f"  Maximum Longitude  (East)  :  {east:.6f}")
    print(f"  Maximum Latitude   (North) :  {north:.6f}")
    print()
    print("  Copernicus / EO Browser  [ West, South, East, North ]:")
    print(f"    {west:.6f}, {south:.6f}, {east:.6f}, {north:.6f}")
    print()
    print(DIV)
    print("  GeoJSON Bounding Box  (copy-paste into STAC / EO Browser / QGIS)")
    print(DIV)
    print()
    print(f"  {geojson_str}")
    print()
    print(DIV)
    print("  TRAIL LENGTH SUMMARY")
    print(DIV)
    print()
    print(f"  Total combined trail length : {total_km:>8.2f} km")
    print(f"  Average per trail           : {total_km / trail_count:>8.2f} km")
    print()
    print(SEP)
    print("  Done.")
    print(SEP)


if __name__ == "__main__":
    main()
