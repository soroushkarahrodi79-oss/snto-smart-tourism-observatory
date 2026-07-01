"""Tests de intervalos de confianza (Gilbert 1987 + bootstrap de bloques).

Cubren ``src/time_series/confidence.py``.
"""
from __future__ import annotations

from src.time_series.confidence import (
    block_bootstrap_ci,
    sens_slope_ci,
)
from src.time_series.mann_kendall import mann_kendall_test

# ── sens_slope_ci ───────────────────────────────────────────────────────────────

def test_ci_brackets_point_estimate():
    series = [0.1 * t + (0.05 if t % 2 else -0.05) for t in range(30)]
    ci = sens_slope_ci(series)
    assert ci.lower <= ci.slope <= ci.upper
    assert ci.lower < ci.upper


def test_ci_slope_matches_mann_kendall():
    series = [0.03 * t + (0.02 if t % 3 == 0 else -0.01) for t in range(40)]
    ci = sens_slope_ci(series)
    mk = mann_kendall_test(series)
    assert ci.slope == mk.sens_slope


def test_ci_positive_trend_excludes_zero():
    # Tendencia fuerte y limpia → el IC 95 % no debe incluir 0.
    series = [0.5 * t for t in range(20)]
    ci = sens_slope_ci(series)
    assert ci.lower > 0.0


def test_ci_flat_noisy_series_includes_zero():
    series = [(1 if t % 2 else -1) * 0.1 for t in range(24)]
    ci = sens_slope_ci(series)
    assert ci.lower <= 0.0 <= ci.upper


def test_ci_degenerate_short_series():
    ci = sens_slope_ci([1.0, 2.0])
    # 1 pendiente → sin varianza utilizable, intervalo degenerado.
    assert ci.lower == ci.slope == ci.upper


def test_ci_empty_series():
    ci = sens_slope_ci([])
    assert ci.n_pairs == 0
    assert ci.slope == 0.0


# ── block_bootstrap_ci ──────────────────────────────────────────────────────────

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def test_bootstrap_reproducible_with_seed():
    series = [float(t % 7) for t in range(50)]
    a = block_bootstrap_ci(series, _mean, n_boot=200, seed=42)
    b = block_bootstrap_ci(series, _mean, n_boot=200, seed=42)
    assert (a.lower, a.upper) == (b.lower, b.upper)


def test_bootstrap_brackets_point():
    series = [float(t % 5) + 0.3 for t in range(60)]
    ci = block_bootstrap_ci(series, _mean, n_boot=300, seed=1)
    assert ci.lower <= ci.point <= ci.upper


def test_bootstrap_constant_series_zero_width():
    ci = block_bootstrap_ci([2.0] * 30, _mean, n_boot=100, seed=0)
    assert ci.lower == ci.upper == 2.0


def test_bootstrap_short_series_guard():
    ci = block_bootstrap_ci([1.0, 2.0, 3.0], _mean, n_boot=100)
    assert ci.n_boot == 0
    assert ci.lower == ci.upper == ci.point


def test_bootstrap_default_block_len():
    series = [float(t) for t in range(27)]   # n^(1/3) = 3
    ci = block_bootstrap_ci(series, _mean, n_boot=50, seed=0)
    assert ci.block_len == 3
