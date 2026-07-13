from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from src.persistence.enums import (
    AlertStatus,
    InterventionStatus,
    ManagedAssetStatus,
    RecommendationStatus,
)
from src.persistence.models import (
    Alert,
    AuditLogEntry,
    Decision,
    FieldVerification,
    Intervention,
    ManagedAsset,
    Observation,
    Recommendation,
    Territory,
)


def _make_territory(session) -> Territory:
    territory = Territory(
        slug="pnsg", name="Sierra de Guadarrama", budget_eur=250_000.0
    )
    session.add(territory)
    session.flush()
    return territory


def _make_asset(session, territory: Territory) -> ManagedAsset:
    asset = ManagedAsset(
        territory_id=territory.id,
        external_asset_id="pnsg-trail-001",
        name="Sendero Circular",
        asset_type="trail",
        geometry_geojson='{"type": "Point", "coordinates": [0, 0]}',
        region="Comunidad de Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def test_managed_asset_defaults_to_detected(db_session) -> None:
    territory = _make_territory(db_session)
    asset = _make_asset(db_session, territory)
    assert asset.status == ManagedAssetStatus.DETECTED
    assert asset.territory.slug == "pnsg"


def test_managed_asset_lifecycle_transition(db_session) -> None:
    territory = _make_territory(db_session)
    asset = _make_asset(db_session, territory)
    asset.status = ManagedAssetStatus.VERIFIED
    db_session.flush()
    db_session.refresh(asset)
    assert asset.status == ManagedAssetStatus.VERIFIED


def test_observation_source_reuses_evidence_class_values(db_session) -> None:
    from src.platform.evidence import EvidenceClass

    territory = _make_territory(db_session)
    asset = _make_asset(db_session, territory)
    observation = Observation(
        asset_id=asset.id,
        observed_at=datetime(2026, 1, 1),
        source=EvidenceClass.REAL.value,
        ehs=0.72,
        ndvi=0.5,
        ndmi=0.3,
        raw_payload={"sensor": "sentinel-2"},
    )
    db_session.add(observation)
    db_session.flush()
    assert observation.source == "real"
    assert observation.asset.id == asset.id


def test_alert_and_recommendation_cost_range(db_session) -> None:
    territory = _make_territory(db_session)
    asset = _make_asset(db_session, territory)
    alert = Alert(
        asset_id=asset.id,
        level="red",
        risk_score=0.91,
        triggered_rules=["erosion_high"],
    )
    db_session.add(alert)
    db_session.flush()
    assert alert.status == AlertStatus.OPEN

    recommendation = Recommendation(
        alert_id=alert.id,
        action_label="Reforzar drenaje del sendero",
        cost_eur_low=2_000.0,
        cost_eur_high=6_000.0,
        confidence=0.65,
        owner="Gestor PNSG",
        deadline=date(2026, 9, 1),
    )
    db_session.add(recommendation)
    db_session.flush()
    assert recommendation.status == RecommendationStatus.PENDING
    assert recommendation.cost_eur_low < recommendation.cost_eur_high
    assert recommendation.alert.id == alert.id


def test_field_verification(db_session) -> None:
    territory = _make_territory(db_session)
    asset = _make_asset(db_session, territory)
    verification = FieldVerification(
        asset_id=asset.id,
        verified_at=datetime(2026, 6, 1),
        method="penetrometro",
        verifier="Equipo de campo PNSG",
        result="Compactacion dentro de rango esperado",
    )
    db_session.add(verification)
    db_session.flush()
    assert verification.asset.id == asset.id


def test_intervention_optional_recommendation(db_session) -> None:
    territory = _make_territory(db_session)
    asset = _make_asset(db_session, territory)
    intervention = Intervention(asset_id=asset.id, budget_eur=3_000.0)
    db_session.add(intervention)
    db_session.flush()
    assert intervention.status == InterventionStatus.PLANNED
    assert intervention.recommendation_id is None
    assert intervention.recommendation is None


def test_decision_and_audit_log_are_polymorphic(db_session) -> None:
    decision = Decision(
        subject_type="alert",
        subject_id=1,
        decided_by="Gestor PNSG",
        decision="assigned",
        reason="Prioridad alta",
    )
    audit_entry = AuditLogEntry(
        actor="api-key:gestor",
        action="create",
        subject_type="alert",
        subject_id=1,
        payload={"level": "red"},
    )
    db_session.add_all([decision, audit_entry])
    db_session.flush()
    assert decision.subject_id == audit_entry.subject_id


def test_managed_asset_requires_territory(db_session) -> None:
    asset = ManagedAsset(
        territory_id=999,
        external_asset_id="orphan-001",
        name="Sin territorio",
        asset_type="trail",
        geometry_geojson="{}",
        region="Nowhere",
    )
    db_session.add(asset)
    with pytest.raises(IntegrityError):
        db_session.flush()
