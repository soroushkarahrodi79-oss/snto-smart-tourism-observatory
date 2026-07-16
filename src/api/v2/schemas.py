"""
Read-only response schemas for the /api/v2 persistence-backed endpoints
(Fase 5, 5.3).

``from_attributes=True`` lets each schema be built straight from a SQLAlchemy
model instance (``ManagedAssetOut.model_validate(orm_obj)``). These are
deliberately output-only DTOs — write schemas arrive with the write endpoints
in step 5.8, so nothing here accepts client-supplied state.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.persistence.enums import ManagedAssetStatus


class TerritoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    budget_eur: float
    created_at: datetime


class ManagedAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    territory_id: int
    external_asset_id: str
    name: str
    asset_type: str
    region: str
    status: ManagedAssetStatus
    created_at: datetime
    updated_at: datetime


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    observed_at: datetime
    source: str
    ehs: float | None
    ndvi: float | None
    ndmi: float | None


class ManagedAssetListResponse(BaseModel):
    total: int
    assets: list[ManagedAssetOut]


class ObservationListResponse(BaseModel):
    total: int
    observations: list[ObservationOut]
