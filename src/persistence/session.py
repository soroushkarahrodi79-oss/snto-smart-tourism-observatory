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

from src.config.settings import settings


class PublicDemoReadOnlyError(SQLAlchemyError):
    """Raised on any write attempt while ``SNTO_PUBLIC_DEMO`` is enabled.

    Subclasses ``SQLAlchemyError`` so existing "backend unavailable" handling in
    the UI degrades gracefully instead of surfacing a traceback.
    """


# First keyword of statements allowed in public-demo mode (read-only).
_READ_ONLY_PREFIXES = ("SELECT", "WITH", "PRAGMA", "EXPLAIN", "SHOW")


def _enforce_read_only(conn, cursor, statement, parameters, context, executemany):
    """``before_cursor_execute`` hook: block every non-read statement."""
    head = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else ""
    if head not in _READ_ONLY_PREFIXES:
        raise PublicDemoReadOnlyError(
            "Demo pública de solo lectura (SNTO_PUBLIC_DEMO): escritura rechazada."
        )

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first use."""
    global _engine
    if _engine is None:
        url = settings.database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
        if settings.snto_public_demo:
            event.listen(_engine, "before_cursor_execute", _enforce_read_only)
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
