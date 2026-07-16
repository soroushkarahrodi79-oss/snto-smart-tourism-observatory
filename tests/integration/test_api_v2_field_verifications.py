"""
Integration tests for the /api/v2 field-verification endpoints (Fase 5, 5.6).
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


def test_create_and_list_field_verification(client: TestClient) -> None:
    created = client.post(
        "/api/v2/managed-assets/1/field-verifications",
        json={
            "verified_at": "2026-06-01T00:00:00",
            "method": "penetrometro",
            "verifier": "Equipo de campo PNSG",
            "result": "42.0",
            "notes": "plot=P1; soil_compaction_mpa=3.0",
        },
    )
    assert created.status_code == 200
    assert created.json()["method"] == "penetrometro"

    listed = client.get("/api/v2/managed-assets/1/field-verifications")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["field_verifications"][0]["verifier"] == "Equipo de campo PNSG"


def test_create_defaults_verified_at_when_omitted(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/1/field-verifications",
        json={"method": "visual", "verifier": "X", "result": "ok"},
    )
    assert resp.status_code == 200
    assert resp.json()["verified_at"] is not None


def test_create_for_missing_asset_404(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/999/field-verifications",
        json={"method": "visual", "verifier": "X", "result": "ok"},
    )
    assert resp.status_code == 404


def test_list_for_missing_asset_404(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/999/field-verifications")
    assert resp.status_code == 404


def test_create_missing_required_field_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/managed-assets/1/field-verifications",
        json={"method": "visual"},  # missing verifier + result
    )
    assert resp.status_code == 422
