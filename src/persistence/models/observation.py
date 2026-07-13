"""
Observation — one dated measurement/reading for a ManagedAsset (Fase 5).

``source`` stores the same string values as
``src.platform.evidence.EvidenceClass`` (real/calibrated/synthetic/simulated/
missing) — one evidence vocabulary, not a second taxonomy (ADR-004 / #10).
Kept as a plain string column (not a SQLAlchemy Enum bound to the
``src.platform`` import) so this module stays importable without pulling in
``src.platform``'s package-level side effects; callers pass
``EvidenceClass.REAL.value`` etc.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.base import Base


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("managed_assets.id"), index=True)
    observed_at: Mapped[datetime]
    source: Mapped[str] = mapped_column(String(16))  # EvidenceClass.value
    ehs: Mapped[float | None] = mapped_column(Float, default=None)
    ndvi: Mapped[float | None] = mapped_column(Float, default=None)
    ndmi: Mapped[float | None] = mapped_column(Float, default=None)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, default=None)

    asset: Mapped["ManagedAsset"] = relationship()  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"Observation(id={self.id!r}, asset_id={self.asset_id!r}, "
            f"observed_at={self.observed_at!r})"
        )
