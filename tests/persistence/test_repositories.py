from __future__ import annotations

from datetime import datetime

from src.persistence.enums import AlertStatus, ManagedAssetStatus
from src.persistence.models import (
    Alert,
    Decision,
    FieldVerification,
    Intervention,
    ManagedAsset,
    Observation,
    Recommendation,
    Territory,
)
from src.persistence.repositories import (
    AlertRepository,
    AuditLogRepository,
    DecisionRepository,
    FieldVerificationRepository,
    InterventionRepository,
    ManagedAssetRepository,
    ObservationRepository,
    RecommendationRepository,
    TerritoryRepository,
)


def _seed_asset(session) -> ManagedAsset:
    territory = TerritoryRepository(session).add(
        Territory(slug="pnsg", name="Sierra de Guadarrama", budget_eur=250_000.0)
    )
    return ManagedAssetRepository(session).add(
        ManagedAsset(
            territory_id=territory.id,
            external_asset_id="pnsg-trail-001",
            name="Sendero Circular",
            asset_type="trail",
            geometry_geojson='{"type": "Point", "coordinates": [0, 0]}',
            region="Comunidad de Madrid",
        )
    )


def test_territory_repository_crud_and_slug_lookup(db_session) -> None:
    repo = TerritoryRepository(db_session)
    territory = repo.add(Territory(slug="pnsg", name="PNSG", budget_eur=1000.0))

    assert repo.get(territory.id) == territory
    assert repo.get_by_slug("pnsg") == territory
    assert repo.get_by_slug("missing") is None
    assert repo.list() == [territory]

    repo.delete(territory)
    assert repo.get(territory.id) is None


def test_managed_asset_repository_lookups(db_session) -> None:
    asset = _seed_asset(db_session)
    repo = ManagedAssetRepository(db_session)

    assert repo.get_by_external_id("pnsg-trail-001") == asset
    assert repo.get_by_external_id("does-not-exist") is None
    assert repo.list_by_territory(asset.territory_id) == [asset]
    assert repo.list_by_status(ManagedAssetStatus.DETECTED) == [asset]
    assert repo.list_by_status(ManagedAssetStatus.VERIFIED) == []


def test_observation_repository_orders_by_date(db_session) -> None:
    asset = _seed_asset(db_session)
    repo = ObservationRepository(db_session)
    later = repo.add(
        Observation(asset_id=asset.id, observed_at=datetime(2026, 2, 1), source="real")
    )
    earlier = repo.add(
        Observation(asset_id=asset.id, observed_at=datetime(2026, 1, 1), source="real")
    )

    assert repo.list_by_asset(asset.id) == [earlier, later]


def test_alert_repository_open_and_by_asset(db_session) -> None:
    asset = _seed_asset(db_session)
    repo = AlertRepository(db_session)
    open_alert = repo.add(Alert(asset_id=asset.id, level="red", risk_score=0.9))
    dismissed = repo.add(Alert(asset_id=asset.id, level="amber", risk_score=0.4))
    dismissed.status = AlertStatus.DISMISSED
    db_session.flush()

    assert repo.list_by_asset(asset.id) == [open_alert, dismissed]
    assert repo.list_open() == [open_alert]


def test_recommendation_repository_by_alert(db_session) -> None:
    asset = _seed_asset(db_session)
    alert = AlertRepository(db_session).add(
        Alert(asset_id=asset.id, level="red", risk_score=0.9)
    )
    repo = RecommendationRepository(db_session)
    recommendation = repo.add(
        Recommendation(
            alert_id=alert.id,
            action_label="Reforzar drenaje",
            cost_eur_low=1000.0,
            cost_eur_high=3000.0,
        )
    )

    assert repo.list_by_alert(alert.id) == [recommendation]


def test_field_verification_repository_by_asset(db_session) -> None:
    asset = _seed_asset(db_session)
    repo = FieldVerificationRepository(db_session)
    verification = repo.add(
        FieldVerification(
            asset_id=asset.id,
            verified_at=datetime(2026, 6, 1),
            method="penetrometro",
            verifier="Equipo de campo",
            result="Ok",
        )
    )

    assert repo.list_by_asset(asset.id) == [verification]


def test_intervention_repository_by_asset(db_session) -> None:
    asset = _seed_asset(db_session)
    repo = InterventionRepository(db_session)
    intervention = repo.add(Intervention(asset_id=asset.id, budget_eur=500.0))

    assert repo.list_by_asset(asset.id) == [intervention]


def test_decision_repository_by_subject(db_session) -> None:
    repo = DecisionRepository(db_session)
    created = repo.add(
        Decision(
            subject_type="alert",
            subject_id=1,
            decided_by="Gestor PNSG",
            decision="assigned",
        )
    )

    assert repo.list_by_subject("alert", 1) == [created]
    assert repo.list_by_subject("alert", 2) == []


def test_audit_log_repository_record_and_lookup(db_session) -> None:
    repo = AuditLogRepository(db_session)
    entry = repo.record(
        actor="api-key:gestor",
        action="create",
        subject_type="alert",
        subject_id=1,
        payload={"level": "red"},
    )

    assert repo.list_by_subject("alert", 1) == [entry]
    assert repo.list_by_subject("alert", 2) == []
