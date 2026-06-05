from __future__ import annotations

import pytest
from src.time_series.mann_kendall import (
    MannKendallResult,
    classify_trend_severity,
    mann_kendall_test,
)


def test_strongly_increasing_series_is_significant():
    series = [float(i) for i in range(1, 49)]
    result = mann_kendall_test(series)
    assert result.is_significant
    assert result.trend_direction == "increasing"
    assert result.sens_slope > 0


def test_strongly_decreasing_series_is_significant():
    series = [float(48 - i) for i in range(48)]
    result = mann_kendall_test(series)
    assert result.is_significant
    assert result.trend_direction == "decreasing"
    assert result.sens_slope < 0


def test_flat_series_no_trend():
    series = [0.35] * 48
    result = mann_kendall_test(series)
    assert not result.is_significant
    assert result.trend_direction == "no_trend"


def test_noisy_flat_series_likely_no_trend():
    import math
    series = [0.35 + 0.01 * math.sin(2 * math.pi * i / 12) for i in range(48)]
    result = mann_kendall_test(series)
    assert result.trend_direction == "no_trend"


def test_p_value_in_range():
    series = [0.3 + 0.001 * i for i in range(48)]
    result = mann_kendall_test(series)
    assert 0.0 <= result.p_value <= 1.0


def test_kendalls_tau_in_range():
    series = [float(i) for i in range(20)]
    result = mann_kendall_test(series)
    assert -1.0 <= result.kendalls_tau <= 1.0


def test_short_series_returns_safe_default():
    result = mann_kendall_test([0.3, 0.4, 0.2])
    assert result.trend_direction == "no_trend"
    assert result.p_value == 1.0


def test_classify_stable_when_not_significant():
    result = MannKendallResult(
        s_statistic=10, z_score=0.5, p_value=0.62, kendalls_tau=0.05,
        sens_slope=-0.001, trend_direction="no_trend", is_significant=False,
        alpha=0.05, n=48,
    )
    assert classify_trend_severity(result) == "stable"


def test_classify_improving_when_significant_positive():
    result = MannKendallResult(
        s_statistic=500, z_score=3.2, p_value=0.001, kendalls_tau=0.42,
        sens_slope=0.003, trend_direction="increasing", is_significant=True,
        alpha=0.05, n=48,
    )
    assert classify_trend_severity(result) == "improving"


def test_classify_strongly_degrading():
    result = MannKendallResult(
        s_statistic=-600, z_score=-3.8, p_value=0.0001, kendalls_tau=-0.51,
        sens_slope=-0.008, trend_direction="decreasing", is_significant=True,
        alpha=0.05, n=48,
    )
    assert classify_trend_severity(result) == "strongly_degrading"


def test_classify_mild_degradation():
    result = MannKendallResult(
        s_statistic=-200, z_score=-2.1, p_value=0.036, kendalls_tau=-0.17,
        sens_slope=-0.001, trend_direction="decreasing", is_significant=True,
        alpha=0.05, n=48,
    )
    assert classify_trend_severity(result) == "mild_degradation"
