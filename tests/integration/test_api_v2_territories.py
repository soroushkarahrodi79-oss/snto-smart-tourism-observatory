"""Integration tests for /api/v2/territories (v3.0, mobile Fase 2 read layer).

Uses the repo's existing FastAPI TestClient pattern (shared in-memory SQLite,
get_db overridden). Covers the new territories router and the managed-assets
enrichment (map centroid, latest-observation freshness/evidence) added
alongside it — both exist to serve the mobile read contract.
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
from src.persistence.enums import AlertStatus
from src.persistence.models import (
    Alert,
    Base,
    ManagedAsset,
    Observation,
    Territory,
)
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
        empty_territory = Territory(slug="empty", name="Sin activos", budget_eur=1.0)
        seed.add_all([territory, empty_territory])
        seed.flush()

        asset = ManagedAsset(
            territory_id=territory.id,
            external_asset_id="pnsg-trail-001",
            name="Sendero Circular",
            asset_type="trail",
            geometry_geojson='{"type": "Point", "coordinates": [-3.96, 40.82]}',
            region="Comunidad de Madrid",
        )
        asset_no_geom = ManagedAsset(
            territory_id=territory.id,
            external_asset_id="pnsg-trail-002",
            name="Sendero sin geometría",
            asset_type="trail",
            geometry_geojson="{not valid geojson",
            region="Comunidad de Madrid",
        )
        seed.add_all([asset, asset_no_geom])
        seed.flush()

        seed.add_all(
            [
                Observation(
                    asset_id=asset.id,
                    observed_at=datetime(2026, 1, 1),
                    source="real",
                    ehs=70.0,
                ),
                Observation(
                    asset_id=asset.id,
                    observed_at=datetime(2026, 6, 1),
                    source="calibrated",
                    ehs=65.0,
                ),
            ]
        )
        seed.add(
            Alert(
                asset_id=asset.id,
                level="URGENT_MONITORING",
                risk_score=0.6,
                status=AlertStatus.OPEN,
            )
        )
        seed.add(
            Alert(
                asset_id=asset.id,
                level="NORMAL",
                risk_score=0.1,
                status=AlertStatus.DISMISSED,
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


# ── /api/v2/territories ──────────────────────────────────────────────────────

def test_list_territories(client: TestClient) -> None:
    resp = client.get("/api/v2/territories/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    slugs = {t["slug"] for t in body["territories"]}
    assert slugs == {"pnsg", "empty"}


def test_get_territory(client: TestClient) -> None:
    resp = client.get("/api/v2/territories/1")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "pnsg"


def test_get_territory_missing_404s(client: TestClient) -> None:
    resp = client.get("/api/v2/territories/999")
    assert resp.status_code == 404


def test_territory_summary_reflects_freshest_observation(client: TestClient) -> None:
    resp = client.get("/api/v2/territories/1/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_count"] == 2
    assert body["open_alert_count"] == 1  # only the OPEN alert counts
    assert body["updated_at"].startswith("2026-06-01")  # the freshest observation
    assert body["evidence_class"] == "calibrated"  # source of the freshest one


def test_territory_summary_with_no_assets_is_honest_not_fabricated(
    client: TestClient,
) -> None:
    resp = client.get("/api/v2/territories/2/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_count"] == 0
    assert body["open_alert_count"] == 0
    assert body["updated_at"] is None
    assert body["evidence_class"] is None


# ── managed-assets enrichment (centroid + freshness/evidence) ───────────────

def test_asset_list_carries_centroid_and_latest_evidence(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/")
    assert resp.status_code == 200
    by_external_id = {a["external_asset_id"]: a for a in resp.json()["assets"]}

    with_geom = by_external_id["pnsg-trail-001"]
    assert with_geom["latitude"] == 40.82
    assert with_geom["longitude"] == -3.96
    assert with_geom["latest_evidence_class"] == "calibrated"
    assert with_geom["latest_observed_at"].startswith("2026-06-01")

    without_geom = by_external_id["pnsg-trail-002"]
    assert without_geom["latitude"] is None
    assert without_geom["longitude"] is None
    # never fabricated even when geometry parsing fails
    assert without_geom["latest_evidence_class"] is None


def test_asset_detail_matches_list_enrichment(client: TestClient) -> None:
    resp = client.get("/api/v2/managed-assets/1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["latitude"] == 40.82
    assert body["longitude"] == -3.96
