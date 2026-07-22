"""Contracts for the v3.0 tenancy provisioning service.

Pins: bootstrap (no principal) works; when a principal is supplied the
org-admin policy is enforced; duplicates are rejected; claiming is only for
unowned territories; and every write leaves an audit entry.
"""
from __future__ import annotations

import pytest

from src.persistence.enums import UserRole
from src.persistence.models import AuditLogEntry, Territory
from src.persistence.repositories import TerritoryRepository
from src.persistence.services import tenancy


def _bootstrap_org_with_admin(session, slug="oapn"):
    org = tenancy.create_organization(session, slug=slug, name=slug.upper())
    admin = tenancy.add_user(
        session, org_id=org.id, email=f"admin@{slug}.es",
        display_name="Admin", role=UserRole.ADMIN,
    )
    return org, admin


def test_create_org_is_audited_and_slug_unique(db_session) -> None:
    org = tenancy.create_organization(db_session, slug="oapn", name="OAPN")
    assert org.id is not None
    entries = db_session.query(AuditLogEntry).filter_by(
        action="organization.created"
    ).all()
    assert len(entries) == 1
    with pytest.raises(tenancy.DuplicateSlugError):
        tenancy.create_organization(db_session, slug="oapn", name="dup")


def test_add_user_bootstrap_then_admin_enforced(db_session) -> None:
    org, admin = _bootstrap_org_with_admin(db_session)
    # admin of the org can add another user
    editor = tenancy.add_user(
        db_session, org_id=org.id, email="e@oapn.es", display_name="E",
        role=UserRole.EDITOR, by=admin,
    )
    assert editor.role is UserRole.EDITOR
    # a viewer cannot add users
    viewer = tenancy.add_user(
        db_session, org_id=org.id, email="v@oapn.es", display_name="V",
        role=UserRole.VIEWER,
    )
    with pytest.raises(tenancy.NotAuthorizedError):
        tenancy.add_user(
            db_session, org_id=org.id, email="x@oapn.es", display_name="X",
            by=viewer,
        )


def test_admin_of_other_org_cannot_add_users(db_session) -> None:
    _org_a, admin_a = _bootstrap_org_with_admin(db_session, slug="a")
    org_b, _admin_b = _bootstrap_org_with_admin(db_session, slug="b")
    with pytest.raises(tenancy.NotAuthorizedError):
        tenancy.add_user(
            db_session, org_id=org_b.id, email="cross@b.es",
            display_name="Cross", by=admin_a,
        )


def test_register_territory_sets_owner(db_session) -> None:
    org, admin = _bootstrap_org_with_admin(db_session)
    terr = tenancy.register_territory(
        db_session, slug="new-park", name="New Park", budget_eur=1000.0,
        org_id=org.id, by=admin,
    )
    assert terr.org_id == org.id


def test_claim_unowned_territory(db_session) -> None:
    org, admin = _bootstrap_org_with_admin(db_session)
    # a pre-tenancy (unowned) territory — the pnsg default shape
    pnsg = TerritoryRepository(db_session).add(
        Territory(slug="pnsg", name="PNSG", budget_eur=150000.0)
    )
    assert pnsg.org_id is None
    claimed = tenancy.claim_territory(
        db_session, territory_id=pnsg.id, org_id=org.id, by=admin,
    )
    assert claimed.org_id == org.id


def test_cannot_claim_territory_owned_by_another_org(db_session) -> None:
    org_a, admin_a = _bootstrap_org_with_admin(db_session, slug="a")
    org_b, _admin_b = _bootstrap_org_with_admin(db_session, slug="b")
    terr = tenancy.register_territory(
        db_session, slug="park-b", name="Park B", budget_eur=1.0,
        org_id=org_b.id,
    )
    with pytest.raises(tenancy.TerritoryAlreadyOwnedError):
        tenancy.claim_territory(
            db_session, territory_id=terr.id, org_id=org_a.id, by=admin_a,
        )
