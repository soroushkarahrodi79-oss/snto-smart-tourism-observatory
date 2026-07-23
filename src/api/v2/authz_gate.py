"""Territory-scoped write authorization for /api/v2 (v3.0, ADR-005).

Additive over the Fase-5 minimal API-key gate (``require_write_auth``): it
enforces the tenancy × role policy (:mod:`src.persistence.services.authz`)
**only once identity is adopted**. It is dormant by design — if no ``User``
rows exist, writes stay exactly as open as before, so the Fase-5 auth
behaviour and its tests are unchanged. Once an organization provisions users,
the actor (an email carried in ``X-Actor``) must map to an **active** user who
``can_write`` the **target territory**, otherwise ``403``.

Authentication stays upstream (``require_write_auth`` today, an SSO/Entra ID
swap later); this only decides *what* an already-identified actor may write.
Endpoints resolve the target territory from the resource they already load and
call :func:`authorize_territory_write` after their own existence (404) check,
so a missing resource still 404s rather than leaking a 403.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.persistence.models.user import User
from src.persistence.repositories import TerritoryRepository, UserRepository
from src.persistence.services.authz import can_write


def _identity_adopted(db: Session) -> bool:
    """True once at least one user exists — the switch that arms enforcement."""
    return db.scalars(select(User).limit(1)).first() is not None


def authorize_territory_write(
    db: Session, actor: str, territory_id: int | None
) -> None:
    """Enforce the write policy for ``actor`` on ``territory_id``; raise 403 if denied.

    No-op (backward compatible) while no users exist. Once identity is adopted,
    an unknown/inactive actor or an actor lacking ``can_write`` on the territory
    is rejected with ``403``.
    """
    if not _identity_adopted(db):
        return
    user = UserRepository(db).get_by_email(actor)
    if user is None or not user.is_active:
        raise HTTPException(status_code=403, detail="Unknown or inactive principal")
    territory = (
        TerritoryRepository(db).get(territory_id) if territory_id is not None else None
    )
    if territory is None or not can_write(user, territory):
        raise HTTPException(
            status_code=403, detail="Not authorized to write this territory"
        )
