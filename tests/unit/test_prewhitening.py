"""Tests de pre-whitening libre de tendencia (Yue-Pilon 2002).

Cubren ``src/time_series/prewhitening.py``: estimación de r1, la regla de
"solo blanquea si es significativo", la preservación de la tendencia y los
guardas de series cortas.
"""
from __future__ import annotations

import math

from src.time_series.mann_kendall import mann_kendall_test
from src.time_series.prewhitening import (
    lag1_autocorrelation,
    trend_free_prewhiten,
)

# ── lag1_autocorrelation ────────────────────────────────────────────────────────

def test_lag1_constant_series_is_zero():
    assert lag1_autocorrelation([5.0] * 10) == 0.0


def test_lag1_short_series_is_zero():
    assert lag1_autocorrelation([1.0]) == 0.0


def test_lag1_positive_for_persistent_series():
    # Serie suave (muestreo denso de un seno): puntos adyacentes muy próximos
    # → autocorrelación de lag-1 fuertemente positiva (≈ cos(0.3) ≈ 0.95).
    series = [math.sin(0.3 * t) for t in range(40)]
    assert lag1_autocorrelation(series) > 0.3


def test_lag1_alternating_series_is_negative():
    series = [1.0, -1.0] * 15
    assert lag1_autocorrelation(series) < -0.5


# ── trend_free_prewhiten ────────────────────────────────────────────────────────

def test_prewhiten_short_series_returns_unchanged():
    r = trend_free_prewhiten([1.0, 2.0, 3.0])
    assert r.applied is False
    assert r.series == [1.0, 2.0, 3.0]


def test_prewhiten_decision_matches_significance_rule():
    # Invariante Yue-Pilon paso 4: se blanquea SI y SOLO SI |r1| supera el
    # umbral de ruido blanco. Se verifica sobre ruido pseudoaleatorio.
    import random
    rng = random.Random(2024)
    series = [rng.gauss(0.0, 1.0) for _ in range(60)]
    r = trend_free_prewhiten(series)
    assert r.applied == (abs(r.lag1_autocorr) > r.significance_bound)
    if not r.applied:
        assert r.series == series      # serie intacta cuando no es significativo


def test_prewhiten_ar1_is_applied_and_shortens_series():
    phi, x, series = 0.85, 0.0, []
    for i in range(40):
        e = math.sin(i) * 0.1        # excitación determinista, autocorrelada vía AR
        x = phi * x + e
        series.append(x)
    r = trend_free_prewhiten(series)
    assert r.applied is True
    assert r.lag1_autocorr > r.significance_bound
    assert r.n_out == r.n_in - 1     # se elimina el primer punto al quitar AR(1)


def test_prewhiten_preserves_linear_trend():
    # Tendencia lineal + AR(1): la pendiente debe sobrevivir al pre-whitening
    # (esa es la ventaja "trend-free" frente al blanqueado ingenuo).
    phi, x, series = 0.7, 0.0, []
    for t in range(48):
        x = phi * x + 0.05
        series.append(0.02 * t + x)
    r = trend_free_prewhiten(series)
    mk_after = mann_kendall_test(r.series)
    assert mk_after.trend_direction == "increasing"
    assert mk_after.sens_slope > 0
