"""
AuditLogRepository — CRUD + polymorphic subject lookup (Fase 5, 5.2).

``record(...)`` is the convenience entry point later write endpoints
(steps 5.3+) will call after each write, per the Fase 5 plan's step 5.7 —
defined here now so every subsequent write path has one place to log to.
"""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.audit_log import AuditLogEntry
from src.persistence.repositories.base import Repository


class AuditLogRepository(Repository[AuditLogEntry]):
    model = AuditLogEntry

    def list_by_subject(
        self, subject_type: str, subject_id: int
    ) -> list[AuditLogEntry]:
        return list(
            self.session.scalars(
                select(AuditLogEntry).where(
                    AuditLogEntry.subject_type == subject_type,
                    AuditLogEntry.subject_id == subject_id,
                )
            )
        )

    def record(
        self,
        *,
        actor: str,
        action: str,
        subject_type: str,
        subject_id: int,
        payload: dict | None = None,
    ) -> AuditLogEntry:
        return self.add(
            AuditLogEntry(
                actor=actor,
                action=action,
                subject_type=subject_type,
                subject_id=subject_id,
                payload=payload,
            )
        )
