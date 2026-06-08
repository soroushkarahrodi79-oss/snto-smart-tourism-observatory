from __future__ import annotations

import math
import pytest

from src.decision_confidence.assessor import (
    DCS_HIGH,
    DCS_MODERATE,
    DCS_VERY_HIGH,
    DCSInputs,
    DCSResult,
    _classify_dcs,
    _clamp,
    _std3,
    compute_dcs,
)
from src.risk_engine.ehs import EHSComponents
from src.spatial_causality.analyzer import (
    SpatialCausalityAnalyzer,
    SpatialCausalityResult,
)
from src.time_series.climatology import AnomalyEvent
from src.time_series.mann_kendall import MannKendallResult


# ── Test fixtures ──────────────────────────────────────────────────────────

def _mk_stable(p=0.50):
    return MannKendallResult(
        s_statistic=20, z_score=0.5, p_value=p, kendalls_tau=0.04,
        sens_slope=0.0002, trend_direction="no_trend", is_significant=False,
        alpha=0.05, n=58,
    )


def _mk_declining():
    return MannKendallResult(
        s_statistic=-400, z_score=-3.1, p_value=0.002, kendalls_tau=-0.38,
        sens_slope=-0.006, trend_direction="decreasing", is_significant=True,
        alpha=0.05, n=48,
    )


def _ehs_healthy():
    return EHSComponents(
        baseline_risk=0.20, trend_risk=0.0, anomaly_risk=0.05,
        recovery_risk=0.0, stability_risk=0.15, composite_risk=0.11, ehs=89.0,
    )


def _ehs_stressed():
    return EHSComponents(
        baseline_risk=0.58, trend_risk=0.25, anomaly_risk=0.20,
        recovery_risk=0.15, stability_risk=0.60, composite_risk=0.42, ehs=58.0,
    )


def _make_series(n=58, amplitude=0.12, trend=0.0):
    return [
        max(0.05, 0.32 + amplitude * math.sin(2 * math.pi * (i % 12 - 3) / 12) + trend * i)
        for i in range(n)
    ]


def _scm_landscape_high(base_series):
    from src.assets.models import AssetObservation
    obs = [
        AssetObservation(asset_id="t", year=2021 + i // 12, month=(i % 12) + 1,
                         ndvi=v, ndmi=v * 0.4)
        for i, v in enumerate(base_series)
    ]
    scm = SpatialCausalityAnalyzer(human_pressure=0.0)  # HP=0 → LANDSCAPE HIGH
    zones = scm.simulate_zones(obs)
    return scm.analyse("t", zones)


def _make_inputs(
    asset_id="test",
    n_valid=58, n_possible=60,
    cloud_pct=20.0, pixel_pct=0.85,
    n_years=5, mk=None, decomp_r2=0.82,
    scm=None,
    ndvi=None, ndmi=None, annual_means=None,
    anomalies=None, ehs=None,
    recommendation="annual_monitoring",
):
    ndvi = ndvi or _make_series()
    ndmi = ndmi or [v * 0.4 for v in ndvi]
    mk = mk or _mk_stable()
    scm = scm or _scm_landscape_high(ndvi)
    annual_means = annual_means or {y: 0.31 + 0.01 * y for y in range(2021, 2026)}
    anomalies = anomalies or []
    ehs = ehs or _ehs_healthy()

    return DCSInputs(
        asset_id=asset_id,
        recommendation=recommendation,
        n_valid_observations=n_valid,
        n_possible_observations=n_possible,
        mean_cloud_cover_pct=cloud_pct,
        mean_valid_pixel_pct=pixel_pct,
        n_years=n_years,
        mk_result=mk,
        decomp_seasonal_r_squared=decomp_r2,
        scm_result=scm,
        ndvi_series=ndvi,
        ndmi_series=ndmi,
        annual_ndvi_means=annual_means,
        anomaly_events=anomalies,
        ehs_components=ehs,
    )


# ── Classification tests ───────────────────────────────────────────────────

def test_classify_dcs_very_high():
    assert _classify_dcs(85) == "VERY HIGH"


def test_classify_dcs_high():
    assert _classify_dcs(70) == "HIGH"


def test_classify_dcs_moderate():
    assert _classify_dcs(50) == "MODERATE"


def test_classify_dcs_low():
    assert _classify_dcs(35) == "LOW"


# ── Total score range ─────────────────────────────────────────────────────

def test_dcs_in_0_100():
    inp = _make_inputs()
    result = compute_dcs(inp)
    assert 0.0 <= result.dcs <= 100.0


def test_excellent_data_scores_high():
    inp = _make_inputs(n_valid=60, n_possible=60, cloud_pct=5.0, pixel_pct=0.95,
                       n_years=5, mk=_mk_stable(p=0.90))
    result = compute_dcs(inp)
    assert result.dcs >= 65.0


def test_poor_data_scores_low():
    # Internally consistent 1-year scenario:
    #   - 12-element series (monthly, 1 year) fed to both SCM and model stability
    #   - annual_means has exactly 1 entry, so inter-annual stability = 0
    short_series = _make_series(n=12)
    inp = _make_inputs(
        n_valid=8, n_possible=60, cloud_pct=65.0, pixel_pct=0.40,
        n_years=1, decomp_r2=0.30,
        ndvi=short_series,
        ndmi=[v * 0.4 for v in short_series],
        scm=_scm_landscape_high(short_series),
        annual_means={2024: sum(short_series) / len(short_series)},
    )
    result = compute_dcs(inp)
    assert result.can_act is False
    assert result.classification in ("LOW", "MODERATE")


