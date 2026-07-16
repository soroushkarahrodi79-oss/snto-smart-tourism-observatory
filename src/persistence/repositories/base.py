"""
Generic typed CRUD repository (Fase 5, step 5.2).

One thin base class so every resource repository shares the same four
operations (``add``, ``get``, ``list``, ``delete``) without re-implementing
them nine times; each resource repository subclasses it only to add the
lookups that are actually specific to that resource (e.g.
``ManagedAssetRepository.get_by_external_id``).
"""
from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.persistence.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def get(self, id_: int) -> ModelT | None:
        return self.session.get(self.model, id_)

    def list(self, *, limit: int | None = None, offset: int = 0) -> list[ModelT]:
        stmt = select(self.model).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()
