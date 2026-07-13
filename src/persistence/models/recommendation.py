"""Recommendation — a costed, owned action attached to an Alert (Fase 5)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.base import Base
from src.persistence.enums import RecommendationStatus


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), index=True)
    action_label: Mapped[str] = mapped_column(String(200))
    # A range, never a false-precision single euro figure (ui-evolution-v2-spec
    # §8 "Budget recommendation": "never false precision to the euro").
    cost_eur_low: Mapped[float | None] = mapped_column(Float, default=None)
    cost_eur_high: Mapped[float | None] = mapped_column(Float, default=None)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)  # DCS
    owner: Mapped[str | None] = mapped_column(String(200), default=None)
    deadline: Mapped[date | None] = mapped_column(default=None)
    status: Mapped[RecommendationStatus] = mapped_column(
        default=RecommendationStatus.PENDING
    )

    alert: Mapped["Alert"] = relationship()  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"Recommendation(id={self.id!r}, alert_id={self.alert_id!r})"
