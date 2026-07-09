from __future__ import annotations

"""
Trend-Free Pre-Whitening (TFPW) for the Mann-Kendall trend test.

WHY
===
The Mann-Kendall test assumes the observations are serially independent under
H0. Positive lag-1 autocorrelation — very common in monthly vegetation series
even AFTER seasonal removal — inflates the variance of the S statistic and
therefore the false-positive (Type I) rate: the test "sees" trends that are
really autocorrelation. Deseasonalising (see decomposition.py) removes the
phenological cycle but not the short-memory persistence of the residuals.

Yue, Pilon, Phinney & Cavadias (2002) proposed Trend-Free Pre-Whitening: remove
the AR(1) component *after* first taking out the trend, so the pre-whitening
step does not also remove part of the very trend we want to detect (a known
flaw of naive pre-whitening, Yue & Wang 2002).

PROCEDURE (Yue-Pilon 2002)
==========================
  1. Estimate the trend slope β with Sen's slope (robust, non-parametric).
  2. Detrend:                 X'_t = X_t − β·t
  3. Compute lag-1 autocorrelation r1 of X'.
  4. If r1 is not significant, the series is treated as independent → return it
     unchanged (naive pre-whitening would only add noise).
  5. Otherwise remove the AR(1):  Y'_t = X'_t − r1·X'_{t-1}   (t = 2..n)
  6. Add the trend back:          Y_t  = Y'_t + β·t
  7. The blended series Y is what the Mann-Kendall test should run on.

References
==========
  Yue, S., Pilon, P., Phinney, B. & Cavadias, G. (2002). The influence of
    autocorrelation on the ability to detect trend in hydrological series.
    Hydrological Processes, 16, 1807-1829.
  Yue, S. & Wang, C.Y. (2002). Applicability of prewhitening to eliminate the
    influence of serial correlation on the Mann-Kendall test. Water Resources
    Research, 38(6).
"""

import math
from dataclasses import dataclass

from src.time_series.mann_kendall import _sens_slope


@dataclass(frozen=True)
class PrewhitenResult:
    """Outcome of Trend-Free Pre-Whitening."""

    series: list[float]        # blended series to feed Mann-Kendall
    lag1_autocorr: float       # estimated r1 of the detrended series
    applied: bool              # True only if r1 was significant and removed
    significance_bound: float  # |r1| threshold used (95% white-noise bound)
    n_in: int
    n_out: int                 # len(series); n-1 when AR(1) removal applied


def lag1_autocorrelation(series: list[float]) -> float:
    """Lag-1 autocorrelation coefficient r1 (biased estimator, mean-centred)."""
    n = len(series)
    if n < 2:
        return 0.0
    mean = sum(series) / n
    denom = sum((x - mean) ** 2 for x in series)
    if denom == 0:
        return 0.0
    numer = sum((series[t] - mean) * (series[t + 1] - mean) for t in range(n - 1))
    return numer / denom


def trend_free_prewhiten(series: list[float], alpha: float = 0.05) -> PrewhitenResult:
    """Apply Yue-Pilon Trend-Free Pre-Whitening.

    Args:
        series: series to be tested (typically already deseasonalised).
        alpha:  significance level for the lag-1 white-noise test. The two-sided
            95% bound for r1 under white noise is ±z_{1-α/2}/√n.

    Returns:
        PrewhitenResult. When r1 is not significant, ``applied`` is False and
        ``series`` is the input unchanged (Yue-Pilon step 4).
    """
    n = len(series)
    if n < 4:
        return PrewhitenResult(
            series=list(series), lag1_autocorr=0.0, applied=False,
            significance_bound=float("inf"), n_in=n, n_out=n,
        )

    # 1-2. Sen's slope β and detrend.
    beta = _sens_slope(series)
    detrended = [series[t] - beta * t for t in range(n)]

    # 3. Lag-1 autocorrelation of the detrended series.
    r1 = lag1_autocorrelation(detrended)

    # 4. White-noise significance bound for r1 (normal approximation).
    from statistics import NormalDist
    z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    bound = z / math.sqrt(n)

    if abs(r1) <= bound:
        # Not significant → leave the series alone (avoid over-whitening).
        return PrewhitenResult(
            series=list(series), lag1_autocorr=round(r1, 4), applied=False,
            significance_bound=round(bound, 4), n_in=n, n_out=n,
        )

    # 5. Remove AR(1) from the detrended series (drops the first point).
    whitened = [detrended[t] - r1 * detrended[t - 1] for t in range(1, n)]

    # 6. Add the trend back over the retained indices (t = 1..n-1).
    blended = [whitened[i] + beta * (i + 1) for i in range(len(whitened))]

    return PrewhitenResult(
        series=blended, lag1_autocorr=round(r1, 4), applied=True,
        significance_bound=round(bound, 4), n_in=n, n_out=len(blended),
    )
