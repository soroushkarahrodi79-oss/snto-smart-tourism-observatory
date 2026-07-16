"""TerritoryRepository — CRUD + slug lookup for Territory (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.territory import Territory
from src.persistence.repositories.base import Repository


class TerritoryRepository(Repository[Territory]):
    model = Territory

    def get_by_slug(self, slug: str) -> Territory | None:
        return self.session.scalars(
            select(Territory).where(Territory.slug == slug)
        ).first()
