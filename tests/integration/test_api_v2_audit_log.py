"""
Integration tests: /api/v2 writes leave an audit trail, and the read endpoint
surfaces it (Fase 5, 5.7).
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


def test_empty_audit_log(client: TestClient) -> None:
    resp = client.get("/api/v2/audit-log/")
    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "entries": []}


def test_transition_write_is_audited_with_actor_header(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/1/transition",
        json={"to_status": "verified"},
        headers={"X-Actor": "gestor-pnsg"},
    )
    assert resp.status_code == 200

    log = client.get("/api/v2/audit-log/").json()
    assert log["total"] == 1
    entry = log["entries"][0]
    assert entry["action"] == "managed_asset.transitioned"
    assert entry["actor"] == "gestor-pnsg"
    assert entry["payload"] == {"from": "detected", "to": "verified"}


def test_actor_defaults_to_anonymous(client: TestClient) -> None:
    client.post(
        "/api/v2/managed-assets/1/interventions", json={"budget_eur": 1000.0}
    )
    log = client.get("/api/v2/audit-log/").json()
    assert log["entries"][0]["actor"] == "anonymous"
    assert log["entries"][0]["action"] == "intervention.created"


def test_failed_write_leaves_no_audit(client: TestClient) -> None:
    # Illegal transition (detected -> funded) returns 409 and must not audit.
    resp = client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "funded"}
    )
    assert resp.status_code == 409
    assert client.get("/api/v2/audit-log/").json()["total"] == 0


def test_filter_by_subject(client: TestClient) -> None:
    client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "verified"}
    )
    created = client.post(
        "/api/v2/managed-assets/1/interventions", json={}
    ).json()

    filtered = client.get(
        "/api/v2/audit-log/",
        params={"subject_type": "intervention", "subject_id": created["id"]},
    ).json()
    assert filtered["total"] == 1
    assert filtered["entries"][0]["action"] == "intervention.created"


def test_partial_subject_filter_422(client: TestClient) -> None:
    resp = client.get(
        "/api/v2/audit-log/", params={"subject_type": "intervention"}
    )
    assert resp.status_code == 422


def test_multiple_writes_newest_first(client: TestClient) -> None:
    client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "verified"}
    )
    client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "assigned"}
    )
    entries = client.get("/api/v2/audit-log/").json()["entries"]
    # id desc → the assigned transition (written last) comes first.
    assert entries[0]["payload"] == {"from": "verified", "to": "assigned"}
    assert entries[1]["payload"] == {"from": "detected", "to": "verified"}
