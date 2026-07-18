"""
Alert triage state machine (Fase 6, step 6.2).

Closes part of the "Urgent actions" P1 gap (`plan_fase6_v2_ui_evolution.md`
§1.3): an open alert can be **assigned**, **escalated**, or **dismissed with a
reason**, mirroring the validated lifecycle state machines from Fase 5.5 and
audited through the single choke-point from Fase 5.7.

`dismissed` requires a reason — that is how a false positive is logged
(spec §6, "false positives logged"): the alert is dismissed with the reason
recorded, never silently deleted. Forward-only in the sense that `dismissed`
is terminal; assign/escalate can still move between each other before a final
dismissal.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.persistence.enums import AlertStatus
from src.persistence.models.alert import Alert
from src.persistence.repositories import AlertRepository
from src.persistence.services import audit
from src.persistence.services.lifecycle import (
    IllegalTransitionError,
    ResourceNotFoundError,
)

# Allowed triage transitions. `dismissed` is terminal.
ALERT_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.OPEN: {
        AlertStatus.ASSIGNED,
        AlertStatus.ESCALATED,
        AlertStatus.DISMISSED,
    },
    AlertStatus.ASSIGNED: {AlertStatus.ESCALATED, AlertStatus.DISMISSED},
    AlertStatus.ESCALATED: {AlertStatus.ASSIGNED, AlertStatus.DISMISSED},
    AlertStatus.DISMISSED: set(),
}


class ReasonRequiredError(ValueError):
    """Raised when dismissing an alert without a reason."""

    def __init__(self) -> None:
        super().__init__("Dismissing an alert requires a reason.")


def triage_alert(
    session: Session,
    alert_id: int,
    to_status: AlertStatus,
    *,
    reason: str | None = None,
    actor: str = audit.ACTOR_SYSTEM,
) -> Alert:
    """Move an alert through triage; dismissing requires a reason. Audited."""
    alert = AlertRepository(session).get(alert_id)
    if alert is None:
        raise ResourceNotFoundError(f"Alert id={alert_id} not found")

    from_status = alert.status
    if to_status not in ALERT_TRANSITIONS.get(from_status, set()):
        raise IllegalTransitionError(from_status, to_status)
    if to_status is AlertStatus.DISMISSED and not (reason and reason.strip()):
        raise ReasonRequiredError()

    alert.status = to_status
    if reason and reason.strip():
        alert.reason = reason.strip()
    session.flush()

    audit.record(
        session,
        actor=actor,
        action=audit.ALERT_TRIAGED,
        subject_type="alert",
        subject_id=alert.id,
        payload={
            "from": from_status.value,
            "to": to_status.value,
            "reason": alert.reason,
        },
    )
    return alert
