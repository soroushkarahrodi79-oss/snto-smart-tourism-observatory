"""
/api/v2/alerts endpoints (Fase 5.4 reads + Fase 6.2 triage).

Exposes the persisted alerts (written by the AlertEngine bridge,
``src.persistence.services.alert_ingest``) and their recommendations, plus a
triage write endpoint (assign / escalate / dismiss-with-reason). The triage
endpoint is auth-gated (`require_write_auth`, 5.8); the reads stay open.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.v2.authz_gate import authorize_territory_write
from src.api.v2.deps import require_write_auth
from src.api.v2.schemas import (
    AlertOut,
    AlertTriageRequest,
    RecommendationListResponse,
    RecommendationOut,
)
from src.persistence.repositories import (
    AlertRepository,
    RecommendationRepository,
)
from src.persistence.services.alert_triage import ReasonRequiredError, triage_alert
from src.persistence.services.lifecycle import (
    IllegalTransitionError,
    ResourceNotFoundError,
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


@router.post("/{alert_id}/triage", response_model=AlertOut)
def triage(
    alert_id: int,
    body: AlertTriageRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(require_write_auth),
) -> AlertOut:
    """
    Triage an alert: assign / escalate / dismiss. Dismissing requires a reason
    (that is how a false positive is logged). Returns 404 if absent, 409 if the
    transition is not allowed from the current status, 422 if dismissing with
    no reason.
    """
    _alert = AlertRepository(db).get(alert_id)
    if _alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    authorize_territory_write(db, actor, _alert.asset.territory_id)
    try:
        alert = triage_alert(
            db, alert_id, body.to_status, reason=body.reason, actor=actor
        )
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Alert not found")
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ReasonRequiredError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    return AlertOut.model_validate(alert)
