from __future__ import annotations

from src.time_series.trend import TrendResult, compute_linear_trend, is_declining, is_rising


def test_rising_series_positive_slope():
    series = [0.1 * i for i in range(1, 13)]
    result = compute_linear_trend(series)
    assert result.slope > 0


def test_declining_series_negative_slope():
    series = [1.0 - 0.05 * i for i in range(12)]
    result = compute_linear_trend(series)
    assert result.slope < 0


def test_flat_series_near_zero_slope():
    series = [0.5] * 12
    result = compute_linear_trend(series)
    assert abs(result.slope) < 1e-10
    assert result.r_squared == 0.0


def test_single_element_returns_zero_slope():
    result = compute_linear_trend([0.42])
    assert result.slope == 0.0
    assert result.intercept == 0.42


def test_perfect_linear_r_squared():
    series = [0.1 + 0.05 * i for i in range(12)]
    result = compute_linear_trend(series)
    assert abs(result.r_squared - 1.0) < 1e-6


def test_is_rising_true():
    trend = TrendResult(slope=0.01, intercept=0.0, r_squared=0.9)
    assert is_rising(trend) is True


def test_is_rising_false_flat():
    trend = TrendResult(slope=0.001, intercept=0.0, r_squared=0.1)
    assert is_rising(trend) is False


def test_is_rising_false_negative():
    trend = TrendResult(slope=-0.01, intercept=0.0, r_squared=0.8)
    assert is_rising(trend) is False


def test_is_rising_requires_min_r_squared():
    # Positive slope but very low R² → not considered credible
    trend = TrendResult(slope=0.01, intercept=0.0, r_squared=0.10)
    assert is_rising(trend) is False


def test_is_declining_true():
    trend = TrendResult(slope=-0.01, intercept=0.0, r_squared=0.75)
    assert is_declining(trend) is True


def test_is_declining_false_positive_slope():
    trend = TrendResult(slope=0.01, intercept=0.0, r_squared=0.80)
    assert is_declining(trend) is False


def test_is_declining_requires_min_r_squared():
    trend = TrendResult(slope=-0.01, intercept=0.0, r_squared=0.10)
    assert is_declining(trend) is False
