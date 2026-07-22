"""OrganizationRepository — CRUD + slug lookup for Organization (v3.0)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.organization import Organization
from src.persistence.repositories.base import Repository


class OrganizationRepository(Repository[Organization]):
    model = Organization

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.session.scalars(
            select(Organization).where(Organization.slug == slug)
        ).first()
