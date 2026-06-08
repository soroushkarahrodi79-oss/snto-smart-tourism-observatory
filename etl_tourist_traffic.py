"""
SNTO ETL — Tourist Traffic Demand Layer
=========================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Adds `annual_visitors` (INTEGER) to production_hiking_trails and
populates it with reproducible mock visitor counts as a proof-of-concept
Demand Layer for the CETS Phase I dossier.

Run order:
  1. db_production_seeder.py
  2. etl_raster_intersection.py
  3. etl_tourist_traffic.py   ← this script
  4. tis_engine.py

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
import random
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import psycopg2

SEP = "=" * 72
DIV = "-" * 72

# ── Visitor range for mock data ───────────────────────────────────────────────
MIN_VISITORS: int = 1_000
MAX_VISITORS: int = 45_000
MOCK_SEED: int = 42          # fixed seed → reproducible across runs

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


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(SEP)
    print("  SNTO ETL — Tourist Traffic Demand Layer")
    print("  Adding annual_visitors to production_hiking_trails")
    print(f"  Target: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print()

    # ── [1/3] Connect ─────────────────────────────────────────────────────────
    print("  [1/3] Connecting to PostgreSQL ...")
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
        print("    3. Re-run this script.")
        sys.exit(1)

    major, minor = divmod(conn.server_version, 10000)
    print(f"  Connected to '{DB_NAME}'. PostgreSQL {major}.{minor}")
    print()

    try:
        # ── [2/3] Ensure column exists ────────────────────────────────────────
        print("  [2/3] Ensuring 'annual_visitors' column exists ...")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE  table_schema = 'public'
                  AND  table_name   = 'production_hiking_trails'
                  AND  column_name  = 'annual_visitors'
                """
            )
            if cur.fetchone() is None:
                print("    Adding column 'annual_visitors' INTEGER ...")
                cur.execute(
                    "ALTER TABLE production_hiking_trails ADD COLUMN annual_visitors INTEGER"
                )
            else:
                print("    Column 'annual_visitors' already exists — will overwrite values.")
        conn.commit()
        print()

        # ── [3/3] Populate with mock demand data ──────────────────────────────
        print("  [3/3] Populating annual_visitors with mock demand data ...")
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM production_hiking_trails ORDER BY id")
            trail_ids = [r[0] for r in cur.fetchall()]

        if not trail_ids:
            print("  WARNING: No trails found. Run db_production_seeder.py first.")
            sys.exit(0)

        rng = random.Random(MOCK_SEED)
        rows = [(rng.randint(MIN_VISITORS, MAX_VISITORS), tid) for tid in trail_ids]

        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE production_hiking_trails SET annual_visitors = %s WHERE id = %s",
                rows,
            )
        conn.commit()

        visitor_values = [r[0] for r in rows]
        print(f"    Trails updated    : {len(rows)}")
        print(f"    Visitor range     : {min(visitor_values):,} – {max(visitor_values):,} annual visitors")
        print(f"    Mock seed         : {MOCK_SEED}  (fixed for reproducibility)")
        print()
        print(DIV)
        print("  Tourist Traffic ETL completed successfully.")
        print("  Run tis_engine.py next to incorporate the Demand Layer into priority scores.")
        print(DIV)

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
