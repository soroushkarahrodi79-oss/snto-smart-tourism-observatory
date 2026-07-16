from __future__ import annotations

import pytest

from src.alerts.engine import Alert as EngineAlert
from src.alerts.engine import AlertLevel
from src.persistence.enums import AlertStatus, RecommendationStatus
from src.persistence.models import ManagedAsset, Territory
from src.persistence.repositories import (
    AlertRepository,
    RecommendationRepository,
)
from src.persistence.services.alert_ingest import (
    AssetNotRegisteredError,
    persist_engine_alert,
)


def _register_asset(session, external_id: str = "pnsg-trail-001") -> ManagedAsset:
    territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
    session.add(territory)
    session.flush()
    asset = ManagedAsset(
        territory_id=territory.id,
        external_asset_id=external_id,
        name="Sendero Circular",
        asset_type="trail",
        geometry_geojson='{"type": "Point", "coordinates": [0, 0]}',
        region="Comunidad de Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def _engine_alert(external_id: str = "pnsg-trail-001") -> EngineAlert:
    return EngineAlert(
        asset_id=external_id,
        level=AlertLevel.CRITICAL_INTERVENTION,
        score=0.91,
        triggered_rules=["score=0.910 > critical_threshold=0.85"],
        recommended_actions=[
            "immediate_site_inspection",
            "access_restriction",
            "emergency_restoration",
        ],
    )


def test_persist_engine_alert_writes_alert_and_recommendations(db_session) -> None:
    asset = _register_asset(db_session)

    alert = persist_engine_alert(db_session, _engine_alert())

    assert alert.asset_id == asset.id
    assert alert.level == "CRITICAL_INTERVENTION"
    assert alert.risk_score == pytest.approx(0.91)
    assert alert.status == AlertStatus.OPEN
    assert alert.triggered_rules == ["score=0.910 > critical_threshold=0.85"]

    recs = RecommendationRepository(db_session).list_by_alert(alert.id)
    assert [r.action_label for r in recs] == [
        "immediate_site_inspection",
        "access_restriction",
        "emergency_restoration",
    ]
    # Engine produces only labels — costs/owner/deadline stay unset, never faked.
    assert all(r.cost_eur_low is None and r.cost_eur_high is None for r in recs)
    assert all(r.status == RecommendationStatus.PENDING for r in recs)


def test_persist_engine_alert_unknown_asset_raises(db_session) -> None:
    with pytest.raises(AssetNotRegisteredError) as exc_info:
        persist_engine_alert(db_session, _engine_alert("does-not-exist"))
    assert exc_info.value.external_asset_id == "does-not-exist"
    # Nothing partially written.
    assert AlertRepository(db_session).list() == []


def test_persist_multiple_alerts_same_asset(db_session) -> None:
    _register_asset(db_session)
    persist_engine_alert(db_session, _engine_alert())
    persist_engine_alert(db_session, _engine_alert())
    assert len(AlertRepository(db_session).list()) == 2
