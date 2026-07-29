"""v3.0 PostGIS geometry: derived ``managed_assets.geom`` column

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-29 12:00:00.000000

Adds a derived spatial mirror of ``managed_assets.geometry_geojson`` for in-DB
spatial queries (ADR-011 §4bis follow-up). ``geometry_geojson`` stays the
canonical, portable geometry; ``geom`` is a materialised index of it.

Dialect-branched and additive:

* **PostgreSQL** — ensure the PostGIS extension, add a real
  ``geometry(Geometry, 4326)`` column, geometry/geography GIST indexes, and one
  database trigger that derives the mirror for every insert and update. Any
  row whose GeoJSON is absent, empty, invalid, explicitly non-RFC-7946 CRS,
  out of WGS84 bounds, or geometrically empty keeps ``geom IS NULL`` —
  geometry is never fabricated and a stale mirror cannot survive.
* **SQLite / others** — add an inert nullable ``Text`` column so the schema
  matches the model (whose base type is ``Text`` off Postgres). No extension,
  no spatial index, no backfill.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SYNC_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION snto_sync_managed_asset_geom()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    payload jsonb;
    candidate geometry;
BEGIN
    -- ``geom`` is derived-only: discard any caller-supplied mirror first.
    NEW.geom := NULL;
    IF NEW.geometry_geojson IS NULL
       OR btrim(NEW.geometry_geojson) IN ('', '{}', 'null')
    THEN
        RETURN NEW;
    END IF;

    BEGIN
        payload := NEW.geometry_geojson::jsonb;
        IF jsonb_typeof(payload) <> 'object' OR payload ? 'crs' THEN
            RETURN NEW;
        END IF;
        IF payload->>'type' = 'Feature' THEN
            payload := payload->'geometry';
        END IF;
        IF payload IS NULL
           OR payload = 'null'::jsonb
           OR jsonb_typeof(payload) <> 'object'
           OR payload ? 'crs'
        THEN
            RETURN NEW;
        END IF;

        candidate := ST_SetSRID(ST_GeomFromGeoJSON(payload), 4326);
        IF candidate IS NULL
           OR ST_IsEmpty(candidate)
           OR NOT ST_IsValid(candidate)
           OR ST_XMin(Box3D(candidate)) < -180
           OR ST_XMax(Box3D(candidate)) > 180
           OR ST_YMin(Box3D(candidate)) < -90
           OR ST_YMax(Box3D(candidate)) > 90
        THEN
            RETURN NEW;
        END IF;
        NEW.geom := candidate;
    EXCEPTION
        -- Expected row-level parse/data failures degrade to missing geometry.
        -- Structural failures (missing PostGIS functions/table/column, etc.)
        -- use other SQLSTATE classes and still abort the migration/write.
        WHEN data_exception OR internal_error THEN
            NEW.geom := NULL;
    END;
    RETURN NEW;
END
$$;
"""

_TRIGGER_SQL = """
CREATE TRIGGER trg_managed_assets_sync_geom
BEFORE INSERT OR UPDATE ON managed_assets
FOR EACH ROW
EXECUTE FUNCTION snto_sync_managed_asset_geom();
"""

_BACKFILL_SQL = """
UPDATE managed_assets
   SET geometry_geojson = geometry_geojson;

DO $$
DECLARE
    total_rows bigint;
    source_rows bigint;
    null_geom_rows bigint;
BEGIN
    SELECT count(*),
           count(*) FILTER (
               WHERE geometry_geojson IS NOT NULL
                 AND btrim(geometry_geojson) NOT IN ('', '{}', 'null')
           ),
           count(*) FILTER (WHERE geom IS NULL)
      INTO total_rows, source_rows, null_geom_rows
      FROM managed_assets;
    RAISE NOTICE
        'managed_assets geom sync: total=%, nonblank_source=%, geom_null=%',
        total_rows, source_rows, null_geom_rows;
END $$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            "ALTER TABLE managed_assets "
            "ALTER COLUMN geometry_geojson DROP NOT NULL"
        )
        op.execute(
            "ALTER TABLE managed_assets "
            "ADD COLUMN geom geometry(Geometry, 4326)"
        )
        op.execute(_SYNC_FUNCTION_SQL)
        op.execute(_TRIGGER_SQL)
        op.execute(_BACKFILL_SQL)
        op.execute(
            "CREATE INDEX ix_managed_assets_geom "
            "ON managed_assets USING GIST (geom)"
        )
        op.execute(
            "CREATE INDEX ix_managed_assets_geom_geography "
            "ON managed_assets USING GIST ((geom::geography))"
        )
    else:
        # SQLite (dev/tests) and any non-PostGIS backend: inert Text mirror.
        with op.batch_alter_table("managed_assets") as batch:
            batch.alter_column(
                "geometry_geojson",
                existing_type=sa.Text(),
                nullable=True,
            )
            batch.add_column(sa.Column("geom", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            DECLARE
                normalised_nulls bigint;
            BEGIN
                SELECT count(*)
                  INTO normalised_nulls
                  FROM managed_assets
                 WHERE geometry_geojson IS NULL;
                UPDATE managed_assets
                   SET geometry_geojson = '{}'
                 WHERE geometry_geojson IS NULL;
                RAISE NOTICE
                    'managed_assets downgrade: NULL sources normalised to {}=%',
                    normalised_nulls;
            END $$;
            """
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_managed_assets_sync_geom "
            "ON managed_assets"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS snto_sync_managed_asset_geom()"
        )
        op.execute("DROP INDEX IF EXISTS ix_managed_assets_geom_geography")
        op.execute("DROP INDEX IF EXISTS ix_managed_assets_geom")
        op.execute("ALTER TABLE managed_assets DROP COLUMN IF EXISTS geom")
        op.execute(
            "ALTER TABLE managed_assets "
            "ALTER COLUMN geometry_geojson SET NOT NULL"
        )
    else:
        # The previous schema cannot represent SQL NULL. ``{}`` was its
        # established missing-geometry sentinel and does not fabricate geometry.
        op.execute(
            "UPDATE managed_assets "
            "SET geometry_geojson = '{}' "
            "WHERE geometry_geojson IS NULL"
        )
        with op.batch_alter_table("managed_assets") as batch:
            batch.drop_column("geom")
            batch.alter_column(
                "geometry_geojson",
                existing_type=sa.Text(),
                nullable=False,
            )
