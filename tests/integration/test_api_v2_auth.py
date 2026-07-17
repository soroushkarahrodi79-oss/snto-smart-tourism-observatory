"""
Integration tests for minimal write-auth (Fase 5, 5.8): the API key gates
writes; reads always stay open. Uses monkeypatch to toggle
``settings.snto_api_key`` per test.
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


def _set_key(monkeypatch, value: str) -> None:
    # The dependency reads settings.snto_api_key at call time.
    from src.config.settings import settings

    monkeypatch.setattr(settings, "snto_api_key", value)


# ── Auth disabled (no key configured) — pre-5.8 behaviour preserved ──────────

def test_write_open_when_no_key(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "verified"}
    )
    assert resp.status_code == 200


# ── Auth enabled (key configured) ────────────────────────────────────────────

def test_write_rejected_without_key(client: TestClient, monkeypatch) -> None:
    _set_key(monkeypatch, "s3cret")
    resp = client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "verified"}
    )
    assert resp.status_code == 401


def test_write_rejected_with_wrong_key(client: TestClient, monkeypatch) -> None:
    _set_key(monkeypatch, "s3cret")
    resp = client.post(
        "/api/v2/managed-assets/1/transition",
        json={"to_status": "verified"},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 401


def test_write_accepted_with_valid_key(client: TestClient, monkeypatch) -> None:
    _set_key(monkeypatch, "s3cret")
    resp = client.post(
        "/api/v2/managed-assets/1/transition",
        json={"to_status": "verified"},
        headers={"X-API-Key": "s3cret", "X-Actor": "gestor-pnsg"},
    )
    assert resp.status_code == 200
    # Authenticated actor flows into the audit trail.
    log = client.get("/api/v2/audit-log/").json()
    assert log["entries"][0]["actor"] == "gestor-pnsg"


def test_authenticated_actor_defaults_to_api_key(
    client: TestClient, monkeypatch
) -> None:
    _set_key(monkeypatch, "s3cret")
    client.post(
        "/api/v2/managed-assets/1/interventions",
        json={"budget_eur": 100.0},
        headers={"X-API-Key": "s3cret"},  # no X-Actor
    )
    log = client.get("/api/v2/audit-log/").json()
    assert log["entries"][0]["actor"] == "api-key"


def test_reads_stay_open_when_key_configured(
    client: TestClient, monkeypatch
) -> None:
    _set_key(monkeypatch, "s3cret")
    # No key header — reads must still work.
    assert client.get("/api/v2/managed-assets/").status_code == 200
    assert client.get("/api/v2/managed-assets/1").status_code == 200
    assert client.get("/api/v2/audit-log/").status_code == 200


def test_rejected_write_leaves_no_state_change(
    client: TestClient, monkeypatch
) -> None:
    _set_key(monkeypatch, "s3cret")
    client.post(
        "/api/v2/managed-assets/1/transition", json={"to_status": "verified"}
    )  # 401, no key
    # State untouched, no audit entry.
    assert client.get("/api/v2/managed-assets/1").json()["status"] == "detected"
    assert client.get("/api/v2/audit-log/").json()["total"] == 0
