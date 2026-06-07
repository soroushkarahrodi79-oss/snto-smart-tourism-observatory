"""
SNTO Phase 6 -- Intervention Impact & Scenario Planning Report Generator
=========================================================================
Generates the 8-section institutional report answering:

  "What happens if we intervene here instead of there?"

REPORT STRUCTURE
================
  Section 1  Intervention Model Overview
             Three intervention types, their logic, costs, and when viable.

  Section 2  Asset Scenario Comparison
             For each asset: 5-scenario table (A-E) with TIS scores.

  Section 3  Recommended Scenarios (summary table)
             Best scenario per asset, reason, DCS constraint flag.

  Section 4  TIS-Optimised Budget Allocation
             EUR 100K allocated by Territorial Impact Score rank.

  Section 5  Counterfactual Analysis (top 5 priority assets)
             3-year no-intervention trajectory + cost of inaction.

  Section 6  Portfolio Impact View
             Territory-level totals: DELTA_EHS, DELTA_RISK, DELTA_VIS, DELTA_DCS.

  Section 7  Decision Explanation Layer
             Chosen / rejected / why / confidence / trade-offs per asset.

  Section 8  Management Summary
             4-bullet executive summary for the director.

LANGUAGE POLICY
===============
  NO NDVI, NO Mann-Kendall, NO z-scores.
  YES to EHS, DCS, TIS, EUR values, visitor counts.
  YES to plain-language cause descriptions.
"""
from __future__ import annotations

from .models import (
    AssetScenarioComparison,
    CounterfactualResult,
    TISBudgetResult,
    DecisionExplanation,
    Phase6ReportSection,
    Phase6Report,
    SCENARIO_LABELS,
    FEASIBILITY_NOT_RECOMMENDED, FEASIBILITY_MARGINAL,
)
from .impact import COST_RESTORATION, COST_MONITORING, COST_PROMOTION


# ── Public entry point ─────────────────────────────────────────────────────

def generate_phase6_report(
    territory_name: str,
    report_date: str,
    assets: list,
    comparisons: list,          # list[AssetScenarioComparison]
    counterfactuals: list,      # list[CounterfactualResult]
    budget: TISBudgetResult,
    explanations: list,         # list[DecisionExplanation]
) -> Phase6Report:
    """Assemble the full 8-section Phase 6 report."""
    assets_by_id = {a.asset_id: a for a in assets}
    sections = [
        _s1_intervention_model(),
        _s2_scenario_comparison(comparisons, assets_by_id),
        _s3_recommended_scenarios(comparisons, assets_by_id),
        _s4_budget(budget),
        _s5_counterfactual(counterfactuals),
        _s6_portfolio_impact(budget, comparisons, assets),
        _s7_decision_explanation(explanations, assets_by_id),
        _s8_management_summary(territory_name, report_date, assets, comparisons, budget, counterfactuals),
    ]
    return Phase6Report(
        territory_name=territory_name,
        report_date=report_date,
        n_assets=len(assets),
        sections=sections,
    )


# ── Section 1: Intervention Model Overview ─────────────────────────────────

