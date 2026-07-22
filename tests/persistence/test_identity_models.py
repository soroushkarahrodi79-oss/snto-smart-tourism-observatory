"""Round-trip + tenancy-scoping tests for the v3.0 identity models.

Verifies the ORM wiring (Organization/User, Territory.org_id) and that the
authorization policy composes with real persisted rows — a user only sees
their org's territory plus the unowned default.
"""
from __future__ import annotations

from src.persistence.enums import UserRole
from src.persistence.models import Organization, Territory, User
from src.persistence.repositories import (
    OrganizationRepository,
    TerritoryRepository,
    UserRepository,
)
from src.persistence.services.authz import can_read, can_write


def test_organization_and_user_round_trip(db_session) -> None:
    org = OrganizationRepository(db_session).add(
        Organization(slug="oapn", name="Organismo Autónomo Parques Nacionales")
    )
    user = UserRepository(db_session).add(
        User(
            org_id=org.id, email="tecnico@oapn.es",
            display_name="Técnico OAPN", role=UserRole.EDITOR,
        )
    )
    assert user.id is not None
    assert UserRepository(db_session).get_by_email("tecnico@oapn.es").id == user.id
    assert OrganizationRepository(db_session).get_by_slug("oapn").id == org.id
    assert user.is_active is True  # server/default applied


def test_territory_org_id_defaults_to_unowned(db_session) -> None:
    # An existing-style territory created without an org stays unowned (pnsg).
    pnsg = TerritoryRepository(db_session).add(
        Territory(slug="pnsg", name="PNSG", budget_eur=150000.0)
    )
    assert pnsg.org_id is None


def test_policy_composes_with_persisted_rows(db_session) -> None:
    org_a = OrganizationRepository(db_session).add(
        Organization(slug="org-a", name="A")
    )
    org_b = OrganizationRepository(db_session).add(
        Organization(slug="org-b", name="B")
    )
    terr_a = TerritoryRepository(db_session).add(
        Territory(slug="ta", name="T-A", budget_eur=1.0, org_id=org_a.id)
    )
    terr_b = TerritoryRepository(db_session).add(
        Territory(slug="tb", name="T-B", budget_eur=1.0, org_id=org_b.id)
    )
    pnsg = TerritoryRepository(db_session).add(
        Territory(slug="pnsg", name="PNSG", budget_eur=1.0)
    )
    editor_a = UserRepository(db_session).add(
        User(org_id=org_a.id, email="a@a.es", display_name="A",
             role=UserRole.EDITOR)
    )
    # own territory: read+write; other org: nothing; unowned default: yes
    assert can_write(editor_a, terr_a)
    assert not can_read(editor_a, terr_b)
    assert can_read(editor_a, pnsg)
