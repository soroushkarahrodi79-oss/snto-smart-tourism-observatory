from __future__ import annotations

import math
import pytest
from src.time_series.decomposition import (
    DecompositionResult,
    harmonic_decompose,
    interpret_seasonality_strength,
)


def _make_seasonal(n=48, amplitude=0.15, trend_slope=0.0, noise=0.0):
    import random
    series = []
    for t in range(n):
        val = (0.35
               + trend_slope * t
               + amplitude * math.sin(2 * math.pi * (t % 12 - 3) / 12))
        series.append(val)
    return series


def test_residuals_near_zero_for_pure_seasonal():
    series = _make_seasonal(n=48, amplitude=0.15, trend_slope=0.0)
    result = harmonic_decompose(series)
    assert result.residual_std < 0.01


def test_trend_extracted_correctly():
    # Series with known linear trend + seasonal
    series = _make_seasonal(n=48, amplitude=0.10, trend_slope=-0.001)
    result = harmonic_decompose(series)
    # Slope should be approximately -0.001
    assert abs(result.trend_slope - (-0.001)) < 0.0005


def test_seasonal_amplitude_captured():
    series = _make_seasonal(n=48, amplitude=0.20)
    result = harmonic_decompose(series)
    seasonal_amp = max(result.seasonal) - min(result.seasonal)
    assert seasonal_amp > 0.25  # 2 × amplitude


def test_r_squared_high_for_seasonal_signal():
    series = _make_seasonal(n=48, amplitude=0.15)
    result = harmonic_decompose(series)
    assert result.r_squared > 0.85


def test_seasonality_strength_high_for_seasonal_data():
    series = _make_seasonal(n=48, amplitude=0.15)
    result = harmonic_decompose(series)
    assert result.seasonality_strength > 0.80


def test_deseasonalized_is_trend_plus_residual():
    series = _make_seasonal(n=48)
    result = harmonic_decompose(series)
    for i, (o, s) in enumerate(zip(result.observed, result.seasonal)):
        expected = result.trend[i] + result.residual[i]
        actual_deseasonalized = result.deseasonalized[i]
        assert abs(actual_deseasonalized - (o - s)) < 1e-9


def test_raises_on_series_shorter_than_period():
    with pytest.raises(ValueError, match="shorter than the seasonal period"):
        harmonic_decompose([0.3, 0.4, 0.5], period=12)


def test_interpretation_dominant():
    assert interpret_seasonality_strength(0.95) == "dominant"


def test_interpretation_strong():
    assert interpret_seasonality_strength(0.75) == "strong"


def test_interpretation_weak():
    assert interpret_seasonality_strength(0.40) == "weak"


def test_n_matches_series_length():
    series = _make_seasonal(n=60)
    result = harmonic_decompose(series)
    assert result.n == 60
    assert len(result.trend) == 60
    assert len(result.seasonal) == 60
    assert len(result.residual) == 60
