"""ObservationRepository — CRUD + per-asset time series lookup (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.observation import Observation
from src.persistence.repositories.base import Repository


class ObservationRepository(Repository[Observation]):
    model = Observation

    def list_by_asset(self, asset_id: int) -> list[Observation]:
        return list(
            self.session.scalars(
                select(Observation)
                .where(Observation.asset_id == asset_id)
                .order_by(Observation.observed_at)
            )
        )
