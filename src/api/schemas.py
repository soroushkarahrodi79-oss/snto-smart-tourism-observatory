from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from src.alerts.engine import AlertLevel
from src.assets.models import AssetType, GeoJSONGeometry


# ── Request ────────────────────────────────────────────────────────────────

class EvaluateAssetRequest(BaseModel):
    asset_id: str
    name: str
    asset_type: AssetType
    geometry: GeoJSONGeometry
    region: str
    country: str = "Spain"
    elevation_m: Optional[float] = None
    metadata: dict[str, Any] = {}
    year: int = 2024


# ── Response ───────────────────────────────────────────────────────────────

class RiskComponentsOut(BaseModel):
    ecological_degradation: float
    human_pressure_proxy: float
    vulnerability_index: float


class EvaluateAssetResponse(BaseModel):
    asset_id: str
    name: str
    risk_score: float
    alert_level: AlertLevel
    components: RiskComponentsOut
    recommended_actions: list[str]
    triggered_rules: list[str]
    computation_trace: dict[str, Any]


class RankedAssetOut(BaseModel):
    rank: int
    asset_id: str
    risk_score: float
    normalized_score: float
    percentile: float


class RankingResponse(BaseModel):
    total: int
    assets: list[RankedAssetOut]


class AlertOut(BaseModel):
    asset_id: str
    level: AlertLevel
    score: float
    triggered_rules: list[str]
    recommended_actions: list[str]


class AlertsResponse(BaseModel):
    total: int
    alerts: list[AlertOut]
