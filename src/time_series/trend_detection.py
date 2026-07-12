"""
Shared trend-detection step: deseasonalise, then Mann-Kendall.

Both temporal pipelines must detect trend the same way. Before this module the
offline analysis (``scripts/run_timeseries_analysis.py``) deseasonalised the
monthly NDVI series before the Mann-Kendall test while the live GEE pipeline
(``run_pipeline_a_timeseries.py``) tested the raw seasonal series — a silent
divergence that also contradicted the methodology notes. This composition layer
is the single source of truth for "how SNTO turns a monthly VI series into a
trend verdict", so the two pipelines can never drift again.

Chain: harmonic deseasonalisation (decomposition.py) → optional Yue-Pilon
pre-whitening (prewhitening.py) → tie-corrected Mann-Kendall (mann_kendall.py).
See docs/nota_metodologica_rigor_estadistico.md for the justification.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.time_series.decomposition import harmonic_decompose
from src.time_series.mann_kendall import MannKendallResult, mann_kendall_test
from src.time_series.prewhitening import trend_free_prewhiten

SEASONAL_PERIOD = 12  # monthly series → annual cycle


@dataclass(frozen=True)
class DeseasonalizedTrend:
    """Mann-Kendall verdict plus the series it ran on and provenance flags."""

    mk: MannKendallResult
    deseasonalized_series: list[float]   # observed − seasonal (pre pre-whitening)
    tested_series: list[float]           # series MK ran on (post pre-whitening)
    deseasonalised: bool                 # False when series too short (< period)
    seasonality_strength: float | None
    prewhitened: bool
    lag1_autocorr: float | None


def deseasonalized_mann_kendall(
    series: list[float],
    *,
    period: int = SEASONAL_PERIOD,
    prewhiten: bool = False,
) -> DeseasonalizedTrend:
    """Deseasonalise (if a full cycle is available) and run Mann-Kendall.

    Args:
        series:   monthly VI values in chronological order.
        period:   seasonal period (12 for monthly annual cycles).
        prewhiten: apply Yue-Pilon trend-free pre-whitening to the
                   deseasonalised series before the test (robustness pass).

    Returns:
        DeseasonalizedTrend. For series shorter than ``period`` the raw series is
        used (``deseasonalised=False``); Mann-Kendall itself guards n < 4.
    """
    if len(series) >= period:
        decomp = harmonic_decompose(series, period=period)
        deseason = list(decomp.deseasonalized)
        deseasonalised = True
        strength = decomp.seasonality_strength
    else:
        deseason = list(series)
        deseasonalised = False
        strength = None

    tested = deseason
    prewhitened_applied = False
    lag1: float | None = None
    if prewhiten:
        pw = trend_free_prewhiten(deseason)
        tested = pw.series
        prewhitened_applied = pw.applied
        lag1 = pw.lag1_autocorr

    return DeseasonalizedTrend(
        mk=mann_kendall_test(tested),
        deseasonalized_series=deseason,
        tested_series=tested,
        deseasonalised=deseasonalised,
        seasonality_strength=strength,
        prewhitened=prewhitened_applied,
        lag1_autocorr=lag1,
    )
