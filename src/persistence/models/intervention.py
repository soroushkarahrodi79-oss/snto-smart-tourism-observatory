"""Intervention — the funded, executed action resolving a Recommendation (Fase 5)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.base import Base
from src.persistence.enums import InterventionStatus


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("managed_assets.id"), index=True)
    recommendation_id: Mapped[int | None] = mapped_column(
        ForeignKey("recommendations.id"), default=None
    )
    status: Mapped[InterventionStatus] = mapped_column(
        default=InterventionStatus.PLANNED
    )
    budget_eur: Mapped[float | None] = mapped_column(Float, default=None)
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)

    asset: Mapped["ManagedAsset"] = relationship()  # noqa: F821
    recommendation: Mapped["Recommendation | None"] = relationship()  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"Intervention(id={self.id!r}, asset_id={self.asset_id!r}, "
            f"status={self.status!r})"
        )
