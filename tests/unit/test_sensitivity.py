"""F4 — Weight sensitivity, ranking stability and Monte-Carlo uncertainty."""
from __future__ import annotations

import pytest

from src.analysis.sensitivity import (
    deficit,
    monte_carlo_ci,
    ranking_stability,
    stress_score,
    weight_band,
)


def test_deficit_formula_and_clamping():
    assert deficit(0.9, 0.9, 0.1) == 0.0          # at healthy reference
    assert deficit(0.1, 0.9, 0.1) == 1.0          # at degraded floor
    assert deficit(0.5, 0.9, 0.1) == pytest.approx(0.5)
    assert deficit(1.5, 0.9, 0.1) == 0.0          # above reference → clamped
    assert deficit(0.5, 0.5, 0.5) == 0.0          # degenerate baseline==floor


def test_stress_score_weight_extremes():
    assert stress_score(1.0, 0.0, w_ndvi=1.0) == 100.0   # all NDVI
    assert stress_score(1.0, 0.0, w_ndvi=0.0) == 0.0     # all NDMI


def test_weight_band_zero_spread_when_deficits_equal():
    band = weight_band(0.5, 0.5)
    assert band.spread == 0.0          # weight choice irrelevant when equal
    assert band.min_score == band.max_score


def test_weight_band_has_spread_when_deficits_differ():
    band = weight_band(0.8, 0.2, w_min=0.4, w_max=0.6)
    assert band.spread > 0.0
    assert band.min_score <= band.mean_score <= band.max_score


def test_ranking_stability_flags_robust_leader():
    items = [
        ("dominant", 0.95, 0.92),   # high on both → always rank 1
        ("mid", 0.50, 0.55),
        ("low", 0.10, 0.12),
    ]
    res = {r.item_id: r for r in ranking_stability(items, top_n=1)}
    assert res["dominant"].best_rank == 1 and res["dominant"].worst_rank == 1
    assert res["dominant"].robust_top_n is True
    assert res["low"].robust_top_n is False


def test_ranking_stability_detects_weight_dependent_flip():
    # Two items that swap depending on whether NDVI or NDMI is weighted more.
    items = [
        ("ndvi_heavy", 0.80, 0.30),
        ("ndmi_heavy", 0.30, 0.80),
    ]
    res = {r.item_id: r for r in ranking_stability(items, top_n=1, w_min=0.3, w_max=0.7)}
    # Neither is a robust sole leader: each is rank 1 for some weights, 2 for others.
    assert res["ndvi_heavy"].best_rank == 1 and res["ndvi_heavy"].worst_rank == 2
    assert res["ndmi_heavy"].best_rank == 1 and res["ndmi_heavy"].worst_rank == 2
    assert res["ndvi_heavy"].robust_top_n is False


def test_monte_carlo_ci_is_ordered_and_deterministic():
    ci1 = monte_carlo_ci(0.6, 0.4, w_ndvi=0.5, sigma=0.05, n=1500, seed=7)
    ci2 = monte_carlo_ci(0.6, 0.4, w_ndvi=0.5, sigma=0.05, n=1500, seed=7)
    assert ci1 == ci2                       # seeded → reproducible
    assert ci1.p5 <= ci1.p50 <= ci1.p95
    assert ci1.p5 < ci1.p95                 # noise produces a real interval
