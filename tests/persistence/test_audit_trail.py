"""
Unit tests: every 5.3–5.6 write path leaves an AuditLogEntry (Fase 5, 5.7).
"""
from __future__ import annotations

from src.alerts.engine import Alert as EngineAlert
from src.alerts.engine import AlertLevel
from src.persistence.enums import InterventionStatus, ManagedAssetStatus
from src.persistence.models import Intervention, ManagedAsset, Territory
from src.persistence.repositories import AuditLogRepository
from src.persistence.services import audit
from src.persistence.services.alert_ingest import persist_engine_alert
from src.persistence.services.field_verification_ingest import (
    persist_field_observation,
)
from src.persistence.services.lifecycle import (
    transition_intervention,
    transition_managed_asset,
)
from src.validation.field import FieldObservation


def _asset(session) -> ManagedAsset:
    territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
    session.add(territory)
    session.flush()
    asset = ManagedAsset(
        territory_id=territory.id,
        external_asset_id="pnsg-trail-001",
        name="Sendero",
        asset_type="trail",
        geometry_geojson="{}",
        region="Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def test_alert_bridge_records_audit(db_session) -> None:
    _asset(db_session)
    persist_engine_alert(
        db_session,
        EngineAlert(
            asset_id="pnsg-trail-001",
            level=AlertLevel.CRITICAL_INTERVENTION,
            score=0.9,
            triggered_rules=["r"],
            recommended_actions=["a"],
        ),
        actor="gestor",
    )
    entries = AuditLogRepository(db_session).list()
    assert len(entries) == 1
    assert entries[0].action == audit.ALERT_PERSISTED
    assert entries[0].actor == "gestor"


def test_field_observation_bridge_records_audit(db_session) -> None:
    _asset(db_session)
    persist_field_observation(
        db_session,
        FieldObservation(
            plot_id="P1",
            lat=40.8,
            lon=-3.9,
            distance_to_trail_m=1.0,
            is_control=False,
            asset_id="pnsg-trail-001",
            veg_cover_pct=50.0,
        ),
        verifier="v",
        actor="gestor",
    )
    entries = AuditLogRepository(db_session).list()
    assert [e.action for e in entries] == [audit.FIELD_VERIFICATION_PERSISTED]


def test_managed_asset_transition_records_audit(db_session) -> None:
    asset = _asset(db_session)
    transition_managed_asset(
        db_session, asset.id, ManagedAssetStatus.VERIFIED, actor="gestor"
    )
    entry = AuditLogRepository(db_session).list_by_subject("managed_asset", asset.id)[0]
    assert entry.action == audit.MANAGED_ASSET_TRANSITIONED
    assert entry.payload == {"from": "detected", "to": "verified"}


def test_intervention_transition_records_audit(db_session) -> None:
    asset = _asset(db_session)
    intervention = Intervention(asset_id=asset.id)
    db_session.add(intervention)
    db_session.flush()
    transition_intervention(
        db_session, intervention.id, InterventionStatus.IN_PROGRESS, actor="gestor"
    )
    entry = AuditLogRepository(db_session).list_by_subject(
        "intervention", intervention.id
    )[0]
    assert entry.action == audit.INTERVENTION_TRANSITIONED
    assert entry.payload == {"from": "planned", "to": "in_progress"}


def test_failed_transition_leaves_no_audit(db_session) -> None:
    asset = _asset(db_session)
    from src.persistence.services.lifecycle import IllegalTransitionError

    try:
        transition_managed_asset(
            db_session, asset.id, ManagedAssetStatus.FUNDED, actor="gestor"
        )
    except IllegalTransitionError:
        pass
    assert AuditLogRepository(db_session).list() == []


def test_default_actor_is_system(db_session) -> None:
    asset = _asset(db_session)
    transition_managed_asset(db_session, asset.id, ManagedAssetStatus.VERIFIED)
    entry = AuditLogRepository(db_session).list()[0]
    assert entry.actor == audit.ACTOR_SYSTEM
