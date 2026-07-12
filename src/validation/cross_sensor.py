"""
SNTO — Inter-sensor cross-validation of the NDVI signal.

WHY
===
The trend and health conclusions rest on Sentinel-2 NDVI. A second, *independent*
sensor is the strongest available check that those conclusions are not an
artefact of one instrument's calibration or cloud handling. MODIS (Terra/Aqua,
MOD13Q1) is genuinely independent of Sentinel-2 and provides a long, well-
characterised NDVI record; Landsat C2 (30 m) is the finer-resolution independent
alternative. (Copernicus HR-VPP is *derived from Sentinel-2* and is therefore
NOT independent — useful for continuity, not for cross-validation.)

WHAT THIS MODULE DOES
=====================
Given two co-located, temporally paired NDVI series — the SNTO primary
(Sentinel-2) and an independent reference — it reports the standard agreement
statistics used in remote-sensing validation:

  * Pearson r              — linear co-variation.
  * RMSE, MAE              — magnitude of disagreement.
  * bias (primary−ref)     — systematic offset between sensors.
  * Willmott's d (1981)    — index of agreement in [0,1], 1 = perfect.
  * Bland-Altman limits    — mean difference ± 1.96·SD (agreement envelope).

RESOLUTION CAVEAT
=================
MOD13Q1 is 250 m; several PNSG assets are points/lines buffered to 30–50 m, i.e.
sub-pixel for MODIS. Against MODIS the validation therefore speaks to the
*pixel-neighbourhood* NDVI level and trend, not to fine within-asset detail. For
asset-scale spatial agreement, use Landsat C2 (30 m). This limitation is
declared, not hidden.

References
==========
  Willmott, C.J. (1981). On the validation of models. Physical Geography, 2(2),
    184–194. [index of agreement d]
  Bland, J.M. & Altman, D.G. (1986). Statistical methods for assessing agreement
    between two methods of clinical measurement. The Lancet, 327, 307–310.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class CrossSensorReport:
    """Agreement between the primary (Sentinel-2) and an independent reference."""

    n: int
    pearson_r: float
    rmse: float
    mae: float
    bias: float               # mean(primary − reference); + = primary reads higher
    willmott_d: float         # index of agreement in [0, 1]
    ba_mean_diff: float       # Bland-Altman mean difference (= bias)
    ba_lower_loa: float       # mean_diff − 1.96·SD
    ba_upper_loa: float       # mean_diff + 1.96·SD
    verdict: str


def _pearson(x: Sequence[float], y: Sequence[float]) -> float:
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sx = sum((a - mx) ** 2 for a in x)
    sy = sum((b - my) ** 2 for b in y)
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return cov / (sx ** 0.5 * sy ** 0.5)


def willmott_index(primary: Sequence[float], reference: Sequence[float]) -> float:
    """Willmott's index of agreement d in [0, 1] (1 = perfect agreement)."""
    o_mean = statistics.fmean(reference)
    num = sum((p - o) ** 2 for p, o in zip(primary, reference))
    den = sum((abs(p - o_mean) + abs(o - o_mean)) ** 2
              for p, o in zip(primary, reference))
    if den == 0:
        return 1.0 if num == 0 else 0.0
    return 1.0 - num / den


def cross_sensor_agreement(
    primary: Sequence[float],
    reference: Sequence[float],
    *,
    strong_r: float = 0.80,
    moderate_r: float = 0.60,
    bias_tol: float = 0.05,
) -> CrossSensorReport:
    """Compute inter-sensor agreement between two paired NDVI series.

    Args:
        primary:   SNTO NDVI (Sentinel-2), temporally aligned to ``reference``.
        reference: independent-sensor NDVI (e.g. MODIS MOD13Q1).
        strong_r / moderate_r: Pearson thresholds for the verdict wording.
        bias_tol:  |bias| below which the sensors are deemed practically unbiased.

    Raises:
        ValueError: if lengths differ or fewer than 3 pairs are given.
    """
    if len(primary) != len(reference):
        raise ValueError("primary and reference must have equal length")
    n = len(primary)
    if n < 3:
        raise ValueError("at least 3 paired observations are required")

    diffs = [p - o for p, o in zip(primary, reference)]
    bias = statistics.fmean(diffs)
    rmse = (sum(d * d for d in diffs) / n) ** 0.5
    mae = statistics.fmean([abs(d) for d in diffs])
    r = _pearson(primary, reference)
    d = willmott_index(primary, reference)
    sd = statistics.pstdev(diffs) if n > 1 else 0.0
    lower = bias - 1.96 * sd
    upper = bias + 1.96 * sd

    if r >= strong_r and abs(bias) <= bias_tol:
        verdict = "concordancia fuerte e insesgada entre sensores"
    elif r >= strong_r:
        verdict = f"buena co-variación pero con sesgo sistemático ({bias:+.3f})"
    elif r >= moderate_r:
        verdict = "concordancia moderada: consistente, revisar resolución/escala"
    elif r > 0:
        verdict = "concordancia débil entre sensores"
    else:
        verdict = "sin concordancia / dirección inesperada — revisar emparejamiento"

    return CrossSensorReport(
        n=n,
        pearson_r=round(r, 4),
        rmse=round(rmse, 4),
        mae=round(mae, 4),
        bias=round(bias, 4),
        willmott_d=round(d, 4),
        ba_mean_diff=round(bias, 4),
        ba_lower_loa=round(lower, 4),
        ba_upper_loa=round(upper, 4),
        verdict=verdict,
    )
