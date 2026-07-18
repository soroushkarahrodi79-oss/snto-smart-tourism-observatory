from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.persistence.enums import AlertStatus, ManagedAssetStatus
from src.persistence.models import (
    Alert,
    Base,
    FieldVerification,
    ManagedAsset,
    Recommendation,
    Territory,
)
from src.ui.services.urgent_actions import list_urgent_actions


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _asset(session, external_id: str, name: str) -> ManagedAsset:
    territory = session.query(Territory).first()
    if territory is None:
        territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
        session.add(territory)
        session.flush()
    asset = ManagedAsset(
        territory_id=territory.id,
        external_asset_id=external_id,
        name=name,
        asset_type="trail",
        geometry_geojson="{}",
        region="Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def _alert(session, asset, level, score, status=AlertStatus.OPEN) -> Alert:
    alert = Alert(asset_id=asset.id, level=level, risk_score=score, status=status)
    session.add(alert)
    session.flush()
    return alert


def test_empty_backend_yields_no_actions(session) -> None:
    assert list_urgent_actions(session) == []


def test_orders_by_risk_desc_and_maps_fields(session) -> None:
    a1 = _asset(session, "t-1", "Sendero A")
    a2 = _asset(session, "t-2", "Sendero B")
    _alert(session, a1, "URGENT_MONITORING", 0.5)
    high = _alert(session, a2, "CRITICAL_INTERVENTION", 0.95)
    session.add(Recommendation(alert_id=high.id, action_label="Cerrar acceso"))
    session.flush()

    actions = list_urgent_actions(session)
    assert [a.asset_name for a in actions] == ["Sendero B", "Sendero A"]
    top = actions[0]
    assert top.level == "CRITICAL_INTERVENTION"
    assert top.top_action == "Cerrar acceso"
    # detected -> next allowed status is verified (5.5 state map).
    assert top.next_status == ManagedAssetStatus.VERIFIED
    assert actions[1].top_action is None


def test_confidence_and_field_verification_enrichment(session) -> None:
    asset = _asset(session, "t-1", "Sendero A")
    alert = _alert(session, asset, "CRITICAL_INTERVENTION", 0.9)
    session.add(
        Recommendation(
            alert_id=alert.id, action_label="Cerrar acceso", confidence=0.72
        )
    )
    session.add(
        FieldVerification(
            asset_id=asset.id,
            verified_at=datetime(2026, 6, 1),
            method="penetrometro",
            verifier="Equipo PNSG",
            result="42.0",
        )
    )
    session.flush()

    action = list_urgent_actions(session)[0]
    assert action.confidence == 0.72
    assert action.field_verified is True


def test_no_recommendation_or_verification_is_honest_null(session) -> None:
    asset = _asset(session, "t-1", "Sendero A")
    _alert(session, asset, "NORMAL", 0.3)
    action = list_urgent_actions(session)[0]
    assert action.confidence is None
    assert action.field_verified is False


def test_only_open_alerts_surface(session) -> None:
    asset = _asset(session, "t-1", "Sendero A")
    _alert(session, asset, "NORMAL", 0.2, status=AlertStatus.DISMISSED)
    assert list_urgent_actions(session) == []


def test_terminal_asset_has_no_next_status(session) -> None:
    asset = _asset(session, "t-1", "Sendero A")
    asset.status = ManagedAssetStatus.MONITORED
    session.flush()
    _alert(session, asset, "NORMAL", 0.3)
    assert list_urgent_actions(session)[0].next_status is None


def test_limit_caps_results(session) -> None:
    for i in range(5):
        asset = _asset(session, f"t-{i}", f"Sendero {i}")
        _alert(session, asset, "NORMAL", 0.1 * i)
    assert len(list_urgent_actions(session, limit=3)) == 3