def _s1_intervention_model() -> Phase6ReportSection:
    lines = [
        "PHASE 6 transforms SNTO from a prioritisation system into a decision",
        "impact simulation system. For each asset, three intervention types are",
        "evaluated and compared against a no-intervention baseline.",
        "",
        "INTERVENTION TYPE A -- RESTORATION  (EUR 35,000)",
        "  Physical field intervention to reduce the source of degradation.",
        "  Examples: trail rehabilitation, riparian bank stabilisation, erosion",
        "  control barriers, visitor access restriction barriers.",
        "  Best for  : Tier 1-2 assets with LOCALIZED (human-driven) cause.",
        "  Less useful: LANDSCAPE-DRIVEN degradation (climate is the driver,",
        "               local action has limited effect).",
        "  EHS gain  : up to 18 points (scales with headroom x causality x evidence).",
        "  Risk gain : up to -0.20 (risk reduction).",
        "",
        "INTERVENTION TYPE B -- MONITORING ENHANCEMENT  (EUR 4,500)",
        "  Infrastructure upgrade to improve evidence quality (DCS).",
        "  Examples: satellite data subscription, field validation stations,",
        "  automated visitor counters, anomaly detection subscriptions.",
        "  Best for  : any asset with DCS < 70 (highest marginal value).",
        "  Less useful: assets already at DCS >= 85 (diminishing returns).",
        "  DCS gain  : up to 15 points (highest for low-DCS assets).",
        "  Secondary : -0.03 risk reduction (early detection enables faster response).",
        "",
        "INTERVENTION TYPE C -- PROMOTION INVESTMENT  (EUR 12,000 / EUR 1,500)",
        "  Digital and physical marketing campaign to grow visitor numbers.",
        "  Full campaign (EUR 12,000) for Tier 4 assets (EHS >= 75, DCS >= 55).",
        "  Feasibility study (EUR 1,500) for borderline or low-evidence assets.",
        "  Best for  : Tier 4 (PROMOTION OPPORTUNITY) assets.",
        "  Harmful   : Tier 1-2 assets -- more visitors accelerate degradation.",
        "  Visitor gain : 8-25% depending on current EHS and evidence quality.",
        "",
        "COMBINED SCENARIO (E):",
        "  Tier 1-2 assets : Restoration + Monitoring (EUR 39,500)",
        "  Tier 4 assets   : Promotion + Monitoring   (EUR 16,500)",
        "  Tier 3 assets   : Monitoring only           (EUR 4,500)",
        "",
        "TERRITORIAL IMPACT SCORE (TIS) -- 0 to 100:",
        "  Measures benefit delivered per euro invested.",
        "  Weighted benefit: Environmental 55% | Economic 30% | Evidence 15%",
        "  Cost modifier: square-root penalty (expensive high-impact scores well).",
        "  TIS > 15 : excellent return -- prioritise this asset.",
        "  TIS 8-15 : good return -- fund when budget permits.",
        "  TIS 3-8  : moderate return -- consider after higher-TIS items.",
        "  TIS < 3  : low return -- defer or use lower-cost option.",
    ]
    return Phase6ReportSection(title="1. INTERVENTION MODEL OVERVIEW", content=lines)


# ── Section 2: Scenario Comparison ────────────────────────────────────────

def _s2_scenario_comparison(
    comparisons: list,
    assets_by_id: dict,
) -> Phase6ReportSection:
    lines: list[str] = []

    for comp in comparisons:
        asset = assets_by_id[comp.asset_id]
        tier_label = {1: "Tier 1 -- IMMEDIATE", 2: "Tier 2 -- PREVENTIVE",
                      3: "Tier 3 -- MONITORING", 4: "Tier 4 -- PROMOTION"}.get(
                          comp.current_tier, "Tier ?")
        dcs_note = " [DCS-GATED]" if comp.dcs_constrained else ""

        lines.append(
            f"{asset.name:<38} [{tier_label} | EHS={comp.current_ehs:.0f} | "
            f"DCS={comp.current_dcs:.0f}{dcs_note}]"
        )
        lines.append(
            f"  {'Scen':<4} {'Intervention':<28} {'dEHS':>6} {'dRisk':>7} "
            f"{'dDCS':>6} {'dVis':>7} {'Cost(EUR)':>10} {'TIS':>6}  Feasibility"
        )
        lines.append("  " + "-" * 87)

        for code in ["A", "B", "C", "D", "E"]:
            s = comp.scenarios[code]
            best_marker = " <<" if code == comp.best_scenario_code else "   "
            feas_short = (
                "NOT REC." if s.feasibility == FEASIBILITY_NOT_RECOMMENDED
                else "MARGINAL" if s.feasibility == FEASIBILITY_MARGINAL
                else ""
            )
            vis_str = f"{s.delta_visitors:+,}" if s.delta_visitors != 0 else "    --"
            ehs_str = f"{s.delta_ehs:+.1f}" if s.delta_ehs != 0 else "  --"
            risk_str = f"{s.delta_risk:+.3f}" if s.delta_risk != 0 else "   --"
            dcs_str  = f"{s.delta_dcs:+.1f}" if s.delta_dcs != 0 else " --"
            cost_str = f"{s.cost_eur:>10,}" if s.cost_eur > 0 else "        --"
            lines.append(
                f"  {code:<4} {s.scenario_label:<28} {ehs_str:>6} {risk_str:>7} "
                f"{dcs_str:>6} {vis_str:>7} {cost_str} {s.tis:>6.1f}{best_marker}"
                + (f"  [{feas_short}]" if feas_short else "")
            )

        lines.append(
            f"  >> RECOMMENDED: {comp.best_scenario_code} -- {comp.best_scenario_label}"
        )
        lines.append(
            "     " + _wrap(comp.best_scenario_reason, 72, "     ")
        )
        lines.append("")

    return Phase6ReportSection(title="2. ASSET SCENARIO COMPARISON (all 20 assets)", content=lines)


