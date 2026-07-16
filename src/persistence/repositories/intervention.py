"""InterventionRepository — CRUD + per-asset lookup (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.intervention import Intervention
from src.persistence.repositories.base import Repository


class InterventionRepository(Repository[Intervention]):
    model = Intervention

    def list_by_asset(self, asset_id: int) -> list[Intervention]:
        return list(
            self.session.scalars(
                select(Intervention).where(Intervention.asset_id == asset_id)
            )
        )
