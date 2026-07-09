from __future__ import annotations

"""
Mann-Kendall trend test and Sen's slope estimator.

These are the scientifically correct methods for detecting monotonic trends
in environmental time series because:
  1. They are non-parametric — no normality assumption on the data.
  2. They are resistant to outliers (important given drought spikes).
  3. They detect any monotonic trend, not just linear trends.
  4. Sen's slope is the preferred magnitude estimator for the same reasons.

The OLS slope implemented in trend.py is ONLY used for the alert engine's
declining/rising gate (a directional test, not a significance test). For
scientific reporting and calibration, Mann-Kendall must be used.

References
==========
  Mann, H.B. (1945). Nonparametric tests against trend.
    Econometrica, 13(3), 245–259.
  Kendall, M.G. (1975). Rank Correlation Methods, 4th ed. Griffin, London.
  Sen, P.K. (1968). Estimates of regression coefficient based on Kendall's tau.
    Journal of the American Statistical Association, 63, 1379–1389.
  Hipel, K.W. & McLeod, A.I. (1994). Time Series Modelling of Water Resources.
    Elsevier, Amsterdam. [Implementation reference for tie correction]
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MannKendallResult:
    """Full output of a Mann-Kendall monotonic trend test."""

    s_statistic: float        # Mann-Kendall S statistic (sum of concordance signs)
    z_score: float            # Standardized test statistic
    p_value: float            # Two-tailed p-value
    kendalls_tau: float       # Normalized correlation coefficient [-1, 1]
    sens_slope: float         # Sen's slope (units/time step)
    trend_direction: str      # "increasing" | "decreasing" | "no_trend"
    is_significant: bool      # True when p_value < alpha
    alpha: float              # Significance level used
    n: int                    # Sample size


def _normal_cdf(z: float) -> float:
    """Cumulative distribution function of the standard normal using math.erfc."""
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def mann_kendall_test(
    series: list[float],
    alpha: float = 0.05,
) -> MannKendallResult:
    """
    Two-sided Mann-Kendall trend test with tie correction.

    Computes the S statistic, its variance (correcting for ties), the
    standardized Z score, and a two-tailed p-value.  A p-value below alpha
    indicates a statistically significant monotonic trend.

    Tie correction uses the standard formula (Hipel & McLeod 1994):
      Var(S) = [n(n-1)(2n+5) - Σ_g t_g(t_g-1)(2*t_g+5)] / 18
    where t_g is the number of tied observations in group g.

    Args:
        series: Ordered sequence of values (e.g. monthly NDVI).
        alpha:  Significance level (default 0.05 → 95% confidence).

    Returns:
        MannKendallResult with all test outputs.
    """
    n = len(series)
    if n < 4:
        return MannKendallResult(
            s_statistic=0.0, z_score=0.0, p_value=1.0,
            kendalls_tau=0.0, sens_slope=0.0,
            trend_direction="no_trend", is_significant=False,
            alpha=alpha, n=n,
        )

    # Compute S statistic
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += _sign(series[j] - series[i])

    # Variance with tie correction (Hipel & McLeod 1994)
    var_s = variance_s(series)

    # Continuity-corrected Z statistic
    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0

    # Two-tailed p-value
    p_value = 2.0 * (1.0 - _normal_cdf(abs(z)))
    p_value = min(1.0, max(0.0, p_value))

    # Kendall's tau (normalised S)
    max_s = n * (n - 1) / 2
    tau = s / max_s if max_s > 0 else 0.0

    # Sen's slope
    s_slope = _sens_slope(series)

    # Direction classification
    if p_value < alpha:
        direction = "increasing" if s > 0 else "decreasing"
    else:
        direction = "no_trend"

    return MannKendallResult(
        s_statistic=float(s),
        z_score=round(z, 4),
        p_value=round(p_value, 4),
        kendalls_tau=round(tau, 4),
        sens_slope=round(s_slope, 6),
        trend_direction=direction,
        is_significant=p_value < alpha,
        alpha=alpha,
        n=n,
    )


def pairwise_slopes(series: list[float]) -> list[float]:
    """All pairwise slopes (x_j - x_i)/(j - i) for i < j (unsorted).

    Public helper shared by Sen's slope and its non-parametric confidence
    interval (see ``src/time_series/confidence.py``) so both derive from a
    single definition of the slope population.
    """
    n = len(series)
    slopes: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            slopes.append((series[j] - series[i]) / (j - i))
    return slopes


def variance_s(series: list[float]) -> float:
    """Variance of the Mann-Kendall S statistic with tie correction.

    Var(S) = [n(n-1)(2n+5) - Σ_g t_g(t_g-1)(2t_g+5)] / 18   (Hipel & McLeod 1994)
    where t_g is the size of tied group g. Guarded to be non-negative.
    """
    from collections import Counter
    n = len(series)
    counts = Counter(series)
    tie_sum = sum(t * (t - 1) * (2 * t + 5) for t in counts.values() if t > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - tie_sum) / 18.0
    return max(var_s, 0.0)


def _sens_slope(series: list[float]) -> float:
    """
    Sen's slope estimator: median of all pairwise slopes (x_j - x_i)/(j - i).

    Robust to outliers because it uses the median rather than mean of slopes.
    For NDVI time series, units are NDVI units per month.
    """
    slopes = pairwise_slopes(series)
    if not slopes:
        return 0.0
    slopes.sort()
    m = len(slopes)
    if m % 2 == 1:
        return slopes[m // 2]
    return (slopes[m // 2 - 1] + slopes[m // 2]) / 2.0


def classify_trend_severity(result: MannKendallResult) -> str:
    """
    Classify the ecological significance of a Mann-Kendall trend result.

    Classification table (Sen's slope in NDVI units/month):
      improving         : significant positive trend
      stable            : no significant trend
      mild_degradation  : significant negative, |slope| < 0.002/month
      degrading         : significant negative, 0.002 ≤ |slope| < 0.005/month
      strongly_degrading: significant negative, |slope| ≥ 0.005/month

    Threshold values calibrated from:
      González-De Vega et al. (2018) — 0.003/month is the 'noticeable change'
      threshold for Iberian Mediterranean scrubland over decadal scales.
    """
    if not result.is_significant:
        return "stable"
    if result.sens_slope > 0:
        return "improving"
    slope_mag = abs(result.sens_slope)
    if slope_mag < 0.002:
        return "mild_degradation"
    if slope_mag < 0.005:
        return "degrading"
    return "strongly_degrading"
