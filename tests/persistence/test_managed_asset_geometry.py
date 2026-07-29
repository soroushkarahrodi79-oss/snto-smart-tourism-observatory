"""ManagedAsset PostGIS geometry (v3.0).

Two paths:

* **SQLite (always runs)** — the ``geom`` column is an inert ``Text`` mirror;
  spatial queries must refuse to run rather than return wrong answers.
* **PostGIS (gated)** — skipped unless the test engine is PostgreSQL (the CI
  ``postgres-integration`` job on the ``postgis`` image). Validates that
  ``ST_DWithin`` / ``ST_Intersects`` filter correctly against ``geom``
  backfilled from the canonical GeoJSON.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from src.persistence.models import ManagedAsset, Territory
from src.persistence.repositories.managed_asset import (
    ManagedAssetRepository,
    PostGISUnavailable,
)

# A point near a PNSG trailhead (lon, lat) and one ~500 km away (Barcelona).
_NEAR = '{"type": "Point", "coordinates": [-3.9251, 40.7405]}'
_FAR = '{"type": "Point", "coordinates": [2.1734, 41.3851]}'


def _register(session, external_id: str, geojson: str) -> ManagedAsset:
    territory = session.scalars(select(Territory).limit(1)).first()
    if territory is None:
        territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
        session.add(territory)
        session.flush()
    territory_id = territory.id
    asset = ManagedAsset(
        territory_id=territory_id,
        external_asset_id=external_id,
        name=external_id,
        asset_type="viewpoint",
        geometry_geojson=geojson,
        region="Comunidad de Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def _is_postgres(session) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def test_geom_column_persists_null_on_sqlite(db_session):
    """A row can be stored with no geometry mirror; geom stays NULL."""
    asset = _register(db_session, "pnsg-vp-001", _NEAR)
    db_session.refresh(asset)
    assert asset.geom is None


def test_spatial_queries_refuse_without_postgis(db_session):
    """On a non-PostGIS backend the spatial helpers raise, never guess."""
    if _is_postgres(db_session):
        pytest.skip("PostGIS backend present; refusal path is SQLite-only")
    _register(db_session, "pnsg-vp-001", _NEAR)
    repo = ManagedAssetRepository(db_session)
    with pytest.raises(PostGISUnavailable):
        repo.list_within_distance(lon=-3.9251, lat=40.7405, meters=1000)
    with pytest.raises(PostGISUnavailable):
        repo.list_intersecting(_NEAR)


def _backfill_geom(session) -> None:
    """Populate geom from the canonical GeoJSON, as the migration does."""
    session.execute(
        text(
            "UPDATE managed_assets "
            "SET geom = ST_SetSRID(ST_GeomFromGeoJSON(geometry_geojson), 4326) "
            "WHERE geometry_geojson IS NOT NULL "
            "AND geometry_geojson <> '' AND geometry_geojson <> '{}'"
        )
    )
    session.flush()


def test_list_within_distance_filters_by_radius(db_session):
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    near = _register(db_session, "near", _NEAR)
    far = _register(db_session, "far", _FAR)
    _backfill_geom(db_session)
    repo = ManagedAssetRepository(db_session)

    hits = repo.list_within_distance(lon=-3.9251, lat=40.7405, meters=1000)
    ids = {a.id for a in hits}
    assert near.id in ids
    assert far.id not in ids

    # Widen the radius past 500 km: both fall inside.
    wide = repo.list_within_distance(lon=-3.9251, lat=40.7405, meters=600_000)
    assert {near.id, far.id} <= {a.id for a in wide}


def test_list_intersecting_matches_polygon(db_session):
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    near = _register(db_session, "near", _NEAR)
    far = _register(db_session, "far", _FAR)
    _backfill_geom(db_session)
    repo = ManagedAssetRepository(db_session)

    # A small box around the PNSG point; should catch `near`, not `far`.
    box = (
        '{"type": "Polygon", "coordinates": '
        "[[[-4.0, 40.6], [-3.8, 40.6], [-3.8, 40.9], [-4.0, 40.9], [-4.0, 40.6]]]}"
    )
    ids = {a.id for a in repo.list_intersecting(box)}
    assert near.id in ids
    assert far.id not in ids


def test_backfill_leaves_invalid_geojson_null(db_session):
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    good = _register(db_session, "good", _NEAR)
    bad = _register(db_session, "bad", "{}")  # empty GeoJSON — never fabricate
    _backfill_geom(db_session)
    db_session.refresh(good)
    db_session.refresh(bad)
    assert good.geom is not None
    assert bad.geom is None
