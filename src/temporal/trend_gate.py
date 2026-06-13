"""
SNTO — Mann-Kendall Trend Validity Gate (F2 scaffolding)
========================================================
Codifies, as a reusable component, the design rule already argued in
``docs/nota_metodologica_temporalidad.md``: *each pipeline emits only the
inference its temporal depth can sustain.*

The gate maps an effective series length to a readiness tier and states,
explicitly, whether a Mann-Kendall trend test is statistically justified and
whether a paired seasonal contrast (ΔEHS) is valid. It is the single source of
truth the dashboard and reports should consult before labelling any result a
"trend" rather than a "seasonal signal".

Thresholds (documented, not magic numbers)
-------------------------------------------
* ``MK_MIN_N = 4`` — below this the Mann-Kendall S statistic and its variance
  are not meaningfully defined; ``mann_kendall_test`` itself returns
  ``no_trend`` for ``n < 4``. This is the floor for *computing* MK at all.
* ``MK_ROBUST_N = 10`` — the large-sample normal approximation of the S
  statistic is generally considered adequate from ~10 observations
  (Hipel & McLeod 1994). Between 4 and 10 the test is computable but
  under-powered, so results are reported with explicit caution.
* For MONTHLY data with strong phenological seasonality, the test should run on
  the deseasonalised residual series (harmonic decomposition) spanning
  ``SEASONAL_CYCLES_MIN = 3`` annual cycles before a trend is treated as a firm
  empirical finding. This module reports that recommendation; it does not
  silently override the count-based tiers.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MK_MIN_N = 4
MK_ROBUST_N = 10
SEASONAL_DELTA_MIN_N = 2
SEASONAL_CYCLES_MIN = 3


class TrendReadiness(str, Enum):
    """How much temporal inference the available depth can sustain."""
    INSUFFICIENT = "insufficient"      # n < 2 — no temporal inference at all
    SEASONAL_ONLY = "seasonal_only"    # 2 ≤ n < 4 — paired ΔEHS valid, no trend
    TREND_EMERGING = "trend_emerging"  # 4 ≤ n < 10 — MK computable, under-powered
    TREND_ROBUST = "trend_robust"      # n ≥ 10 — MK normal approximation adequate


@dataclass(frozen=True)
class TrendGateResult:
    readiness: TrendReadiness
    n_obs: int
    mann_kendall_justified: bool
    seasonal_delta_valid: bool
    reason: str


def assess_trend_readiness(n_obs: int) -> TrendGateResult:
    """Classify what temporal inference ``n_obs`` valid observations sustain.

    Args:
        n_obs: number of *valid* observations in the (optionally deseasonalised)
            series — i.e. periods that passed the quality floor, not the number
            of periods the spec expected.

    Returns:
        TrendGateResult with the readiness tier and explicit booleans for the
        two inference types the project makes (Mann-Kendall trend vs paired
        seasonal ΔEHS contrast).
    """
    n = max(0, int(n_obs))

    if n < SEASONAL_DELTA_MIN_N:
        return TrendGateResult(
            readiness=TrendReadiness.INSUFFICIENT,
            n_obs=n,
            mann_kendall_justified=False,
            seasonal_delta_valid=False,
            reason=(
                f"{n} observación(es): insuficiente para cualquier inferencia "
                f"temporal (se requieren ≥ {SEASONAL_DELTA_MIN_N} para un "
                f"contraste pareado)."
            ),
        )

    if n < MK_MIN_N:
        return TrendGateResult(
            readiness=TrendReadiness.SEASONAL_ONLY,
            n_obs=n,
            mann_kendall_justified=False,
            seasonal_delta_valid=True,
            reason=(
                f"{n} observaciones: válido como contraste estacional pareado "
                f"(ΔEHS), pero Mann-Kendall requiere ≥ {MK_MIN_N} y no se aplica. "
                f"Es el estado actual de PNSG con dos escenas reales."
            ),
        )

    if n < MK_ROBUST_N:
        return TrendGateResult(
            readiness=TrendReadiness.TREND_EMERGING,
            n_obs=n,
            mann_kendall_justified=True,
            seasonal_delta_valid=True,
            reason=(
                f"{n} observaciones: Mann-Kendall es computable pero la "
                f"aproximación normal del estadístico S está infra-potenciada "
                f"(robusta desde ≥ {MK_ROBUST_N}). Reportar la tendencia con "
                f"cautela explícita."
            ),
        )

    return TrendGateResult(
        readiness=TrendReadiness.TREND_ROBUST,
        n_obs=n,
        mann_kendall_justified=True,
        seasonal_delta_valid=True,
        reason=(
            f"{n} observaciones: Mann-Kendall estadísticamente robusto "
            f"(aproximación normal adecuada). Para datos mensuales, ejecutar "
            f"sobre la serie desestacionalizada con ≥ {SEASONAL_CYCLES_MIN} "
            f"ciclos anuales."
        ),
    )
