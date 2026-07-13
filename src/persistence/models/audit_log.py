"""
AuditLogEntry — an immutable record of a write action (Fase 5).

Same polymorphic ``subject_type``/``subject_id`` shape as ``Decision``, but
for system-level bookkeeping (who did what, when) rather than a human
decision's rationale.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(64))
    subject_type: Mapped[str] = mapped_column(String(64), index=True)
    subject_id: Mapped[int] = mapped_column(index=True)
    payload: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"AuditLogEntry(id={self.id!r}, actor={self.actor!r}, "
            f"action={self.action!r})"
        )