# ── Section 3: Recommended scenarios summary ───────────────────────────────

def _s3_recommended_scenarios(
    comparisons: list,
    assets_by_id: dict,
) -> Phase6ReportSection:
    header = (
        f"  {'Rank':<5} {'Asset':<38} {'Tier':<4} {'Scenario':<26} "
        f"{'TIS':>6} {'Cost(EUR)':>10}  Note"
    )
    lines = [header, "  " + "-" * 100]

    sorted_comps = sorted(
        comparisons,
        key=lambda c: (-(c.scenarios[c.best_scenario_code].tis),
                       assets_by_id[c.asset_id].tier or 3)
    )

    for rank, comp in enumerate(sorted_comps, 1):
        asset   = assets_by_id[comp.asset_id]
        chosen  = comp.scenarios[comp.best_scenario_code]
        tier    = comp.current_tier
        note    = "[DCS-GATED]" if comp.dcs_constrained else ""
        label   = f"{comp.best_scenario_code}: {comp.best_scenario_label}"[:25]
        lines.append(
            f"  {rank:<5} {asset.name:<38} T{tier}   {label:<26} "
            f"{chosen.tis:>6.1f} {chosen.cost_eur:>10,}  {note}"
        )

    total_cost = sum(
        comp.scenarios[comp.best_scenario_code].cost_eur for comp in comparisons
    )
    n_constrained = sum(1 for c in comparisons if c.dcs_constrained)
    lines += [
        "",
        f"Total if all recommended scenarios funded: EUR {total_cost:,}",
        f"DCS-constrained assets (monitoring mandatory): {n_constrained}",
        f"Note: [DCS-GATED] assets cannot receive restoration or promotion until",
        f"      DCS reaches 55+. Monitoring first.",
    ]
    return Phase6ReportSection(
        title="3. RECOMMENDED SCENARIOS (all assets, ranked by TIS)", content=lines
    )


# ── Section 4: TIS budget allocation ──────────────────────────────────────

def _s4_budget(budget: TISBudgetResult) -> Phase6ReportSection:
    lines = [
        f"Available budget : EUR {budget.total_budget_eur:,}",
        f"Total allocated  : EUR {budget.total_allocated_eur:,}",
        f"Remaining        : EUR {budget.remaining_eur:,}",
        f"Assets funded    : {len(budget.funded_items)} | "
        f"Deferred: {len(budget.deferred_items)}",
        f"Portfolio TIS    : {budget.portfolio_tis:.1f}/100 (budget-weighted average)",
        "",
        "FUNDED ITEMS (ranked by TIS, highest first):",
        f"  {'#':<4} {'Asset':<38} {'T':<2} {'Scenario':<28} "
        f"{'TIS':>6} {'Cost(EUR)':>10}",
        "  " + "-" * 95,
    ]

    for rank, item in enumerate(budget.funded_items, 1):
        label = f"{item.scenario_code}: {item.intervention_label.split(' -- ')[0]}"[:27]
        lines.append(
            f"  {rank:<4} {item.asset_name:<38} T{item.tier}  {label:<28} "
            f"{item.tis:>6.1f} {item.cost_eur:>10,}"
        )

    if budget.deferred_items:
        lines += [
            "",
            "DEFERRED ITEMS (budget exhausted -- next cycle):",
            f"  {'Asset':<38} {'T':<2} {'Scenario':<28} {'TIS':>6} {'Need(EUR)':>10}",
            "  " + "-" * 90,
        ]
        for item in budget.deferred_items:
            label = f"{item.scenario_code}: {item.intervention_label.split(' -- ')[0]}"[:27]
            lines.append(
                f"  {item.asset_name:<38} T{item.tier}  {label:<28} "
                f"{item.tis:>6.1f} {item.cost_eur:>10,}"
            )

    lines += [
        "",
        "PORTFOLIO IMPACT OF FUNDED INTERVENTIONS:",
        f"  Total DELTA_EHS     : +{budget.portfolio_delta_ehs:.1f} pts "
        "(combined environmental health gain)",
        f"  Total DELTA_RISK    :  {budget.portfolio_delta_risk:+.3f} "
        "(combined risk reduction)",
        f"  Total DELTA_VISITORS: +{budget.portfolio_delta_visitors:,} "
        "visitors/yr (combined visitor growth)",
        f"  Total DELTA_DCS     : +{budget.portfolio_delta_dcs:.1f} pts "
        "(combined evidence quality gain)",
    ]
    return Phase6ReportSection(
        title="4. TIS-OPTIMISED BUDGET ALLOCATION (EUR 100,000)", content=lines
    )


