"""UserRepository — CRUD + email lookup for User (v3.0, ADR-005)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.user import User
from src.persistence.repositories.base import Repository


class UserRepository(Repository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalars(
            select(User).where(User.email == email)
        ).first()

    def list_by_org(self, org_id: int) -> list[User]:
        return list(
            self.session.scalars(select(User).where(User.org_id == org_id))
        )
