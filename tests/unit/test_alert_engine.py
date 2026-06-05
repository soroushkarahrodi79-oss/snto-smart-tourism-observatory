from __future__ import annotations

from src.alerts.engine import AlertEngine, AlertLevel
from src.risk_engine.components import RiskComponents
from src.risk_engine.scorer import RiskScore
from src.time_series.trend import TrendResult


def _make_risk_score(score: float) -> RiskScore:
    comp = RiskComponents(
        ecological_degradation=score,
        human_pressure_proxy=score,
        vulnerability_index=score,
    )
    return RiskScore(asset_id="test", score=score, components=comp, computation_trace={})


def _trend(slope: float) -> TrendResult:
    return TrendResult(slope=slope, intercept=0.0, r_squared=0.0)


engine = AlertEngine()


def test_critical_intervention_above_085():
    alert = engine.evaluate_asset(_make_risk_score(0.90), _trend(0.0))
    assert alert.level == AlertLevel.CRITICAL_INTERVENTION


def test_urgent_monitoring_with_declining_trend():
    # High score + NDVI actively declining (credible negative slope) → URGENT
    # R² must be >= 0.30 for the slope to be considered credible
    declining = TrendResult(slope=-0.01, intercept=0.5, r_squared=0.80)
    alert = engine.evaluate_asset(_make_risk_score(0.75), declining)
    assert alert.level == AlertLevel.URGENT_MONITORING


def test_preventive_action_when_score_high_but_trend_not_credible():
    # Negative slope but very low R² → trend not credible → falls through to PREVENTIVE
    low_r2 = TrendResult(slope=-0.01, intercept=0.5, r_squared=0.10)
    alert = engine.evaluate_asset(_make_risk_score(0.75), low_r2)
    assert alert.level == AlertLevel.PREVENTIVE_ACTION


def test_preventive_action_when_urgent_but_recovering():
    # High score + NDVI improving (rising) → situation not worsening → PREVENTIVE
    alert = engine.evaluate_asset(_make_risk_score(0.75), _trend(0.01))
    assert alert.level == AlertLevel.PREVENTIVE_ACTION


def test_preventive_action_mid_range():
    alert = engine.evaluate_asset(_make_risk_score(0.60), _trend(0.0))
    assert alert.level == AlertLevel.PREVENTIVE_ACTION


def test_normal_below_threshold():
    alert = engine.evaluate_asset(_make_risk_score(0.30), _trend(0.0))
    assert alert.level == AlertLevel.NORMAL


def test_all_levels_have_recommended_actions():
    for score, slope in [(0.90, 0.0), (0.75, 0.01), (0.60, 0.0), (0.20, 0.0)]:
        alert = engine.evaluate_asset(_make_risk_score(score), _trend(slope))
        assert len(alert.recommended_actions) > 0, f"No actions for {alert.level}"


def test_triggered_rules_not_empty():
    alert = engine.evaluate_asset(_make_risk_score(0.90), _trend(0.0))
    assert len(alert.triggered_rules) > 0
