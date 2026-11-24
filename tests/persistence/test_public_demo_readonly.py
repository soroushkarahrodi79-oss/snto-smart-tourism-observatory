"""SNTO_PUBLIC_DEMO: persistence boundary rejects every write, allows reads.

The guard lives in ``src.persistence.session`` (engine ``before_cursor_execute``),
so it covers the UI services, ``/api/v2`` and migrations alike — not just
hidden buttons.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from src.config.settings import settings
from src.persistence import session as session_mod
from src.persistence.models import Base
from src.persistence.models.organization import Organization
from src.persistence.session import PublicDemoReadOnlyError, session_scope


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Fresh file-backed SQLite; engine globals reset around each test."""
    monkeypatch.setattr(settings, "snto_database_url", f"sqlite:///{tmp_path/'t.db'}")

    def reset(demo: bool) -> None:
        monkeypatch.setattr(settings, "snto_public_demo", demo)
        session_mod._engine = None
        session_mod._SessionLocal = None

    yield reset
    session_mod._engine = None
    session_mod._SessionLocal = None


def _seed(reset) -> None:
    reset(False)
    Base.metadata.create_all(session_mod.get_engine())
    with session_scope() as s:
        s.add(Organization(slug="oapn", name="OAPN"))


def test_normal_mode_still_writes(db):
    _seed(db)
    with session_scope() as s:
        assert s.scalar(select(Organization.slug)) == "oapn"


def test_demo_mode_allows_reads(db):
    _seed(db)
    db(True)
    with session_scope() as s:
        assert s.scalar(select(Organization.slug)) == "oapn"
        assert s.execute(text("SELECT 1")).scalar() == 1


def test_demo_mode_rejects_orm_insert(db):
    _seed(db)
    db(True)
    with pytest.raises(PublicDemoReadOnlyError):
        with session_scope() as s:
            s.add(Organization(slug="x", name="X"))
    db(False)
    with session_scope() as s:
        assert list(s.scalars(select(Organization.slug))) == ["oapn"]


@pytest.mark.parametrize(
    "stmt",
    [
        "UPDATE organizations SET name='h'",
        "DELETE FROM organizations",
        "DROP TABLE organizations",
        "CREATE TABLE evil (id integer)",
    ],
)
def test_demo_mode_rejects_raw_writes_and_ddl(db, stmt):
    _seed(db)
    db(True)
    with pytest.raises(PublicDemoReadOnlyError):
        with session_scope() as s:
            s.execute(text(stmt))


def test_demo_mode_blocks_ui_write_services(db):
    """The real UI write path reports a failure result and never persists."""
    from src.ui.services.field_capture import CaptureStatus, capture_field_plot
    from src.validation.field import FieldObservation

    _seed(db)
    db(True)
    obs = FieldObservation(
        plot_id="P1", lat=40.8, lon=-3.9, distance_to_trail_m=1.0,
        is_control=False, asset_id="pnsg-nat-1",
        soil_compaction_mpa=None, veg_cover_pct=None, erosion_class=None,
        observed_at=None,
    )
    result = capture_field_plot(obs, verifier="x", actor="ui")
    assert result.status is not CaptureStatus.PERSISTED
