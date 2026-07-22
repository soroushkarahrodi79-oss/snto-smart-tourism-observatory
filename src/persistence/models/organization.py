"""Organization — the tenant that owns territories and users (v3.0, ADR-002/005).

The multi-tenancy anchor. Fase 5 shipped ``Territory`` as the top-level scope but
with no owner; v3.0 introduces the ``Organization`` above it so access can be
scoped per tenant. Adoption is *additive*: a ``Territory.org_id`` is nullable, so
existing single-park data (the ``pnsg`` default) keeps working with no tenant
attached until an organization claims it — preserving the byte-identical-``pnsg``
invariant.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.persistence.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"Organization(id={self.id!r}, slug={self.slug!r})"
