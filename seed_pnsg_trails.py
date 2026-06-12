"""
SNTO — Seeder PNSG Hiking Trails
=================================
Carga pnsg_hiking_trails.geojson en production_hiking_trails añadiendo
una columna 'territory' para distinguir territorios.

Lo que hace:
  1. Añade columna 'territory TEXT' a production_hiking_trails si no existe
  2. Marca las filas existentes como territory='sierra_del_rincon'
  3. Elimina cualquier fila PNSG previa (idempotente)
  4. Inserta las 95 sendas de PNSG con territory='pnsg'

No borra ni modifica las sendas de Sierra del Rincón.

Credenciales (env vars con fallback):
  SNTO_DB_HOST  localhost
  SNTO_DB_PORT  5432
  SNTO_DB_NAME  snto
  SNTO_DB_USER  postgres
  SNTO_DB_PASS  secret (o vacío)
"""
from __future__ import annotations

import io
import math
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

import geopandas as gpd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

SEP = "=" * 72
DIV = "-" * 72

PROJECT_ROOT = Path(__file__).parent
# Cartografía OFICIAL OAPN (225 sendas homologadas del PN Sierra de Guadarrama).
PNSG_TRAILS_FILE = PROJECT_ROOT / "data" / "raw_assets" / "vector_data" / "pnsg_oapn_trails.geojson"

DB_HOST = os.getenv("SNTO_DB_HOST", "localhost")
DB_PORT = int(os.getenv("SNTO_DB_PORT", "5432"))
DB_NAME = os.getenv("SNTO_DB_NAME", "snto")
DB_USER = os.getenv("SNTO_DB_USER", "postgres")
DB_PASS = os.getenv("SNTO_DB_PASS", "")


def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS, connect_timeout=10,
    )


def _s(val: object) -> str | None:
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    return str(val)


