"""
Read-only response schemas for the /api/v2 persistence-backed endpoints
(Fase 5, 5.3).

``from_attributes=True`` lets each schema be built straight from a SQLAlchemy
model instance (``ManagedAssetOut.model_validate(orm_obj)``). These are
deliberately output-only DTOs — write schemas arrive with the write endpoints
in step 5.8, so nothing here accepts client-supplied state.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from src.persistence.enums import (
    AlertStatus,
    InterventionStatus,
    ManagedAssetStatus,
    RecommendationStatus,
)


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
    # Mobile Fase 2 read layer (v3.0): a rough map-pin coordinate — derived
    # from geometry_geojson, never a fabricated point (src.api.v2.geometry).
    latitude: float | None = None
    longitude: float | None = None
    # Freshness + evidence class of the most recent Observation, so a list
    # view doesn't need one round-trip per asset. None when the asset has no
    # observation yet — never defaulted to "now" or a guessed evidence class.
    latest_observed_at: datetime | None = None
    latest_evidence_class: str | None = None  # EvidenceClass.value


class TerritorySummaryOut(BaseModel):
    """Mobile-facing territory roll-up (Fase 2): exactly what a home screen needs.

    Distinct from ``TerritoryOut`` (the plain ORM passthrough): this is a
    purpose-built, computed summary so the mobile home screen needs one call,
    not N. ``updated_at``/``evidence_class`` are None when the territory has no
    managed assets or observations yet — never fabricated.
    """

    model_config = ConfigDict(from_attributes=True)

    territory_id: int
    slug: str
    name: str
    asset_count: int
    open_alert_count: int
    updated_at: datetime | None
    evidence_class: str | None  # EvidenceClass.value of the freshest observation


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    observed_at: datetime
    source: str
    ehs: float | None
    ndvi: float | None
    ndmi: float | None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    level: str
    risk_score: float
    triggered_rules: list[str]
    status: AlertStatus
    reason: str | None
    created_at: datetime


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int
    action_label: str
    cost_eur_low: float | None
    cost_eur_high: float | None
    confidence: float | None
    owner: str | None
    deadline: date | None
    status: RecommendationStatus


class InterventionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    recommendation_id: int | None
    status: InterventionStatus
    budget_eur: float | None
    started_at: datetime | None
    resolved_at: datetime | None


class FieldVerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    verified_at: datetime
    method: str
    verifier: str
    result: str
    photo_ref: str | None
    notes: str | None


# ── Write request bodies (Fase 5.5+) ─────────────────────────────────────────
# First client-supplied inputs in /api/v2. These endpoints are not auth-gated
# yet — minimal auth gates every write in step 5.8 (ADR-011).

class InterventionCreate(BaseModel):
    recommendation_id: int | None = None
    budget_eur: float | None = None


class FieldVerificationCreate(BaseModel):
    verified_at: datetime | None = None  # defaults to now() at the endpoint
    method: str
    verifier: str
    result: str
    photo_ref: str | None = None
    notes: str | None = None


class ManagedAssetTransitionRequest(BaseModel):
    to_status: ManagedAssetStatus


class InterventionTransitionRequest(BaseModel):
    to_status: InterventionStatus


class AlertTriageRequest(BaseModel):
    to_status: AlertStatus
    reason: str | None = None  # required by the service when dismissing


class ManagedAssetListResponse(BaseModel):
    total: int
    assets: list[ManagedAssetOut]


class TerritoryListResponse(BaseModel):
    total: int
    territories: list[TerritoryOut]


class ObservationListResponse(BaseModel):
    total: int
    observations: list[ObservationOut]


class AlertListResponse(BaseModel):
    total: int
    alerts: list[AlertOut]


class FieldVerificationListResponse(BaseModel):
    total: int
    field_verifications: list[FieldVerificationOut]


class AuditLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    subject_type: str
    subject_id: int
    payload: dict | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    total: int
    entries: list[AuditLogEntryOut]


class RecommendationListResponse(BaseModel):
    total: int
    recommendations: list[RecommendationOut]
