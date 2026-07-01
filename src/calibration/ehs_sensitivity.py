from __future__ import annotations

"""
Global sensitivity analysis of the Environmental Health Score (Morris method).

WHY
===
The EHS aggregates five risk components under expert-elicited weights. A
reviewer's fair objection is: *"are those weights driving an arbitrary number?"*
The answer requires a **global** sensitivity analysis — one that varies all
drivers simultaneously over their plausible ranges, not a one-factor-at-nominal
tweak. This module applies the Morris elementary-effects method (Morris 1991) in
its radial sampling variant (Campolongo, Cariboni & Saltelli 2011), which is
cheap, model-agnostic and dependency-light (numpy only).

WHAT IT REPORTS (per input)
===========================
  μ*  — mean absolute elementary effect: overall influence on the EHS.
  μ   — mean signed elementary effect: direction (does raising it raise EHS?).
  σ   — std of the elementary effects: non-linearity / interaction with others.
        A near-zero σ means the input acts additively; a large σ flags that its
        effect depends on the others (e.g. the dense-canopy regime switch).

All inputs are sampled in the unit cube [0,1] and mapped to their physical
ranges inside the model wrapper, so μ* is directly comparable across drivers of
different units.

References
==========
  Morris, M.D. (1991). Factorial sampling plans for preliminary computational
    experiments. Technometrics, 33(2), 161–174.
  Campolongo, F., Cariboni, J. & Saltelli, A. (2007/2011). An effective
    screening design / radial sampling for global sensitivity analysis.
    Environmental Modelling & Software.
"""

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from src.risk_engine.ehs import compute_ehs
from src.time_series.mann_kendall import MannKendallResult


@dataclass(frozen=True)
class MorrisResult:
    """Elementary-effects screening result, one entry per named input."""

    names: list[str]
    mu_star: list[float]   # mean |EE| — overall influence (dimensionless)
    mu: list[float]        # mean EE — direction
    sigma: list[float]     # std EE — non-linearity / interaction
    n_base: int            # number of radial base points used

    def ranked(self) -> list[tuple[str, float]]:
        """(name, μ*) pairs sorted by descending influence."""
        return sorted(zip(self.names, self.mu_star), key=lambda t: -t[1])


def morris_radial(
    model_unit: Callable[[np.ndarray], float],
    names: Sequence[str],
    *,
    n_base: int = 300,
    seed: int = 0,
    min_jump: float = 0.05,
) -> MorrisResult:
    """Radial Morris elementary effects for ``model_unit`` on the unit cube.

    Args:
        model_unit: maps a length-k vector in [0,1]^k to a scalar output.
        names:      input names (len k).
        n_base:     number of radial base points (each yields k elementary
                    effects). Reproducible via ``seed``.
        min_jump:   minimum |b_i - a_i| to avoid unstable small denominators.
    """
    k = len(names)
    rng = np.random.default_rng(seed)
    effects: list[list[float]] = [[] for _ in range(k)]

    done = 0
    attempts = 0
    while done < n_base and attempts < n_base * 20:
        attempts += 1
        a = rng.random(k)
        b = rng.random(k)
        if np.any(np.abs(b - a) < min_jump):
            continue
        y0 = model_unit(a)
        for i in range(k):
            c = a.copy()
            c[i] = b[i]
            effects[i].append((model_unit(c) - y0) / (b[i] - a[i]))
        done += 1

    mu = [float(np.mean(e)) if e else 0.0 for e in effects]
    mu_star = [float(np.mean(np.abs(e))) if e else 0.0 for e in effects]
    sigma = [float(np.std(e)) if e else 0.0 for e in effects]
    return MorrisResult(
        names=list(names), mu_star=mu_star, mu=mu, sigma=sigma, n_base=done,
    )


# ── EHS-specific driver bounds ────────────────────────────────────────────────
# Physical ranges spanning the realistic operating envelope of the PNSG
# portfolio. mean_ndvi crosses the dense-canopy threshold (0.80) on purpose, so
# the analysis exercises the regime switch and can expose its non-linearity.
_EHS_DRIVERS: list[tuple[str, float, float]] = [
    ("mean_ndvi",        0.30, 0.90),   # nivel base vegetal (cruza 0.80 dense-canopy)
    ("sens_slope",      -0.006, 0.001),  # pendiente de tendencia (NDVI/mes)
    ("anomaly_frac",     0.00, 0.50),   # fracción de meses anómalos
    ("residual_std",     0.00, 0.15),   # variabilidad inter-anual (estabilidad)
    ("recovery_frac",    0.50, 1.00),   # NDVI post/pre sequía (recuperación)
    ("mean_evi",         0.20, 0.60),   # EVI (relevante en dense-canopy)
]


def _map_unit(u: np.ndarray) -> dict:
    """Map a unit-cube vector to the physical EHS driver values."""
    out = {}
    for value, (name, lo, hi) in zip(u, _EHS_DRIVERS):
        out[name] = lo + float(value) * (hi - lo)
    return out


def _ehs_of_drivers(d: dict) -> float:
    """Evaluate the real EHS model at a physical driver vector."""
    slope = d["sens_slope"]
    # p_value fixed below 0.05 so the trend_risk term is always live under test.
    mk = MannKendallResult(
        s_statistic=0.0, z_score=0.0, p_value=0.01,
        kendalls_tau=0.0, sens_slope=slope,
        trend_direction="decreasing" if slope < 0 else "increasing",
        is_significant=True, alpha=0.05, n=60,
    )
    n_total = 60
    n_anom = int(round(d["anomaly_frac"] * n_total))
    return compute_ehs(
        mean_ndvi=d["mean_ndvi"],
        mk_result=mk,
        n_anomalous_months=n_anom,
        n_total_months=n_total,
        pre_drought_ndvi=1.0,
        post_drought_ndvi=d["recovery_frac"],
        residual_std=d["residual_std"],
        mean_evi=d["mean_evi"],
    ).ehs


def ehs_driver_sensitivity(*, n_base: int = 300, seed: int = 0) -> MorrisResult:
    """Morris screening of the EHS over its six physical drivers.

    Returns a MorrisResult ranking which driver most influences the EHS and
    whether the score behaves additively (small σ) or with regime interactions
    (large σ, e.g. around the dense-canopy NDVI switch).
    """
    names = [name for name, _, _ in _EHS_DRIVERS]

    def model_unit(u: np.ndarray) -> float:
        return _ehs_of_drivers(_map_unit(u))

    return morris_radial(model_unit, names, n_base=n_base, seed=seed)
