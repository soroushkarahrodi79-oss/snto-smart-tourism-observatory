"""
Integration tests for the /api/v2 alert & recommendation read endpoints
(Fase 5, 5.4). Seeds through the AlertEngine->persistence bridge itself, so
this exercises the full path: engine Alert -> persist_engine_alert -> HTTP read.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.alerts.engine import Alert as EngineAlert
from src.alerts.engine import AlertLevel
from src.api.main import create_app
from src.persistence.models import Base, ManagedAsset, Territory
from src.persistence.services.alert_ingest import persist_engine_alert
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
        seed.flush()
        persist_engine_alert(
            seed,
            EngineAlert(
                asset_id="pnsg-trail-001",
                level=AlertLevel.CRITICAL_INTERVENTION,
                score=0.91,
                triggered_rules=["score=0.910 > critical_threshold=0.85"],
                recommended_actions=[
                    "immediate_site_inspection",
                    "access_restriction",
                ],
            ),
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


def test_list_asset_alerts(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/1/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["alerts"][0]["level"] == "CRITICAL_INTERVENTION"
    assert body["alerts"][0]["status"] == "open"
    assert body["alerts"][0]["risk_score"] == 0.91


def test_list_asset_alerts_missing_asset_404(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/999/alerts")
    assert resp.status_code == 404


def test_get_alert_by_id(client: TestClient) -> None:
    resp = client.get("/api/v2/alerts/1")
    assert resp.status_code == 200
    assert resp.json()["triggered_rules"] == [
        "score=0.910 > critical_threshold=0.85"
    ]


def test_get_alert_404(client: TestClient) -> None:
    resp = client.get("/api/v2/alerts/999")
    assert resp.status_code == 404


def test_list_alert_recommendations(client: TestClient) -> None:
    resp = client.get("/api/v2/alerts/1/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    labels = [r["action_label"] for r in body["recommendations"]]
    assert labels == ["immediate_site_inspection", "access_restriction"]
    # Engine produced only labels; costs stay null (never fabricated).
    assert all(r["cost_eur_low"] is None for r in body["recommendations"])
    assert all(r["status"] == "pending" for r in body["recommendations"])


def test_recommendations_for_missing_alert_404(client: TestClient) -> None:
    resp = client.get("/api/v2/alerts/999/recommendations")
    assert resp.status_code == 404


# ── Triage (Fase 6.2) ────────────────────────────────────────────────────────

def test_triage_assign(client: TestClient) -> None:
    resp = client.post("/api/v2/alerts/1/triage", json={"to_status": "assigned"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "assigned"
    # Persisted + audited.
    assert client.get("/api/v2/alerts/1").json()["status"] == "assigned"
    log = client.get("/api/v2/audit-log/").json()
    assert log["entries"][0]["action"] == "alert.triaged"


def test_triage_dismiss_requires_reason_422(client: TestClient) -> None:
    resp = client.post("/api/v2/alerts/1/triage", json={"to_status": "dismissed"})
    assert resp.status_code == 422
    # Unchanged.
    assert client.get("/api/v2/alerts/1").json()["status"] == "open"


def test_triage_dismiss_with_reason(client: TestClient) -> None:
    resp = client.post(
        "/api/v2/alerts/1/triage",
        json={"to_status": "dismissed", "reason": "falso positivo"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "dismissed"
    assert body["reason"] == "falso positivo"


def test_triage_illegal_transition_409(client: TestClient) -> None:
    client.post(
        "/api/v2/alerts/1/triage",
        json={"to_status": "dismissed", "reason": "cerrado"},
    )
    # dismissed is terminal.
    resp = client.post("/api/v2/alerts/1/triage", json={"to_status": "assigned"})
    assert resp.status_code == 409


def test_triage_missing_alert_404(client: TestClient) -> None:
    resp = client.post("/api/v2/alerts/999/triage", json={"to_status": "assigned"})
    assert resp.status_code == 404


def test_triage_invalid_status_422(client: TestClient) -> None:
    resp = client.post("/api/v2/alerts/1/triage", json={"to_status": "nonsense"})
    assert resp.status_code == 422
