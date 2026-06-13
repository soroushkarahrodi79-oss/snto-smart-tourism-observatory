"""
SNTO — Weight Sensitivity & Uncertainty (F4)
============================================
Many SNTO constants are expert-based: the EHS index weights (W_NDVI = W_NDMI =
0.5), TPI component weights, etc. The audit's point is that a ranking is only
defensible if it is *stable* under reasonable perturbation of those weights:
"if the NDVI weight varies from 0.4 to 0.6, does this trail stay in the top 3?"

This module answers that, with pure functions (no I/O):

* ``deficit`` / ``stress_score`` mirror the operational Pipeline A formula
  (``calculate_delta_ehs``) so sensitivity is computed with the real model.
* ``weight_band`` sweeps the NDVI/NDMI weight split and returns the score range.
* ``ranking_stability`` reports, per item, the rank range across the weight grid
  and flags items that stay within the top-N for *every* weight (robust_top_n).
* ``monte_carlo_ci`` propagates input noise into a score confidence interval.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from typing import Optional, Sequence


def deficit(observed: float, baseline: float, floor: float) -> float:
    """Per-index deficit fraction, clamped to [0, 1] (mirrors Pipeline A).

    deficit = (baseline - observed) / (baseline - floor)
    0 → at/above the healthy reference; 1 → at/below the degraded floor.
    """
    if baseline == floor:
        return 0.0
    return max(0.0, min(1.0, (baseline - observed) / (baseline - floor)))


def stress_score(d_ndvi: float, d_ndmi: float, w_ndvi: float) -> float:
    """Composite stress score 0-100 for a given NDVI weight (w_ndmi = 1 - w_ndvi)."""
    w_ndvi = max(0.0, min(1.0, w_ndvi))
    w_ndmi = 1.0 - w_ndvi
    return round(100.0 * (w_ndvi * d_ndvi + w_ndmi * d_ndmi), 4)


def _weight_grid(w_min: float, w_max: float, steps: int) -> list[float]:
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if steps == 1:
        return [(w_min + w_max) / 2.0]
    span = w_max - w_min
    return [round(w_min + span * i / (steps - 1), 6) for i in range(steps)]


@dataclass(frozen=True)
class WeightBand:
    """Range of an item's stress score as the NDVI weight sweeps a grid."""
    min_score: float
    max_score: float
    mean_score: float
    spread: float          # max - min: how much the weight choice moves the score
    w_min: float
    w_max: float


def weight_band(
    d_ndvi: float,
    d_ndmi: float,
    w_min: float = 0.4,
    w_max: float = 0.6,
    steps: int = 9,
) -> WeightBand:
    """Stress-score band for one item across the NDVI weight range [w_min, w_max]."""
    grid = _weight_grid(w_min, w_max, steps)
    scores = [stress_score(d_ndvi, d_ndmi, w) for w in grid]
    lo, hi = min(scores), max(scores)
    return WeightBand(
        min_score=round(lo, 4),
        max_score=round(hi, 4),
        mean_score=round(statistics.fmean(scores), 4),
        spread=round(hi - lo, 4),
        w_min=w_min,
        w_max=w_max,
    )


@dataclass(frozen=True)
class RankStability:
    """How an item's rank moves across the weight grid (rank 1 = most stressed)."""
    item_id: str
    best_rank: int
    worst_rank: int
    modal_rank: int
    robust_top_n: bool   # worst_rank <= top_n across every weight tested


def ranking_stability(
    items: Sequence[tuple[str, float, float]],
    top_n: int = 3,
    w_min: float = 0.4,
    w_max: float = 0.6,
    steps: int = 9,
) -> list[RankStability]:
    """Assess rank stability of items under the NDVI weight sweep.

    Args:
        items: sequence of (item_id, d_ndvi, d_ndmi).
        top_n: an item is ``robust_top_n`` if its WORST rank across all tested
            weights is still within the top N (rank 1 = highest stress first).
        w_min, w_max, steps: NDVI weight grid.

    Returns:
        One RankStability per item, ordered by modal rank ascending.
    """
    grid = _weight_grid(w_min, w_max, steps)
    ids = [it[0] for it in items]
    # rank of each item at each weight (1 = most stressed)
    ranks_by_item: dict[str, list[int]] = {i: [] for i in ids}
    for w in grid:
        scored = [(it[0], stress_score(it[1], it[2], w)) for it in items]
        order = sorted(scored, key=lambda x: x[1], reverse=True)
        for rank, (item_id, _) in enumerate(order, start=1):
            ranks_by_item[item_id].append(rank)

    out: list[RankStability] = []
    for item_id, ranks in ranks_by_item.items():
        out.append(RankStability(
            item_id=item_id,
            best_rank=min(ranks),
            worst_rank=max(ranks),
            modal_rank=statistics.mode(ranks),
            robust_top_n=max(ranks) <= top_n,
        ))
    out.sort(key=lambda r: (r.modal_rank, r.worst_rank))
    return out


@dataclass(frozen=True)
class ScoreCI:
    """Monte-Carlo confidence interval of a stress score under input noise."""
    p5: float
    p50: float
    p95: float
    mean: float
    n: int


def monte_carlo_ci(
    d_ndvi: float,
    d_ndmi: float,
    w_ndvi: float = 0.5,
    sigma: float = 0.05,
    n: int = 2000,
    seed: Optional[int] = 42,
) -> ScoreCI:
    """Propagate Gaussian noise on the deficits into a stress-score CI.

    ``sigma`` is the 1-σ uncertainty on each (clamped) deficit — a proxy for
    spatial heterogeneity / pixel noise. Returns the 5th/50th/95th percentiles.
    """
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n):
        dn = max(0.0, min(1.0, d_ndvi + rng.gauss(0.0, sigma)))
        dm = max(0.0, min(1.0, d_ndmi + rng.gauss(0.0, sigma)))
        samples.append(stress_score(dn, dm, w_ndvi))
    samples.sort()

    def _pct(p: float) -> float:
        k = max(0, min(len(samples) - 1, int(round(p * (len(samples) - 1)))))
        return round(samples[k], 4)

    return ScoreCI(
        p5=_pct(0.05),
        p50=_pct(0.50),
        p95=_pct(0.95),
        mean=round(statistics.fmean(samples), 4),
        n=n,
    )
