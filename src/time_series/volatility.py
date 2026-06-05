from __future__ import annotations

import math


def compute_volatility(series: list[float]) -> float:
    """Population standard deviation of series. Returns 0.0 for < 2 elements."""
    n = len(series)
    if n < 2:
        return 0.0
    mean = sum(series) / n
    variance = sum((x - mean) ** 2 for x in series) / n
    return math.sqrt(variance)


def compute_coefficient_of_variation(series: list[float]) -> float:
    """CV = std / |mean|. Returns 0.0 when mean is zero."""
    mean = sum(series) / len(series) if series else 0.0
    if mean == 0.0:
        return 0.0
    return compute_volatility(series) / abs(mean)


def compute_deseasonalized_volatility(series: list[float]) -> float:
    """
    Residual std after removing a 2-harmonic Fourier seasonal model.

    Uses the annual fundamental (period T = 12 months) AND its first overtone
    (period T/2 = 6 months).  Two harmonics are required for Mediterranean
    scrubland because the phenological cycle is strongly asymmetric: rapid
    spring green-up followed by a deep, sustained summer drought trough.  A
    single sinusoid (1 harmonic) fails to capture this asymmetry and leaves
    large structured residuals that are falsely interpreted as disturbance.

    Model: y(t) = a0
                + a1*cos(2π*t/12) + b1*sin(2π*t/12)   [annual]
                + a2*cos(4π*t/12) + b2*sin(4π*t/12)   [semi-annual]

    After fitting, the residuals represent only non-seasonal variance:
    trampling events, fire scars, construction damage, storm damage.

    Reference: Julien & Sobrino (2009) — harmonic analysis of MODIS NDVI
    time series for Mediterranean biomes confirms that 2 harmonics explain
    ≥ 95% of explained seasonal variance in semi-arid scrubland.

    Falls back to raw volatility for series shorter than 6 elements.
    """
    n = len(series)
    if n < 6:
        return compute_volatility(series)

    import numpy as np

    T = 12.0
    t = np.arange(1, n + 1, dtype=float)
    # 2-harmonic design matrix: intercept + cos1 + sin1 + cos2 + sin2
    A = np.column_stack([
        np.ones(n),
        np.cos(2 * math.pi * t / T),
        np.sin(2 * math.pi * t / T),
        np.cos(4 * math.pi * t / T),
        np.sin(4 * math.pi * t / T),
    ])
    y = np.array(series, dtype=float)
    coeffs, *_ = np.linalg.lstsq(A, y, rcond=None)
    residuals = y - A @ coeffs

    return float(np.std(residuals))
