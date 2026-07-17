"""
Single choke-point for writing audit-trail entries (Fase 5, step 5.7).

Every write introduced in steps 5.3–5.6 records one ``AuditLogEntry`` through
``record()`` here, so there is one documented action vocabulary rather than
ad-hoc strings scattered across services and routers.

``actor`` is *who* performed the write. Auth does not exist yet (step 5.8), so
API callers thread a value from the ``get_actor`` dependency (``anonymous`` by
default) and non-API callers (batch bridges) default to ``ACTOR_SYSTEM``. When
5.8 lands, only the source of ``actor`` changes — every call site here stays
the same.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.persistence.models.audit_log import AuditLogEntry
from src.persistence.repositories import AuditLogRepository

ACTOR_SYSTEM = "system"

# Action vocabulary (subject_type + verb). Kept as constants so the audit log
# is queryable against a stable set of strings.
ALERT_PERSISTED = "alert.persisted"
FIELD_VERIFICATION_PERSISTED = "field_verification.persisted"
FIELD_VERIFICATION_CREATED = "field_verification.created"
MANAGED_ASSET_TRANSITIONED = "managed_asset.transitioned"
INTERVENTION_CREATED = "intervention.created"
INTERVENTION_TRANSITIONED = "intervention.transitioned"


def record(
    session: Session,
    *,
    actor: str,
    action: str,
    subject_type: str,
    subject_id: int,
    payload: dict | None = None,
) -> AuditLogEntry:
    """Append one audit entry in the caller's session (committed by the caller)."""
    return AuditLogRepository(session).record(
        actor=actor,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        payload=payload,
    )
