"""AlertRepository — CRUD + open-alert / per-asset lookups (Fase 5, 5.2)."""
from __future__ import annotations

from sqlalchemy import select

from src.persistence.enums import AlertStatus
from src.persistence.models.alert import Alert
from src.persistence.repositories.base import Repository


class AlertRepository(Repository[Alert]):
    model = Alert

    def list_by_asset(self, asset_id: int) -> list[Alert]:
        return list(
            self.session.scalars(select(Alert).where(Alert.asset_id == asset_id))
        )

    def list_open(self) -> list[Alert]:
        return list(
            self.session.scalars(
                select(Alert).where(Alert.status == AlertStatus.OPEN)
            )
        )
