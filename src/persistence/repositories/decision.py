"""DecisionRepository — CRUD + polymorphic subject lookup (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.decision import Decision
from src.persistence.repositories.base import Repository


class DecisionRepository(Repository[Decision]):
    model = Decision

    def list_by_subject(self, subject_type: str, subject_id: int) -> list[Decision]:
        return list(
            self.session.scalars(
                select(Decision).where(
                    Decision.subject_type == subject_type,
                    Decision.subject_id == subject_id,
                )
            )
        )
