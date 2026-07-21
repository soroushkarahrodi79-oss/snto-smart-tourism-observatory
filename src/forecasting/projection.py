"""
Trend projection with an explicit, horizon-widening uncertainty band.

SNTO's analytical core is retrospective: it *detects* whether a series has
declined (Mann-Kendall, Sen's slope, change points). v2.2 adds the first
forward-looking layer — but under the project's non-negotiable evidence rule
(ADR-004 / CLAUDE.md): **a projection is a scenario, never an observation.**

Method
======
A non-parametric linear projection built on the module SNTO already uses for
trend magnitude, ``src.time_series.confidence.sens_slope_ci``:

  1. Sen's slope ``m`` (median of pairwise slopes) — the robust trend rate,
     the environmental-monitoring standard (USGS/US-EPA), insensitive to
     outliers a least-squares slope would chase.
  2. Its exact non-parametric CI ``[m_lo, m_hi]`` (Gilbert 1987) — the slope
     uncertainty that drives the band.
  3. A robust Theil-Sen level (median intercept) so the projection is anchored
     on the fitted line's end, not on the last (possibly noisy) observation.

The point path is ``level + m·h``; the band is ``level + m_lo·h`` …
``level + m_hi·h``. Because ``m_lo ≤ m ≤ m_hi``, the band contains the point
path and **widens with the horizon h** — the honest shape of trend
extrapolation: the further out, the less we know.

Evidence discipline
===================
Every :class:`Forecast` carries ``EvidenceClass.SIMULATED`` — whose canonical
``allowed_uses`` is empty (:mod:`src.platform.evidence`), so a projection can
back *no* decision (not monitoring, prioritisation, intervention, nor public
reporting). It is a "¿y si?", surfaced as such. A factory guard makes the class
un-settable to ``REAL``; a test pins it.

This deliberately does **not** model seasonality, regime change, or exogenous
drivers — a linear extrapolation is a floor, not a climate model. Its caveat
says so. Seasonal-pressure projection (harmonic) is a separate follow-up.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.platform.evidence import EvidenceClass
from src.time_series.confidence import sens_slope_ci

# A projection is always a scenario. This module never emits any other class;
# the constant exists so the rule is expressed once and asserted by tests.
FORECAST_EVIDENCE_CLASS = EvidenceClass.SIMULATED

_MIN_OBS = 3  # a projection from < 3 points is not defensible

_CAVEAT = (
    "Proyección lineal (Sen) de la tendencia histórica, con banda de "
    "incertidumbre que se ensancha con el horizonte. Es un ESCENARIO, no una "
    "observación: no modela estacionalidad, cambios de régimen ni factores "
    "externos, y no debe usarse para diagnóstico, priorización, gasto ni "
    "comunicación pública. Vale como suelo orientativo de 'si nada cambia'."
)


class ThresholdDirection(str, Enum):
    """Which side of a threshold counts as crossing it."""
    BELOW = "below"   # degradation when the value falls below (e.g. EHS floor)
    ABOVE = "above"   # degradation when the value rises above (e.g. a risk cap)


@dataclass(frozen=True)
class ThresholdCrossing:
    """When a projected trajectory first reaches a threshold, if ever."""
    threshold: float
    direction: ThresholdDirection
    # 1-indexed step where each path first crosses; None = not within horizon.
    point_step: int | None
    lower_step: int | None   # pessimistic band edge
    upper_step: int | None   # optimistic band edge


@dataclass(frozen=True)
class Forecast:
    """A horizon-h linear projection with an uncertainty band.

    Steps are 1-indexed into the future: ``point[i]`` is the projection ``i+1``
    periods after the last observation. ``lower``/``upper`` are the band edges
    at the same steps (``lower[i] <= point[i] <= upper[i]`` for every i).
    """
    horizon: int
    point: list[float]
    lower: list[float]
    upper: list[float]
    slope: float                 # Sen's slope (units per period)
    slope_lower: float
    slope_upper: float
    anchor: float                # robust level at the last observation
    n_obs: int
    alpha: float
    method: str = "theil-sen linear projection (Sen slope CI band)"
    evidence_class: EvidenceClass = field(default=FORECAST_EVIDENCE_CLASS)
    caveat: str = _CAVEAT

    def __post_init__(self) -> None:
        # Evidence guard: a projection is never observation. This cannot be
        # bypassed by passing evidence_class=REAL at construction.
        if self.evidence_class is EvidenceClass.REAL:
            raise ValueError(
                "A Forecast can never carry EvidenceClass.REAL — a projection "
                "is a scenario, not an observation (ADR-004)."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "horizon": self.horizon,
            "point": self.point,
            "lower": self.lower,
            "upper": self.upper,
            "slope": self.slope,
            "slope_ci": [self.slope_lower, self.slope_upper],
            "anchor": self.anchor,
            "n_obs": self.n_obs,
            "alpha": self.alpha,
            "method": self.method,
            "evidence_class": self.evidence_class.value,
            "caveat": self.caveat,
        }


def _theil_sen_level(series: list[float], slope: float) -> float:
    """Robust level at the last index: median intercept + slope·(n−1).

    Anchoring on the Theil-Sen fitted line's end (rather than ``series[-1]``)
    keeps a single noisy final observation from tilting the whole projection.
    """
    n = len(series)
    intercepts = sorted(y - slope * i for i, y in enumerate(series))
    m = len(intercepts)
    if m % 2 == 1:
        b0 = intercepts[m // 2]
    else:
        b0 = 0.5 * (intercepts[m // 2 - 1] + intercepts[m // 2])
    return b0 + slope * (n - 1)


def project_trend(
    series: list[float],
    horizon: int,
    *,
    alpha: float = 0.05,
    clamp: tuple[float, float] | None = None,
) -> Forecast:
    """Project ``series`` ``horizon`` periods ahead with a slope-CI band.

    Args:
        series: Historical values in chronological order (e.g. the real
            2021–2026 EHS/NDVI series). At least ``_MIN_OBS`` points.
        horizon: Number of future periods to project (≥ 1).
        alpha: 1 − confidence level for the band (0.05 → 95%).
        clamp: Optional ``(lo, hi)`` to bound every path to a physical range
            (e.g. ``(0, 100)`` for EHS, ``(-1, 1)`` for NDVI). Bands are
            clamped *after* projection, so a band that runs into the bound
            flattens there rather than reporting impossible values.

    Returns:
        A :class:`Forecast` carrying ``EvidenceClass.SIMULATED``.

    Raises:
        ValueError: if ``series`` is too short or ``horizon`` < 1.
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    if len(series) < _MIN_OBS:
        raise ValueError(
            f"need at least {_MIN_OBS} observations to project, got {len(series)}"
        )

    ci = sens_slope_ci(series, alpha=alpha)
    level = _theil_sen_level(series, ci.slope)

    def _clamp(v: float) -> float:
        if clamp is None:
            return v
        lo, hi = clamp
        return max(lo, min(hi, v))

    point: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    for h in range(1, horizon + 1):
        point.append(_clamp(level + ci.slope * h))
        # m_lo <= m_hi ⇒ these are ordered before clamping; clamp preserves order.
        lower.append(_clamp(level + ci.lower * h))
        upper.append(_clamp(level + ci.upper * h))

    return Forecast(
        horizon=horizon,
        point=point,
        lower=lower,
        upper=upper,
        slope=ci.slope,
        slope_lower=ci.lower,
        slope_upper=ci.upper,
        anchor=level,
        n_obs=len(series),
        alpha=alpha,
    )


def threshold_crossing(
    forecast: Forecast,
    threshold: float,
    direction: ThresholdDirection,
) -> ThresholdCrossing:
    """First step at which each projected path reaches a degradation threshold.

    Returns the earliest 1-indexed step where the point path and each band edge
    cross ``threshold`` in the degrading ``direction`` (``None`` if a path never
    crosses within the horizon). The gap between ``lower_step`` and
    ``upper_step`` is the honest spread of "when might this happen".
    """
    def _first_cross(path: list[float]) -> int | None:
        for i, v in enumerate(path, start=1):
            if direction is ThresholdDirection.BELOW and v <= threshold:
                return i
            if direction is ThresholdDirection.ABOVE and v >= threshold:
                return i
        return None

    # For a BELOW threshold the pessimistic edge is `lower`; for ABOVE it is
    # `upper`. We report both edges regardless so the caller sees the full span.
    return ThresholdCrossing(
        threshold=threshold,
        direction=direction,
        point_step=_first_cross(forecast.point),
        lower_step=_first_cross(forecast.lower),
        upper_step=_first_cross(forecast.upper),
    )