# ── Section 5: Counterfactual analysis ────────────────────────────────────

def _s5_counterfactual(counterfactuals: list) -> Phase6ReportSection:
    lines = [
        "The following 5 assets were selected for counterfactual analysis:",
        "What does the environmental trajectory look like if we do nothing?",
        "",
    ]

    for cf in counterfactuals:
        lines.append(f"ASSET: {cf.asset_name}  [{cf.ehs_trajectory}]")
        lines.append(
            f"  Uncertainty: {cf.uncertainty} "
            f"| Risk trajectory: {cf.risk_trajectory}"
        )
        lines.append(
            f"  {'Year':<6} {'EHS':>6} {'Risk':>7} {'Visitor %':>10} {'Alert'}"
        )
        lines.append("  " + "-" * 50)
        for yr in cf.years:
            vis_str  = f"{yr.visitor_pct_change:+.0f}%" if yr.visitor_pct_change else "  --"
            alert_str = f"  -> {yr.alert_escalation}" if yr.alert_escalation else ""
            lines.append(
                f"  Year {yr.year:<3} {yr.ehs:>6.1f} {yr.risk:>7.3f} "
                f"{vis_str:>10}{alert_str}"
            )
        lines += [
            f"  Cumulative visitor loss (3 yr): {cf.cumulative_visitor_loss:,}",
            f"  Est. cost of inaction        : EUR {cf.estimated_inaction_cost_eur:,}",
            f"  Narrative: {_wrap(cf.narrative, 70, '    ')}",
            "",
        ]

    return Phase6ReportSection(
        title="5. COUNTERFACTUAL ANALYSIS (top-5 priority assets -- no intervention)",
        content=lines,
    )


# ── Section 6: Portfolio impact view ──────────────────────────────────────

