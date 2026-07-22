"""Authorization policy for the multi-tenant layer (v3.0, ADR-002/005).

Pure decision logic — no session, no Streamlit — so it is exhaustively
unit-testable and reusable by both the ``/api/v2`` write gate (a later,
clearly-scoped swap of ``require_write_auth``) and any in-app write surface.

Two orthogonal checks combine:

1. **Tenancy scope** — a user may touch a territory iff the territory is
   *unowned* (``org_id is None`` — the pre-tenancy / shared default, e.g. the
   ``pnsg`` pilot) **or** it belongs to the user's own organization. A user of
   org A can never read or write org B's territory.
2. **Role capability** — ``VIEWER`` reads; ``EDITOR`` also writes; ``ADMIN``
   also manages (territories/users) within the org; ``OWNER`` is the strongest.

Inactive users are denied everything. The functions accept the model instances
(or anything exposing the same attributes), never a session, so a caller must
have already loaded the principal.
"""
from __future__ import annotations

from src.persistence.enums import UserRole

# Capability rank — higher grants everything the lower ones do.
_RANK: dict[UserRole, int] = {
    UserRole.VIEWER: 0,
    UserRole.EDITOR: 1,
    UserRole.ADMIN: 2,
    UserRole.OWNER: 3,
}


def _role_of(user) -> UserRole:
    """Coerce a user's stored role (enum or raw str) to ``UserRole``."""
    role = user.role
    return role if isinstance(role, UserRole) else UserRole(role)


def _rank(user) -> int:
    return _RANK[_role_of(user)]


def in_scope(user, territory) -> bool:
    """True if the territory is unowned or belongs to the user's organization."""
    if not getattr(user, "is_active", False):
        return False
    org_id = getattr(territory, "org_id", None)
    return org_id is None or org_id == user.org_id


def can_read(user, territory) -> bool:
    """Any active, in-scope user may read (VIEWER and above)."""
    return in_scope(user, territory)


def can_write(user, territory) -> bool:
    """Write (triage, field capture, interventions) needs EDITOR+ in scope."""
    return in_scope(user, territory) and _rank(user) >= _RANK[UserRole.EDITOR]


def can_manage(user, territory) -> bool:
    """Managing a territory/users (register, edit thresholds) needs ADMIN+."""
    return in_scope(user, territory) and _rank(user) >= _RANK[UserRole.ADMIN]
