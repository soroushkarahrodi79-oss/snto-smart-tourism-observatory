"""
Integration tests for the /api/v2 read endpoints (Fase 5, 5.3).

Uses FastAPI's TestClient with get_db overridden to a shared in-memory SQLite
session, seeded with one territory / asset / two observations.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.main import create_app
from src.persistence.models import Base, ManagedAsset, Observation, Territory
from src.persistence.session import get_db


@pytest.fixture
def client() -> Iterator[TestClient]:
    # StaticPool + check_same_thread=False: one shared in-memory DB across the
    # seeding thread and TestClient's request thread (a plain sqlite:///:memory:
    # would give each connection its own empty database).
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as seed:
        territory = Territory(slug="pnsg", name="PNSG", budget_eur=250_000.0)
        seed.add(territory)
        seed.flush()
        asset = ManagedAsset(
            territory_id=territory.id,
            external_asset_id="pnsg-trail-001",
            name="Sendero Circular",
            asset_type="trail",
            geometry_geojson='{"type": "Point", "coordinates": [0, 0]}',
            region="Comunidad de Madrid",
        )
        seed.add(asset)
        seed.flush()
        seed.add_all(
            [
                Observation(
                    asset_id=asset.id,
                    observed_at=datetime(2026, 1, 1),
                    source="real",
                    ehs=0.7,
                ),
                Observation(
                    asset_id=asset.id,
                    observed_at=datetime(2026, 2, 1),
                    source="calibrated",
                    ehs=0.6,
                ),
            ]
        )
        seed.commit()

    def _override_get_db() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def test_list_managed_assets(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["assets"][0]["external_asset_id"] == "pnsg-trail-001"
    assert body["assets"][0]["status"] == "detected"


def test_get_managed_asset_by_id(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Sendero Circular"


def test_get_managed_asset_404(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/999")
    assert resp.status_code == 404


def test_filter_by_status(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/", params={"status": "detected"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp_empty = client.get(
        "/api/v2/managed-assets/", params={"status": "verified"}
    )
    assert resp_empty.json()["total"] == 0


def test_list_asset_observations_ordered(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/1/observations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    # ordered by observed_at ascending
    assert body["observations"][0]["observed_at"] < (
        body["observations"][1]["observed_at"]
    )
    assert body["observations"][0]["source"] == "real"


def test_observations_for_missing_asset_404(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/999/observations")
    assert resp.status_code == 404


def test_existing_health_endpoint_unchanged(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
