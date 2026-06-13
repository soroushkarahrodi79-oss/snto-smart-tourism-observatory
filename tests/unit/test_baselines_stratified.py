"""F4 — Stratified spectral baselines."""
from __future__ import annotations

import pytest

from src.risk_engine.baselines import compute_stratified_baselines


def _vals(center: float, n: int) -> list[float]:
    # deterministic spread around a center, width 0.1
    return [center - 0.05 + 0.1 * i / (n - 1) for i in range(n)]


def test_pooled_baseline_spans_full_distribution():
    values = _vals(0.6, 200)
    strata = ["A"] * 200
    bs = compute_stratified_baselines(values, strata)
    assert bs.pooled.p_base > bs.pooled.p_floor
    assert bs.pooled.n == 200


def test_depressed_stratum_gets_its_own_lower_reference():
    """The core F4 point: a regionally stressed habitat is compared against its
    own healthy reference, not the (higher) scene-wide P90."""
    healthy = _vals(0.75, 200)   # stratum A: vigorous
    stressed = _vals(0.35, 200)  # stratum B: depressed
    values = healthy + stressed
    strata = ["A"] * 200 + ["B"] * 200
    bs = compute_stratified_baselines(values, strata)
    assert bs.by_stratum["B"].p_base < bs.pooled.p_base
    assert bs.by_stratum["A"].p_base > bs.by_stratum["B"].p_base
    assert not bs.by_stratum["A"].fell_back


def test_small_stratum_falls_back_to_pooled():
    values = _vals(0.6, 200) + [0.2, 0.21, 0.22]  # tiny stratum "rare"
    strata = ["A"] * 200 + ["rare"] * 3
    bs = compute_stratified_baselines(values, strata, min_pixels=100)
    rare = bs.by_stratum["rare"]
    assert rare.fell_back is True
    assert rare.p_base == bs.pooled.p_base and rare.p_floor == bs.pooled.p_floor


def test_for_stratum_falls_back_for_unknown_or_none():
    bs = compute_stratified_baselines(_vals(0.6, 200), ["A"] * 200)
    assert bs.for_stratum(None) is bs.pooled
    assert bs.for_stratum("does-not-exist") is bs.pooled
    assert bs.for_stratum("A").stratum == "A"


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        compute_stratified_baselines([0.1, 0.2], ["A"])


def test_insufficient_pool_raises():
    with pytest.raises(ValueError):
        compute_stratified_baselines([0.5] * 10, ["A"] * 10, min_pixels=100)
