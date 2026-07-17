"""
/api/v2/managed-assets endpoints (Fase 5, 5.3 read + 5.5 lifecycle transition).

Backed by ManagedAssetRepository over the persistence session. Optional
filters (territory_id, status) map to the repository's typed lookups; the
unfiltered path lists everything with limit/offset paging. The transition
endpoint (5.5) is the first write here and is not auth-gated yet — minimal
auth gates writes in step 5.8.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.v2.deps import get_actor
from src.api.v2.schemas import (
    AlertListResponse,
    AlertOut,
    ManagedAssetListResponse,
    ManagedAssetOut,
    ManagedAssetTransitionRequest,
    ObservationListResponse,
    ObservationOut,
)
from src.persistence.enums import ManagedAssetStatus
from src.persistence.repositories import (
    AlertRepository,
    ManagedAssetRepository,
    ObservationRepository,
)
from src.persistence.services.lifecycle import (
    IllegalTransitionError,
    ResourceNotFoundError,
    transition_managed_asset,
)
from src.persistence.session import get_db

router = APIRouter(tags=["managed-assets"])


@router.get("/", response_model=ManagedAssetListResponse)
def list_managed_assets(
    territory_id: int | None = None,
    status: ManagedAssetStatus | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ManagedAssetListResponse:
    repo = ManagedAssetRepository(db)
    if territory_id is not None:
        assets = repo.list_by_territory(territory_id)
    elif status is not None:
        assets = repo.list_by_status(status)
    else:
        assets = repo.list(limit=limit, offset=offset)
    return ManagedAssetListResponse(
        total=len(assets),
        assets=[ManagedAssetOut.model_validate(a) for a in assets],
    )


@router.get("/{asset_id}", response_model=ManagedAssetOut)
def get_managed_asset(
    asset_id: int, db: Session = Depends(get_db)
) -> ManagedAssetOut:
    asset = ManagedAssetRepository(db).get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="ManagedAsset not found")
    return ManagedAssetOut.model_validate(asset)


@router.get(
    "/{asset_id}/observations", response_model=ObservationListResponse
)
def list_asset_observations(
    asset_id: int, db: Session = Depends(get_db)
) -> ObservationListResponse:
    if ManagedAssetRepository(db).get(asset_id) is None:
        raise HTTPException(status_code=404, detail="ManagedAsset not found")
    observations = ObservationRepository(db).list_by_asset(asset_id)
    return ObservationListResponse(
        total=len(observations),
        observations=[ObservationOut.model_validate(o) for o in observations],
    )


@router.get("/{asset_id}/alerts", response_model=AlertListResponse)
def list_asset_alerts(
    asset_id: int, db: Session = Depends(get_db)
) -> AlertListResponse:
    if ManagedAssetRepository(db).get(asset_id) is None:
        raise HTTPException(status_code=404, detail="ManagedAsset not found")
    alerts = AlertRepository(db).list_by_asset(asset_id)
    return AlertListResponse(
        total=len(alerts),
        alerts=[AlertOut.model_validate(a) for a in alerts],
    )


@router.post("/{asset_id}/transition", response_model=ManagedAssetOut)
def transition_asset(
    asset_id: int,
    body: ManagedAssetTransitionRequest,
    db: Session = Depends(get_db),
    actor: str = Depends(get_actor),
) -> ManagedAssetOut:
    """
    Advance a ManagedAsset along its lifecycle
    (detected→verified→assigned→funded→resolved→monitored). Returns 404 if the
    asset is absent, 409 if the transition is not allowed from the current
    state.
    """
    try:
        asset = transition_managed_asset(db, asset_id, body.to_status, actor=actor)
    except ResourceNotFoundError:
        raise HTTPException(status_code=404, detail="ManagedAsset not found")
    except IllegalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    db.commit()
    return ManagedAssetOut.model_validate(asset)
