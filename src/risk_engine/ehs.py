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
1. baseline_risk (weight 0.30 — or 0.20 in dense-canopy mode)
   How far the long-term mean NDVI (or EVI) sits below the healthy reference.
   baseline_risk = clamp((baseline_ref - effective_vi) / baseline_ref)
   Full range: 0 (at or above baseline) → 1 (completely bare soil)

2. trend_risk (weight 0.25 — or 0.30 in dense-canopy mode)
   Magnitude of statistically significant negative Sen's slope.
   trend_risk = clamp(|slope| / max_slope) when slope < 0 AND p < 0.05
   max_slope = 0.005 NDVI units/month (severe sustained decline)
   = 0 when slope >= 0 or trend not significant

3. anomaly_risk (weight 0.25 — or 0.30 in dense-canopy mode)
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

DENSE-CANOPY ADAPTATION
========================
When mean_ndvi >= DENSE_CANOPY_NDVI_THRESHOLD (0.80), NDVI saturates in
closed-canopy ecosystems (beech groves, dense oak/pine stands).  In this
regime the score switches to "dense-canopy mode":

  1. If mean_evi is provided, it replaces NDVI for baseline_risk, using a
     separate EVI healthy reference (BASELINE_EVI_DENSE = 0.40).  EVI does
     not saturate in dense forests.
  2. Component weights shift away from the now-less-informative baseline term
     toward trend and anomaly, where NDMI-derived signals are embedded:
       baseline 0.30 → 0.20   (less reliable at saturation)
       trend    0.25 → 0.30   (temporal decline still measurable)
       anomaly  0.25 → 0.30   (NDMI anomalies captured here)
       recovery 0.10 → 0.10   (unchanged)
       stability0.10 → 0.10   (unchanged)

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
    0-39: Critical  — severe, likely irreversible degradation
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
    is_dense_canopy: bool = False   # True when NDVI saturation guard was triggered


# ── Normal-mode weights (Mediterranean scrubland) ─────────────────────────────
_W_BASELINE:  float = 0.30
_W_TREND:     float = 0.25
_W_ANOMALY:   float = 0.25
_W_RECOVERY:  float = 0.10
_W_STABILITY: float = 0.10

# ── Dense-canopy mode weights ─────────────────────────────────────────────────
# Shift 0.10 from baseline (saturated NDVI) to trend + anomaly where
# NDMI-derived signals are more sensitive to sub-canopy stress.
_W_BASELINE_DENSE:  float = 0.20
_W_TREND_DENSE:     float = 0.30
_W_ANOMALY_DENSE:   float = 0.30
_W_RECOVERY_DENSE:  float = 0.10
_W_STABILITY_DENSE: float = 0.10

# ── Calibration constants ─────────────────────────────────────────────────────
_BASELINE_NDVI: float = 0.55        # healthy Mediterranean scrubland
_BASELINE_EVI_DENSE: float = 0.40   # healthy dense forest (EVI reference; Huete et al.)
_MAX_TREND_SLOPE: float = 0.005     # severe sustained decline (NDVI units/month)
_MAX_RESIDUAL_FRACTION: float = 0.20  # 20% of mean NDVI = max acceptable inter-annual σ

# Threshold above which NDVI saturates in closed-canopy ecosystems.
# Based on Myneni et al. (1995) and confirmed for Iberian Hayedos.
DENSE_CANOPY_NDVI_THRESHOLD: float = 0.80


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
    mean_evi: float | None = None,
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
        mean_evi:             Mean EVI over the full record.  When provided and
                              mean_ndvi >= DENSE_CANOPY_NDVI_THRESHOLD, EVI
                              replaces NDVI for the baseline_risk component.

    Returns:
        EHSComponents with all sub-scores, final EHS, and is_dense_canopy flag.
    """
    # ── Dense-canopy detection ────────────────────────────────────────────────
    is_dense_canopy = mean_ndvi >= DENSE_CANOPY_NDVI_THRESHOLD

    if is_dense_canopy:
        w_baseline  = _W_BASELINE_DENSE
        w_trend     = _W_TREND_DENSE
        w_anomaly   = _W_ANOMALY_DENSE
        w_recovery  = _W_RECOVERY_DENSE
        w_stability = _W_STABILITY_DENSE
    else:
        w_baseline  = _W_BASELINE
        w_trend     = _W_TREND
        w_anomaly   = _W_ANOMALY
        w_recovery  = _W_RECOVERY
        w_stability = _W_STABILITY

    # 1. Baseline risk
    # In dense-canopy mode, use EVI if available (no saturation above 0.80).
    # Fall back to NDVI if EVI is absent — the reduced weight mitigates bias.
    if is_dense_canopy and mean_evi is not None:
        baseline_risk = _clamp((_BASELINE_EVI_DENSE - mean_evi) / _BASELINE_EVI_DENSE)
    else:
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
    ref_vi = mean_evi if (is_dense_canopy and mean_evi is not None) else mean_ndvi
    if ref_vi > 0:
        stability_risk = _clamp(residual_std / (ref_vi * _MAX_RESIDUAL_FRACTION))
    else:
        stability_risk = 1.0

    # Weighted composite
    composite = (
        w_baseline  * baseline_risk
        + w_trend   * trend_risk
        + w_anomaly * anomaly_risk
        + w_recovery  * recovery_risk
        + w_stability * stability_risk
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
        is_dense_canopy=is_dense_canopy,
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
