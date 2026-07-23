"""Integration tests for territory-scoped write authorization (v3.0, ADR-005).

Once identity is adopted (users exist), a write is allowed only for an active
user who can_write the target territory — the actor is the X-Actor email.
Backward compatibility (no users -> writes open) is covered by
test_api_v2_auth.py; here every fixture seeds users so enforcement is armed.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.api.main import create_app
from src.persistence.enums import UserRole
from src.persistence.models import (
    Base,
    ManagedAsset,
    Organization,
    Territory,
    User,
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
        org_a = Organization(slug="org-a", name="Org A")
        org_b = Organization(slug="org-b", name="Org B")
        seed.add_all([org_a, org_b])
        seed.flush()
        terr_a = Territory(
            slug="pnsg", name="PNSG", budget_eur=250_000.0, org_id=org_a.id
        )
        seed.add(terr_a)
        seed.flush()
        seed.add(
            ManagedAsset(
                territory_id=terr_a.id, external_asset_id="pnsg-trail-001",
                name="Sendero Circular", asset_type="trail",
                geometry_geojson='{"type": "Point", "coordinates": [0, 0]}',
                region="Comunidad de Madrid",
            )
        )
        seed.add_all([
            User(org_id=org_a.id, email="editor@a.es", display_name="Editor A",
                 role=UserRole.EDITOR),
            User(org_id=org_a.id, email="viewer@a.es", display_name="Viewer A",
                 role=UserRole.VIEWER),
            User(org_id=org_b.id, email="editor@b.es", display_name="Editor B",
                 role=UserRole.EDITOR),
        ])
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


def _transition(client: TestClient, actor: str):
    return client.post(
        "/api/v2/managed-assets/1/transition",
        json={"to_status": "verified"},
        headers={"X-Actor": actor},
    )


def test_editor_of_owning_org_can_write(client: TestClient) -> None:
    assert _transition(client, "editor@a.es").status_code == 200


def test_viewer_cannot_write(client: TestClient) -> None:
    resp = _transition(client, "viewer@a.es")
    assert resp.status_code == 403


def test_cross_org_editor_cannot_write(client: TestClient) -> None:
    resp = _transition(client, "editor@b.es")
    assert resp.status_code == 403


def test_unknown_actor_is_rejected(client: TestClient) -> None:
    resp = _transition(client, "nobody@nowhere.es")
    assert resp.status_code == 403


def test_missing_asset_still_404s_not_403(client: TestClient) -> None:
    # existence check precedes authz, so a missing resource does not leak a 403
    resp = client.post(
        "/api/v2/managed-assets/999/transition",
        json={"to_status": "verified"},
        headers={"X-Actor": "editor@a.es"},
    )
    assert resp.status_code == 404


def test_reads_stay_open_regardless_of_identity(client: TestClient) -> None:
    # reads never depend on the write gate
    assert client.get("/api/v2/managed-assets/1").status_code == 200
