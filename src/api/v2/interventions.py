"""
/api/v2/interventions endpoints (Fase 5, 5.5).

The Intervention resource with its ``planned → in_progress → resolved``
lifecycle. Create/transition are writes — not auth-gated yet; minimal auth
gates every write in step 5.8 (ADR-011). Transitions are validated against
``src.persistence.services.lifecycle`` so an illegal jump returns 409 rather
than corrupting the record.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.v2.deps import require_write_auth
from src.api.v2.schemas import (
    InterventionCreate,
    InterventionOut,
    InterventionTransitionRequest,
)
from src.persistence.models.intervention import Intervention
from src.persistence.repositories import (
    InterventionRepository,
    ManagedAssetRepository,
)
from src.persistence.services import audit
from src.persistence.services.lifecycle import (
    IllegalTransitionError,
    ResourceNotFoundError,
    transition_intervention,
)
from src.persistence.session import get_db

router = APIRouter(tags=["interventions"])


@router.post(
    "/managed-assets/{asset_id}/interventions", response_model=InterventionOut
)
def create_intervention(
    asset_id: int,
    body: InterventionCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_write_auth),
) -> InterventionOut:
    if ManagedAssetRepository(db).get(asset_id) is None:
        raise HTTPException(status_code=404, detail="ManagedAsset not found")
    intervention = InterventionRepository(db).add(
        Intervention(
            asset_id=asset_id,
            recommendation_id=body.recommendation_id,
            budget_eur=body.budget_eur,
        )
    )
    audit.record(
        db,
        actor=actor,
        action=audit.INTERVENTION_CREATED,
        subject_type="intervention",
        subject_id=intervention.id,
        payload={"asset_id": asset_id, "budget_eur": body.budget_eur},
    )
    db.commit()
    return InterventionOut.model_validate(intervention)


@router.get("/interventions/{intervention_id}", response_model=InterventionOut)
def get_intervention(
    intervention_id: int, db: Session = Depends(get_db)
) -> InterventionOut:
    intervention = InterventionRepository(db).get(intervention_id)
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return InterventionOut.model_validate(intervention)


@router.post(
    "/interventions/{intervention_id}/transition",
    response_model=InterventionOut,
)
def transition_intervention_status(
    intervention_id: int,
    body: InterventionTransitionRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(require_write_auth),
) -> InterventionOut:
    try:
        intervention = transition_intervention(
            db, intervention_id, body.to_status, actor=actor
        )
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="Intervention not found")
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    db.commit()
    return InterventionOut.model_validate(intervention)
