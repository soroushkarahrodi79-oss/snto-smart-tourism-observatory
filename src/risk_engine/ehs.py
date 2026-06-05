from __future__ import annotations

"""
Environmental Health Score (EHS) — 0 to 100 composite metric.

PURPOSE
=======
The EHS summarises the long-term environmental condition of a natural tourism
asset into a single defensible number suitable for:
  - public administration dashboards
  - inter-asset comparison
  - temporal tracking (year-over-year EHS trends)
  - institutional reporting (Sismotur, REDNAT, EUROPARC)

FORMULA
=======
EHS = 100 × (1 − risk)

where:

  risk = w_baseline * baseline_risk
       + w_trend    * trend_risk
       + w_anomaly  * anomaly_risk
       + w_recovery * recovery_risk
       + w_stability* stability_risk

Components
----------
1. baseline_risk (weight 0.30)
   How far the long-term mean NDVI sits below the healthy reference baseline.
   baseline_risk = clamp((baseline_ndvi - mean_ndvi) / baseline_ndvi)
   Full range: 0 (at or above baseline) → 1 (completely bare soil)

2. trend_risk (weight 0.25)
   Magnitude of statistically significant negative Sen's slope.
   trend_risk = clamp(|slope| / max_slope) when slope < 0 AND p < 0.05
   max_slope = 0.005 NDVI units/month (severe sustained decline)
   = 0 when slope >= 0 or trend not significant

3. anomaly_risk (weight 0.25)
   Fraction of months classified as severely anomalous (|z| >= 1.5).
   anomaly_risk = n_anomalous / n_total
   Captures both drought frequency and severity.

4. recovery_risk (weight 0.10)
   How well the asset recovered after the worst drought event.
   recovery_risk = clamp(1 - recovery_fraction)
   recovery_fraction = post_drought_ndvi / pre_drought_ndvi (capped at 1)
   = 0 if no significant drought event detected

5. stability_risk (weight 0.10)
   Inter-annual residual variability relative to mean NDVI.
   stability_risk = clamp(residual_std / (mean_ndvi * 0.20))
   20% of mean NDVI is the upper bound of acceptable inter-annual variability.

CALIBRATION
===========
Weights derived from expert elicitation for Mediterranean scrubland monitoring
(Pellizzaro et al. 2007, Lloret et al. 2012, Fernández-Manso et al. 2016):
  - Long-term NDVI level is the most reliable indicator of habitat quality.
  - Recovery capacity distinguishes climate-stressed from degraded sites.
  - Trend significance prevents noise-driven score changes.

INTERPRETATION SCALE
====================
  90–100: Excellent — vegetation well above regional baseline, highly stable
   75–89: Good      — moderate seasonal stress, stable long-term condition
   60–74: Moderate  — noticeable chronic stress, annual monitoring recommended
   40–59: Poor      — persistent degradation or recurring anomalies, intervention needed
    0-39: Critical  -- severe, likely irreversible degradation
"""

import math
from dataclasses import dataclass

from src.time_series.mann_kendall import MannKendallResult


@dataclass(frozen=True)
class EHSComponents:
    baseline_risk: float
    trend_risk: float
    anomaly_risk: float
    recovery_risk: float
    stability_risk: float
    composite_risk: float
    ehs: float


# Component weights
_W_BASELINE: float = 0.30
_W_TREND: float = 0.25
_W_ANOMALY: float = 0.25
_W_RECOVERY: float = 0.10
_W_STABILITY: float = 0.10

# Calibration constants
_BASELINE_NDVI: float = 0.55        # healthy Mediterranean scrubland
_MAX_TREND_SLOPE: float = 0.005     # severe sustained decline (NDVI units/month)
_MAX_RESIDUAL_FRACTION: float = 0.20  # 20% of mean NDVI = max acceptable inter-annual σ


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def compute_ehs(
    mean_ndvi: float,
    mk_result: MannKendallResult,
    n_anomalous_months: int,
    n_total_months: int,
    pre_drought_ndvi: float | None = None,
    post_drought_ndvi: float | None = None,
    residual_std: float = 0.0,
) -> EHSComponents:
    """
    Compute the Environmental Health Score from multi-year analysis outputs.

    Args:
        mean_ndvi:            Annual mean NDVI over the full record.
        mk_result:            Result of Mann-Kendall test on the series.
        n_anomalous_months:   Months with |z| >= 1.5 (severe anomaly).
        n_total_months:       Total valid observations.
        pre_drought_ndvi:     Mean NDVI in the 12 months before the worst drought.
                              None if no drought event detected.
        post_drought_ndvi:    Mean NDVI in the 12 months after the worst drought.
                              None if no drought event or insufficient post data.
        residual_std:         Std of decomposition residuals (inter-annual noise).

    Returns:
        EHSComponents with all sub-scores and final EHS value.
    """
    # 1. Baseline risk
    baseline_risk = _clamp((_BASELINE_NDVI - mean_ndvi) / _BASELINE_NDVI)

    # 2. Trend risk — only penalises statistically significant declines
    if mk_result.is_significant and mk_result.sens_slope < 0:
        trend_risk = _clamp(abs(mk_result.sens_slope) / _MAX_TREND_SLOPE)
    else:
        trend_risk = 0.0

    # 3. Anomaly risk — fraction of severely anomalous months
    anomaly_risk = _clamp(n_anomalous_months / max(1, n_total_months))

    # 4. Recovery risk
    if pre_drought_ndvi is not None and post_drought_ndvi is not None and pre_drought_ndvi > 0:
        recovery_fraction = _clamp(post_drought_ndvi / pre_drought_ndvi)
        recovery_risk = _clamp(1.0 - recovery_fraction)
    else:
        recovery_risk = 0.0

    # 5. Stability risk — inter-annual variability relative to mean
    if mean_ndvi > 0:
        stability_risk = _clamp(residual_std / (mean_ndvi * _MAX_RESIDUAL_FRACTION))
    else:
        stability_risk = 1.0

    # Weighted composite
    composite = (
        _W_BASELINE * baseline_risk
        + _W_TREND * trend_risk
        + _W_ANOMALY * anomaly_risk
        + _W_RECOVERY * recovery_risk
        + _W_STABILITY * stability_risk
    )

    ehs = round(100.0 * (1.0 - composite), 1)

    return EHSComponents(
        baseline_risk=round(baseline_risk, 4),
        trend_risk=round(trend_risk, 4),
        anomaly_risk=round(anomaly_risk, 4),
        recovery_risk=round(recovery_risk, 4),
        stability_risk=round(stability_risk, 4),
        composite_risk=round(composite, 4),
        ehs=ehs,
    )


def interpret_ehs(ehs: float) -> str:
    """Qualitative label for the EHS score."""
    if ehs >= 90:
        return "Excellent"
    if ehs >= 75:
        return "Good"
    if ehs >= 60:
        return "Moderate"
    if ehs >= 40:
        return "Poor"
    return "Critical"
