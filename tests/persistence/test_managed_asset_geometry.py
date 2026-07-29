"""ManagedAsset's canonical GeoJSON and derived PostGIS mirror (v3.0)."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from src.persistence.models import ManagedAsset, Territory
from src.persistence.repositories.managed_asset import (
    ManagedAssetRepository,
    PostGISUnavailable,
    SpatialQueryValidationError,
)

_ROOT = Path(__file__).resolve().parents[2]
_PREVIOUS_HEAD = "f1a2b3c4d5e6"
_NEAR = '{"type":"Point","coordinates":[-3.9251,40.7405]}'
_FAR = '{"type":"Point","coordinates":[2.1734,41.3851]}'
_LINE = (
    '{"type":"LineString","coordinates":'
    "[[-3.93,40.73],[-3.92,40.75]]}"
)
_BOX = (
    '{"type":"Polygon","coordinates":'
    "[[[-4.0,40.6],[-3.8,40.6],[-3.8,40.9],[-4.0,40.9],[-4.0,40.6]]]}"
)
_BOX_FEATURE = f'{{"type":"Feature","properties":{{}},"geometry":{_BOX}}}'


def _is_postgres(session: Session) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def _territory(session: Session, slug: str = "pnsg") -> Territory:
    territory = session.scalars(
        select(Territory).where(Territory.slug == slug)
    ).first()
    if territory is None:
        territory = Territory(slug=slug, name=slug.upper(), budget_eur=1000.0)
        session.add(territory)
        session.flush()
    return territory


def _register(
    session: Session,
    external_id: str,
    geojson: str | None,
    *,
    territory: Territory | None = None,
) -> ManagedAsset:
    territory = territory or _territory(session)
    asset = ManagedAsset(
        territory_id=territory.id,
        external_asset_id=external_id,
        name=external_id,
        asset_type="viewpoint",
        geometry_geojson=geojson,
        region="Comunidad de Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def test_sqlite_keeps_an_inert_null_mirror(db_session: Session) -> None:
    if _is_postgres(db_session):
        pytest.skip("SQLite-only inert-column contract")
    asset = _register(db_session, "pnsg-vp-001", _NEAR)
    db_session.refresh(asset)
    assert asset.geometry_geojson == _NEAR
    assert asset.geom is None


def test_spatial_queries_refuse_without_postgis(db_session: Session) -> None:
    if _is_postgres(db_session):
        pytest.skip("PostGIS backend present")
    territory = _territory(db_session)
    repo = ManagedAssetRepository(db_session)
    with pytest.raises(PostGISUnavailable):
        repo.list_within_distance(
            territory.id, lon=-3.9251, lat=40.7405, meters=1000
        )
    with pytest.raises(PostGISUnavailable):
        repo.list_intersecting(territory.id, geojson=_NEAR)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("territory_id", 0),
        ("territory_id", True),
        ("lon", -180.01),
        ("lon", 180.01),
        ("lon", float("nan")),
        ("lat", -90.01),
        ("lat", 90.01),
        ("lat", float("inf")),
        ("meters", -0.01),
        ("meters", float("nan")),
    ],
)
def test_distance_inputs_are_validated_before_sql(
    db_session: Session, field: str, value: object
) -> None:
    arguments: dict[str, object] = {
        "territory_id": 1,
        "lon": -3.9251,
        "lat": 40.7405,
        "meters": 1000.0,
    }
    arguments[field] = value
    with pytest.raises(SpatialQueryValidationError):
        ManagedAssetRepository(db_session).list_within_distance(
            arguments["territory_id"],  # type: ignore[arg-type]
            lon=arguments["lon"],  # type: ignore[arg-type]
            lat=arguments["lat"],  # type: ignore[arg-type]
            meters=arguments["meters"],  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "geojson",
    [
        "",
        "{not json",
        "[]",
        '{"type":"FeatureCollection","features":[]}',
        '{"type":"Feature","properties":{},"geometry":null}',
        '{"type":"Point","coordinates":[]}',
        '{"type":"Point","coordinates":[181,40]}',
        '{"type":"Point","coordinates":[0,91]}',
        '{"type":"LineString","coordinates":[[0,0]]}',
        '{"type":"Polygon","coordinates":[]}',
        '{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,1]]]}',
        (
            '{"type":"Point","coordinates":[0,0],'
            '"crs":{"type":"name","properties":{"name":"EPSG:3857"}}}'
        ),
    ],
)
def test_intersection_geojson_is_validated_before_sql(
    db_session: Session, geojson: str
) -> None:
    with pytest.raises(SpatialQueryValidationError):
        ManagedAssetRepository(db_session).list_intersecting(1, geojson=geojson)


def test_postgis_insert_update_and_invalidation_are_automatic(
    db_session: Session,
) -> None:
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    asset = _register(db_session, "sync", _NEAR)

    srid, geometry_type = db_session.execute(
        text(
            "SELECT ST_SRID(geom), GeometryType(geom) "
            "FROM managed_assets WHERE id = :id"
        ),
        {"id": asset.id},
    ).one()
    assert (srid, geometry_type) == (4326, "POINT")

    asset.geometry_geojson = _LINE
    db_session.flush()
    assert db_session.scalar(
        text("SELECT GeometryType(geom) FROM managed_assets WHERE id = :id"),
        {"id": asset.id},
    ) == "LINESTRING"

    invalid_sources: tuple[str | None, ...] = (
        None,
        "",
        "{}",
        "{not json",
        '{"type":"Point","coordinates":[]}',
        '{"type":"Feature","properties":{},"geometry":null}',
        '{"type":"Point","coordinates":[181,40]}',
        '{"type":"Polygon","coordinates":[]}',
    )
    for invalid in invalid_sources:
        asset.geometry_geojson = _NEAR
        db_session.flush()
        asset.geometry_geojson = invalid
        db_session.flush()
        assert db_session.scalar(
            text("SELECT geom IS NULL FROM managed_assets WHERE id = :id"),
            {"id": asset.id},
        ) is True


def test_postgis_mirror_cannot_be_overridden_directly(db_session: Session) -> None:
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    asset = _register(db_session, "derived-only", _NEAR)
    db_session.execute(
        text(
            "UPDATE managed_assets "
            "SET geom = ST_SetSRID(ST_MakePoint(0, 0), 4326) "
            "WHERE id = :id"
        ),
        {"id": asset.id},
    )
    longitude = db_session.scalar(
        text("SELECT ST_X(geom) FROM managed_assets WHERE id = :id"),
        {"id": asset.id},
    )
    assert longitude == pytest.approx(-3.9251)


@pytest.mark.parametrize(
    ("external_id", "geojson", "expected_type"),
    [
        ("point", _NEAR, "POINT"),
        ("line", _LINE, "LINESTRING"),
        ("polygon", _BOX, "POLYGON"),
        (
            "feature",
            '{"type":"Feature","properties":{},"geometry":'
            '{"type":"Point","coordinates":[-3.9251,40.7405]}}',
            "POINT",
        ),
    ],
)
def test_postgis_supports_geometry_fragments_and_features(
    db_session: Session,
    external_id: str,
    geojson: str,
    expected_type: str,
) -> None:
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    asset = _register(db_session, external_id, geojson)
    assert db_session.scalar(
        text("SELECT GeometryType(geom) FROM managed_assets WHERE id = :id"),
        {"id": asset.id},
    ) == expected_type


def test_spatial_queries_are_territory_scoped(db_session: Session) -> None:
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    territory_a = _territory(db_session, "park-a")
    territory_b = _territory(db_session, "park-b")
    near_a = _register(
        db_session, "near-a", _NEAR, territory=territory_a
    )
    _register(db_session, "far-a", _FAR, territory=territory_a)
    near_b = _register(
        db_session, "near-b", _NEAR, territory=territory_b
    )
    _register(db_session, "missing-a", "{}", territory=territory_a)
    repo = ManagedAssetRepository(db_session)

    distance_ids = {
        asset.id
        for asset in repo.list_within_distance(
            territory_a.id,
            lon=-3.9251,
            lat=40.7405,
            meters=1000,
        )
    }
    assert near_a.id in distance_ids
    assert near_b.id not in distance_ids

    intersection_ids = {
        asset.id
        for asset in repo.list_intersecting(
            territory_a.id, geojson=_BOX_FEATURE
        )
    }
    assert intersection_ids == {near_a.id}


def test_postgis_query_plans_can_use_both_spatial_indexes(
    db_session: Session,
) -> None:
    if not _is_postgres(db_session):
        pytest.skip("requires PostgreSQL/PostGIS")
    territory = _territory(db_session)
    _register(db_session, "indexed", _NEAR, territory=territory)
    db_session.execute(text("SET LOCAL enable_seqscan = off"))

    distance_plan = "\n".join(
        db_session.scalars(
            text(
                "EXPLAIN (COSTS OFF) "
                "SELECT id FROM managed_assets "
                "WHERE territory_id = :territory_id "
                "AND ST_DWithin("
                "geom::geography, "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, "
                ":meters)"
            ),
            {
                "territory_id": territory.id,
                "lon": -3.9251,
                "lat": 40.7405,
                "meters": 1000.0,
            },
        )
    )
    assert "ix_managed_assets_geom_geography" in distance_plan

    intersection_plan = "\n".join(
        db_session.scalars(
            text(
                "EXPLAIN (COSTS OFF) "
                "SELECT id FROM managed_assets "
                "WHERE territory_id = :territory_id "
                "AND ST_Intersects("
                "geom, ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))"
            ),
            {"territory_id": territory.id, "geojson": _BOX},
        )
    )
    assert "ix_managed_assets_geom" in intersection_plan


def _config(connection: Connection) -> Config:
    config = Config(str(_ROOT / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


def _at_revision(engine: Engine, revision: str) -> None:
    with engine.begin() as connection:
        command.upgrade(_config(connection), revision)


def _downgrade_to_previous(engine: Engine) -> None:
    with engine.begin() as connection:
        command.downgrade(_config(connection), _PREVIOUS_HEAD)


@pytest.fixture
def migration_engine(
    postgres_engine: Engine | None, tmp_path: Path
) -> Iterator[Engine]:
    if postgres_engine is not None:
        with postgres_engine.begin() as connection:
            connection.exec_driver_sql(
                "TRUNCATE TABLE managed_assets, territories "
                "RESTART IDENTITY CASCADE"
            )
        _downgrade_to_previous(postgres_engine)
        yield postgres_engine
        _at_revision(postgres_engine, "head")
        with postgres_engine.begin() as connection:
            connection.exec_driver_sql(
                "TRUNCATE TABLE managed_assets, territories "
                "RESTART IDENTITY CASCADE"
            )
        return

    engine = create_engine(f"sqlite:///{tmp_path / 'migration-cycle.db'}")
    _at_revision(engine, _PREVIOUS_HEAD)
    yield engine
    engine.dispose()


def test_upgrade_downgrade_upgrade_cycle_preserves_canonical_geometry(
    migration_engine: Engine,
) -> None:
    with migration_engine.begin() as connection:
        territory_id = connection.execute(
            text(
                "INSERT INTO territories (slug, name, budget_eur) "
                "VALUES ('cycle', 'Cycle', 1.0) RETURNING id"
            )
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO managed_assets "
                "(territory_id, external_asset_id, name, asset_type, "
                "geometry_geojson, region, status) "
                "VALUES (:territory_id, 'cycle-asset', 'Cycle asset', "
                "'trail', :geojson, 'Test', 'DETECTED')"
            ),
            {"territory_id": territory_id, "geojson": _NEAR},
        )

    _at_revision(migration_engine, "head")
    assert "geom" in {
        column["name"]
        for column in inspect(migration_engine).get_columns("managed_assets")
    }
    with migration_engine.connect() as connection:
        canonical, mirror_missing = connection.execute(
            text(
                "SELECT geometry_geojson, geom IS NULL "
                "FROM managed_assets WHERE external_asset_id = 'cycle-asset'"
            )
        ).one()
    assert canonical == _NEAR
    assert bool(mirror_missing) is (
        migration_engine.dialect.name != "postgresql"
    )

    with migration_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE managed_assets SET geometry_geojson = NULL "
                "WHERE external_asset_id = 'cycle-asset'"
            )
        )
        assert connection.scalar(
            text(
                "SELECT geom IS NULL FROM managed_assets "
                "WHERE external_asset_id = 'cycle-asset'"
            )
        )

    _downgrade_to_previous(migration_engine)
    assert "geom" not in {
        column["name"]
        for column in inspect(migration_engine).get_columns("managed_assets")
    }
    with migration_engine.connect() as connection:
        assert connection.scalar(
            text(
                "SELECT geometry_geojson FROM managed_assets "
                "WHERE external_asset_id = 'cycle-asset'"
            )
        ) == "{}"

    _at_revision(migration_engine, "head")
    assert "geom" in {
        column["name"]
        for column in inspect(migration_engine).get_columns("managed_assets")
    }
