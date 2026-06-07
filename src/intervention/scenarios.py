"""
SNTO Phase 6 -- Scenario Comparison, Budget Optimizer & Counterfactual
=======================================================================
Three analytical engines in one module:

  1. SCENARIO COMPARISON ENGINE
     compare_scenarios(asset, territory_max_visitors)
       -> AssetScenarioComparison

     Computes all 5 scenarios (A-E) for one asset and selects the
     best intervention following DCS evidence gates and tier logic.

  2. TIS BUDGET OPTIMIZER
     allocate_tis_budget(comparisons, assets_by_id, total_budget_eur)
       -> TISBudgetResult

     Ranks interventions by TIS (highest first) and allocates budget
     greedily until exhausted. DCS gate: assets with DCS < 55 are
     eligible only for monitoring enhancement.

  3. COUNTERFACTUAL REASONING ENGINE
     compute_counterfactual(asset) -> CounterfactualResult

     Projects the 3-year environmental trajectory under no intervention.
     Quantifies the economic cost of inaction (visitor revenue loss +
     future restoration premium) and assigns uncertainty based on DCS.

COMBINED SCENARIO (E) LOGIC
============================
Tier 1-2 (degraded) : RESTORATION + MONITORING
  delta_ehs  = restoration_ehs    (monitoring does not add EHS)
  delta_risk = restoration_risk + monitoring_risk (additive)
  delta_dcs  = restoration_dcs + monitoring_dcs  (additive, capped at headroom)
  cost       = 35,000 + 4,500 = 39,500 EUR

Tier 4 (healthy)    : PROMOTION + MONITORING
  delta_vis  = promotion_vis      (promotion drives visitors)
  delta_ehs  = promotion_ehs      (slight wear from more visitors)
  delta_dcs  = promotion_dcs + monitoring_dcs (capped)
  cost       = 12,000 + 4,500 = 16,500 EUR

Tier 3 (stable)     : MONITORING ONLY
  Same as Scenario C.
  cost       = 4,500 EUR
"""
from __future__ import annotations

