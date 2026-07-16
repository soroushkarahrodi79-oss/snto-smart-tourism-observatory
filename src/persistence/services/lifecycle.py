"""
State-machine validation for lifecycle transitions (Fase 5, step 5.5).

Two state machines are enforced here:

- ``ManagedAssetStatus`` — the central product lifecycle from
  ``docs/ux/ui-evolution-v2-spec.md`` §3:
  ``detected → verified → assigned → funded → resolved → monitored``.
- ``InterventionStatus`` — ``planned → in_progress → resolved``.

Both are **forward-only** in this first cut: a state may only advance to its
immediate successor. Re-opening a ``monitored`` asset (or a ``resolved``
intervention) after fresh degradation is a deliberate future enhancement, not
silently allowed here — the point of this step is that an illegal jump raises
rather than corrupting the record.

The transition maps are the single source of truth; the API layer calls
``transition_managed_asset`` / ``transition_intervention`` and never mutates
``status`` directly.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.persistence.enums import InterventionStatus, ManagedAssetStatus
from src.persistence.repositories import (
    InterventionRepository,
    ManagedAssetRepository,
)

# Allowed forward transitions. A status absent as a key is terminal.
MANAGED_ASSET_TRANSITIONS: dict[ManagedAssetStatus, set[ManagedAssetStatus]] = {
    ManagedAssetStatus.DETECTED: {ManagedAssetStatus.VERIFIED},
    ManagedAssetStatus.VERIFIED: {ManagedAssetStatus.ASSIGNED},
    ManagedAssetStatus.ASSIGNED: {ManagedAssetStatus.FUNDED},
    ManagedAssetStatus.FUNDED: {ManagedAssetStatus.RESOLVED},
    ManagedAssetStatus.RESOLVED: {ManagedAssetStatus.MONITORED},
    ManagedAssetStatus.MONITORED: set(),
}

INTERVENTION_TRANSITIONS: dict[InterventionStatus, set[InterventionStatus]] = {
    InterventionStatus.PLANNED: {InterventionStatus.IN_PROGRESS},
    InterventionStatus.IN_PROGRESS: {InterventionStatus.RESOLVED},
    InterventionStatus.RESOLVED: set(),
}


class IllegalTransitionError(ValueError):
    """Raised when a requested state transition is not in the allowed map."""

    def __init__(self, current: object, requested: object) -> None:
        super().__init__(
            f"Illegal transition {getattr(current, 'value', current)!r} -> "
            f"{getattr(requested, 'value', requested)!r}"
        )
        self.current = current
        self.requested = requested


class ResourceNotFoundError(LookupError):
    """Raised when the resource to transition does not exist."""


def _validate(current, requested, transitions) -> None:
    if requested not in transitions.get(current, set()):
        raise IllegalTransitionError(current, requested)


def transition_managed_asset(
    session: Session, asset_id: int, to_status: ManagedAssetStatus
):
    """Advance a ManagedAsset's status if the transition is allowed."""
    asset = ManagedAssetRepository(session).get(asset_id)
    if asset is None:
        raise ResourceNotFoundError(f"ManagedAsset id={asset_id} not found")
    _validate(asset.status, to_status, MANAGED_ASSET_TRANSITIONS)
    asset.status = to_status
    session.flush()
    return asset


def transition_intervention(
    session: Session, intervention_id: int, to_status: InterventionStatus
):
    """Advance an Intervention's status if the transition is allowed."""
    intervention = InterventionRepository(session).get(intervention_id)
    if intervention is None:
        raise ResourceNotFoundError(
            f"Intervention id={intervention_id} not found"
        )
    _validate(intervention.status, to_status, INTERVENTION_TRANSITIONS)
    intervention.status = to_status
    session.flush()
    return intervention
