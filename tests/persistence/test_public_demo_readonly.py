"""SNTO_PUBLIC_DEMO: nothing persistent can be written, reads keep working.

Every test uses a temporary database *with the real schema and seeded rows*, so a
refusal comes from the read-only guard and not from missing tables or records.
Each write path is first run in normal mode (the control: it must succeed) and
then in public-demo mode (it must fail and leave the database untouched).

SQLite file by default; the dedicated test Postgres when
``SNTO_TEST_DATABASE_URL`` is set (CI job ``postgres-integration``).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.config.settings import Settings, is_public_demo, settings
from src.persistence import session as session_mod
from src.persistence.enums import AlertStatus, ManagedAssetStatus, UserRole
from src.persistence.models import Alert, Base, ManagedAsset, Territory
from src.persistence.session import PublicDemoReadOnlyError, session_scope

_ROOT = Path(__file__).resolve().parents[2]


def _reset_engine() -> None:
    if session_mod._engine is not None:
        session_mod._engine.dispose()
    session_mod._engine = None
    session_mod._SessionLocal = None


def _truncate(engine) -> None:
    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.exec_driver_sql(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE")


def _seed(engine) -> dict[str, int]:
    from src.persistence.services import tenancy

    with Session(engine) as s:
        org = tenancy.create_organization(s, slug="oapn", name="OAPN", actor="seed")
        territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
        s.add(territory)
        s.flush()
        asset = ManagedAsset(
            territory_id=territory.id, external_asset_id="pnsg-001",
            name="Sendero", asset_type="trail", geometry_geojson="{}",
            region="Madrid",
        )
        s.add(asset)
        s.flush()
        alert = Alert(
            asset_id=asset.id, level="CRITICAL_INTERVENTION", risk_score=0.9
        )
        s.add(alert)
        s.flush()
        ids = {
            "org": org.id, "territory": territory.id,
            "asset": asset.id, "alert": alert.id,
        }
        s.commit()
    return ids


@pytest.fixture
def db(postgres_engine, tmp_path, monkeypatch):
    """Seeded temporary database; ``db.demo(True)`` switches public mode on."""
    if postgres_engine is not None:
        url = postgres_engine.url.render_as_string(hide_password=False)
        _truncate(postgres_engine)
        setup_engine = postgres_engine
    else:
        url = f"sqlite:///{tmp_path / 't.db'}"
        setup_engine = create_engine(url)
        Base.metadata.create_all(setup_engine)
    monkeypatch.setattr(settings, "snto_database_url", url)

    class Db:
        ids = _seed(setup_engine)

        @staticmethod
        def demo(enabled: bool) -> None:
            monkeypatch.setattr(settings, "snto_public_demo", enabled)
            _reset_engine()

        @staticmethod
        def snapshot() -> dict[str, list]:
            """Every row of every table, read through an independent engine."""
            with setup_engine.connect() as conn:
                return {
                    t.name: sorted(map(repr, conn.execute(t.select()).all()))
                    for t in Base.metadata.sorted_tables
                }

    Db.demo(False)
    yield Db
    _reset_engine()
    if postgres_engine is not None:
        _truncate(postgres_engine)
    else:
        setup_engine.dispose()


# ── Write paths reachable from the application ───────────────────────────────


def _create_org(ids):
    from src.ui.services.territory_admin import create_organization

    return create_organization("nueva", "Nueva")


def _add_user(ids):
    from src.ui.services.territory_admin import add_user

    return add_user(
        ids["org"], "a@example.test", "A", UserRole.ADMIN, acting_user_id=None
    )


def _register_territory(ids):
    from src.ui.services.territory_admin import register_territory

    return register_territory(
        "otro", "Otro", 10.0, ids["org"], acting_user_id=None
    )


def _claim_territory(ids):
    from src.ui.services.territory_admin import claim_territory

    return claim_territory(ids["territory"], ids["org"], acting_user_id=None)


def _capture_plot(ids):
    from src.ui.services.field_capture import capture_field_plot
    from src.validation.field import FieldObservation

    observation = FieldObservation(
        plot_id="P1", lat=40.8, lon=-3.9, distance_to_trail_m=1.0,
        is_control=False, asset_id="pnsg-001", veg_cover_pct=40.0,
        observed_at="2026-06-01",
    )
    return capture_field_plot(observation, verifier="x", actor="ui")


def _triage_alert(ids):
    from src.ui.tabs.tab_urgent_actions import _triage

    _triage(ids["alert"], AlertStatus.ASSIGNED.value)


def _advance_asset(ids):
    from src.ui.tabs.tab_urgent_actions import _advance_asset

    _advance_asset(ids["asset"], ManagedAssetStatus.VERIFIED.value)


def _api_triage(ids):
    from src.api.main import app

    response = TestClient(app).post(
        f"/api/v2/alerts/{ids['alert']}/triage", json={"to_status": "assigned"}
    )
    assert response.status_code == 200, response.text


def _orm_modify_asset(ids):
    with session_scope() as s:
        s.get(ManagedAsset, ids["asset"]).name = "Renombrado"


_WRITE_PATHS = [
    _create_org, _add_user, _register_territory, _claim_territory,
    _capture_plot, _triage_alert, _advance_asset, _api_triage,
    _orm_modify_asset,
]


@pytest.mark.parametrize("write", _WRITE_PATHS)
def test_control_write_path_persists_in_normal_mode(db, write):
    before = db.snapshot()
    write(db.ids)
    assert db.snapshot() != before


@pytest.mark.parametrize("write", _WRITE_PATHS)
def test_public_demo_blocks_write_path(db, write):
    before = db.snapshot()
    db.demo(True)
    try:
        result = write(db.ids)
    except SQLAlchemyError:
        pass  # PublicDemoReadOnlyError, raised straight to the caller
    else:
        # UI services translate the refusal into a typed failure result.
        assert result is not None
        assert result.status.value == "no_backend"
    assert db.snapshot() == before


# ── Bypass attempts ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "stmt",
    [
        "UPDATE organizations SET name='h'",
        "DELETE FROM organizations",
        "DROP TABLE alerts",
        "CREATE TABLE evil (id integer)",
        "WITH x AS (SELECT 1) DELETE FROM alerts",
        "EXPLAIN ANALYZE DELETE FROM alerts",
        "PRAGMA query_only = OFF",
        "SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE",
    ],
)
def test_public_demo_blocks_raw_sql(db, stmt):
    before = db.snapshot()
    db.demo(True)
    try:
        with session_scope() as s:
            s.execute(text(stmt))
    except SQLAlchemyError:
        pass
    # SQLite's EXPLAIN variants may "succeed" without running anything; what
    # matters is that no row or table changed.
    assert db.snapshot() == before


def test_public_demo_database_refuses_writes_behind_sqlalchemy(db):
    """A raw DBAPI cursor skips the statement guard; the connection still refuses."""
    before = db.snapshot()
    db.demo(True)
    raw = session_mod.get_engine().raw_connection()
    try:
        with pytest.raises(Exception, match="(?i)read.?only"):
            cursor = raw.cursor()
            cursor.execute("DELETE FROM alerts")
    finally:
        raw.rollback()
        raw.close()
    assert db.snapshot() == before


def test_public_demo_refuses_migrations(db):
    db.demo(True)
    before = db.snapshot()
    with pytest.raises(PublicDemoReadOnlyError):
        command.upgrade(Config(str(_ROOT / "alembic.ini")), "head")
    assert db.snapshot() == before


# ── Reads keep working ───────────────────────────────────────────────────────


def test_public_demo_allows_reads(db):
    from src.ui.services.territory_admin import load_registry_state

    db.demo(True)
    with session_scope() as s:
        assert s.scalar(select(func.count()).select_from(Alert)) == 1
        assert s.execute(text("SELECT 1")).scalar() == 1
    assert load_registry_state().backend_available


def test_public_demo_raises_typed_error(db):
    db.demo(True)
    with pytest.raises(PublicDemoReadOnlyError):
        _orm_modify_asset(db.ids)


# ── Configuration behaviour ──────────────────────────────────────────────────


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv("SNTO_PUBLIC_DEMO", raising=False)
    return monkeypatch


def test_setting_defaults_to_off(env):
    assert Settings(_env_file=None).snto_public_demo is False


@pytest.mark.parametrize("raw", ["true", "True", "1", "yes", "on"])
def test_setting_truthy_values(env, raw):
    env.setenv("SNTO_PUBLIC_DEMO", raw)
    assert Settings(_env_file=None).snto_public_demo is True


@pytest.mark.parametrize("raw", ["", "ture", "enabled", "2"])
def test_malformed_setting_stops_startup(env, raw):
    env.setenv("SNTO_PUBLIC_DEMO", raw)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


class _FakeSecrets(dict):
    def load_if_toml_exists(self) -> bool:
        return True


@pytest.mark.parametrize(
    ("secret", "expected"),
    [
        (True, True),  # unquoted TOML bool: never exported to the environment
        ("true", True),
        ("ture", True),  # malformed fails closed
        (False, False),
        ("false", False),
    ],
)
def test_streamlit_secret_is_honoured(monkeypatch, secret, expected):
    import streamlit as st

    monkeypatch.setattr(settings, "snto_public_demo", False)
    monkeypatch.setattr(st, "secrets", _FakeSecrets(SNTO_PUBLIC_DEMO=secret))
    assert is_public_demo() is expected


def test_read_only_wins_when_sources_conflict(monkeypatch):
    import streamlit as st

    monkeypatch.setattr(settings, "snto_public_demo", True)
    monkeypatch.setattr(st, "secrets", _FakeSecrets(SNTO_PUBLIC_DEMO=False))
    assert is_public_demo() is True


def test_unreadable_secrets_file_fails_closed(monkeypatch):
    import streamlit as st

    class Broken(_FakeSecrets):
        def load_if_toml_exists(self) -> bool:
            raise ValueError("bad toml")

    monkeypatch.setattr(settings, "snto_public_demo", False)
    monkeypatch.setattr(st, "secrets", Broken())
    assert is_public_demo() is True
