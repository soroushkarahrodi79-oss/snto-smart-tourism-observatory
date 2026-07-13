"""FieldVerification — a manual ground-truth check for a ManagedAsset (Fase 5)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.base import Base


class FieldVerification(Base):
    __tablename__ = "field_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("managed_assets.id"), index=True)
    verified_at: Mapped[datetime]
    method: Mapped[str] = mapped_column(String(64))
    verifier: Mapped[str] = mapped_column(String(200))
    result: Mapped[str] = mapped_column(Text)
    photo_ref: Mapped[str | None] = mapped_column(String(500), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    asset: Mapped["ManagedAsset"] = relationship()  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return (
            f"FieldVerification(id={self.id!r}, asset_id={self.asset_id!r}, "
            f"verified_at={self.verified_at!r})"
        )
