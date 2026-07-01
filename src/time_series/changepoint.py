from __future__ import annotations

"""
Non-parametric abrupt change-point detection (Pettitt test).

WHY
===
Mann-Kendall answers "is there a monotonic trend?"; a land manager also needs
"*when* did a disturbance happen, and is it real?". The Pettitt test (1979)
locates a single abrupt shift in the distribution of a series and tests its
significance, without assuming normality — consistent with the rank-based,
outlier-resistant philosophy of the rest of the temporal toolkit.

Applied to the *deseasonalised* NDVI series (seasonality removed, see
decomposition.py), it isolates genuine regime shifts — most notably the 2022
Iberian drought trough — rather than the phenological cycle.

METHOD (Pettitt 1979)
=====================
For a series x_1..x_n, using the whole-series ranks r_i, the Mann-Whitney style
statistic at split t is
    U_{t} = 2·Σ_{i≤t} r_i − t·(n+1).
The change-point τ is the t that maximises |U_t|; the test statistic is
K = |U_τ|. Its approximate two-sided significance is
    p ≈ 2·exp( −6·K² / (n³ + n²) ).
The second regime is taken to start at 0-based index τ.

SCOPE / FUTURE WORK
===================
This detects a *single* abrupt change (adequate for a 5–6 year monthly series
dominated by one event). Multiple breakpoints and joint trend/seasonal break
decomposition (BFAST, Verbesselt et al. 2010) are the natural next step and are
declared as open work, not silently approximated here.

References
==========
  Pettitt, A.N. (1979). A non-parametric approach to the change-point problem.
    Journal of the Royal Statistical Society C (Applied Statistics), 28(2),
    126–135.
  Verbesselt, J. et al. (2010). Detecting trend and seasonal changes in
    satellite image time series. Remote Sensing of Environment, 114, 106–115.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PettittResult:
    """Outcome of a single-change-point Pettitt test."""

    change_index: int | None   # 0-based start of the second regime (None if n<4)
    k_statistic: float         # K = max_t |U_t|
    p_value: float             # approximate two-sided p-value
    is_significant: bool       # p_value < alpha
    n: int


def _average_ranks(values: list[float]) -> list[float]:
    """1-based ranks with ties resolved by their average rank."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and values[order[j]] == values[order[i]]:
            j += 1
        avg = (i + j - 1) / 2.0 + 1.0   # mean of the 1-based positions i..j-1
        for k in range(i, j):
            ranks[order[k]] = avg
        i = j
    return ranks


def pettitt_test(series: list[float], alpha: float = 0.05) -> PettittResult:
    """Locate and test a single abrupt change-point in ``series``.

    Returns ``change_index=None`` for series too short to support the test
    (n < 4). The index marks the 0-based start of the second regime, so it maps
    directly onto the position (and hence the date) of the input series.
    """
    n = len(series)
    if n < 4:
        return PettittResult(
            change_index=None, k_statistic=0.0, p_value=1.0,
            is_significant=False, n=n,
        )

    ranks = _average_ranks(series)
    best_abs = -1.0
    tau = 1
    csum = 0.0
    for t in range(1, n):                       # split between index t-1 and t
        csum += ranks[t - 1]
        u_t = 2.0 * csum - t * (n + 1)
        if abs(u_t) > best_abs:
            best_abs = abs(u_t)
            tau = t

    k = best_abs
    p = 2.0 * math.exp(-6.0 * k * k / (n ** 3 + n ** 2))
    p = min(1.0, p)
    return PettittResult(
        change_index=tau, k_statistic=k, p_value=round(p, 4),
        is_significant=p < alpha, n=n,
    )
