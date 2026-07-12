"""Tests de la cadena compartida desestacionalización + Mann-Kendall.

Cubren ``src/time_series/trend_detection.py`` — la única fuente de verdad usada
por el pipeline offline y el pipeline en vivo.
"""
from __future__ import annotations

import math

from src.time_series.decomposition import harmonic_decompose
from src.time_series.mann_kendall import mann_kendall_test
from src.time_series.trend_detection import deseasonalized_mann_kendall


def _seasonal_with_trend(n=60, slope=0.002):
    return [0.4 + slope * t + 0.1 * math.sin(2 * math.pi * t / 12) for t in range(n)]


def test_deseasonalises_when_full_cycle_available():
    tr = deseasonalized_mann_kendall(_seasonal_with_trend())
    assert tr.deseasonalised is True
    assert tr.seasonality_strength is not None
    # sin pre-whitening la serie testada es la desestacionalizada
    assert tr.tested_series == tr.deseasonalized_series
    assert tr.prewhitened is False


def test_matches_mann_kendall_on_deseasonalized_series():
    series = _seasonal_with_trend()
    tr = deseasonalized_mann_kendall(series)
    expected = mann_kendall_test(harmonic_decompose(series, period=12).deseasonalized)
    assert tr.mk == expected


def test_detects_upward_trend_through_seasonality():
    tr = deseasonalized_mann_kendall(_seasonal_with_trend(slope=0.004))
    assert tr.mk.trend_direction == "increasing"
    assert tr.mk.is_significant is True


def test_short_series_uses_raw_not_deseasonalised():
    tr = deseasonalized_mann_kendall([0.4, 0.41, 0.39, 0.42, 0.43, 0.40])  # n<12
    assert tr.deseasonalised is False
    assert tr.seasonality_strength is None
    assert tr.tested_series == [0.4, 0.41, 0.39, 0.42, 0.43, 0.40]


def test_prewhiten_flag_records_provenance():
    tr = deseasonalized_mann_kendall(_seasonal_with_trend(), prewhiten=True)
    # applied depende de si el lag-1 residual es significativo; el flag debe ser
    # coherente con que la serie testada cambie sólo cuando se aplica.
    if tr.prewhitened:
        assert tr.lag1_autocorr is not None
        assert tr.tested_series != tr.deseasonalized_series
    else:
        assert tr.tested_series == tr.deseasonalized_series
