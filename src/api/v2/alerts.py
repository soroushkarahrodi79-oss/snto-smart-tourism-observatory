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
    AlertListResponse,
    AlertOut,
    AlertTriageRequest,
    RecommendationListResponse,
    RecommendationOut,
)
from src.persistence.enums import AlertStatus
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


@router.get("/", response_model=AlertListResponse)
def list_alerts(
    territory_id: int | None = None,
    status: AlertStatus | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> AlertListResponse:
    """Flat alert listing (mobile Fase 2, ADR-014 addendum).

    Mirrors ``list_managed_assets``'s own filter precedent: ``territory_id``
    scopes to one territory (the join query — the actual point of this
    endpoint, since no per-asset round-trip scales to "every alert a
    territory has"); without it, every alert is listed, optionally narrowed
    by ``status`` alone.
    """
    repo = AlertRepository(db)
    if territory_id is not None:
        alerts = repo.list_by_territory(territory_id, status=status)
    elif status is not None:
        alerts = repo.list_by_status(status)
    else:
        alerts = repo.list(limit=limit, offset=offset)
    return AlertListResponse(
        total=len(alerts), alerts=[AlertOut.model_validate(a) for a in alerts]
    )


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
