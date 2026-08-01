from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from src.persistence.models import Base

# CI (job postgres-integration) exporta SNTO_TEST_DATABASE_URL apuntando a un
# Postgres real de servicio; en local queda vacío y se usa SQLite en memoria.
# Nunca apuntar esta variable a una base con datos: el fixture migra, trunca y
# revierte todas las tablas de aplicación.
_TEST_DB_URL = os.environ.get("SNTO_TEST_DATABASE_URL", "")
_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config(connection: Connection) -> Config:
    config = Config(str(_ROOT / "alembic.ini"))
    config.attributes["connection"] = connection
    return config


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine | None]:
    """Migrate the dedicated PostGIS test database once for the test session."""
    if not _TEST_DB_URL:
        yield None
        return

    engine = create_engine(_TEST_DB_URL)
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")
    yield engine
    with engine.begin() as connection:
        command.downgrade(_alembic_config(connection), "base")
    engine.dispose()


def _truncate_application_tables(engine: Engine) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"
        )


@pytest.fixture
def db_session(postgres_engine: Engine | None) -> Iterator[Session]:
    """A fresh schema per test, built straight from the models.

    In-memory SQLite by default; a real database when SNTO_TEST_DATABASE_URL
    is set (the CI Postgres job), so the suite also validates the engine that
    production runs on.
    """
    if postgres_engine is not None:
        _truncate_application_tables(postgres_engine)
        with Session(postgres_engine) as session:
            yield session
            session.rollback()
        _truncate_application_tables(postgres_engine)
        return

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:
        # SQLite ignores FOREIGN KEY constraints unless explicitly enabled per
        # connection — without this, test_managed_asset_requires_territory
        # would silently insert an orphan row instead of raising.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()