def _s6_portfolio_impact(
    budget: TISBudgetResult,
    comparisons: list,
    assets: list,
) -> Phase6ReportSection:
    n_improved    = sum(1 for c in comparisons
                        if c.scenarios[c.best_scenario_code].delta_ehs > 0)
    n_risk_red    = sum(1 for c in comparisons
                        if c.scenarios[c.best_scenario_code].delta_risk < 0)
    n_vis_gain    = sum(1 for c in comparisons
                        if c.scenarios[c.best_scenario_code].delta_visitors > 0)

    funded_cost   = budget.total_allocated_eur
    funded_dEHS   = budget.portfolio_delta_ehs
    funded_dRisk  = budget.portfolio_delta_risk
    funded_dVis   = budget.portfolio_delta_visitors
    funded_dDCS   = budget.portfolio_delta_dcs

    # Full-territory potential (if all recommended scenarios were funded)
    all_dEHS  = sum(c.scenarios[c.best_scenario_code].delta_ehs  for c in comparisons)
    all_dRisk = sum(c.scenarios[c.best_scenario_code].delta_risk for c in comparisons)
    all_dVis  = sum(c.scenarios[c.best_scenario_code].delta_visitors for c in comparisons)
    all_dDCS  = sum(c.scenarios[c.best_scenario_code].delta_dcs  for c in comparisons)
    all_cost  = sum(c.scenarios[c.best_scenario_code].cost_eur   for c in comparisons)

    efficiency_pct = round(funded_cost / max(all_cost, 1) * 100, 1)

    lines = [
        "TERRITORY-LEVEL IMPACT SUMMARY",
        "",
        "With EUR 100,000 budget (funded interventions only):",
        f"  Delta EHS total         : +{funded_dEHS:.1f} pts across funded assets",
        f"  Delta Risk total        :  {funded_dRisk:+.3f} (risk reduction)",
        f"  Delta Visitors total    : +{funded_dVis:,} visitors/yr",
        f"  Delta DCS total         : +{funded_dDCS:.1f} pts (evidence quality)",
        f"  Funded cost             : EUR {funded_cost:,} ({efficiency_pct}% of full need)",
        "",
        "Full recommended portfolio (all 20 assets, if fully funded):",
        f"  Delta EHS total         : +{all_dEHS:.1f} pts",
        f"  Delta Risk total        :  {all_dRisk:+.3f}",
        f"  Delta Visitors total    : +{all_dVis:,} visitors/yr",
        f"  Delta DCS total         : +{all_dDCS:.1f} pts",
        f"  Total required          : EUR {all_cost:,}",
        "",
        "ASSET IMPACT BREAKDOWN:",
        f"  Assets gaining EHS improvement : {n_improved} / {len(comparisons)}",
        f"  Assets gaining risk reduction  : {n_risk_red} / {len(comparisons)}",
        f"  Assets gaining visitor volume  : {n_vis_gain} / {len(comparisons)}",
        "",
        "INTERVENTION TYPE EFFECTIVENESS (if all recommended funded):",
    ]

    # Summarise by intervention type
    type_stats: dict[str, dict] = {}
    for comp in comparisons:
        s    = comp.scenarios[comp.best_scenario_code]
        itype = s.intervention_type
        if itype not in type_stats:
            type_stats[itype] = {"n": 0, "ehs": 0.0, "risk": 0.0, "vis": 0, "cost": 0}
        type_stats[itype]["n"]    += 1
        type_stats[itype]["ehs"]  += s.delta_ehs
        type_stats[itype]["risk"] += s.delta_risk
        type_stats[itype]["vis"]  += s.delta_visitors
        type_stats[itype]["cost"] += s.cost_eur

    for itype, st in sorted(type_stats.items()):
        lines.append(
            f"  {itype:<28}: {st['n']} assets, "
            f"DELTA_EHS=+{st['ehs']:.1f}, "
            f"DELTA_RISK={st['risk']:+.3f}, "
            f"EUR {st['cost']:,}"
        )

    return Phase6ReportSection(
        title="6. PORTFOLIO IMPACT VIEW (territory-level aggregates)", content=lines
    )


# ── Section 7: Decision explanation layer ─────────────────────────────────

def _s7_decision_explanation(
    explanations: list,
    assets_by_id: dict,
) -> Phase6ReportSection:
    lines = [
        "FULL DECISION TRANSPARENCY -- one record per asset.",
        "Each record states: CHOSEN intervention, REJECTED alternatives,",
        "TRADE-OFFS, CONFIDENCE level, and COUNTERFACTUAL headline.",
        "",
    ]

    for exp in explanations:
        asset = assets_by_id.get(exp.asset_id)
        tier  = (asset.tier or 3) if asset else "?"
        ehs_s = f"EHS={asset.ehs:.0f}" if asset else ""
        dcs_s = f"DCS={asset.dcs:.0f}" if asset else ""
        lines.append(
            f"[{exp.asset_name}]  Tier {tier} | "
            f"{ehs_s} | {dcs_s} | TIS={exp.chosen_tis:.1f} | "
            f"Confidence: {exp.confidence_level}"
        )
        lines.append(
            f"  CHOSEN  : {exp.chosen_scenario} -- {exp.chosen_intervention} "
            f"(EUR {exp.chosen_cost_eur:,}, TIS={exp.chosen_tis:.1f})"
        )
        lines.append(
            "  REASON  : " + _wrap(exp.chosen_rationale, 70, "            ")
        )
        if exp.rejected:
            lines.append("  REJECTED:")
            for r in exp.rejected:
                lines.append(
                    f"    {r['code']} ({r['label']}, TIS={r['tis']:.1f}): "
                    + _wrap(r["reason"], 65, "       ")
                )
        lines.append(
            "  TRADE-OFFS: " + _wrap(exp.trade_offs, 70, "              ")
        )
        lines.append(
            "  CONFIDENCE NOTE: " + _wrap(exp.confidence_note, 67, "                 ")
        )
        lines.append(
            "  IF NOTHING: " + _wrap(exp.counterfactual_headline, 70, "              ")
        )
        lines.append("")

    return Phase6ReportSection(
        title="7. DECISION EXPLANATION LAYER (chosen / rejected / why / confidence)",
        content=lines,
    )


