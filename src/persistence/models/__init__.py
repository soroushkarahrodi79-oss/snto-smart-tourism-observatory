"""
All SNTO persistence models, imported here so:

1. SQLAlchemy's mapper configuration can resolve every ``relationship()``
   forward string-reference (e.g. ``Mapped["ManagedAsset"]``) — they are only
   resolvable once every model class has been imported into some namespace.
2. Alembic's ``env.py`` can point autogenerate at one ``Base.metadata`` that
   already knows about every table (see ``src/persistence/base.py``).
"""
from __future__ import annotations

from src.persistence.base import Base
from src.persistence.models.alert import Alert
from src.persistence.models.audit_log import AuditLogEntry
from src.persistence.models.decision import Decision
from src.persistence.models.field_verification import FieldVerification
from src.persistence.models.intervention import Intervention
from src.persistence.models.managed_asset import ManagedAsset
from src.persistence.models.observation import Observation
from src.persistence.models.recommendation import Recommendation
from src.persistence.models.territory import Territory

__all__ = [
    "Base",
    "Alert",
    "AuditLogEntry",
    "Decision",
    "FieldVerification",
    "Intervention",
    "ManagedAsset",
    "Observation",
    "Recommendation",
    "Territory",
]
