"""
SNTO Phase 6 -- Rule-Based Impact Functions
============================================
Computes the expected environmental, economic, and evidence delta for each
intervention type applied to a single asset.

NO ML. NO PREDICTION. All outputs are derived from deterministic rules
that a territorial manager can follow on a printed decision tree.

RESTORATION IMPACT
==================
Three factors govern EHS recovery from physical restoration work:

  Headroom       (100 - ehs) / 100
    A healthy site (EHS=90) has only 10% room to improve.
    A critical site (EHS=30) has 70% room. Headroom scales the benefit.

  Causality factor  (SCM classification)
    LOCALIZED_IMPACT  : 1.00  Human pressure is the driver; reduce it
                               and the ecosystem recovers.
    MIXED             : 0.65  Cause is unclear; intervention helps partially.
    LANDSCAPE_DRIVEN  : 0.40  Climate is the driver; local restoration
                               cannot fix the weather. Limited effectiveness.

  Confidence factor  min(1.0, DCS / 80)
    Low evidence -> uncertain outcome. A DCS=40 asset's restoration may
    achieve zero improvement; a DCS=83 asset's restoration is predictable.

  delta_ehs = 18.0 * headroom * causality * confidence    (max ~18 pts)
  delta_risk = -0.18 * risk_score * causality * confidence

MONITORING ENHANCEMENT IMPACT
==============================
Monitoring does NOT change the environment. It changes our knowledge:
  delta_dcs   = 15 * headroom * (1 - dcs/200)    (diminishing returns)
  delta_risk  = -0.03                              (early detection -> smaller escalations)
  delta_ehs   = 0
  delta_vis   = 0

PROMOTION IMPACT
================
Visitor growth depends on current health and evidence quality:
  rate = 0.25 if EHS >= 80 | 0.15 if >= 70 | 0.08 if >= 60 | 0.05 otherwise
  delta_vis = int(visitor_capacity * rate * confidence_factor)

Environmental cost of more visitors:
  EHS >= 75 : pressure_factor = 1.5  (healthy site tolerates increased use)
  EHS <  75 : pressure_factor = 6.0  (stressed site degrades rapidly with more use)
  delta_ehs  = -pressure_factor * (delta_vis / visitor_capacity)

TERRITORIAL IMPACT SCORE (TIS)
================================
TIS = 100 * impact_score * cost_factor

  impact_score = ENV(55%) + ECON(30%) + EVID(15%)
    ENV  = 0.55 * (0.60 * env_ehs_norm + 0.40 * env_risk_norm)
    ECON = 0.30 * min(1, max(0, delta_vis) / territory_max_visitors)
    EVID = 0.15 * min(1, max(0, delta_dcs) / 15.0)

  cost_factor = 1.0 / (1.0 + sqrt(cost_eur / 10_000))
    Square-root penalty: doubling cost -> ~30% TIS reduction (not 50%).
    Expensive high-impact interventions can still score well.

  Negative deltas (e.g. promotion on stressed site increasing risk) are
  floored to 0 for the TIS calculation -- they appear in feasibility warnings.
"""
from __future__ import annotations

import math

from .models import (
    InterventionEffect,
    RESTORATION, MONITORING_ENHANCEMENT, PROMOTION,
    FEASIBILITY_VIABLE, FEASIBILITY_MARGINAL, FEASIBILITY_NOT_RECOMMENDED,
)

# ── Base costs (EUR) ───────────────────────────────────────────────────────

COST_RESTORATION     = 35_000
COST_MONITORING      = 4_500
COST_PROMOTION       = 12_000
COST_PROMOTION_LITE  = 1_500   # feasibility study for marginal assets

# ── Reference bounds for TIS normalization ─────────────────────────────────

_MAX_DELTA_EHS  = 18.0    # best possible restoration
_MAX_DELTA_RISK = 0.20    # best possible risk reduction
_MAX_DELTA_DCS  = 15.0    # best possible monitoring upgrade


# ── Shared helpers ─────────────────────────────────────────────────────────

_LOC_FACTOR: dict[str, float] = {
    "LOCALIZED_IMPACT":  1.00,
    "MIXED":             0.65,
    "LANDSCAPE_DRIVEN":  0.40,
}


def _conf(dcs: float) -> float:
    """DCS to [0, 1] confidence factor, diminishing above 80."""
    return min(1.0, dcs / 80.0)


def _dcs_label(dcs: float) -> str:
    if dcs >= 80: return "VERY HIGH"
    if dcs >= 70: return "HIGH"
    if dcs >= 55: return "MODERATE"
    return "LOW"


# ── RESTORATION impact ─────────────────────────────────────────────────────

