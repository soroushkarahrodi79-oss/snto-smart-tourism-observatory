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

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first use."""
    global _engine
    if _engine is None:
        url = settings.database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
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
