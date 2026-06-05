from __future__ import annotations

from src.risk_engine.ehs import EHSComponents, compute_ehs, interpret_ehs
from src.time_series.mann_kendall import MannKendallResult


def _stable_mk():
    return MannKendallResult(
        s_statistic=10, z_score=0.5, p_value=0.62, kendalls_tau=0.05,
        sens_slope=-0.001, trend_direction="no_trend", is_significant=False,
        alpha=0.05, n=48,
    )


def _declining_mk():
    return MannKendallResult(
        s_statistic=-500, z_score=-3.2, p_value=0.001, kendalls_tau=-0.42,
        sens_slope=-0.007, trend_direction="decreasing", is_significant=True,
        alpha=0.05, n=48,
    )


def test_ehs_in_range():
    comp = compute_ehs(
        mean_ndvi=0.32, mk_result=_stable_mk(),
        n_anomalous_months=6, n_total_months=48,
        pre_drought_ndvi=0.35, post_drought_ndvi=0.33,
        residual_std=0.025,
    )
    assert 0.0 <= comp.ehs <= 100.0


def test_excellent_site_scores_high():
    comp = compute_ehs(
        mean_ndvi=0.58,
        mk_result=MannKendallResult(
            s_statistic=50, z_score=0.8, p_value=0.42, kendalls_tau=0.08,
            sens_slope=0.0005, trend_direction="no_trend", is_significant=False,
            alpha=0.05, n=48,
        ),
        n_anomalous_months=1, n_total_months=48,
        residual_std=0.010,
    )
    assert comp.ehs >= 75


def test_degraded_site_scores_low():
    comp = compute_ehs(
        mean_ndvi=0.20, mk_result=_declining_mk(),
        n_anomalous_months=20, n_total_months=48,
        pre_drought_ndvi=0.40, post_drought_ndvi=0.15,
        residual_std=0.06,
    )
    assert comp.ehs < 50


def test_trend_risk_zero_when_not_significant():
    comp = compute_ehs(
        mean_ndvi=0.35, mk_result=_stable_mk(),
        n_anomalous_months=3, n_total_months=48,
        residual_std=0.020,
    )
    assert comp.trend_risk == 0.0


def test_trend_risk_positive_for_significant_decline():
    comp = compute_ehs(
        mean_ndvi=0.35, mk_result=_declining_mk(),
        n_anomalous_months=3, n_total_months=48,
        residual_std=0.020,
    )
    assert comp.trend_risk > 0.0


def test_recovery_risk_low_for_full_recovery():
    comp = compute_ehs(
        mean_ndvi=0.35, mk_result=_stable_mk(),
        n_anomalous_months=5, n_total_months=48,
        pre_drought_ndvi=0.35, post_drought_ndvi=0.36,
        residual_std=0.025,
    )
    assert comp.recovery_risk < 0.10


def test_interpret_ehs_labels():
    assert interpret_ehs(95) == "Excellent"
    assert interpret_ehs(80) == "Good"
    assert interpret_ehs(65) == "Moderate"
    assert interpret_ehs(50) == "Poor"
    assert interpret_ehs(30) == "Critical"


def test_components_sum_consistent():
    comp = compute_ehs(
        mean_ndvi=0.32, mk_result=_stable_mk(),
        n_anomalous_months=6, n_total_months=48,
        pre_drought_ndvi=0.35, post_drought_ndvi=0.33,
        residual_std=0.025,
    )
    # EHS = 100 * (1 - composite_risk)
    assert abs(comp.ehs - 100 * (1 - comp.composite_risk)) < 0.2
