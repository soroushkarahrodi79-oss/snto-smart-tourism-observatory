"""Alert — a persisted, triageable warning for a ManagedAsset (Fase 5)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.base import Base
from src.persistence.enums import AlertStatus


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("managed_assets.id"), index=True)
    level: Mapped[str] = mapped_column(String(32))  # src.alerts.engine.AlertLevel.value
    risk_score: Mapped[float] = mapped_column(Float)
    triggered_rules: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[AlertStatus] = mapped_column(default=AlertStatus.OPEN)
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    asset: Mapped["ManagedAsset"] = relationship()  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"Alert(id={self.id!r}, asset_id={self.asset_id!r}, "
            f"level={self.level!r})"
        )
