"""/api/v2/territories endpoints (v3.0, mobile Fase 2 read layer).

``TerritoryOut`` existed as a schema since Fase 5 but nothing mounted a router
for it — the persisted ``Territory`` table had no read surface at all. This
adds it, plus a purpose-built ``/summary`` (exactly the roll-up a mobile home
screen needs: asset count, open alert count, freshest observation timestamp
and its evidence class) so that screen needs one call, not N. All reads;
writes to territories go through the v3.0 tenancy service
(``src.persistence.services.tenancy``), not this router.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.v2.schemas import (
    TerritoryListResponse,
    TerritoryOut,
    TerritorySummaryOut,
)
from src.persistence.enums import AlertStatus
from src.persistence.repositories import (
    AlertRepository,
    ManagedAssetRepository,
    ObservationRepository,
    TerritoryRepository,
)
from src.persistence.session import get_db

router = APIRouter(tags=["territories"])


@router.get("/", response_model=TerritoryListResponse)
def list_territories(db: Session = Depends(get_db)) -> TerritoryListResponse:
    territories = TerritoryRepository(db).list()
    return TerritoryListResponse(
        total=len(territories),
        territories=[TerritoryOut.model_validate(t) for t in territories],
    )


@router.get("/{territory_id}", response_model=TerritoryOut)
def get_territory(territory_id: int, db: Session = Depends(get_db)) -> TerritoryOut:
    territory = TerritoryRepository(db).get(territory_id)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territory not found")
    return TerritoryOut.model_validate(territory)


@router.get("/{territory_id}/summary", response_model=TerritorySummaryOut)
def get_territory_summary(
    territory_id: int, db: Session = Depends(get_db)
) -> TerritorySummaryOut:
    territory = TerritoryRepository(db).get(territory_id)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territory not found")

    asset_repo = ManagedAssetRepository(db)
    assets = asset_repo.list_by_territory(territory_id)
    alert_repo = AlertRepository(db)
    _open_statuses = (AlertStatus.OPEN, AlertStatus.ASSIGNED, AlertStatus.ESCALATED)
    open_count = sum(
        1
        for a in assets
        for alert in alert_repo.list_by_asset(a.id)
        if alert.status in _open_statuses
    )

    obs_repo = ObservationRepository(db)
    latest_per_asset = [
        obs for a in assets if (obs := obs_repo.get_latest_by_asset(a.id)) is not None
    ]
    freshest = max(latest_per_asset, key=lambda o: o.observed_at, default=None)

    return TerritorySummaryOut(
        territory_id=territory.id,
        slug=territory.slug,
        name=territory.name,
        asset_count=len(assets),
        open_alert_count=open_count,
        updated_at=freshest.observed_at if freshest else None,
        evidence_class=freshest.source if freshest else None,
    )