import math
from .models import (
    ScenarioResult, AssetScenarioComparison,
    CounterfactualYear, CounterfactualResult,
    TISBudgetItem, TISBudgetResult,
    SCENARIO_LABELS,
    NO_INTERVENTION, RESTORATION, MONITORING_ENHANCEMENT, PROMOTION, COMBINED,
    FEASIBILITY_VIABLE, FEASIBILITY_NOT_RECOMMENDED,
)
from .impact import (
    compute_restoration_effect,
    compute_monitoring_effect,
    compute_promotion_effect,
    compute_tis,
    COST_RESTORATION, COST_MONITORING, COST_PROMOTION, COST_PROMOTION_LITE,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. SCENARIO COMPARISON ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def compare_scenarios(
    asset,                      # TerritorialAsset (from Phase 5)
    territory_max_visitors: int,
) -> AssetScenarioComparison:
    """
    Build all 5 scenario results for one asset and identify the recommended one.

    Scenarios:
      A -- No Intervention   (baseline, zero cost, zero benefit)
      B -- Restoration       (field work, EUR 35,000)
      C -- Monitoring Enh.   (data quality, EUR 4,500)
      D -- Promotion         (visitor growth, EUR 1,500-12,000)
      E -- Combined Optimal  (tier-dependent combination)
    """
    tier = asset.tier or 3
    dcs  = asset.dcs

    # Compute individual intervention effects
    eff_r = compute_restoration_effect(
        asset.asset_id, asset.ehs, asset.risk_score,
        dcs, asset.scm_classification, tier,
    )
    eff_m = compute_monitoring_effect(asset.asset_id, dcs)
    eff_p = compute_promotion_effect(
        asset.asset_id, asset.ehs, dcs, asset.risk_score,
        asset.visitor_capacity_annual, tier,
    )

    # Combined scenario deltas
    if tier in (1, 2):
        # Degraded asset: restoration heals + monitoring builds post-action evidence
        c_ehs  = eff_r.delta_ehs
        c_risk = eff_r.delta_risk + eff_m.delta_risk
        c_dcs  = min(100.0 - dcs, eff_r.delta_dcs + eff_m.delta_dcs)
        c_vis  = 0
        c_cost = COST_RESTORATION + COST_MONITORING
    elif tier == 4:
        # Healthy asset: promote + monitor to build evidence pre-campaign
        c_ehs  = eff_p.delta_ehs
        c_risk = eff_p.delta_risk
        c_dcs  = min(100.0 - dcs, eff_p.delta_dcs + eff_m.delta_dcs)
        c_vis  = eff_p.delta_visitors
        c_cost = eff_p.cost_eur + COST_MONITORING
    else:
        # Tier 3 (stable): monitoring only -- same as C
        c_ehs  = eff_m.delta_ehs
        c_risk = eff_m.delta_risk
        c_dcs  = eff_m.delta_dcs
        c_vis  = 0
        c_cost = COST_MONITORING

    def _make(code, intv, d_ehs, d_risk, d_dcs, d_vis, cost, feas=FEASIBILITY_VIABLE):
        tis = compute_tis(d_ehs, d_risk, d_dcs, d_vis, cost, territory_max_visitors)
        return ScenarioResult(
            asset_id=asset.asset_id,
            scenario_code=code,
            scenario_label=SCENARIO_LABELS[code],
            intervention_type=intv,
            delta_ehs=round(d_ehs, 2),
            delta_risk=round(d_risk, 3),
            delta_dcs=round(d_dcs, 2),
            delta_visitors=int(d_vis),
            projected_ehs=round(min(100.0, max(0.0, asset.ehs + d_ehs)), 1),
            projected_risk=round(min(1.0, max(0.0, asset.risk_score + d_risk)), 3),
            projected_dcs=round(min(100.0, max(0.0, dcs + d_dcs)), 1),
            projected_visitors=max(0, asset.visitor_capacity_annual + int(d_vis)),
            cost_eur=cost,
            tis=tis,
            feasibility=feas,
        )

    scenarios: dict[str, ScenarioResult] = {
        "A": _make("A", NO_INTERVENTION,        0,              0,              0,              0, 0),
        "B": _make("B", RESTORATION,            eff_r.delta_ehs, eff_r.delta_risk,
                   eff_r.delta_dcs, 0,              COST_RESTORATION, eff_r.feasibility),
        "C": _make("C", MONITORING_ENHANCEMENT, 0,              eff_m.delta_risk,
                   eff_m.delta_dcs, 0,              COST_MONITORING,  eff_m.feasibility),
        "D": _make("D", PROMOTION,              eff_p.delta_ehs, eff_p.delta_risk,
                   eff_p.delta_dcs, eff_p.delta_visitors, eff_p.cost_eur, eff_p.feasibility),
        "E": _make("E", COMBINED,               c_ehs, c_risk, c_dcs, c_vis, c_cost),
    }

    best_code, reason = _select_best(asset, scenarios, tier, dcs)

    return AssetScenarioComparison(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        current_tier=tier,
        current_ehs=asset.ehs,
        current_dcs=dcs,
        scenarios=scenarios,
        best_scenario_code=best_code,
        best_scenario_label=SCENARIO_LABELS[best_code],
        best_scenario_reason=reason,
        dcs_constrained=(dcs < 55),
    )


def _select_best(asset, scenarios, tier, dcs) -> tuple[str, str]:
    """Apply evidence gate and tier logic to identify the recommended scenario."""

    # DCS gate: insufficient evidence -> monitoring before any capital spend
    if dcs < 55:
        return "C", (
            f"DCS={dcs:.0f} (LOW evidence). Monitoring enhancement is the mandatory "
            "first step. Gather evidence before committing EUR 35,000+ to restoration "
            "or promotion. Monitoring will raise DCS and enable confident future action."
        )

    if tier == 4:
        # Promotion-ready: compare D vs E (promotion vs promotion+monitoring)
        if scenarios["E"].tis >= scenarios["D"].tis:
            return "E", (
                f"Tier 4 (PROMOTION OPPORTUNITY). Combined Promotion + Monitoring "
                f"delivers TIS={scenarios['E'].tis:.1f} vs Promotion alone "
                f"TIS={scenarios['D'].tis:.1f}. Monitoring before campaign launch "
                "strengthens evidence and reduces campaign risk."
            )
        return "D", (
            f"Tier 4 (PROMOTION OPPORTUNITY). Promotion alone delivers "
            f"TIS={scenarios['D'].tis:.1f}, which exceeds the combined scenario "
            f"(TIS={scenarios['E'].tis:.1f}) -- monitoring overhead reduces "
            "cost-efficiency when DCS is already sufficient."
        )

    if tier in (1, 2):
        # Urgent/preventive: compare B (restoration) vs E (restoration+monitoring)
        tis_b = scenarios["B"].tis
        tis_e = scenarios["E"].tis
        if tis_e >= tis_b:
            return "E", (
                f"Tier {tier} (urgent intervention). Combined Restoration + Monitoring "
                f"delivers TIS={tis_e:.1f}, higher than restoration alone "
                f"(TIS={tis_b:.1f}). Post-restoration monitoring is critical "
                "for tracking recovery and catching setbacks early."
            )
        return "B", (
            f"Tier {tier} (urgent intervention). Restoration alone delivers "
            f"TIS={tis_b:.1f} vs combined TIS={tis_e:.1f}. The EUR 4,500 monitoring "
            "overhead reduces cost-efficiency when restoration dominates the budget. "
            "Add monitoring separately if budget allows."
        )

    # Tier 3 (stable): monitoring is the correct and most efficient choice
    return "C", (
        f"Tier 3 (ROUTINE MONITORING). Asset is stable (EHS={asset.ehs:.0f}/100). "
        "Monitoring enhancement (TIS={t:.1f}) preserves evidence quality at low cost. "
        "Restoration would be wasteful; promotion requires higher EHS.".format(
            t=scenarios["C"].tis
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. COUNTERFACTUAL REASONING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def compute_counterfactual(asset) -> CounterfactualResult:
    """
    Project the 3-year no-intervention trajectory for one asset.

    Key assumptions:
      - Declining LOCALIZED assets: human pressure continues or grows
        (no management action = no reduction in visitor stress).
      - Declining LANDSCAPE assets: climate variability continues; slight
        improvement possible but not guaranteed.
      - Stable/improving assets: slow natural aging (~0.3-1.0 EHS/yr).

    Economic cost of inaction:
      visitor_revenue_loss  = cumulative_visitors_lost * EUR 45 / visitor
      restoration_premium   = cost to fix the asset after 3 years of neglect
                              (escalates as condition worsens)
    """
    trend = asset.trend_direction
    scm   = asset.scm_classification
    ehs   = asset.ehs
    risk  = asset.risk_score
    dcs   = asset.dcs

    # Annual EHS decline rate (starting value, may accelerate)
    if trend == "decreasing":
        if scm == "LOCALIZED_IMPACT":
            base_decline = max(2.0, 5.0 * (1.0 - ehs / 100.0))
        elif scm == "LANDSCAPE_DRIVEN":
            base_decline = max(1.0, 3.0 * (1.0 - ehs / 100.0))
        else:  # MIXED
            base_decline = max(1.5, 4.0 * (1.0 - ehs / 100.0))
    elif trend == "no_trend" and ehs < 60:
        base_decline = 1.0    # slow drift downward for stressed stable assets
    elif trend == "no_trend":
        base_decline = 0.3    # healthy stable assets degrade very slowly
    else:
        # Improving: slight continued improvement, but nature is never linear
        base_decline = -0.5   # slight annual gain continues

    # Annual risk increase rate
    if trend == "decreasing":
        base_risk_rise = 0.04 * (1.0 + (1.0 - ehs / 100.0))
    else:
        base_risk_rise = 0.01

    # Project year by year
    years: list[CounterfactualYear] = []
    cur_ehs  = ehs
    cur_risk = risk

    for yr in range(1, 4):
        # Acceleration: as EHS drops, degradation speeds up (feedback loop)
        acceleration = 1.0 + 0.15 * (yr - 1) * max(0.0, 1.0 - cur_ehs / 100.0)
        yr_decline   = base_decline * acceleration
        yr_risk_rise = base_risk_rise * acceleration

        new_ehs  = max(0.0, cur_ehs  - yr_decline)
        new_risk = min(1.0, cur_risk + yr_risk_rise)

        # Alert level escalation check
        alert_esc = ""
        orig_alert = asset.alert_level
        if new_ehs < 30 and orig_alert not in ("CRITICAL_INTERVENTION",):
            alert_esc = "CRITICAL_INTERVENTION"
        elif new_ehs < 45 and orig_alert in ("NORMAL", "PREVENTIVE_ACTION"):
            alert_esc = "URGENT_MONITORING"
        elif new_ehs < 60 and orig_alert == "NORMAL":
            alert_esc = "PREVENTIVE_ACTION"

        # Visitor impact: tourists perceive and respond to environmental quality
        ehs_drop = ehs - new_ehs
        if ehs_drop >= 15:
            visitor_pct = -20.0
        elif ehs_drop >= 8:
            visitor_pct = -10.0
        elif ehs_drop >= 4:
            visitor_pct = -4.0
        else:
            visitor_pct = 0.0

        years.append(CounterfactualYear(
            year=yr,
            ehs=round(new_ehs, 1),
            risk=round(new_risk, 3),
            visitor_pct_change=visitor_pct,
            alert_escalation=alert_esc,
        ))
        cur_ehs  = new_ehs
        cur_risk = new_risk

    # Cumulative visitor loss (absolute)
    cumulative_loss = int(sum(
        asset.visitor_capacity_annual * abs(min(0.0, y.visitor_pct_change)) / 100.0
        for y in years
    ))

    # Economic cost: lost tourism revenue + higher future restoration cost
    revenue_loss = cumulative_loss * 45   # EUR 45 per visitor (conservative estimate)

    yr3_ehs = years[2].ehs
    if yr3_ehs < 30:
        restoration_premium = 55_000   # emergency work, higher contractor rates
    elif yr3_ehs < 45:
        restoration_premium = 35_000   # standard restoration
    else:
        restoration_premium = 15_000   # light preventive work still needed

    economic_cost = revenue_loss + restoration_premium

    # Trajectory labels
    drop_3yr = ehs - years[2].ehs
    if drop_3yr >= 8:
        ehs_traj = "ACCELERATING_DECLINE"
    elif drop_3yr >= 2:
        ehs_traj = "DECLINING"
    else:
        ehs_traj = "STABLE"

    risk_rise_3yr = years[2].risk - risk
    if risk_rise_3yr >= 0.10:
        risk_traj = "RAPIDLY_RISING"
    elif risk_rise_3yr >= 0.04:
        risk_traj = "RISING"
    else:
        risk_traj = "STABLE"

    uncertainty = "HIGH" if dcs < 50 else ("MODERATE" if dcs < 70 else "LOW")

    narrative = _cf_narrative(asset, years, ehs_traj, risk_traj, economic_cost)

    return CounterfactualResult(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        years=years,
        ehs_trajectory=ehs_traj,
        risk_trajectory=risk_traj,
        cumulative_visitor_loss=cumulative_loss,
        estimated_inaction_cost_eur=economic_cost,
        uncertainty=uncertainty,
        narrative=narrative,
    )


def _cf_narrative(asset, years, ehs_traj, risk_traj, economic_cost) -> str:
    yr3 = years[2]
    trend_desc = {
        "decreasing": "continuing its measured decline",
        "no_trend":   "stationary but environmentally vulnerable",
        "increasing": "in gradual recovery (but without management, rate may slow)",
    }.get(asset.trend_direction, "uncertain")

    ehs_desc = {
        "ACCELERATING_DECLINE": (
            f"falling to {yr3.ehs:.0f}/100 by year 3 -- a threshold that "
            "typically triggers emergency intervention at EUR 55,000+"
        ),
        "DECLINING": f"declining to {yr3.ehs:.0f}/100 by year 3",
        "STABLE":    f"remaining near {yr3.ehs:.0f}/100 over three years",
    }[ehs_traj]

    risk_desc = {
        "RAPIDLY_RISING": "with risk escalating sharply",
        "RISING":         "with gradual risk escalation",
        "STABLE":         "with risk remaining relatively stable",
    }[risk_traj]

    escalation = next((y.alert_escalation for y in years if y.alert_escalation), "")
    esc_note = (
        f" Alert level is expected to escalate to {escalation} within 3 years."
        if escalation else ""
    )

    return (
        f"{asset.name} is currently {trend_desc}. Without intervention, "
        f"environmental health is projected to be {ehs_desc}, {risk_desc}.{esc_note} "
        f"Estimated cost of inaction over 3 years: EUR {economic_cost:,} "
        "(visitor revenue loss + future restoration premium)."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. TIS BUDGET OPTIMIZER
# ─────────────────────────────────────────────────────────────────────────────

def allocate_tis_budget(
    comparisons: list,           # list[AssetScenarioComparison]
    assets_by_id: dict,          # asset_id -> TerritorialAsset
    total_budget_eur: int,
) -> TISBudgetResult:
    """
    Rank interventions by TIS (highest first) and allocate budget greedily.

    Tie-breaking: equal TIS -> higher urgency tier first (Tier 1 > 2 > 3 > 4).

    DCS constraint:
      Assets with DCS < 55 are already recommended monitoring-only (Scenario C)
      by compare_scenarios(). This budget optimizer inherits that constraint
      automatically by using the best_scenario_code from each comparison.
    """
    # Build ranked candidate list
    candidates = []
    for comp in comparisons:
        asset   = assets_by_id[comp.asset_id]
        chosen  = comp.scenarios[comp.best_scenario_code]
        tier    = asset.tier or 3
        candidates.append((chosen.tis, tier, comp, chosen, asset))

    # Sort: highest TIS first; lower tier (more urgent) breaks ties
    candidates.sort(key=lambda x: (-x[0], x[1]))

    remaining = total_budget_eur
    funded:   list[TISBudgetItem] = []
    deferred: list[TISBudgetItem] = []

    tot_ehs  = 0.0
    tot_risk = 0.0
    tot_vis  = 0
    tot_dcs  = 0.0
    weighted_tis  = 0.0
    weighted_cost = 0

    for tis, tier, comp, scenario, asset in candidates:
        cost = scenario.cost_eur

        if cost == 0:
            # Zero-cost items (Scenario A / no intervention) are never allocated
            continue

        label = SCENARIO_LABELS[comp.best_scenario_code] + " -- " + scenario.intervention_type

        if cost <= remaining:
            remaining -= cost
            item = TISBudgetItem(
                asset_id=asset.asset_id,
                asset_name=asset.name,
                tier=tier,
                scenario_code=comp.best_scenario_code,
                intervention_label=label,
                cost_eur=cost,
                tis=tis,
                funded=True,
                fund_rationale=(
                    f"TIS={tis:.1f}/100. EUR {cost:,} allocated from "
                    f"EUR {remaining + cost:,} remaining."
                ),
                defer_reason="",
            )
            funded.append(item)
            tot_ehs  += scenario.delta_ehs
            tot_risk += scenario.delta_risk
            tot_vis  += scenario.delta_visitors
            tot_dcs  += scenario.delta_dcs
            weighted_tis  += tis * cost
            weighted_cost += cost
        else:
            item = TISBudgetItem(
                asset_id=asset.asset_id,
                asset_name=asset.name,
                tier=tier,
                scenario_code=comp.best_scenario_code,
                intervention_label=label,
                cost_eur=cost,
                tis=tis,
                funded=False,
                fund_rationale="",
                defer_reason=(
                    f"Insufficient budget (EUR {remaining:,} remaining < "
                    f"EUR {cost:,} needed). Defer to next budget cycle."
                ),
            )
            deferred.append(item)

    portfolio_tis = (
        round(weighted_tis / weighted_cost, 1) if weighted_cost > 0 else 0.0
    )
    total_allocated = total_budget_eur - remaining

    return TISBudgetResult(
        total_budget_eur=total_budget_eur,
        total_allocated_eur=total_allocated,
        remaining_eur=remaining,
        funded_items=funded,
        deferred_items=deferred,
        portfolio_delta_ehs=round(tot_ehs, 1),
        portfolio_delta_risk=round(tot_risk, 3),
        portfolio_delta_visitors=tot_vis,
        portfolio_delta_dcs=round(tot_dcs, 1),
        portfolio_tis=portfolio_tis,
    )
