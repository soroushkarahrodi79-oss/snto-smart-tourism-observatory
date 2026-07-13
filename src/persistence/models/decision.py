"""
Decision — a recorded human choice on some subject (Fase 5).

Generic on purpose: ``subject_type``/``subject_id`` point at any other
persisted record (an Alert, a Recommendation, an Intervention...) so this
table doesn't need one FK per decidable entity. Mirrors the same
polymorphic-reference shape as ``AuditLogEntry``.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(64), index=True)
    subject_id: Mapped[int] = mapped_column(index=True)
    decided_by: Mapped[str] = mapped_column(String(200))
    decision: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    decided_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"Decision(id={self.id!r}, subject_type={self.subject_type!r}, "
            f"subject_id={self.subject_id!r})"
        )
