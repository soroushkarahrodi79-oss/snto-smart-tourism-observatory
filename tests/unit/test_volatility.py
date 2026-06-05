from __future__ import annotations

import math

from src.time_series.volatility import (
    compute_coefficient_of_variation,
    compute_deseasonalized_volatility,
    compute_volatility,
)


def test_single_element_returns_zero():
    assert compute_volatility([0.5]) == 0.0


def test_empty_series_returns_zero():
    assert compute_volatility([]) == 0.0


def test_known_volatility():
    # Population std of [0.2, 0.4, 0.6, 0.8] = 0.2236...
    series = [0.2, 0.4, 0.6, 0.8]
    result = compute_volatility(series)
    mean = sum(series) / len(series)
    expected = math.sqrt(sum((x - mean) ** 2 for x in series) / len(series))
    assert abs(result - expected) < 1e-10


def test_constant_series_zero_volatility():
    assert compute_volatility([0.42] * 12) == 0.0


def test_cv_zero_mean_returns_zero():
    assert compute_coefficient_of_variation([0.0, 0.0]) == 0.0


def test_cv_proportional():
    series = [1.0, 2.0, 3.0, 4.0]
    cv = compute_coefficient_of_variation(series)
    assert cv > 0


# ── Deseasonalized volatility ─────────────────────────────────────────────

def test_perfect_seasonal_signal_near_zero_residual():
    # Pure sine wave: deseasonalized std should be ~0
    import math
    series = [0.5 + 0.2 * math.sin(2 * math.pi * (t - 4) / 12) for t in range(1, 13)]
    result = compute_deseasonalized_volatility(series)
    assert result < 0.01  # residuals after removing the fitted sinusoid approach 0


def test_disturbed_series_higher_than_smooth():
    import math
    # Smooth seasonal base
    smooth = [0.5 + 0.2 * math.sin(2 * math.pi * (t - 4) / 12) for t in range(1, 13)]
    # Same series with a sharp disturbance spike in month 6
    disturbed = smooth[:]
    disturbed[5] -= 0.15  # sudden NDVI drop (e.g. fire scar, construction)
    assert compute_deseasonalized_volatility(disturbed) > compute_deseasonalized_volatility(smooth)


def test_deseasonalized_returns_float():
    series = [0.4 + 0.1 * i / 12 for i in range(12)]
    result = compute_deseasonalized_volatility(series)
    assert isinstance(result, float)
    assert result >= 0.0


def test_deseasonalized_short_series_falls_back():
    # Less than 4 elements → falls back to raw volatility
    short = [0.3, 0.5]
    assert compute_deseasonalized_volatility(short) == compute_volatility(short)
