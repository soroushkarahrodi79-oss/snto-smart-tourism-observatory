"""
Declarative base for the SNTO persistence layer (Fase 5, ADR-011).

A single shared ``Base`` so Alembic's autogenerate can see every model's
metadata from one import (``src.persistence.base.Base.metadata``).
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for every table in ``src/persistence/models/``."""
