"""v3.0 PostGIS geometry: derived ``managed_assets.geom`` column

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-29 12:00:00.000000

Adds a derived spatial mirror of ``managed_assets.geometry_geojson`` for in-DB
spatial queries (ADR-011 §4bis follow-up). ``geometry_geojson`` stays the
canonical, portable geometry; ``geom`` is a materialised index of it.

Dialect-branched and additive:

* **PostgreSQL** — ensure the PostGIS extension, add a real
  ``geometry(Geometry, 4326)`` column, a GIST index, and backfill it from the
  GeoJSON. The backfill is per-row exception-guarded: any row whose GeoJSON is
  absent, empty (``''`` / ``'{}'``) or unparseable keeps ``geom IS NULL`` —
  geometry is never fabricated.
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


_BACKFILL_SQL = """
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT id, geometry_geojson
          FROM managed_assets
         WHERE geometry_geojson IS NOT NULL
           AND geometry_geojson <> ''
           AND geometry_geojson <> '{}'
    LOOP
        BEGIN
            UPDATE managed_assets
               SET geom = ST_SetSRID(ST_GeomFromGeoJSON(r.geometry_geojson), 4326)
             WHERE id = r.id;
        EXCEPTION WHEN OTHERS THEN
            -- Unparseable GeoJSON: leave geom NULL, never fabricate geometry.
            NULL;
        END;
    END LOOP;
END $$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            "ALTER TABLE managed_assets "
            "ADD COLUMN geom geometry(Geometry, 4326)"
        )
        op.execute(
            "CREATE INDEX ix_managed_assets_geom "
            "ON managed_assets USING GIST (geom)"
        )
        op.execute(_BACKFILL_SQL)
    else:
        # SQLite (dev/tests) and any non-PostGIS backend: inert Text mirror.
        with op.batch_alter_table("managed_assets") as batch:
            batch.add_column(sa.Column("geom", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_managed_assets_geom")
        op.execute("ALTER TABLE managed_assets DROP COLUMN IF EXISTS geom")
    else:
        with op.batch_alter_table("managed_assets") as batch:
            batch.drop_column("geom")
