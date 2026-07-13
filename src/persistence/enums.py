"""
Lifecycle enums for the SNTO persistence layer (Fase 5, ADR-011).

These are new, domain-specific state machines (not reused from elsewhere).
``ManagedAssetStatus`` is exactly the lifecycle named in
``docs/ux/ui-evolution-v2-spec.md`` §3
(``detected -> verified -> assigned -> funded -> resolved -> monitored``) —
the central product object v2.0 is built around.

Evidence provenance (``real``/``calibrated``/``synthetic``/``simulated``/
``missing``) is intentionally *not* re-declared here: ``Observation.source``
stores the same string values as ``src.platform.evidence.EvidenceClass`` so
there is exactly one evidence vocabulary, per the non-negotiable in ADR-004 /
issue #10 (see ``docs/methodology/evidence-classes.md``). Persistence code
that needs the enum object imports it directly from
``src.platform.evidence``; only the column's stored values are constrained
here, to keep this module importable without pulling in ``src.platform``'s
heavier package init.
"""
from __future__ import annotations

from enum import Enum


class ManagedAssetStatus(str, Enum):
    """The managed-asset lifecycle (``ui-evolution-v2-spec.md`` §3)."""
    DETECTED = "detected"
    VERIFIED = "verified"
    ASSIGNED = "assigned"
    FUNDED = "funded"
    RESOLVED = "resolved"
    MONITORED = "monitored"


class AlertStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    DISMISSED = "dismissed"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DONE = "done"


class InterventionStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
