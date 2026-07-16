"""RecommendationRepository — CRUD + per-alert lookup (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.recommendation import Recommendation
from src.persistence.repositories.base import Repository


class RecommendationRepository(Repository[Recommendation]):
    model = Recommendation

    def list_by_alert(self, alert_id: int) -> list[Recommendation]:
        return list(
            self.session.scalars(
                select(Recommendation).where(Recommendation.alert_id == alert_id)
            )
        )
