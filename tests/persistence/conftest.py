from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.persistence.models import Base

# CI (job postgres-integration) exporta SNTO_TEST_DATABASE_URL apuntando a un
# Postgres real de servicio; en local queda vacío y se usa SQLite en memoria.
# Nunca apuntar esta variable a una base con datos: el fixture hace drop_all.
_TEST_DB_URL = os.environ.get("SNTO_TEST_DATABASE_URL", "")


@pytest.fixture
def db_session() -> Iterator[Session]:
    """A fresh schema per test, built straight from the models.

    In-memory SQLite by default; a real database when SNTO_TEST_DATABASE_URL
    is set (the CI Postgres job), so the suite also validates the engine that
    production runs on.
    """
    if _TEST_DB_URL:
        engine = create_engine(_TEST_DB_URL)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
        Base.metadata.drop_all(engine)
        engine.dispose()
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
