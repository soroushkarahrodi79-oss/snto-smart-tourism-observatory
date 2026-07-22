"""Territory/organization administration service (v3.0, ADR-002/005).

The Gobernar-layer "Configuración territorial" module (Fase 6.7f) has always
shown a curated, code-reviewed registry of OAPN parks and their scientific
validation state (`src.platform.territory_registry`) — that dataset is
deliberately **not** user-editable; it describes readiness, not tenancy.

This module is the *separate*, additive layer v3.0 adds on top: real,
persisted `Organization` / `User` / `Territory` rows (the tenancy foundation
from `src.persistence.services.tenancy`), surfaced so an authorized user can
actually register organizations, add users, and register or claim territories
from the app — not just read a static list.

Honesty note: there is no login/session system yet (SSO/Entra ID is a
deferred, additive swap of `require_write_auth`, ADR-005). So every write here
takes an explicit **acting user id** chosen from the registered users, rather
than pretending a real authenticated session exists — the authz policy
(`can_administer_org` / `can_manage`) is still enforced against whichever user
is selected, so the UI exercises the real policy honestly.

Pure data access + typed results, no Streamlit — testable against an
in-memory session and reusable by any surface.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.persistence.enums import UserRole
from src.persistence.repositories import (
    OrganizationRepository,
    TerritoryRepository,
    UserRepository,
)
from src.persistence.services import tenancy
from src.persistence.session import session_scope


@contextmanager
def _open_session() -> Iterator[Session]:
    """Session seam — real ``session_scope`` in the app, patched in tests."""
    with session_scope() as session:
        yield session


class AdminStatus(str, Enum):
    OK = "ok"
    DUPLICATE = "duplicate"
    NOT_AUTHORIZED = "not_authorized"
    NOT_FOUND = "not_found"
    ALREADY_OWNED = "already_owned"
    NO_BACKEND = "no_backend"


@dataclass(frozen=True)
class AdminResult:
    status: AdminStatus
    message: str


@dataclass(frozen=True)
class OrgRow:
    id: int
    slug: str
    name: str
    n_users: int
    n_territories: int


@dataclass(frozen=True)
class UserRow:
    id: int
    email: str
    display_name: str
    role: str
    org_name: str


@dataclass(frozen=True)
class TerritoryRow:
    id: int
    slug: str
    name: str
    owner_org: str | None  # None = unowned (the pre-tenancy default, e.g. pnsg)


@dataclass(frozen=True)
class RegistryState:
    backend_available: bool
    organizations: list[OrgRow]
    users: list[UserRow]
    territories: list[TerritoryRow]


def load_registry_state(*, session: Session | None = None) -> RegistryState:
    """Read the persisted tenancy registry; degrades honestly if unreachable."""
    if session is not None:
        return _load(session)
    try:
        with _open_session() as own:
            return _load(own)
    except SQLAlchemyError:
        return RegistryState(False, [], [], [])


def _load(session: Session) -> RegistryState:
    orgs = OrganizationRepository(session).list()
    users = UserRepository(session).list()
    territories = TerritoryRepository(session).list()
    org_name_by_id = {o.id: o.name for o in orgs}
    n_users_by_org: dict[int, int] = {}
    n_terr_by_org: dict[int, int] = {}
    for u in users:
        n_users_by_org[u.org_id] = n_users_by_org.get(u.org_id, 0) + 1
    for t in territories:
        if t.org_id is not None:
            n_terr_by_org[t.org_id] = n_terr_by_org.get(t.org_id, 0) + 1
    return RegistryState(
        backend_available=True,
        organizations=[
            OrgRow(
                id=o.id, slug=o.slug, name=o.name,
                n_users=n_users_by_org.get(o.id, 0),
                n_territories=n_terr_by_org.get(o.id, 0),
            )
            for o in orgs
        ],
        users=[
            UserRow(
                id=u.id, email=u.email, display_name=u.display_name,
                role=u.role.value if isinstance(u.role, UserRole) else str(u.role),
                org_name=org_name_by_id.get(u.org_id, "?"),
            )
            for u in users
        ],
        territories=[
            TerritoryRow(
                id=t.id, slug=t.slug, name=t.name,
                owner_org=org_name_by_id.get(t.org_id) if t.org_id else None,
            )
            for t in territories
        ],
    )


def _wrap(fn, *args, **kwargs) -> AdminResult:
    try:
        fn(*args, **kwargs)
    except tenancy.NotAuthorizedError as exc:
        return AdminResult(AdminStatus.NOT_AUTHORIZED, str(exc))
    except tenancy.TerritoryAlreadyOwnedError as exc:
        return AdminResult(AdminStatus.ALREADY_OWNED, str(exc))
    except (tenancy.DuplicateSlugError, tenancy.DuplicateEmailError) as exc:
        return AdminResult(AdminStatus.DUPLICATE, str(exc))
    except tenancy.TenancyError as exc:
        return AdminResult(AdminStatus.NOT_FOUND, str(exc))
    return AdminResult(AdminStatus.OK, "hecho")


def create_organization(
    slug: str, name: str, *, session: Session | None = None, actor: str = "ui",
) -> AdminResult:
    def _do(s: Session) -> None:
        tenancy.create_organization(s, slug=slug, name=name, actor=actor)

    return _run(_do, session=session)


def add_user(
    org_id: int, email: str, display_name: str, role: UserRole,
    *, acting_user_id: int | None, session: Session | None = None,
    actor: str = "ui",
) -> AdminResult:
    def _do(s: Session) -> None:
        by = UserRepository(s).get(acting_user_id) if acting_user_id else None
        tenancy.add_user(
            s, org_id=org_id, email=email, display_name=display_name,
            role=role, by=by, actor=actor,
        )

    return _run(_do, session=session)


def register_territory(
    slug: str, name: str, budget_eur: float, org_id: int,
    *, acting_user_id: int | None, session: Session | None = None,
    actor: str = "ui",
) -> AdminResult:
    def _do(s: Session) -> None:
        by = UserRepository(s).get(acting_user_id) if acting_user_id else None
        tenancy.register_territory(
            s, slug=slug, name=name, budget_eur=budget_eur, org_id=org_id,
            by=by, actor=actor,
        )

    return _run(_do, session=session)


def claim_territory(
    territory_id: int, org_id: int,
    *, acting_user_id: int | None, session: Session | None = None,
    actor: str = "ui",
) -> AdminResult:
    def _do(s: Session) -> None:
        by = UserRepository(s).get(acting_user_id) if acting_user_id else None
        tenancy.claim_territory(
            s, territory_id=territory_id, org_id=org_id, by=by, actor=actor,
        )

    return _run(_do, session=session)


def _run(do, *, session: Session | None) -> AdminResult:
    if session is not None:
        return _wrap(do, session)
    try:
        with _open_session() as own:
            return _wrap(do, own)
    except SQLAlchemyError:
        return AdminResult(
            AdminStatus.NO_BACKEND, "Backend de persistencia no disponible."
        )
