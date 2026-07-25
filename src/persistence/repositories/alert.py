"""AlertRepository — CRUD + open-alert / per-asset lookups (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.enums import AlertStatus
from src.persistence.models.alert import Alert
from src.persistence.models.managed_asset import ManagedAsset
from src.persistence.repositories.base import Repository


class AlertRepository(Repository[Alert]):
    model = Alert

    def list_by_asset(self, asset_id: int) -> list[Alert]:
        return list(
            self.session.scalars(select(Alert).where(Alert.asset_id == asset_id))
        )

    def list_by_territory(
        self, territory_id: int, *, status: AlertStatus | None = None
    ) -> list[Alert]:
        """Every alert across a territory's assets (join through ManagedAsset).

        Powers the flat ``GET /api/v2/alerts/`` listing (mobile Fase 2, ADR-014
        addendum) — the per-asset lookup above does not scale to "every alert a
        territory has" without one call per asset.
        """
        stmt = (
            select(Alert)
            .join(ManagedAsset, Alert.asset_id == ManagedAsset.id)
            .where(ManagedAsset.territory_id == territory_id)
        )
        if status is not None:
            stmt = stmt.where(Alert.status == status)
        return list(self.session.scalars(stmt))

    def list_open(self) -> list[Alert]:
        return list(
            self.session.scalars(
                select(Alert).where(Alert.status == AlertStatus.OPEN)
            )
        )

    def list_by_status(self, status: AlertStatus) -> list[Alert]:
        return list(
            self.session.scalars(select(Alert).where(Alert.status == status))
        )