def compute_restoration_effect(
    asset_id: str,
    ehs: float,
    risk_score: float,
    dcs: float,
    scm_classification: str,
    tier: int,
) -> InterventionEffect:
    """
    Compute expected impact of a physical restoration intervention.

    Restoration involves field crews removing sources of degradation
    (trail rehabilitation, riparian restoration, erosion control, etc.).
    """
    loc  = _LOC_FACTOR.get(scm_classification, 0.60)
    conf = _conf(dcs)
    headroom = max(0.0, (100.0 - ehs) / 100.0)

    delta_ehs  = round(18.0 * headroom * loc * conf, 2)
    delta_risk = round(-0.18 * risk_score * loc * conf, 3)
    delta_dcs  = round(5.0 * conf, 2)   # field validation improves evidence
    delta_vis  = 0

    # Feasibility classification
    if tier == 4:
        feasibility = FEASIBILITY_NOT_RECOMMENDED
        reason = (
            f"Asset is healthy (EHS={ehs:.0f}/100, Tier 4 -- Promotion). "
            "Physical restoration on a healthy site wastes EUR 35,000 for "
            f"only {delta_ehs:.1f} EHS improvement. "
            "Allocate to promotion campaign instead."
        )
    elif scm_classification == "LANDSCAPE_DRIVEN" and dcs < 55:
        feasibility = FEASIBILITY_MARGINAL
        reason = (
            f"Climate-driven degradation (LANDSCAPE) with LOW evidence "
            f"(DCS={dcs:.0f}). Local restoration is only 40% effective "
            "against climate stress. Gather field evidence before committing "
            "EUR 35,000."
        )
    elif dcs < 40:
        feasibility = FEASIBILITY_MARGINAL
        reason = (
            f"DCS={dcs:.0f} (VERY LOW evidence). Restoration outcome is "
            f"highly uncertain (predicted delta_ehs={delta_ehs:.1f} but "
            "confidence interval is wide). Data collection upgrade required first."
        )
    else:
        feasibility = FEASIBILITY_VIABLE
        reason = (
            f"Environmental headroom {headroom:.0%}, {scm_classification} "
            f"driver, DCS={dcs:.0f} ({_dcs_label(dcs)} evidence). "
            f"Expected EHS gain: +{delta_ehs:.1f} pts."
        )

    return InterventionEffect(
        asset_id=asset_id,
        intervention_type=RESTORATION,
        delta_ehs=delta_ehs,
        delta_risk=delta_risk,
        delta_dcs=delta_dcs,
        delta_visitors=delta_vis,
        cost_eur=COST_RESTORATION,
        feasibility=feasibility,
        feasibility_reason=reason,
    )


# ── MONITORING ENHANCEMENT impact ──────────────────────────────────────────

def compute_monitoring_effect(
    asset_id: str,
    dcs: float,
) -> InterventionEffect:
    """
    Compute expected impact of a monitoring infrastructure upgrade.

    Monitoring upgrades include: additional Sentinel-2 pass processing,
    automated anomaly detection, field validation stations, visitor counters.
    The primary output is improved DCS; the secondary output is earlier
    detection of degradation events (reducing risk escalation).
    """
    headroom = max(0.0, (100.0 - dcs) / 100.0)
    # Diminishing returns: low-DCS assets benefit much more than high-DCS ones
    delta_dcs  = round(15.0 * headroom * (1.0 - dcs / 200.0), 2)
    delta_risk = -0.03   # early detection -> faster management response
    delta_ehs  = 0.0     # monitoring changes knowledge, not the environment
    delta_vis  = 0

    if dcs >= 85:
        feasibility = FEASIBILITY_MARGINAL
        reason = (
            f"DCS={dcs:.0f} is already VERY HIGH. Monitoring upgrade yields "
            f"only +{delta_dcs:.1f} DCS points (diminishing returns). "
            "EUR 4,500 may be better deployed elsewhere."
        )
    else:
        feasibility = FEASIBILITY_VIABLE
        reason = (
            f"DCS={dcs:.0f} ({_dcs_label(dcs)} evidence). Monitoring upgrade "
            f"will add +{delta_dcs:.1f} DCS points, enabling more confident "
            "future management decisions."
        )

    return InterventionEffect(
        asset_id=asset_id,
        intervention_type=MONITORING_ENHANCEMENT,
        delta_ehs=delta_ehs,
        delta_risk=delta_risk,
        delta_dcs=delta_dcs,
        delta_visitors=delta_vis,
        cost_eur=COST_MONITORING,
        feasibility=feasibility,
        feasibility_reason=reason,
    )


# ── PROMOTION impact ───────────────────────────────────────────────────────