# ── Section 8: Management summary ─────────────────────────────────────────

def _s8_management_summary(
    territory_name: str,
    report_date: str,
    assets: list,
    comparisons: list,
    budget: TISBudgetResult,
    counterfactuals: list,
) -> Phase6ReportSection:
    n_tier1  = sum(1 for a in assets if a.tier == 1)
    n_funded = len(budget.funded_items)
    n_defer  = len(budget.deferred_items)

    # Top TIS item
    top_item = (
        max(budget.funded_items, key=lambda x: x.tis)
        if budget.funded_items else None
    )

    # Highest inaction cost
    if counterfactuals:
        worst_cf = max(counterfactuals, key=lambda c: c.estimated_inaction_cost_eur)
    else:
        worst_cf = None

    lines = [
        f"TERRITORY   : {territory_name}",
        f"REPORT DATE : {report_date}",
        "",
        "KEY FINDINGS:",
        "",
        f"1. INTERVENTION IMPACT POTENTIAL  (all 20 assets, full portfolio):",
        f"   If all recommended interventions were funded (EUR "
        f"{sum(c.scenarios[c.best_scenario_code].cost_eur for c in comparisons):,}),",
        f"   the territory would gain +{sum(c.scenarios[c.best_scenario_code].delta_ehs for c in comparisons):.1f} EHS pts "
        f"and +{sum(c.scenarios[c.best_scenario_code].delta_visitors for c in comparisons):,} visitors/yr.",
        "",
        f"2. EUR 100,000 BUDGET -- TIS-OPTIMISED ALLOCATION:",
        f"   {n_funded} assets funded | {n_defer} deferred | "
        f"Portfolio TIS = {budget.portfolio_tis:.1f}/100.",
    ]

    if top_item:
        lines.append(
            f"   Highest-value intervention: {top_item.asset_name} "
            f"({top_item.intervention_label.split(' -- ')[0]}, TIS={top_item.tis:.1f})."
        )

    if worst_cf:
        lines += [
            "",
            f"3. COST OF INACTION (worst case in top-5 priority assets):",
            f"   Without intervention, {worst_cf.asset_name} is projected to reach "
            f"EHS={worst_cf.years[2].ehs:.0f}/100 by year 3.",
            f"   Estimated inaction cost: EUR {worst_cf.estimated_inaction_cost_eur:,} "
            f"over 3 years (visitor loss + emergency restoration premium).",
        ]

    lines += [
        "",
        f"4. CRITICAL CONSTRAINT -- DCS EVIDENCE GATE:",
        f"   {sum(1 for c in comparisons if c.dcs_constrained)} assets have DCS < 55 "
        f"and cannot receive restoration or promotion funding.",
        "   These assets are locked into monitoring-only mode until evidence improves.",
        "   EUR 4,500/asset invested in monitoring today unlocks EUR 35,000+ decisions tomorrow.",
        "",
        "RECOMMENDED MANAGEMENT ACTIONS:",
        "  (a) Fund all Tier 1 restorations immediately (highest TIS, human-driven, preventable).",
        "  (b) Prioritise monitoring upgrades for DCS-gated assets to unlock future investment.",
        "  (c) Use deferred promotion campaigns as the request for next-year budget supplement.",
        "  (d) Review counterfactual costs for the board: inaction is not free.",
    ]

    return Phase6ReportSection(title="8. MANAGEMENT SUMMARY", content=lines)


# ── Decision explanation builder ───────────────────────────────────────────

