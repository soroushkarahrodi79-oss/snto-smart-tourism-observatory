"""Contracts for the v3.0 authorization policy (tenancy scope × role).

Pins the two non-negotiables of the multi-tenant layer:
- a user of org A can never read or write org B's territory;
- the pre-tenancy default (unowned territory) stays reachable, so the pnsg
  pilot keeps working; and write/manage require the right role.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.persistence.enums import UserRole
from src.persistence.services.authz import (
    can_manage,
    can_read,
    can_write,
    in_scope,
)


@dataclass
class _User:
    org_id: int
    role: UserRole
    is_active: bool = True


@dataclass
class _Territory:
    org_id: int | None


def test_unowned_territory_is_readable_and_writable_by_any_active_user() -> None:
    # The pnsg default (org_id None) must keep working for an active editor.
    editor = _User(org_id=1, role=UserRole.EDITOR)
    pnsg = _Territory(org_id=None)
    assert in_scope(editor, pnsg)
    assert can_read(editor, pnsg)
    assert can_write(editor, pnsg)


def test_cross_org_access_is_denied() -> None:
    user_a = _User(org_id=1, role=UserRole.ADMIN)
    territory_b = _Territory(org_id=2)
    assert not in_scope(user_a, territory_b)
    assert not can_read(user_a, territory_b)
    assert not can_write(user_a, territory_b)
    assert not can_manage(user_a, territory_b)


def test_same_org_access_is_allowed() -> None:
    user = _User(org_id=7, role=UserRole.VIEWER)
    territory = _Territory(org_id=7)
    assert can_read(user, territory)
    assert not can_write(user, territory)  # viewer cannot write


def test_role_capabilities_ladder() -> None:
    t = _Territory(org_id=1)
    viewer = _User(org_id=1, role=UserRole.VIEWER)
    editor = _User(org_id=1, role=UserRole.EDITOR)
    admin = _User(org_id=1, role=UserRole.ADMIN)
    # read: everyone in scope
    assert can_read(viewer, t) and can_read(editor, t) and can_read(admin, t)
    # write: editor and above
    assert not can_write(viewer, t)
    assert can_write(editor, t) and can_write(admin, t)
    # manage: admin and above
    assert not can_manage(viewer, t) and not can_manage(editor, t)
    assert can_manage(admin, t)


def test_inactive_user_is_denied_everything() -> None:
    ghost = _User(org_id=1, role=UserRole.OWNER, is_active=False)
    assert not can_read(ghost, _Territory(org_id=1))
    assert not can_write(ghost, _Territory(org_id=None))
    assert not can_manage(ghost, _Territory(org_id=1))


def test_role_accepts_raw_string_value() -> None:
    # A row may hydrate role as the stored str; the policy coerces it.
    editor = _User(org_id=1, role="editor")  # type: ignore[arg-type]
    assert can_write(editor, _Territory(org_id=1))
