"""User — an authenticated principal within an organization (v3.0, ADR-005).

Fase 5's auth was a single shared API key with a free-text ``actor`` string.
v3.0 gives that actor an identity: a ``User`` belongs to exactly one
``Organization`` and carries a ``UserRole`` that the authorization policy
(``src.persistence.services.authz``) turns into read/write/manage capabilities.

Deliberately minimal: no password/credential columns here — authentication
(SSO / Entra ID) is delegated upstream and swapped in at the ``require_write_auth``
seam; this table only models *who* a principal is and *what* they may do, not
*how* they prove it.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.persistence.base import Base
from src.persistence.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(String(16), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    organization: Mapped["Organization"] = relationship()  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f"User(id={self.id!r}, email={self.email!r}, role={self.role!r})"
