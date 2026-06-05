from __future__ import annotations

from src.alerts.engine import AlertEngine, AlertLevel
from src.features.spectral import extract_spectral_features
from src.geospatial.geometry import enrich_asset_geometry
from src.ingestion.mock_generator import MockDataGenerator
from src.ranking.ranker import AssetRanker
from src.reporting.report_builder import build_report
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


def _run_pipeline(asset):
    """Execute full Phase 1 pipeline; return (risk_score, alert, trend)."""
    asset = enrich_asset_geometry(asset)
    gen = MockDataGenerator()
    observations = gen.fetch_time_series(asset, year=2024)

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

    risk_score = RiskScorer().compute_risk_score(asset.asset_id, components)
    alert = AlertEngine().evaluate_asset(risk_score, trend)
    return risk_score, alert, trend


def test_masatrigo_pipeline_score_in_range(masatrigo_asset):
    risk_score, _, _ = _run_pipeline(masatrigo_asset)
    assert 0.0 <= risk_score.score <= 1.0


def test_masatrigo_pipeline_computation_trace_populated(masatrigo_asset):
    risk_score, _, _ = _run_pipeline(masatrigo_asset)
    trace = risk_score.computation_trace
    assert trace["components"]["ecological_degradation"] >= 0.0
    assert trace["components"]["human_pressure_proxy"] >= 0.0
    assert trace["components"]["vulnerability_index"] >= 0.0
    assert "final_score" in trace


def test_masatrigo_pipeline_is_reproducible(masatrigo_asset):
    score1, _, _ = _run_pipeline(masatrigo_asset)
    score2, _, _ = _run_pipeline(masatrigo_asset)
    assert score1.score == score2.score


def test_masatrigo_alert_level_is_valid(masatrigo_asset):
    _, alert, _ = _run_pipeline(masatrigo_asset)
    assert alert.level in list(AlertLevel)


def test_masatrigo_alert_has_actions(masatrigo_asset):
    _, alert, _ = _run_pipeline(masatrigo_asset)
    assert len(alert.recommended_actions) > 0


def test_multi_asset_ranking(masatrigo_asset, viewpoint_asset, recreational_area_asset):
    scores = []
    for asset in [masatrigo_asset, viewpoint_asset, recreational_area_asset]:
        rs, _, _ = _run_pipeline(asset)
        scores.append(rs)

    ranked = AssetRanker().rank_assets(scores)
    assert len(ranked) == 3
    assert ranked[0].rank == 1
    assert ranked[0].risk_score >= ranked[1].risk_score >= ranked[2].risk_score


def test_report_builder_structure(masatrigo_asset, viewpoint_asset):
    scores, alerts_list, trends = [], [], []
    for asset in [masatrigo_asset, viewpoint_asset]:
        rs, alert, trend = _run_pipeline(asset)
        scores.append(rs)
        alerts_list.append(alert)

    ranked = AssetRanker().rank_assets(scores)
    report = build_report(scores, alerts_list, ranked, report_date="2024-06-01")

    assert "metadata" in report
    assert "executive_summary" in report
    assert "kpi_section" in report
    assert "critical_assets" in report
    assert "recommended_actions" in report
    assert "risk_trends" in report
    assert report["metadata"]["total_assets_evaluated"] == 2
