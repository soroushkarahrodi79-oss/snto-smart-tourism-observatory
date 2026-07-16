"""
Integration tests for the /api/v2 lifecycle write endpoints (Fase 5, 5.5):
ManagedAsset transitions and the Intervention create/read/transition flow.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.main import create_app
from src.persistence.models import Base, ManagedAsset, Territory
from src.persistence.session import get_db


@pytest.fixture
def client() -> Iterator[TestClient]:
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
        seed.add(
            ManagedAsset(
                territory_id=territory.id,
                external_asset_id="pnsg-trail-001",
                name="Sendero Circular",
                asset_type="trail",
                geometry_geojson='{"type": "Point", "coordinates": [0, 0]}',
                region="Comunidad de Madrid",
            )
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


def test_managed_asset_legal_transition(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "verified"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"
    # Persisted: a subsequent GET reflects the new state.
    assert client.get("/api/v2/managed-assets/1").json()["status"] == "verified"


def test_managed_asset_illegal_transition_409(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "funded"}
    )
    assert resp.status_code == 409
    # State untouched.
    assert client.get("/api/v2/managed-assets/1").json()["status"] == "detected"


def test_managed_asset_transition_missing_404(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/999/transition", json={"to_status": "verified"}
    )
    assert resp.status_code == 404


def test_managed_asset_transition_invalid_status_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "nonsense"}
    )
    assert resp.status_code == 422


def test_intervention_create_read_transition(client: TestClient) -> None:
    created = client.post(
        "/api/v2/managed-assets/1/interventions", json={"budget_eur": 5000.0}
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "planned"
    assert body["budget_eur"] == 5000.0
    intervention_id = body["id"]

    got = client.get(f"/api/v2/interventions/{intervention_id}")
    assert got.status_code == 200
    assert got.json()["asset_id"] == 1

    advanced = client.post(
        f"/api/v2/interventions/{intervention_id}/transition",
        json={"to_status": "in_progress"},
    )
    assert advanced.status_code == 200
    assert advanced.json()["status"] == "in_progress"


def test_intervention_illegal_transition_409(client: TestClient) -> None:
    created = client.post(
        "/api/v2/managed-assets/1/interventions", json={}
    )
    intervention_id = created.json()["id"]
    resp = client.post(
        f"/api/v2/interventions/{intervention_id}/transition",
        json={"to_status": "resolved"},
    )
    assert resp.status_code == 409


def test_intervention_create_for_missing_asset_404(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/999/interventions", json={"budget_eur": 1.0}
    )
    assert resp.status_code == 404


def test_intervention_get_missing_404(client: TestClient) -> None:
    resp = client.get("/api/v2/interventions/999")
    assert resp.status_code == 404
