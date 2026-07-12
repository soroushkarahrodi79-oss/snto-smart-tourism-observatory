"""Unit tests for the director risk brief (issue #12)."""

from __future__ import annotations

from src.alerts.engine import Alert, AlertLevel
from src.platform.satellite_trends import AssetTrend
from src.ranking.ranker import RankedAsset
from src.reporting.risk_brief import (
    Confidence,
    ProbableCause,
    assess_confidence,
    build_risk_brief,
    infer_probable_cause,
    render_risk_brief_markdown,
)
from src.risk_engine.components import RiskComponents
from src.risk_engine.scorer import RiskScore


def _trend(
    asset_id: str,
    *,
    p_value: float,
    trend: str,
    ci: tuple[float, float] | None,
    worst_year: str | None = "2022",
) -> AssetTrend:
    return AssetTrend(
        asset_id=asset_id,
        category="senderismo",
        n_observations=60,
        tau=-0.3,
        p_value=p_value,
        trend=trend,
        annual_mean_ndvi={"2021": 0.4},
        partial_years=[],
        worst_year=worst_year,
        best_year="2024",
        ndvi_min=0.2,
        ndvi_max=0.5,
        sens_slope=-0.001,
        sens_slope_ci=ci,
    )


# ── assess_confidence ────────────────────────────────────────────────────────

def test_confidence_high_when_significant_and_ci_excludes_zero():
    t = _trend("a", p_value=0.01, trend="decreasing", ci=(-0.003, -0.001))
    level, basis = assess_confidence(t)
    assert level is Confidence.HIGH
    assert "excluye 0" in basis


def test_confidence_medium_when_only_significant():
    # significant p, but CI straddles zero → partial evidence
    t = _trend("a", p_value=0.01, trend="decreasing", ci=(-0.003, 0.001))
    level, _ = assess_confidence(t)
    assert level is Confidence.MEDIUM


def test_confidence_medium_when_only_ci_excludes_zero():
    t = _trend("a", p_value=0.20, trend="no trend", ci=(0.001, 0.003))
    level, _ = assess_confidence(t)
    assert level is Confidence.MEDIUM


def test_confidence_low_when_no_support():
    t = _trend("a", p_value=0.40, trend="no trend", ci=(-0.003, 0.002))
    level, _ = assess_confidence(t)
    assert level is Confidence.LOW


def test_confidence_no_data_when_trend_missing():
    level, basis = assess_confidence(None)
    assert level is Confidence.NO_DATA
    assert "Sin serie" in basis


# ── infer_probable_cause ─────────────────────────────────────────────────────

def test_cause_tourism_when_pressure_and_degradation_high():
    cause, caveat = infer_probable_cause(0.6, 0.6, None, "2022")
    assert cause is ProbableCause.TOURISM
    assert "preliminar" in caveat.lower()


def test_cause_climate_when_low_pressure_and_shares_worst_year():
    t = _trend(
        "a", p_value=0.01, trend="decreasing", ci=(-0.003, -0.001), worst_year="2022"
    )
    cause, caveat = infer_probable_cause(0.6, 0.2, t, "2022")
    assert cause is ProbableCause.CLIMATE
    assert "2022" in caveat


def test_cause_mixed_when_degraded_but_ambiguous():
    # degraded, mid pressure, does not share the drought year
    t = _trend("a", p_value=0.5, trend="no trend", ci=None, worst_year="2024")
    cause, _ = infer_probable_cause(0.6, 0.4, t, "2022")
    assert cause is ProbableCause.MIXED


def test_cause_none_when_not_degraded():
    cause, _ = infer_probable_cause(0.2, 0.9, None, "2022")
    assert cause is ProbableCause.NONE


# ── build_risk_brief ─────────────────────────────────────────────────────────

def _fixture():
    scores = [
        RiskScore("high_risk", 0.82, RiskComponents(0.75, 0.65, 0.5), {}),
        RiskScore("climate_case", 0.55, RiskComponents(0.6, 0.2, 0.4), {}),
        RiskScore("calm", 0.10, RiskComponents(0.1, 0.1, 0.1), {}),
    ]
    alerts = [
        Alert(
            "high_risk", AlertLevel.CRITICAL_INTERVENTION, 0.82, [],
            ["Inspección urgente"],
        ),
        Alert(
            "climate_case", AlertLevel.URGENT_MONITORING, 0.55, [],
            ["Monitorizar mensualmente"],
        ),
        Alert("calm", AlertLevel.NORMAL, 0.10, [], ["Sin acción"]),
    ]
    ranked = [
        RankedAsset(1, "high_risk", 0.82, 1.0, 100.0),
        RankedAsset(2, "climate_case", 0.55, 0.6, 66.0),
        RankedAsset(3, "calm", 0.10, 0.1, 33.0),
    ]
    trends = [
        _trend("high_risk", p_value=0.01, trend="decreasing", ci=(-0.003, -0.001)),
        _trend("climate_case", p_value=0.02, trend="decreasing", ci=(-0.002, -0.0005)),
    ]
    return scores, alerts, ranked, trends


def test_brief_filters_by_percentile_and_orders_by_rank():
    scores, alerts, ranked, trends = _fixture()
    brief = build_risk_brief(scores, alerts, ranked, trends, min_percentile=50.0)
    ids = [e["asset_id"] for e in brief["entries"]]
    assert ids == ["high_risk", "climate_case"]  # 'calm' below percentile 50
    assert brief["metadata"]["assets_in_brief"] == 2
    assert brief["metadata"]["assets_evaluated"] == 3


def test_brief_carries_confidence_and_cause():
    scores, alerts, ranked, trends = _fixture()
    brief = build_risk_brief(scores, alerts, ranked, trends, min_percentile=50.0)
    top = brief["entries"][0]
    assert top["confidence"] == Confidence.HIGH.value
    assert top["probable_cause"] == ProbableCause.TOURISM.value
    climate = brief["entries"][1]
    assert climate["probable_cause"] == ProbableCause.CLIMATE.value


def test_brief_budget_and_owner_optional():
    scores, alerts, ranked, trends = _fixture()
    brief = build_risk_brief(
        scores, alerts, ranked, trends,
        budgets={"high_risk": 12000.0},
        owners={"high_risk": "Guardería PNSG"},
        min_percentile=50.0,
    )
    assert brief["total_indicative_budget_eur"] == 12000.0
    top = brief["entries"][0]
    assert top["budget_eur"] == 12000.0
    assert top["owner"] == "Guardería PNSG"
    # missing budget/owner degrade explicitly, not fabricated
    assert brief["entries"][1]["budget_eur"] is None
    assert brief["entries"][1]["owner"] is None


def test_brief_handles_missing_trends_gracefully():
    scores, alerts, ranked, _ = _fixture()
    brief = build_risk_brief(scores, alerts, ranked, trends=None, min_percentile=50.0)
    assert all(e["confidence"] == Confidence.NO_DATA.value for e in brief["entries"])


def test_render_markdown_contains_director_columns():
    scores, alerts, ranked, trends = _fixture()
    brief = build_risk_brief(scores, alerts, ranked, trends, min_percentile=50.0)
    md = render_risk_brief_markdown(brief)
    assert "Informe de riesgo para dirección" in md
    for col in [
        "Estado ecológico", "Causa probable", "Confianza", "Prioridad", "Coste",
    ]:
        assert col in md
    assert "high_risk" in md
    assert "pendiente" in md  # climate_case has no budget → explicit placeholder
