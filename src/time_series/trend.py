from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.config.constants import TREND_RISING_SLOPE


@dataclass(frozen=True)
class TrendResult:
    slope: float      # units/month — negative means declining NDVI
    intercept: float
    r_squared: float


def compute_linear_trend(series: list[float]) -> TrendResult:
    """
    Ordinary least squares linear regression via numpy.linalg.lstsq.
    Returns slope, intercept, and R² for the series indexed by position.
    """
    n = len(series)
    if n < 2:
        return TrendResult(slope=0.0, intercept=series[0] if series else 0.0, r_squared=0.0)

    x = np.arange(n, dtype=float)
    y = np.array(series, dtype=float)
    A = np.column_stack([x, np.ones(n)])
    result, *_ = np.linalg.lstsq(A, y, rcond=None)
    slope, intercept = float(result[0]), float(result[1])

    y_mean = float(np.mean(y))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 0.0

    return TrendResult(slope=slope, intercept=intercept, r_squared=r_squared)


def is_rising(
    trend: TrendResult,
    threshold: float = TREND_RISING_SLOPE,
    min_r_squared: float = 0.30,
) -> bool:
    """
    True when the linear NDVI trend is:
      (a) positive and above threshold — vegetation improving, AND
      (b) statistically credible (R² >= min_r_squared).

    A slope computed from 12 seasonal data points with R² < 0.30 is dominated
    by noise/seasonality and should not be used to infer direction. The R²
    gate prevents spurious alert decisions driven by phase alignment artefacts.
    """
    return trend.slope > threshold and trend.r_squared >= min_r_squared


def is_declining(
    trend: TrendResult,
    threshold: float = TREND_RISING_SLOPE,
    min_r_squared: float = 0.30,
) -> bool:
    """
    True when the linear NDVI trend is negative and statistically credible.
    Used by the alert engine to identify actively worsening assets.
    """
    return trend.slope < -threshold and trend.r_squared >= min_r_squared
