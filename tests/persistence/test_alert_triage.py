from __future__ import annotations

import pytest

from src.persistence.enums import AlertStatus
from src.persistence.models import Alert, ManagedAsset, Territory
from src.persistence.repositories import AuditLogRepository
from src.persistence.services import audit
from src.persistence.services.alert_triage import (
    ReasonRequiredError,
    triage_alert,
)
from src.persistence.services.lifecycle import (
    IllegalTransitionError,
    ResourceNotFoundError,
)


def _alert(session, status: AlertStatus = AlertStatus.OPEN) -> Alert:
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
    alert = Alert(asset_id=asset.id, level="CRITICAL_INTERVENTION", risk_score=0.9)
    alert.status = status
    session.add(alert)
    session.flush()
    return alert


def test_assign_open_alert(db_session) -> None:
    alert = _alert(db_session)
    triage_alert(db_session, alert.id, AlertStatus.ASSIGNED, actor="gestor")
    assert alert.status == AlertStatus.ASSIGNED
    entry = AuditLogRepository(db_session).list_by_subject("alert", alert.id)[0]
    assert entry.action == audit.ALERT_TRIAGED
    assert entry.payload == {"from": "open", "to": "assigned", "reason": None}


def test_dismiss_requires_reason(db_session) -> None:
    alert = _alert(db_session)
    with pytest.raises(ReasonRequiredError):
        triage_alert(db_session, alert.id, AlertStatus.DISMISSED)
    # Unchanged, and no audit written.
    assert alert.status == AlertStatus.OPEN
    assert AuditLogRepository(db_session).list() == []


def test_dismiss_with_reason_logs_false_positive(db_session) -> None:
    alert = _alert(db_session)
    triage_alert(
        db_session,
        alert.id,
        AlertStatus.DISMISSED,
        reason="falso positivo: artefacto de máscara SCL",
        actor="gestor",
    )
    assert alert.status == AlertStatus.DISMISSED
    assert "falso positivo" in alert.reason
    entry = AuditLogRepository(db_session).list_by_subject("alert", alert.id)[0]
    assert entry.payload["reason"].startswith("falso positivo")


def test_illegal_transition_from_dismissed(db_session) -> None:
    alert = _alert(db_session, status=AlertStatus.DISMISSED)
    with pytest.raises(IllegalTransitionError):
        triage_alert(db_session, alert.id, AlertStatus.ASSIGNED)


def test_blank_reason_rejected_on_dismiss(db_session) -> None:
    alert = _alert(db_session)
    with pytest.raises(ReasonRequiredError):
        triage_alert(db_session, alert.id, AlertStatus.DISMISSED, reason="   ")


def test_missing_alert_raises(db_session) -> None:
    with pytest.raises(ResourceNotFoundError):
        triage_alert(db_session, 999, AlertStatus.ASSIGNED)


def test_escalated_can_still_be_dismissed(db_session) -> None:
    alert = _alert(db_session, status=AlertStatus.ESCALATED)
    triage_alert(
        db_session, alert.id, AlertStatus.DISMISSED, reason="resuelto en campo"
    )
    assert alert.status == AlertStatus.DISMISSED
