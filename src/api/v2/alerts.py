"""
Read-only /api/v2/alerts endpoints (Fase 5, 5.4).

Exposes the persisted alerts (written by the AlertEngine bridge,
``src.persistence.services.alert_ingest``) and their recommendations. Still
read-only — triage/state changes arrive as auth-gated write endpoints in
step 5.8.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.v2.schemas import (
    AlertOut,
    RecommendationListResponse,
    RecommendationOut,
)
from src.persistence.repositories import (
    AlertRepository,
    RecommendationRepository,
)
from src.persistence.session import get_db

router = APIRouter(tags=["alerts-v2"])


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertOut:
    alert = AlertRepository(db).get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertOut.model_validate(alert)


@router.get(
    "/{alert_id}/recommendations", response_model=RecommendationListResponse
)
def list_alert_recommendations(
    alert_id: int, db: Session = Depends(get_db)
) -> RecommendationListResponse:
    if AlertRepository(db).get(alert_id) is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    recommendations = RecommendationRepository(db).list_by_alert(alert_id)
    return RecommendationListResponse(
        total=len(recommendations),
        recommendations=[
            RecommendationOut.model_validate(r) for r in recommendations
        ],
    )