def compute_promotion_effect(
    asset_id: str,
    ehs: float,
    dcs: float,
    risk_score: float,
    visitor_capacity: int,
    tier: int,
) -> InterventionEffect:
    """
    Compute expected impact of a digital tourism promotion campaign.

    Promotion drives more visitors. For healthy assets (EHS >= 75),
    increased visitor volume is manageable and economically beneficial.
    For degraded assets, more visitors accelerate the degradation.
    """
    conf = _conf(dcs)

    # Visitor growth rate depends on current environmental quality
    if ehs >= 80:
        rate = 0.25    # excellent assets attract 25% more with promotion
    elif ehs >= 70:
        rate = 0.15
    elif ehs >= 60:
        rate = 0.08    # borderline -- limited promotion scope
    else:
        rate = 0.05    # minimal; asset not suited for promotion

    delta_vis = int(visitor_capacity * rate * conf)
    visitor_pressure = delta_vis / max(visitor_capacity, 1)   # 0-1

    # Environmental cost: more visitors = more wear
    if ehs >= 75:
        delta_ehs  = round(-1.5 * visitor_pressure, 2)
        delta_risk = round(+0.02 * visitor_pressure, 3)
    else:
        # Stressed site degrades much faster under increased use
        delta_ehs  = round(-6.0 * visitor_pressure, 2)
        delta_risk = round(+0.08 * visitor_pressure, 3)

    # Marketing data generation slightly improves evidence
    delta_dcs = round(2.0 * conf, 2) if dcs >= 55 else 0.0

    # Feasibility and cost
    if tier == 4:
        cost        = COST_PROMOTION
        feasibility = FEASIBILITY_VIABLE
        reason = (
            f"Tier 4 (PROMOTION OPPORTUNITY): EHS={ehs:.0f}/100, "
            f"DCS={dcs:.0f}/100. Expected +{delta_vis:,} visitors/yr. "
            f"Environmental impact is acceptably low (delta_ehs={delta_ehs:.1f})."
        )
    elif ehs >= 65 and dcs >= 50:
        cost        = COST_PROMOTION_LITE
        feasibility = FEASIBILITY_MARGINAL
        reason = (
            f"EHS={ehs:.0f}/100 and DCS={dcs:.0f}/100 are borderline. "
            "A promotion feasibility study (EUR 1,500) is recommended "
            "before committing to a full EUR 12,000 campaign."
        )
    else:
        cost        = COST_PROMOTION_LITE
        feasibility = FEASIBILITY_NOT_RECOMMENDED
        reason = (
            f"EHS={ehs:.0f}/100 -- asset is degraded. Additional visitors "
            "will worsen conditions. delta_ehs={d:.1f}, delta_risk=+{r:.3f}. "
            "Restore environmental health before any promotion.".format(
                d=delta_ehs, r=delta_risk
            )
        )

    return InterventionEffect(
        asset_id=asset_id,
        intervention_type=PROMOTION,
        delta_ehs=delta_ehs,
        delta_risk=delta_risk,
        delta_dcs=delta_dcs,
        delta_visitors=delta_vis,
        cost_eur=cost,
        feasibility=feasibility,
        feasibility_reason=reason,
    )


# ── Territorial Impact Score ───────────────────────────────────────────────

def compute_tis(
    delta_ehs: float,
    delta_risk: float,
    delta_dcs: float,
    delta_visitors: int,
    cost_eur: int,
    territory_max_visitors: int,
) -> float:
    """
    Territorial Impact Score (TIS) in [0, 100].
    Higher = more territorial benefit per euro invested.

    Three weighted benefit dimensions:
      Environmental (55%)  : EHS improvement + risk reduction
      Economic      (30%)  : visitor increase / territory max (relative gain)
      Evidence      (15%)  : DCS improvement (enables future decisions)

    Cost modifier: TIS is penalised by cost via a square-root function,
    so that expensive interventions with high impact still score well,
    while cheap interventions with negligible impact remain low.

    Negative environment or risk deltas (e.g. promotion on degraded site)
    are floored to 0 -- captured in feasibility warnings, not double-penalised.
    """
    max_vis = max(1, territory_max_visitors)

    env_ehs  = min(1.0, max(0.0, delta_ehs)  / _MAX_DELTA_EHS)
    env_risk = min(1.0, max(0.0, -delta_risk) / _MAX_DELTA_RISK)
    env  = 0.55 * (0.60 * env_ehs + 0.40 * env_risk)
    econ = 0.30 * min(1.0, max(0.0, delta_visitors) / max_vis)
    evid = 0.15 * min(1.0, max(0.0, delta_dcs)      / _MAX_DELTA_DCS)

    impact = env + econ + evid   # 0 to 1.0

    # Square-root cost penalty: TIS is bounded as cost -> infinity
    cost_factor = 1.0 / (1.0 + math.sqrt(max(0, cost_eur) / 10_000))

    return round(100.0 * impact * cost_factor, 1)
