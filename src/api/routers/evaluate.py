from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from src.alerts.engine import AlertEngine
from src.api.schemas import (
    EvaluateAssetRequest,
    EvaluateAssetResponse,
    RiskComponentsOut,
)
from src.assets.models import TourismAsset
from src.config.settings import settings
from src.features.spectral import extract_spectral_features
from src.geospatial.geometry import enrich_asset_geometry
from src.ingestion.gee_adapter import GEEAdapter
from src.ingestion.mock_generator import MockDataGenerator
from src.risk_engine.components import (
    RiskComponents,
    compute_ecological_degradation,
    compute_human_pressure_proxy,
    compute_vulnerability_index,
)
from src.risk_engine.scorer import RiskScorer
from src.time_series.anomaly import compute_anomaly
from src.time_series.trend import compute_linear_trend
from src.time_series.volatility import compute_volatility

router = APIRouter(tags=["evaluation"])


def _get_adapter():
    if settings.use_mock_data:
        return MockDataGenerator()
    return GEEAdapter(
        project_id=settings.gee_project_id,
        key_file=settings.gee_key_file,
    )


@router.post("/", response_model=EvaluateAssetResponse)
async def evaluate_asset(request: EvaluateAssetRequest) -> EvaluateAssetResponse:
    """Run the full SNTO pipeline for a single asset and return scored result."""
    try:
        asset = TourismAsset(
            asset_id=request.asset_id,
            name=request.name,
            asset_type=request.asset_type,
            geometry=request.geometry,
            region=request.region,
            country=request.country,
            elevation_m=request.elevation_m,
            metadata=request.metadata,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    asset = enrich_asset_geometry(asset)

    adapter = _get_adapter()
    observations = adapter.fetch_time_series(asset, year=request.year)

    features = extract_spectral_features(observations)
    trend = compute_linear_trend(features.ndvi_series)
    volatility = compute_volatility(features.ndvi_series)
    anomaly = compute_anomaly(
        current_value=features.ndvi_series[-1],
        historical_series=features.ndvi_series[:-1],
    )

    components = RiskComponents(
        ecological_degradation=compute_ecological_degradation(features, trend),
        human_pressure_proxy=compute_human_pressure_proxy(features, volatility, asset.metadata),
        vulnerability_index=compute_vulnerability_index(features, anomaly, asset.elevation_m),
    )

    scorer = RiskScorer()
    risk_score = scorer.compute_risk_score(asset.asset_id, components)

    alert_engine = AlertEngine()
    alert = alert_engine.evaluate_asset(risk_score, trend)

    return EvaluateAssetResponse(
        asset_id=asset.asset_id,
        name=asset.name,
        risk_score=risk_score.score,
        alert_level=alert.level,
        components=RiskComponentsOut(
            ecological_degradation=components.ecological_degradation,
            human_pressure_proxy=components.human_pressure_proxy,
            vulnerability_index=components.vulnerability_index,
        ),
        recommended_actions=alert.recommended_actions,
        triggered_rules=alert.triggered_rules,
        computation_trace=risk_score.computation_trace,
    )
