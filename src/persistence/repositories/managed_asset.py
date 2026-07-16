"""ManagedAssetRepository — CRUD + lifecycle/territory lookups (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.enums import ManagedAssetStatus
from src.persistence.models.managed_asset import ManagedAsset
from src.persistence.repositories.base import Repository


class ManagedAssetRepository(Repository[ManagedAsset]):
    model = ManagedAsset

    def get_by_external_id(self, external_asset_id: str) -> ManagedAsset | None:
        return self.session.scalars(
            select(ManagedAsset).where(
                ManagedAsset.external_asset_id == external_asset_id
            )
        ).first()

    def list_by_territory(self, territory_id: int) -> list[ManagedAsset]:
        return list(
            self.session.scalars(
                select(ManagedAsset).where(ManagedAsset.territory_id == territory_id)
            )
        )

    def list_by_status(self, status: ManagedAssetStatus) -> list[ManagedAsset]:
        return list(
            self.session.scalars(
                select(ManagedAsset).where(ManagedAsset.status == status)
            )
        )
