"""FieldVerificationRepository — CRUD + per-asset lookup (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.models.field_verification import FieldVerification
from src.persistence.repositories.base import Repository


class FieldVerificationRepository(Repository[FieldVerification]):
    model = FieldVerification

    def list_by_asset(self, asset_id: int) -> list[FieldVerification]:
        return list(
            self.session.scalars(
                select(FieldVerification).where(
                    FieldVerification.asset_id == asset_id
                )
            )
        )
