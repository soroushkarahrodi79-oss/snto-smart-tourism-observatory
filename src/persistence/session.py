"""
Engine/session factory for the SNTO persistence layer (Fase 5, ADR-011).

Reads ``settings.database_url`` (SQLite by default, Postgres if
``SNTO_DB_HOST`` is set — see ``src/config/settings.py``). A single module-
level engine/sessionmaker pair, created lazily so importing this module never
opens a connection or creates a SQLite file as a side effect.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import is_public_demo, settings


class PublicDemoReadOnlyError(SQLAlchemyError):
    """Raised on any write attempt while ``SNTO_PUBLIC_DEMO`` is enabled.

    Subclasses ``SQLAlchemyError`` so existing "backend unavailable" handling in
    the UI degrades gracefully instead of surfacing a traceback.
    """


# Two layers, both active only in public-demo mode:
# 1. the connection itself is opened read-only (the database refuses writes,
#    including ones hidden in a CTE or sent through a raw DBAPI cursor);
# 2. a statement guard rejects obvious writes early with a typed error, and
#    blocks PRAGMA/SET so layer 1 cannot be switched back off through SQLAlchemy.
_READ_ONLY_PREFIXES = ("SELECT", "WITH", "EXPLAIN", "SHOW")
_READ_ONLY_CONNECT_SQL = {
    "sqlite": "PRAGMA query_only = ON",
    "postgresql": "SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY",
}


def _enforce_read_only(conn, cursor, statement, parameters, context, executemany):
    """``before_cursor_execute`` hook: block every non-read statement."""
    head = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else ""
    if head not in _READ_ONLY_PREFIXES:
        raise PublicDemoReadOnlyError(
            "Demo pública de solo lectura (SNTO_PUBLIC_DEMO): escritura rechazada."
        )

def _apply_read_only(engine: Engine) -> None:
    """Install both read-only layers on a freshly created engine."""
    connect_sql = _READ_ONLY_CONNECT_SQL.get(engine.dialect.name)

    if connect_sql is not None:

        @event.listens_for(engine, "connect")
        def _open_read_only(dbapi_connection, _record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute(connect_sql)
            cursor.close()
            dbapi_connection.commit()

    event.listen(engine, "before_cursor_execute", _enforce_read_only)


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first use."""
    global _engine
    if _engine is None:
        url = settings.database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        if is_public_demo():
            _apply_read_only(_engine)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    """Return the process-wide sessionmaker, creating it on first use."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False
        )
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context-managed session: commits on success, rolls back on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session, closes it after the request."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