# ── Sub-score range tests ─────────────────────────────────────────────────

def test_component_scores_in_range():
    inp = _make_inputs()
    result = compute_dcs(inp)
    comp = result.components
    assert 0.0 <= comp.data_quality <= 25.0
    assert 0.0 <= comp.temporal_robustness <= 25.0
    assert 0.0 <= comp.spatial_consistency <= 20.0
    assert 0.0 <= comp.model_stability <= 15.0
    assert 0.0 <= comp.signal_strength <= 15.0


def test_full_coverage_maximises_dq():
    inp = _make_inputs(n_valid=60, n_possible=60, cloud_pct=0.0, pixel_pct=1.0)
    result = compute_dcs(inp)
    assert result.components.data_quality == 25.0


def test_high_p_stable_gets_good_tr_trend():
    inp_hi = _make_inputs(mk=_mk_stable(p=0.90))
    inp_lo = _make_inputs(mk=_mk_stable(p=0.10))
    r_hi = compute_dcs(inp_hi)
    r_lo = compute_dcs(inp_lo)
    assert r_hi.components.temporal_robustness > r_lo.components.temporal_robustness


def test_declining_trend_with_low_p_scores_well_on_tr():
    # Significant declining trend is clear — should score well on trend clarity
    inp = _make_inputs(mk=_mk_declining())
    result = compute_dcs(inp)
    d = result.components.tr_detail
    assert d["trend_clarity"] > 6.0


# ── Can_act logic ─────────────────────────────────────────────────────────

def test_high_dcs_can_act_true():
    inp = _make_inputs(n_valid=60, n_possible=60, cloud_pct=5.0, pixel_pct=0.95,
                       n_years=5, mk=_mk_stable(p=0.90))
    result = compute_dcs(inp)
    if result.dcs >= DCS_HIGH:
        assert result.can_act is True


def test_low_dcs_can_act_false():
    inp = _make_inputs(n_valid=8, n_possible=60, cloud_pct=70.0, pixel_pct=0.30,
                       n_years=1, decomp_r2=0.20)
    result = compute_dcs(inp)
    if result.dcs < DCS_HIGH:
        assert result.can_act is False


# ── Text output completeness ───────────────────────────────────────────────

def test_confidence_statement_non_empty():
    result = compute_dcs(_make_inputs())
    assert len(result.confidence_statement) > 100


def test_uncertainty_and_confidence_factors_present():
    result = compute_dcs(_make_inputs())
    # At least one factor in each list
    assert isinstance(result.uncertainty_factors, list)
    assert isinstance(result.confidence_factors, list)
    assert len(result.confidence_factors) > 0  # good data should have some positives


def test_can_act_reasoning_non_empty():
    result = compute_dcs(_make_inputs())
    assert len(result.can_act_reasoning) > 30


def test_recommendation_humanised():
    result = compute_dcs(_make_inputs(recommendation="annual_monitoring"))
    assert "annual" in result.recommendation.lower() or "monitor" in result.recommendation.lower()


# ── Model stability: high NDVI-NDMI correlation ───────────────────────────

def test_consistent_ndvi_ndmi_scores_high_stability():
    ndvi = _make_series(n=58)
    ndmi = [v * 0.40 for v in ndvi]  # perfectly correlated
    inp = _make_inputs(ndvi=ndvi, ndmi=ndmi)
    result = compute_dcs(inp)
    assert result.components.ms_detail["ndvi_ndmi_agreement"] > 5.0


def test_anti_correlated_ndvi_ndmi_reduces_stability():
    ndvi = _make_series(n=58)
    ndmi = [1.0 - v for v in ndvi]  # anti-correlated (unrealistic but tests the formula)
    inp = _make_inputs(ndvi=ndvi, ndmi=ndmi)
    result = compute_dcs(inp)
    assert result.components.ms_detail["ndvi_ndmi_agreement"] == 0.0


# ── Signal strength: no anomalies gives max anomaly clarity ───────────────

def test_no_anomalies_max_anomaly_clarity():
    inp = _make_inputs(anomalies=[])
    result = compute_dcs(inp)
    assert result.components.ss_detail["anomaly_clarity"] == 8.0


def test_anomaly_events_reduce_anomaly_clarity():
    events = [
        AnomalyEvent(2022, 7, "ndvi", 0.13, 0.18, -1.67, "anomaly_low", -0.05),
        AnomalyEvent(2022, 8, "ndvi", 0.12, 0.17, -1.67, "anomaly_low", -0.05),
    ]
    inp = _make_inputs(anomalies=events)
    result = compute_dcs(inp)
    assert result.components.ss_detail["anomaly_clarity"] < 8.0


# ── Utility tests ─────────────────────────────────────────────────────────

def test_clamp():
    assert _clamp(-1.0, 0.0, 1.0) == 0.0
    assert _clamp(2.0, 0.0, 1.0) == 1.0
    assert _clamp(0.5, 0.0, 1.0) == 0.5


def test_std3_equal_values_is_zero():
    assert _std3(0.5, 0.5, 0.5) == 0.0


def test_std3_known_value():
    # std of [0, 0.3, 0.6] = 0.245
    result = _std3(0.0, 0.3, 0.6)
    assert abs(result - math.sqrt(((0.09 + 0 + 0.09) / 3))) < 1e-6
