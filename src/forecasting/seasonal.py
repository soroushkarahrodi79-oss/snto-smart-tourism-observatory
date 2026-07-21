"""
Seasonal-aware projection for series with an annual cycle.

The plain :func:`src.forecasting.projection.project_trend` extrapolates the
underlying trend but ignores seasonality — for a visitor-pressure or NDVI series
with a strong annual cycle, that flattens the peaks and troughs that actually
drive management (summer footfall, the growing season). This module keeps the
cycle.

Method
======
Composition of two pieces SNTO already has and tests:

  1. ``src.time_series.decomposition.harmonic_decompose`` splits the series into
     trend + a *purely periodic* seasonal component + residual.
  2. ``project_trend`` runs on the **deseasonalized** level (trend + residual),
     giving a point path and a horizon-widening band from Sen's slope CI.
  3. The seasonal component is added back **deterministically**: because the
     fitted seasonal is exactly periodic with the given ``period``, the value
     for a future step at phase ``φ`` is the fitted seasonal at that same phase.

So the band still widens with the horizon (it comes from the trend part), while
the seasonal shape repeats on top of it. The seasonal add is treated as a known
pattern, not a source of widening uncertainty — an honest simplification stated
in the caveat.

Evidence discipline
===================
Like every forecast here, a :class:`SeasonalForecast` carries
``EvidenceClass.SIMULATED`` (see :mod:`src.forecasting.projection`): a scenario,
never an observation, backing no decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.forecasting.projection import (
    FORECAST_EVIDENCE_CLASS,
    Forecast,
    project_trend,
)
from src.platform.evidence import EvidenceClass
from src.time_series.decomposition import harmonic_decompose

_CAVEAT = (
    "Proyección estacional (armónicos + tendencia Sen sobre la serie "
    "desestacionalizada): la banda se ensancha con el horizonte por la "
    "incertidumbre de tendencia; el patrón estacional se repite de forma "
    "determinista (no añade banda propia). Es un ESCENARIO, no una observación: "
    "no modela cambios de régimen ni factores externos, y no debe usarse para "
    "diagnóstico, priorización, gasto ni comunicación pública."
)


@dataclass(frozen=True)
class SeasonalForecast:
    """A horizon-h seasonal projection: trend band + repeated seasonal cycle.

    ``point[i]`` is the projection ``i+1`` periods after the last observation,
    with ``lower[i] <= point[i] <= upper[i]``. ``seasonal[i]`` is the seasonal
    offset applied at that step (for transparency).
    """
    horizon: int
    period: int
    point: list[float]
    lower: list[float]
    upper: list[float]
    seasonal: list[float]
    trend_point: list[float]        # deseasonalized trend path (point, pre-seasonal)
    seasonality_strength: float     # Wang et al. F_S in [0, 1]
    n_obs: int
    alpha: float
    method: str = "harmonic seasonal + Sen-slope trend band"
    evidence_class: EvidenceClass = field(default=FORECAST_EVIDENCE_CLASS)
    caveat: str = _CAVEAT

    def __post_init__(self) -> None:
        if self.evidence_class is EvidenceClass.REAL:
            raise ValueError(
                "A SeasonalForecast can never carry EvidenceClass.REAL — a "
                "projection is a scenario, not an observation (ADR-004)."
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "horizon": self.horizon,
            "period": self.period,
            "point": self.point,
            "lower": self.lower,
            "upper": self.upper,
            "seasonal": self.seasonal,
            "seasonality_strength": self.seasonality_strength,
            "n_obs": self.n_obs,
            "alpha": self.alpha,
            "method": self.method,
            "evidence_class": self.evidence_class.value,
            "caveat": self.caveat,
        }


def project_seasonal(
    series: list[float],
    horizon: int,
    *,
    period: int = 12,
    alpha: float = 0.05,
    clamp: tuple[float, float] | None = None,
) -> SeasonalForecast:
    """Project ``series`` ``horizon`` periods ahead keeping the seasonal cycle.

    Args:
        series: Historical values in chronological order. At least one full
            ``period`` of observations is required (harmonic fit needs a cycle).
        horizon: Number of future periods to project (>= 1).
        period: Seasonal period (12 for monthly series with an annual cycle).
        alpha: 1 − confidence level for the trend band (0.05 → 95%).
        clamp: Optional ``(lo, hi)`` bounding every path to a physical range;
            applied after the seasonal component is added.

    Returns:
        A :class:`SeasonalForecast` carrying ``EvidenceClass.SIMULATED``.

    Raises:
        ValueError: if ``horizon`` < 1 or ``series`` is shorter than ``period``.
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    if len(series) < period:
        raise ValueError(
            f"need at least one full period ({period} obs) to project "
            f"seasonally, got {len(series)}"
        )

    decomp = harmonic_decompose(series, period=period)
    n = decomp.n

    # Trend band on the deseasonalized level (trend + residual). The band's
    # widening comes entirely from here.
    trend_fc: Forecast = project_trend(
        decomp.deseasonalized, horizon, alpha=alpha, clamp=None
    )

    def _clamp(v: float) -> float:
        if clamp is None:
            return v
        lo, hi = clamp
        return max(lo, min(hi, v))

    point: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    seasonal_offsets: list[float] = []
    for h in range(1, horizon + 1):
        # Fitted seasonal is exactly periodic with `period`; the future phase
        # (n-1+h) mod period indexes an observed step of the same phase.
        phase = (n - 1 + h) % period
        s = decomp.seasonal[phase]
        seasonal_offsets.append(s)
        i = h - 1
        point.append(_clamp(trend_fc.point[i] + s))
        lower.append(_clamp(trend_fc.lower[i] + s))
        upper.append(_clamp(trend_fc.upper[i] + s))

    return SeasonalForecast(
        horizon=horizon,
        period=period,
        point=point,
        lower=lower,
        upper=upper,
        seasonal=seasonal_offsets,
        trend_point=list(trend_fc.point),
        seasonality_strength=decomp.seasonality_strength,
        n_obs=n,
        alpha=alpha,
    )