def main() -> None:
    print(SEP)
    print("  SNTO — Seeder PNSG Hiking Trails")
    print(f"  Fuente : {PNSG_TRAILS_FILE.name}")
    print(f"  Target : postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(SEP)
    print()

    # ── [1/5] Verificar archivo fuente ───────────────────────────────────────
    print("  [1/5] Verificando archivo GeoJSON ...")
    if not PNSG_TRAILS_FILE.exists():
        print(f"  ERROR: No se encuentra {PNSG_TRAILS_FILE}")
        sys.exit(1)

    gdf = gpd.read_file(PNSG_TRAILS_FILE)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    print(f"    Features cargadas : {len(gdf)}")
    print(f"    CRS               : {gdf.crs}")
    print(f"    Bbox (WGS84)      : {[round(v,4) for v in gdf.total_bounds]}")
    print()

    # ── [2/5] Conectar a PostgreSQL ──────────────────────────────────────────
    print("  [2/5] Conectando a PostgreSQL ...")
    try:
        conn = _connect()
    except (psycopg2.OperationalError, UnicodeDecodeError) as exc:
        print(f"  ERROR: No se puede conectar — {type(exc).__name__}")
        print("  Asegúrate de que PostgreSQL está arrancado.")
        print("  Variables de entorno: SNTO_DB_HOST / PORT / NAME / USER / PASS")
        sys.exit(1)

    major, minor = divmod(conn.server_version, 10000)
    print(f"  Conectado. PostgreSQL {major}.{minor}")
    print()

    try:
        with conn.cursor() as cur:
            # ── [3/5] Añadir columna territory (idempotente) ─────────────────
            print("  [3/5] Gestionando columna 'territory' ...")

            cur.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE  table_schema = 'public'
                  AND  table_name   = 'production_hiking_trails'
                  AND  column_name  = 'territory'
            """)
            col_exists = cur.fetchone() is not None

            if col_exists:
                print("    Columna 'territory' ya existe.")
            else:
                print("    Añadiendo columna 'territory' TEXT ...")
                cur.execute(
                    "ALTER TABLE production_hiking_trails ADD COLUMN territory TEXT"
                )
                conn.commit()
                print("    Columna añadida.")

            # Etiquetar filas existentes (Sierra del Rincón) si aún no tienen territory
            cur.execute("""
                UPDATE production_hiking_trails
                   SET territory = 'sierra_del_rincon'
                 WHERE territory IS NULL
            """)
            updated_rincon = cur.rowcount
            conn.commit()
            if updated_rincon:
                print(f"    {updated_rincon} filas existentes etiquetadas como 'sierra_del_rincon'.")
            else:
                print("    Filas de Sierra del Rincón ya etiquetadas — sin cambios.")
            print()

            # ── [4/5] Eliminar PNSG previos e insertar ────────────────────────
            print("  [4/5] Cargando sendas PNSG ...")

            cur.execute(
                "DELETE FROM production_hiking_trails WHERE territory = 'pnsg'"
            )
            deleted = cur.rowcount
            if deleted:
                print(f"    {deleted} filas PNSG anteriores eliminadas.")

            # Preparar filas
            linear_types = {"LineString", "MultiLineString"}
            rows: list[tuple] = []
            for _, row in gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                if geom.geom_type not in linear_types:
                    continue
                trail_type = _s(row.get("highway")) or "path"
                rows.append((
                    _s(row.get("id")),
                    _s(row.get("name")),
                    trail_type,
                    geom.wkt,
                    "pnsg",
                ))

            execute_values(
                cur,
                """INSERT INTO production_hiking_trails
                       (osm_id, name, type, geometry, territory)
                   VALUES %s""",
                rows,
                template="(%s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326), %s)",
            )
            conn.commit()
            print(f"    {len(rows)} sendas PNSG insertadas.")
            print()

            # ── [5/5] Verificación ────────────────────────────────────────────
            print(DIV)
            print("  [5/5] VERIFICACIÓN")
            print(DIV)
            print()

            cur.execute("""
                SELECT territory, COUNT(*) AS n,
                       ROUND(CAST(SUM(ST_Length(geometry::geography))/1000.0 AS numeric), 1) AS km
                FROM   production_hiking_trails
                GROUP  BY territory
                ORDER  BY territory
            """)
            rows_report = cur.fetchall()
            print(f"  {'Territorio':<25} {'Sendas':>7}  {'Longitud (km)':>14}")
            print(f"  {'-'*50}")
            total_sendas = 0
            total_km = 0.0
            for territory, n, km in rows_report:
                t = territory or "(sin etiquetar)"
                km_val = float(km) if km is not None else 0.0
                print(f"  {t:<25} {n:>7}  {km_val:>14.1f} km")
                total_sendas += n
                total_km += km_val
            print(f"  {'-'*50}")
            print(f"  {'TOTAL':<25} {total_sendas:>7}  {total_km:>14.1f} km")
            print()

            # Validez geométrica PNSG
            cur.execute("""
                SELECT COUNT(*) FROM production_hiking_trails
                WHERE territory = 'pnsg'
                  AND NOT ST_IsValid(geometry)
            """)
            invalid = cur.fetchone()[0]
            print(f"  Geometrías PNSG inválidas : {invalid}  {'[LIMPIO]' if invalid == 0 else '[ATENCIÓN]'}")
            print()

            # Muestra top-10 sendas PNSG
            cur.execute("""
                SELECT name, type,
                       ROUND(CAST(ST_Length(geometry::geography)/1000.0 AS numeric), 2) AS km
                FROM   production_hiking_trails
                WHERE  territory = 'pnsg'
                ORDER  BY ST_Length(geometry::geography) DESC
                LIMIT  10
            """)
            print("  Top-10 sendas PNSG por longitud:")
            for name, typ, km in cur.fetchall():
                print(f"    {(name or '?')[:50]:<50}  {km:>5.2f} km  [{typ}]")
            print()

            print(DIV)
            print("  PNSG cargado correctamente en production_hiking_trails")
            print(DIV)
            print()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
