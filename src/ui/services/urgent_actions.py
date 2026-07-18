"""
"Urgent actions" query service (Fase 5, step 5.9).

The first UI consumer of the persistent backend (P1 in
``docs/ux/ui-evolution-v2-spec.md`` §6). This module is pure data access — no
Streamlit — so it is unit-testable against an in-memory session and reused
verbatim by ``src/ui/tabs/tab_urgent_actions.py``.

It reads the same persistence layer the ``/api/v2`` endpoints expose (open
alerts, their top recommendation, and the asset's lifecycle state), ordered by
descending risk so the most urgent decisions surface first. An HTTP-backed
variant (calling the running API instead of the in-process session) is a future
swap that does not change this module's return shape.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.persistence.enums import ManagedAssetStatus
from src.persistence.repositories import (
    AlertRepository,
    FieldVerificationRepository,
    ManagedAssetRepository,
    RecommendationRepository,
)
from src.persistence.services.lifecycle import MANAGED_ASSET_TRANSITIONS


@dataclass(frozen=True)
class UrgentAction:
    """One open alert surfaced as a decision, joined to its asset + action."""

    alert_id: int
    asset_id: int
    asset_name: str
    asset_external_id: str
    asset_status: ManagedAssetStatus
    level: str
    risk_score: float
    top_action: str | None
    next_status: ManagedAssetStatus | None
    # DCS of the top recommendation, when the engine produced one (often None —
    # populating it is the P2 "Confidence & uncertainty" module, spec §6). Shown
    # for triage context; ordering stays by risk_score until confidence is real.
    confidence: float | None
    # Whether the asset has any FieldVerification record (Fase 5.6). Lets a
    # manager see, per alert, if the signal was ground-checked — the field-
    # verification-status item of the Urgent-actions P1 gap.
    field_verified: bool


def _next_status(current: ManagedAssetStatus) -> ManagedAssetStatus | None:
    """The single allowed forward status, or None if terminal (5.5 state map)."""
    successors = MANAGED_ASSET_TRANSITIONS.get(current, set())
    return next(iter(successors), None)


def list_urgent_actions(session: Session, *, limit: int = 20) -> list[UrgentAction]:
    """Open alerts as urgent actions, most-critical first (by risk score)."""
    alert_repo = AlertRepository(session)
    asset_repo = ManagedAssetRepository(session)
    rec_repo = RecommendationRepository(session)
    fv_repo = FieldVerificationRepository(session)

    open_alerts = sorted(
        alert_repo.list_open(), key=lambda a: a.risk_score, reverse=True
    )[:limit]

    actions: list[UrgentAction] = []
    for alert in open_alerts:
        asset = asset_repo.get(alert.asset_id)
        if asset is None:  # pragma: no cover - referential integrity guards this
            continue
        recs = rec_repo.list_by_alert(alert.id)
        top_rec = recs[0] if recs else None
        actions.append(
            UrgentAction(
                alert_id=alert.id,
                asset_id=asset.id,
                asset_name=asset.name,
                asset_external_id=asset.external_asset_id,
                asset_status=asset.status,
                level=alert.level,
                risk_score=alert.risk_score,
                top_action=top_rec.action_label if top_rec else None,
                next_status=_next_status(asset.status),
                confidence=top_rec.confidence if top_rec else None,
                field_verified=bool(fv_repo.list_by_asset(asset.id)),
            )
        )
    return actions
