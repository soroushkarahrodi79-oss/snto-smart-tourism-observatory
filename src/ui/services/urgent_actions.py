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


def _next_status(current: ManagedAssetStatus) -> ManagedAssetStatus | None:
    """The single allowed forward status, or None if terminal (5.5 state map)."""
    successors = MANAGED_ASSET_TRANSITIONS.get(current, set())
    return next(iter(successors), None)


def list_urgent_actions(session: Session, *, limit: int = 20) -> list[UrgentAction]:
    """Open alerts as urgent actions, most-critical first (by risk score)."""
    alert_repo = AlertRepository(session)
    asset_repo = ManagedAssetRepository(session)
    rec_repo = RecommendationRepository(session)

    open_alerts = sorted(
        alert_repo.list_open(), key=lambda a: a.risk_score, reverse=True
    )[:limit]

    actions: list[UrgentAction] = []
    for alert in open_alerts:
        asset = asset_repo.get(alert.asset_id)
        if asset is None:  # pragma: no cover - referential integrity guards this
            continue
        recs = rec_repo.list_by_alert(alert.id)
        actions.append(
            UrgentAction(
                alert_id=alert.id,
                asset_id=asset.id,
                asset_name=asset.name,
                asset_external_id=asset.external_asset_id,
                asset_status=asset.status,
                level=alert.level,
                risk_score=alert.risk_score,
                top_action=recs[0].action_label if recs else None,
                next_status=_next_status(asset.status),
            )
        )
    return actions
