"""Contracts for the v3.0 territory/organization admin service (UI layer).

Pins: reads reflect real persisted rows (unowned territories show owner_org
None); writes go through the real authz-enforced tenancy service and report a
typed AdminStatus rather than raising into the UI.
"""
from __future__ import annotations

from src.persistence.enums import UserRole
from src.persistence.models import Territory
from src.persistence.repositories import TerritoryRepository
from src.persistence.services import tenancy
from src.ui.services.territory_admin import (
    AdminStatus,
    add_user,
    claim_territory,
    create_organization,
    load_registry_state,
    register_territory,
)


def test_empty_registry_reads_honestly(db_session) -> None:
    state = load_registry_state(session=db_session)
    assert state.backend_available is True
    assert state.organizations == []
    assert state.territories == []


def test_create_organization_then_visible_in_state(db_session) -> None:
    result = create_organization("oapn", "OAPN", session=db_session)
    assert result.status is AdminStatus.OK
    state = load_registry_state(session=db_session)
    assert len(state.organizations) == 1
    assert state.organizations[0].slug == "oapn"


def test_duplicate_organization_reports_duplicate(db_session) -> None:
    create_organization("oapn", "OAPN", session=db_session)
    result = create_organization("oapn", "dup", session=db_session)
    assert result.status is AdminStatus.DUPLICATE


def test_unowned_territory_shows_no_owner(db_session) -> None:
    TerritoryRepository(db_session).add(
        Territory(slug="pnsg", name="PNSG", budget_eur=150000.0)
    )
    state = load_registry_state(session=db_session)
    assert len(state.territories) == 1
    assert state.territories[0].owner_org is None


def test_add_user_without_acting_user_is_bootstrap(db_session) -> None:
    create_organization("oapn", "OAPN", session=db_session)
    org_id = load_registry_state(session=db_session).organizations[0].id
    result = add_user(
        org_id, "admin@oapn.es", "Admin", UserRole.ADMIN,
        acting_user_id=None, session=db_session,
    )
    assert result.status is AdminStatus.OK


def test_add_user_denied_when_acting_user_is_not_admin(db_session) -> None:
    create_organization("oapn", "OAPN", session=db_session)
    org_id = load_registry_state(session=db_session).organizations[0].id
    add_user(
        org_id, "viewer@oapn.es", "Viewer", UserRole.VIEWER,
        acting_user_id=None, session=db_session,
    )
    viewer_id = load_registry_state(session=db_session).users[0].id
    result = add_user(
        org_id, "new@oapn.es", "New", UserRole.EDITOR,
        acting_user_id=viewer_id, session=db_session,
    )
    assert result.status is AdminStatus.NOT_AUTHORIZED


def test_register_and_claim_flow_via_service(db_session) -> None:
    create_organization("oapn", "OAPN", session=db_session)
    org_id = load_registry_state(session=db_session).organizations[0].id
    add_user(
        org_id, "admin@oapn.es", "Admin", UserRole.ADMIN,
        acting_user_id=None, session=db_session,
    )
    admin_id = load_registry_state(session=db_session).users[0].id

    reg = register_territory(
        "new-park", "New Park", 1000.0, org_id,
        acting_user_id=admin_id, session=db_session,
    )
    assert reg.status is AdminStatus.OK

    # a pre-tenancy unowned territory can be claimed by the same admin
    pnsg = TerritoryRepository(db_session).add(
        Territory(slug="pnsg", name="PNSG", budget_eur=150000.0)
    )
    claim = claim_territory(
        pnsg.id, org_id, acting_user_id=admin_id, session=db_session,
    )
    assert claim.status is AdminStatus.OK
    state = load_registry_state(session=db_session)
    pnsg_row = next(t for t in state.territories if t.slug == "pnsg")
    assert pnsg_row.owner_org == "OAPN"


def test_claim_already_owned_territory_reports_already_owned(db_session) -> None:
    create_organization("a", "A", session=db_session)
    create_organization("b", "B", session=db_session)
    orgs = {o.slug: o.id for o in load_registry_state(session=db_session).organizations}
    terr = tenancy.register_territory(
        db_session, slug="park-b", name="Park B", budget_eur=1.0, org_id=orgs["b"],
    )
    result = claim_territory(
        terr.id, orgs["a"], acting_user_id=None, session=db_session,
    )
    assert result.status is AdminStatus.ALREADY_OWNED
