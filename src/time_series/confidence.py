from __future__ import annotations

"""
Confidence intervals for trend magnitude and composite indicators.

A trend slope or an Environmental Health Score reported without an uncertainty
band is not defensible for public-administration decision making: it hides
whether "−0.003 NDVI/month" is a firm decline or noise. This module provides:

  1. sens_slope_ci  — the exact non-parametric confidence interval for Sen's
     slope (Gilbert 1987), the standard in environmental trend analysis
     (USGS, US-EPA). Deterministic, tie-aware, no resampling.
  2. block_bootstrap_ci — a moving-block bootstrap for arbitrary statistics
     (e.g. the EHS composite) where no closed-form interval exists. Blocks
     preserve short-range serial dependence that an i.i.d. bootstrap would
     destroy (Künsch 1989).

References
==========
  Gilbert, R.O. (1987). Statistical Methods for Environmental Pollution
    Monitoring, §16.4.2. Van Nostrand Reinhold. [Sen slope CI]
  Künsch, H.R. (1989). The jackknife and the bootstrap for general stationary
    observations. Annals of Statistics, 17(3), 1217-1241. [moving blocks]
"""

import math
import random
from dataclasses import dataclass
from statistics import NormalDist
from typing import Callable, Sequence, TypeVar

from src.time_series.mann_kendall import pairwise_slopes, variance_s

_T = TypeVar("_T")


@dataclass(frozen=True)
class SlopeCI:
    """Non-parametric confidence interval for Sen's slope."""

    slope: float          # Sen's slope point estimate (median of pairwise slopes)
    lower: float
    upper: float
    alpha: float          # 1 - confidence level (0.05 → 95% CI)
    n_pairs: int          # number of pairwise slopes (N')


@dataclass(frozen=True)
class BootstrapCI:
    """Percentile confidence interval from a moving-block bootstrap."""

    point: float
    lower: float
    upper: float
    alpha: float
    n_boot: int
    block_len: int


def _order_statistic(sorted_vals: list[float], rank: float) -> float:
    """Value at a 1-based fractional rank, linearly interpolated between order
    statistics. rank <= 1 → minimum; rank >= N → maximum."""
    n = len(sorted_vals)
    if rank <= 1:
        return sorted_vals[0]
    if rank >= n:
        return sorted_vals[-1]
    lo = int(math.floor(rank))
    frac = rank - lo
    return sorted_vals[lo - 1] + frac * (sorted_vals[lo] - sorted_vals[lo - 1])


def sens_slope_ci(series: list[float], alpha: float = 0.05) -> SlopeCI:
    """Exact non-parametric CI for Sen's slope (Gilbert 1987, §16.4.2).

    Given N' pairwise slopes and the tie-corrected Var(S):
        C_α = z_{1-α/2} · √Var(S)
        M1  = (N' − C_α) / 2
        M2  = (N' + C_α) / 2
    the lower/upper limits are the order statistics of the ranked slopes at
    ranks M1 and M2+1. Reduces to the Theil-Sen interval when there is no tie
    correction.

    Returns a degenerate interval (lower == upper == slope) when the series is
    too short for a meaningful slope population.
    """
    slopes = sorted(pairwise_slopes(series))
    n_pairs = len(slopes)
    if n_pairs == 0:
        return SlopeCI(slope=0.0, lower=0.0, upper=0.0, alpha=alpha, n_pairs=0)

    m = n_pairs
    if m % 2 == 1:
        slope = slopes[m // 2]
    else:
        slope = 0.5 * (slopes[m // 2 - 1] + slopes[m // 2])

    var_s = variance_s(series)
    if var_s <= 0 or n_pairs < 2:
        return SlopeCI(
            slope=slope, lower=slope, upper=slope, alpha=alpha, n_pairs=n_pairs
        )

    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    c_alpha = z * math.sqrt(var_s)
    m1 = (n_pairs - c_alpha) / 2.0
    m2 = (n_pairs + c_alpha) / 2.0

    lower = _order_statistic(slopes, m1)
    upper = _order_statistic(slopes, m2 + 1.0)
    return SlopeCI(slope=slope, lower=lower, upper=upper, alpha=alpha, n_pairs=n_pairs)


def block_bootstrap_ci(
    series: Sequence[_T],
    statistic: Callable[[Sequence[_T]], float],
    *,
    n_boot: int = 1000,
    block_len: int | None = None,
    alpha: float = 0.05,
    seed: int = 0,
) -> BootstrapCI:
    """Percentile CI for ``statistic`` via a moving-block bootstrap.

    Blocks of length ``block_len`` (default ⌈n^{1/3}⌉) are drawn with
    replacement and concatenated to a resample of the original length,
    preserving short-range dependence. ``seed`` makes the interval reproducible
    — important for a pipeline whose outputs feed institutional reports.

    ``series`` may hold any element type (floats, or richer records such as
    monthly observations): the blocks are resampled by position and ``statistic``
    reduces a resample to a scalar. Resampling whole records keeps the correlated
    channels (e.g. NDVI/NDMI/EVI of the same month) aligned, so a composite like
    the EHS can be bootstrapped end-to-end without breaking cross-index pairing.
    """
    n = len(series)
    if n < 4:
        pt = statistic(series) if n else 0.0
        return BootstrapCI(point=pt, lower=pt, upper=pt, alpha=alpha,
                           n_boot=0, block_len=0)

    if block_len is None:
        block_len = max(1, round(n ** (1.0 / 3.0)))
    block_len = min(block_len, n)
    n_blocks = math.ceil(n / block_len)
    max_start = n - block_len
    rng = random.Random(seed)

    stats: list[float] = []
    for _ in range(n_boot):
        resample: list[_T] = []
        for _ in range(n_blocks):
            start = rng.randint(0, max_start)
            resample.extend(series[start:start + block_len])
        stats.append(statistic(resample[:n]))

    stats.sort()
    lo_idx = max(0, int((alpha / 2.0) * n_boot))
    hi_idx = min(n_boot - 1, int((1.0 - alpha / 2.0) * n_boot))
    return BootstrapCI(
        point=statistic(series),
        lower=stats[lo_idx],
        upper=stats[hi_idx],
        alpha=alpha,
        n_boot=n_boot,
        block_len=block_len,
    )