def build_explanation(
    comp: AssetScenarioComparison,
    asset,
    counterfactual: CounterfactualResult,
) -> DecisionExplanation:
    """Build a DecisionExplanation from a scenario comparison and counterfactual."""
    chosen  = comp.scenarios[comp.best_scenario_code]

    # Rejected alternatives (all other VIABLE or MARGINAL scenarios with cost > 0)
    rejected = []
    for code, s in comp.scenarios.items():
        if code == comp.best_scenario_code or s.cost_eur == 0:
            continue
        reason = _rejection_reason(code, s, comp.best_scenario_code, chosen, comp)
        rejected.append({
            "code":  code,
            "label": s.scenario_label,
            "tis":   s.tis,
            "reason": reason,
        })
    rejected.sort(key=lambda r: -r["tis"])

    # Confidence
    dcs = asset.dcs
    if dcs >= 70:
        conf_level = "HIGH"
        conf_note  = (
            f"DCS={dcs:.0f}/100 provides HIGH decision confidence. "
            "The predicted intervention outcome is reliable."
        )
    elif dcs >= 55:
        conf_level = "MODERATE"
        conf_note  = (
            f"DCS={dcs:.0f}/100. MODERATE confidence: the outcome is likely but "
            "should be monitored and documented post-intervention."
        )
    else:
        conf_level = "LOW"
        conf_note  = (
            f"DCS={dcs:.0f}/100 (LOW evidence). Monitoring mandatory first. "
            "Capital action deferred until DCS reaches 55+."
        )

    # Trade-off description
    if comp.dcs_constrained:
        trade_off = (
            "By choosing monitoring over restoration, EUR 4,500 is spent to build "
            f"evidence rather than immediately fixing the asset. The cost of waiting: "
            f"{counterfactual.narrative.split('.')[0]}."
        )
    elif asset.tier == 4:
        trade_off = (
            "Promotion brings economic benefit but adds slight environmental pressure "
            f"(delta_ehs={chosen.delta_ehs:.1f}). If EHS drops below 75, the asset "
            "will be reclassified to Tier 2 and promotion suspended."
        )
    elif comp.best_scenario_code == "B":
        trade_off = (
            f"Restoration (EUR {chosen.cost_eur:,}) is the largest single-asset "
            "investment. If the underlying cause is climate-driven rather than "
            "visitor-driven, effectiveness will be lower than predicted."
        )
    else:
        trade_off = (
            "Monitoring preserves evidence quality at low cost. The downside: "
            "environmental conditions may continue to decline while data is collected."
        )

    # Counterfactual headline
    yr3 = counterfactual.years[2]
    cf_headline = (
        f"Without action: EHS projected at {yr3.ehs:.0f}/100 by year 3 "
        f"({counterfactual.ehs_trajectory}). "
        f"Estimated inaction cost: EUR {counterfactual.estimated_inaction_cost_eur:,}."
    )

    return DecisionExplanation(
        asset_id=comp.asset_id,
        asset_name=comp.asset_name,
        chosen_scenario=comp.best_scenario_code,
        chosen_intervention=chosen.intervention_type,
        chosen_cost_eur=chosen.cost_eur,
        chosen_tis=chosen.tis,
        chosen_rationale=comp.best_scenario_reason,
        rejected=rejected,
        trade_offs=trade_off,
        confidence_level=conf_level,
        confidence_note=conf_note,
        counterfactual_headline=cf_headline,
    )


def _rejection_reason(
    code: str,
    scenario,
    best_code: str,
    best_scenario,
    comp: AssetScenarioComparison,
) -> str:
    if scenario.feasibility == FEASIBILITY_NOT_RECOMMENDED:
        return (
            f"Not recommended for this asset type/condition "
            f"(TIS={scenario.tis:.1f}, feasibility: NOT RECOMMENDED)."
        )
    if scenario.feasibility == FEASIBILITY_MARGINAL:
        return (
            f"Marginal feasibility (TIS={scenario.tis:.1f}). "
            f"Better to invest in {SCENARIO_LABELS[best_code]} "
            f"(TIS={best_scenario.tis:.1f})."
        )
    if scenario.tis < best_scenario.tis:
        return (
            f"TIS={scenario.tis:.1f} is lower than chosen scenario "
            f"(TIS={best_scenario.tis:.1f}). Less territorial impact per euro."
        )
    return f"TIS={scenario.tis:.1f} -- equivalent to chosen, but chosen has better evidence basis."


# ── Text utilities ─────────────────────────────────────────────────────────

def _wrap(text: str, width: int = 72, subsequent_indent: str = "  ") -> str:
    """Simple word-wrap with hanging indent for subsequent lines."""
    words = text.split()
    if not words:
        return ""
    out_lines: list[str] = []
    line = words[0]
    for w in words[1:]:
        if len(line) + 1 + len(w) > width:
            out_lines.append(line)
            line = subsequent_indent + w
        else:
            line += " " + w
    out_lines.append(line)
    return "\n".join(out_lines)
