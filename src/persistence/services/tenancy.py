"""Tenancy provisioning service (v3.0, ADR-002/005).

Makes the identity tables from the foundation PR *usable*: create an
``Organization``, add ``User``s to it, and register/claim ``Territory`` rows
under it — every write audited through the single choke-point.

Authorization is **opt-in and additive**, matching the persistence layer's
permissive default: a call may pass ``by=<User>`` to enforce the policy
(``authz.can_administer_org`` / ``can_manage``), or omit it for a system/bootstrap
path (creating the very first org and its first admin has no prior admin to
check). When ``by`` is given, an unauthorized principal raises
``NotAuthorizedError`` and nothing is written.

Nothing here authenticates a principal — that is the ``require_write_auth`` seam
(SSO/Entra ID, a later swap). This only decides *what* an already-identified
principal may provision.
"""
from __future__ import annotations

from src.persistence.enums import UserRole
from src.persistence.models import Organization, Territory, User
from src.persistence.repositories import (
    OrganizationRepository,
    TerritoryRepository,
    UserRepository,
)
from src.persistence.services import audit
from src.persistence.services.authz import can_administer_org, can_manage


class TenancyError(ValueError):
    """Base for provisioning errors."""


class DuplicateSlugError(TenancyError):
    """An organization slug is already taken."""


class DuplicateEmailError(TenancyError):
    """A user email is already registered."""


class NotAuthorizedError(TenancyError):
    """The acting principal lacks the required capability."""


class TerritoryAlreadyOwnedError(TenancyError):
    """A territory is already owned by a different organization."""


def create_organization(
    session,
    *,
    slug: str,
    name: str,
    actor: str = audit.ACTOR_SYSTEM,
) -> Organization:
    """Create a tenant. Bootstrap/platform action — no per-org admin exists yet."""
    repo = OrganizationRepository(session)
    if repo.get_by_slug(slug) is not None:
        raise DuplicateSlugError(slug)
    org = repo.add(Organization(slug=slug, name=name))
    audit.record(
        session, actor=actor, action=audit.ORGANIZATION_CREATED,
        subject_type="organization", subject_id=org.id, payload={"slug": slug},
    )
    return org


def add_user(
    session,
    *,
    org_id: int,
    email: str,
    display_name: str,
    role: UserRole = UserRole.VIEWER,
    by: User | None = None,
    actor: str = audit.ACTOR_SYSTEM,
) -> User:
    """Add a user to an org. Enforces org-admin when ``by`` is supplied."""
    if by is not None and not can_administer_org(by, org_id):
        raise NotAuthorizedError(
            f"principal {getattr(by, 'email', by)!r} cannot administer org {org_id}"
        )
    repo = UserRepository(session)
    if repo.get_by_email(email) is not None:
        raise DuplicateEmailError(email)
    user = repo.add(
        User(org_id=org_id, email=email, display_name=display_name, role=role)
    )
    audit.record(
        session, actor=actor, action=audit.USER_ADDED,
        subject_type="user", subject_id=user.id,
        payload={"org_id": org_id, "role": role.value},
    )
    return user


def register_territory(
    session,
    *,
    slug: str,
    name: str,
    budget_eur: float,
    org_id: int,
    by: User | None = None,
    actor: str = audit.ACTOR_SYSTEM,
) -> Territory:
    """Create a new territory owned by ``org_id``. Enforces org-admin when ``by``."""
    if by is not None and not can_administer_org(by, org_id):
        raise NotAuthorizedError(
            f"principal cannot register a territory for org {org_id}"
        )
    repo = TerritoryRepository(session)
    if repo.get_by_slug(slug) is not None:
        raise DuplicateSlugError(slug)
    territory = repo.add(
        Territory(slug=slug, name=name, budget_eur=budget_eur, org_id=org_id)
    )
    audit.record(
        session, actor=actor, action=audit.TERRITORY_REGISTERED,
        subject_type="territory", subject_id=territory.id,
        payload={"slug": slug, "org_id": org_id},
    )
    return territory


def claim_territory(
    session,
    *,
    territory_id: int,
    org_id: int,
    by: User | None = None,
    actor: str = audit.ACTOR_SYSTEM,
) -> Territory:
    """Assign an **unowned** territory (the pnsg default) to an organization.

    Enforces (when ``by`` is supplied) that the principal can manage the target
    territory and administer the claiming org. A territory already owned by a
    *different* org raises rather than being reassigned.
    """
    territory = TerritoryRepository(session).get(territory_id)
    if territory is None:
        raise TenancyError(f"territory {territory_id} not found")
    if territory.org_id is not None and territory.org_id != org_id:
        raise TerritoryAlreadyOwnedError(
            f"territory {territory_id} is owned by org {territory.org_id}"
        )
    if by is not None and not (
        can_manage(by, territory) and can_administer_org(by, org_id)
    ):
        raise NotAuthorizedError(
            f"principal cannot claim territory {territory_id} for org {org_id}"
        )
    territory.org_id = org_id
    session.flush()
    audit.record(
        session, actor=actor, action=audit.TERRITORY_CLAIMED,
        subject_type="territory", subject_id=territory.id,
        payload={"org_id": org_id},
    )
    return territory
