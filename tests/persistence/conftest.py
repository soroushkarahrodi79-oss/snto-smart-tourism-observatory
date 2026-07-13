from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.persistence.models import Base


@pytest.fixture
def db_session() -> Iterator[Session]:
    """A fresh in-memory SQLite schema per test, built straight from the models."""
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
