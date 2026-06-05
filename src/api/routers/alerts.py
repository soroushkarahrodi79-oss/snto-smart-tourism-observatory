from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import AlertOut, AlertsResponse
from src.alerts.engine import AlertLevel

router = APIRouter(tags=["alerts"])

_alerts_store: list[dict] = []


def update_alerts_store(entry: dict) -> None:
    """Called by the evaluate router to persist alert results."""
    _alerts_store.append(entry)


@router.get("/", response_model=AlertsResponse)
async def get_alerts(level: AlertLevel | None = None) -> AlertsResponse:
    """
    Return all alerts, optionally filtered by level.
    Results are sorted by descending score (most critical first).
    """
    filtered = _alerts_store
    if level is not None:
        filtered = [a for a in _alerts_store if a["level"] == level.value]

    sorted_alerts = sorted(filtered, key=lambda a: a["score"], reverse=True)
    alerts = [
        AlertOut(
            asset_id=a["asset_id"],
            level=AlertLevel(a["level"]),
            score=a["score"],
            triggered_rules=a["triggered_rules"],
            recommended_actions=a["recommended_actions"],
        )
        for a in sorted_alerts
    ]
    return AlertsResponse(total=len(alerts), alerts=alerts)
