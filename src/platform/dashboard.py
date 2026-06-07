"""
SNTO Phase 7 -- Executive Destination Health Dashboard
=======================================================
TASK 3: 10 executive KPIs for destination intelligence.

DESIGN PRINCIPLE
================
Every KPI must answer a question a manager or director would actually ask.
No statistical indicators. No technical scores. Numbers only when they
communicate a clear decision trigger or trend.

THE 10 KPIs
===========
 1. Territory Health Index       -- Is the destination healthy overall?
 2. Assets Requiring Action      -- How many sites need intervention now?
 3. Visitor Capacity at Risk     -- How many visitor experiences are at risk?
 4. Investment Backlog           -- How much unmet conservation investment exists?
 5. Decision Confidence Rate     -- What % of our recommendations are reliable?
 6. Promotion Pipeline           -- How many sites are ready to grow tourism?
 7. Human Pressure Alerts        -- How many sites are being damaged by visitors?
 8. Budget Efficiency Index      -- What return are we getting on conservation spend?
 9. Recovery Progress            -- How many sites are improving?
10. Evidence Coverage Gap        -- How many sites still lack enough data to manage?
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DashboardKPI:
    """One executive KPI with value, status, interpretation, and recommended action."""
    number: int
    name: str
    value: str              # formatted value for display (e.g. "65/100", "5 sites", "43%")
    status: str             # GREEN | AMBER | RED | BLUE (for colour coding)
    status_label: str       # "HEALTHY" | "CAUTION" | "CRITICAL" | "OPPORTUNITY"
    what_it_means: str      # plain-language explanation of the KPI value
    recommended_action: str # one-sentence action recommendation
    technical_basis: str    # brief note on what SNTO outputs power this KPI


@dataclass(frozen=True)
class ExecutiveDashboard:
    """Complete 10-KPI destination intelligence dashboard."""
    territory_name: str
    report_date: str
    n_assets: int
    kpis: list             # list[DashboardKPI]
    headline: str          # one-line executive headline
    call_to_action: str    # most urgent single action required


def compute_executive_dashboard(
    territory_name: str,
    report_date: str,
    assets: list,          # list[TerritorialAsset] (Phase 5 output, with tier + tpi set)
    budget_result,         # TISBudgetResult (Phase 6 output)
    comparisons: list,     # list[AssetScenarioComparison] (Phase 6)
) -> ExecutiveDashboard:
    """
    Compute all 10 KPIs from Phase 5+6 outputs.
    Returns an ExecutiveDashboard ready for display.
    """
    n = len(assets)
    if n == 0:
        raise ValueError("At least one asset is required to compute dashboard.")

    kpis = [
        _kpi_territory_health(assets),
        _kpi_assets_requiring_action(assets),
        _kpi_visitor_capacity_at_risk(assets),
        _kpi_investment_backlog(assets, comparisons),
        _kpi_decision_confidence_rate(assets),
        _kpi_promotion_pipeline(assets),
        _kpi_human_pressure_alerts(assets),
        _kpi_budget_efficiency(budget_result, comparisons),
        _kpi_recovery_progress(assets),
        _kpi_evidence_coverage_gap(assets),
    ]

    # Headline: status of the most critical KPI
    headline = _generate_headline(assets, kpis)
    cta      = _generate_call_to_action(assets)

    return ExecutiveDashboard(
        territory_name=territory_name,
        report_date=report_date,
        n_assets=n,
        kpis=kpis,
        headline=headline,
        call_to_action=cta,
    )


# ── KPI builders ───────────────────────────────────────────────────────────

def _kpi_territory_health(assets: list) -> DashboardKPI:
    """KPI 1: Territory Health Index -- overall portfolio condition."""
    score = sum(a.ehs for a in assets) / len(assets)
    value = f"{score:.0f}/100"

    if score >= 75:
        status, label = "GREEN", "HEALTHY"
        meaning = (
            f"The destination is in good environmental health overall ({score:.0f}/100). "
            "The natural asset portfolio is well-managed and can support tourism growth."
        )
        action = "Maintain current monitoring and continue developing promotion-ready assets."
    elif score >= 60:
        status, label = "AMBER", "MODERATE"
        meaning = (
            f"The destination is under moderate environmental stress ({score:.0f}/100). "
            "Some assets require attention but the overall portfolio is not at risk."
        )
        action = "Prioritise preventive interventions and reinforce monitoring at stressed sites."
    elif score >= 45:
        status, label = "RED", "AT RISK"
        meaning = (
            f"The destination health score ({score:.0f}/100) indicates significant "
            "environmental pressure. A substantial portion of assets require active management."
        )
        action = "Approve emergency funding for Tier 1 assets. Restrict visitors at critical sites."
    else:
        status, label = "RED", "CRITICAL"
        meaning = (
            f"The destination health score ({score:.0f}/100) is critically low. "
            "The natural asset portfolio is at risk of irreversible degradation."
        )
        action = "Immediate emergency intervention required across multiple critical assets."

    return DashboardKPI(
        number=1, name="Territory Health Index",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Mean EHS across all monitored assets (Phase 1-4 outputs).",
    )


def _kpi_assets_requiring_action(assets: list) -> DashboardKPI:
    """KPI 2: Assets requiring immediate or preventive action."""
    t1 = [a for a in assets if a.tier == 1]
    t2 = [a for a in assets if a.tier == 2]
    n_urgent = len(t1)
    n_prev   = len(t2)
    total    = n_urgent + n_prev
    n        = len(assets)

    value = f"{n_urgent} urgent, {n_prev} preventive"
    if n_urgent >= 3:
        status, label = "RED", "CRITICAL BACKLOG"
        meaning = (
            f"{n_urgent} sites are in urgent need of intervention and {n_prev} more "
            f"require preventive action -- {total} of {n} monitored assets need management "
            "attention. Visitor experience and environmental integrity are at risk."
        )
        action = f"Approve restoration funding for {n_urgent} Tier 1 asset(s) immediately."
    elif n_urgent >= 1:
        status, label = "AMBER", "ACTION REQUIRED"
        meaning = (
            f"{n_urgent} asset(s) require urgent intervention. "
            f"An additional {n_prev} need preventive maintenance within 12 months."
        )
        action = f"Schedule restoration for {n_urgent} urgent asset(s) in next budget cycle."
    elif n_prev >= 3:
        status, label = "AMBER", "PREVENTIVE NEEDED"
        meaning = (
            f"No immediate emergencies, but {n_prev} assets show early stress indicators "
            "that will become more expensive if not addressed within 12 months."
        )
        action = f"Plan preventive maintenance schedule for {n_prev} assets."
    else:
        status, label = "GREEN", "MANAGEABLE"
        meaning = (
            f"Only {total} asset(s) require management attention, which is within "
            "normal operational capacity."
        )
        action = "Continue standard monitoring. Review preventive schedule quarterly."

    return DashboardKPI(
        number=2, name="Assets Requiring Action",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Tier 1 (TPI + EHS trigger) and Tier 2 (TPI >= 38, EHS < 75) classifications.",
    )


def _kpi_visitor_capacity_at_risk(assets: list) -> DashboardKPI:
    """KPI 3: Annual visitor experiences at degraded sites."""
    at_risk = sum(a.visitor_capacity_annual for a in assets if a.tier in (1, 2))
    pct = round(at_risk / max(1, sum(a.visitor_capacity_annual for a in assets)) * 100)
    value = f"{at_risk:,} visitors/yr ({pct}%)"

    if pct >= 40:
        status, label = "RED", "HIGH RISK"
        meaning = (
            f"{at_risk:,} annual visitors -- {pct}% of total -- are visiting sites in "
            "deteriorating or poor environmental condition. Their experience is compromised "
            "and they may become carriers of negative destination reputation."
        )
        action = "Implement visitor redirection and remediation plan as a matter of urgency."
    elif pct >= 20:
        status, label = "AMBER", "MODERATE RISK"
        meaning = (
            f"{at_risk:,} annual visitors ({pct}%) are at sites under environmental stress. "
            "While not yet a crisis, the experience quality at these sites needs attention."
        )
        action = "Prioritise intervention at highest-traffic stressed sites first."
    else:
        status, label = "GREEN", "LOW RISK"
        meaning = (
            f"Only {at_risk:,} annual visitors ({pct}%) are at sites requiring management "
            "attention. The majority of visitor experiences are at healthy sites."
        )
        action = "Monitor stressed sites closely during peak season."

    return DashboardKPI(
        number=3, name="Visitor Capacity at Risk",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Sum of visitor_capacity_annual for Tier 1+2 assets.",
    )


def _kpi_investment_backlog(assets: list, comparisons: list) -> DashboardKPI:
    """KPI 4: Total unmet conservation investment need."""
    comp_by_id = {c.asset_id: c for c in comparisons}
    total_need = sum(
        comp_by_id[a.asset_id].scenarios[comp_by_id[a.asset_id].best_scenario_code].cost_eur
        for a in assets if a.tier in (1, 2) and a.asset_id in comp_by_id
    )
    value = f"EUR {total_need:,}"

    if total_need >= 200_000:
        status, label = "RED", "LARGE BACKLOG"
        meaning = (
            f"EUR {total_need:,} is needed to fully address all urgent and preventive "
            "conservation requirements. This significantly exceeds a typical annual budget "
            "and requires multi-year planning."
        )
        action = "Develop a 3-year investment plan. Apply for EU or national conservation funds."
    elif total_need >= 100_000:
        status, label = "AMBER", "SIGNIFICANT NEED"
        meaning = (
            f"EUR {total_need:,} is the total investment required to address all priority "
            "conservation needs. Exceeds a single annual budget; phased allocation is needed."
        )
        action = "Prioritise Tier 1 assets for current year; plan Tier 2 for next cycle."
    else:
        status, label = "GREEN", "MANAGEABLE"
        meaning = (
            f"EUR {total_need:,} covers all priority conservation needs -- a manageable "
            "investment relative to the destination's budget capacity."
        )
        action = "Seek budget approval for full conservation investment plan."

    return DashboardKPI(
        number=4, name="Conservation Investment Backlog",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Sum of recommended intervention costs for Tier 1+2 assets (TIS optimised).",
    )


def _kpi_decision_confidence_rate(assets: list) -> DashboardKPI:
    """KPI 5: % of assets with sufficient evidence to act confidently."""
    n_confident = sum(1 for a in assets if a.dcs >= 65)
    pct = round(n_confident / len(assets) * 100)
    value = f"{pct}% ({n_confident}/{len(assets)} assets)"

    if pct >= 75:
        status, label = "GREEN", "HIGH RELIABILITY"
        meaning = (
            f"{pct}% of assets have strong enough evidence to support confident management "
            "decisions. The monitoring infrastructure is working effectively."
        )
        action = "Maintain monitoring quality. Fill remaining evidence gaps for low-DCS assets."
    elif pct >= 50:
        status, label = "AMBER", "IMPROVING"
        meaning = (
            f"{pct}% of assets have reliable evidence. The remainder require monitoring "
            "upgrades before major investment can be confidently committed."
        )
        action = f"Invest EUR 4,500/asset in monitoring upgrades for {len(assets)-n_confident} low-confidence assets."
    else:
        status, label = "RED", "EVIDENCE GAP"
        meaning = (
            f"Only {pct}% of assets have sufficient evidence for confident decisions. "
            "A significant evidence gap limits the reliability of management recommendations."
        )
        action = "Prioritise monitoring investment before capital restoration spend."

    return DashboardKPI(
        number=5, name="Decision Confidence Rate",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="% of assets with DCS >= 65 (HIGH or VERY HIGH confidence).",
    )


def _kpi_promotion_pipeline(assets: list) -> DashboardKPI:
    """KPI 6: Assets ready for active tourism promotion."""
    t4 = [a for a in assets if a.tier == 4]
    total_visitors = sum(a.visitor_capacity_annual for a in t4)
    value = f"{len(t4)} assets ({total_visitors:,} visitor reach)"

    if len(t4) >= 5:
        status, label = "BLUE", "STRONG PIPELINE"
        meaning = (
            f"{len(t4)} assets qualify for active promotion, with a combined visitor "
            f"reach of {total_visitors:,} visitors per year. This represents a significant "
            "growth opportunity for destination tourism revenue."
        )
        action = f"Launch promotion campaigns for top {min(3, len(t4))} assets. Budget EUR 12,000-18,000 each."
    elif len(t4) >= 2:
        status, label = "GREEN", "GOOD PIPELINE"
        meaning = (
            f"{len(t4)} assets qualify for promotion, reaching up to {total_visitors:,} "
            "visitors per year. A targeted campaign will deliver measurable tourism growth."
        )
        action = "Develop targeted digital campaigns for promotion-ready assets."
    elif len(t4) == 1:
        status, label = "AMBER", "LIMITED PIPELINE"
        meaning = (
            f"Only 1 asset currently qualifies for active promotion. "
            "More assets will become promotion-ready as conservation investment takes effect."
        )
        action = "Focus promotion budget on the single qualifying asset while investing in others."
    else:
        status, label = "RED", "NO PIPELINE"
        meaning = (
            "No assets currently qualify for active promotion. "
            "Environmental health must be improved before marketing investment is justified."
        )
        action = "Prioritise conservation investment to create a future promotion pipeline."

    return DashboardKPI(
        number=6, name="Promotion Pipeline",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Tier 4 assets: EHS>=75, risk<=0.35, DCS>=55, trend not declining.",
    )


def _kpi_human_pressure_alerts(assets: list) -> DashboardKPI:
    """KPI 7: Sites where visitor behaviour is causing measurable damage."""
    human_driven = [
        a for a in assets
        if a.scm_classification == "LOCALIZED_IMPACT" and a.tier in (1, 2)
    ]
    n = len(human_driven)
    value = f"{n} site(s)"

    if n >= 3:
        status, label = "RED", "MULTIPLE ALERTS"
        meaning = (
            f"{n} sites are experiencing measurable environmental damage caused by "
            "visitor pressure. These are the most actionable cases: the cause is known "
            "and visitor management can directly address it."
        )
        action = f"Implement visitor management measures at {n} sites. Consider seasonal closures."
    elif n >= 1:
        status, label = "AMBER", "ACTIVE ALERT"
        meaning = (
            f"{n} site(s) show confirmed visitor-driven environmental damage. "
            "This is the most direct form of tourism pressure on the destination's assets."
        )
        action = "Implement visitor management measures. Consider visitor quotas or guided-only access."
    else:
        status, label = "GREEN", "NO ALERTS"
        meaning = (
            "No sites are currently flagged for visitor-driven environmental damage. "
            "Environmental changes appear to be driven by natural climate variability."
        )
        action = "Continue monitoring visitor impact indicators."

    return DashboardKPI(
        number=7, name="Human Pressure Alerts",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="LOCALIZED_IMPACT classification from SCM at Tier 1 or Tier 2 assets.",
    )


def _kpi_budget_efficiency(budget_result, comparisons: list) -> DashboardKPI:
    """KPI 8: Investment efficiency -- portfolio TIS score."""
    tis   = getattr(budget_result, 'portfolio_tis', 0.0)
    alloc = getattr(budget_result, 'total_allocated_eur', 0)
    total = getattr(budget_result, 'total_budget_eur', 100_000)
    pct   = round(alloc / total * 100) if total > 0 else 0

    value = f"TIS={tis:.1f}/100 ({pct}% budget deployed)"
    if tis >= 12:
        status, label = "GREEN", "EXCELLENT EFFICIENCY"
        meaning = (
            f"The recommended investment plan achieves a portfolio efficiency score of "
            f"{tis:.1f}/100 -- every euro invested delivers strong territorial benefit. "
            f"{pct}% of the available budget is deployed."
        )
        action = "Approve recommended investment plan. High efficiency justifies immediate action."
    elif tis >= 7:
        status, label = "GREEN", "GOOD EFFICIENCY"
        meaning = (
            f"Investment efficiency is good (TIS={tis:.1f}/100). The allocation plan "
            "delivers solid territorial benefit per euro invested."
        )
        action = "Proceed with recommended allocation. Consider increasing budget for deferred items."
    else:
        status, label = "AMBER", "MODERATE EFFICIENCY"
        meaning = (
            f"Investment efficiency is moderate (TIS={tis:.1f}/100). "
            "Evidence constraints (low DCS on several assets) are limiting investment effectiveness."
        )
        action = "Invest in evidence improvement (monitoring) to unlock more efficient future allocations."

    return DashboardKPI(
        number=8, name="Budget Efficiency Index",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Budget-weighted average TIS from Phase 6 TIS-optimised allocation.",
    )


def _kpi_recovery_progress(assets: list) -> DashboardKPI:
    """KPI 9: Assets on an improving trend."""
    improving = [a for a in assets if a.trend_direction == "increasing"]
    declining = [a for a in assets if a.trend_direction == "decreasing"]
    n_imp  = len(improving)
    n_dec  = len(declining)
    n      = len(assets)
    pct    = round(n_imp / n * 100)
    value  = f"{n_imp} improving, {n_dec} declining"

    if n_dec == 0:
        status, label = "GREEN", "NO DECLINES"
        meaning = (
            f"{n_imp} assets are improving and none are in decline. "
            "The destination is on a positive environmental trajectory."
        )
        action = "Maintain current management practices. Investigate drivers of improvement."
    elif n_imp > n_dec:
        status, label = "GREEN", "NET POSITIVE"
        meaning = (
            f"More assets are improving ({n_imp}) than declining ({n_dec}). "
            "The overall trajectory is positive, though declining sites need attention."
        )
        action = f"Investigate and arrest declining trend at {n_dec} site(s)."
    elif n_imp == n_dec:
        status, label = "AMBER", "MIXED SIGNALS"
        meaning = (
            f"Equal numbers improving ({n_imp}) and declining ({n_dec}). "
            "Net environmental trend is neutral; intervention needed to tip the balance."
        )
        action = "Focus conservation investment on declining sites to shift the trend positive."
    else:
        status, label = "RED", "NET NEGATIVE"
        meaning = (
            f"More assets are declining ({n_dec}) than improving ({n_imp}). "
            "The destination is on a negative environmental trajectory."
        )
        action = "Urgent management review required. Prioritise arrest of declining trends."

    return DashboardKPI(
        number=9, name="Recovery Progress",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Mann-Kendall trend direction per asset (Phase 3 output).",
    )


def _kpi_evidence_coverage_gap(assets: list) -> DashboardKPI:
    """KPI 10: Assets still lacking enough data for reliable management."""
    evidence_gaps = [a for a in assets if a.dcs < 55]
    n = len(evidence_gaps)
    value = f"{n} site(s) with insufficient evidence"

    if n == 0:
        status, label = "GREEN", "NO GAPS"
        meaning = (
            "All monitored assets have sufficient evidence to support management decisions. "
            "The monitoring network is comprehensive."
        )
        action = "Maintain monitoring quality. Annual recalibration recommended."
    elif n <= 3:
        status, label = "AMBER", "MINOR GAPS"
        meaning = (
            f"{n} site(s) have insufficient evidence (DCS < 55). "
            "This prevents confident capital investment for these specific assets."
        )
        action = f"Invest EUR {n * 4_500:,} in monitoring upgrades to close evidence gaps."
    else:
        status, label = "RED", "SIGNIFICANT GAPS"
        meaning = (
            f"{n} assets lack sufficient evidence for confident management. "
            "A significant proportion of the destination portfolio cannot be effectively managed."
        )
        action = f"Prioritise monitoring investment: EUR {n * 4_500:,} to close all evidence gaps."

    return DashboardKPI(
        number=10, name="Evidence Coverage Gap",
        value=value, status=status, status_label=label,
        what_it_means=meaning, recommended_action=action,
        technical_basis="Assets with DCS < 55 (below the management action threshold).",
    )


# ── Summary generators ─────────────────────────────────────────────────────

def _generate_headline(assets: list, kpis: list) -> str:
    """Create one-line dashboard headline from the most critical KPI status."""
    n_red = sum(1 for k in kpis if k.status == "RED")
    n_amb = sum(1 for k in kpis if k.status == "AMBER")
    th    = kpis[0]  # Territory Health (KPI 1)

    if n_red >= 3:
        return (
            f"DESTINATION ALERT: {n_red} critical indicators require immediate management attention."
        )
    if n_red >= 1:
        return (
            f"Territory health is {th.value} with {n_red} critical area(s) requiring urgent action."
        )
    if n_amb >= 3:
        return (
            f"Territory health is {th.value}. Moderate stress across {n_amb} indicator(s): preventive action recommended."
        )
    return (
        f"Territory is {th.value}. Environmental management is performing well."
    )


def _generate_call_to_action(assets: list) -> str:
    """Identify the single most important action the director must take now."""
    t1_localized = [
        a for a in assets
        if a.tier == 1 and a.scm_classification == "LOCALIZED_IMPACT" and a.dcs >= 55
    ]
    if t1_localized:
        top = sorted(t1_localized, key=lambda a: -(a.tpi or 0))[0]
        return (
            f"Approve restoration funding for {top.name} immediately. "
            "The cause (visitor pressure) is confirmed and the evidence is reliable. "
            "Each month of delay increases restoration cost and visitor experience damage."
        )

    evidence_gaps = [a for a in assets if a.dcs < 40 and a.tier == 1]
    if evidence_gaps:
        return (
            f"Commission a monitoring upgrade for {len(evidence_gaps)} Tier-1 asset(s) "
            "that currently lack sufficient evidence. This is a prerequisite for any "
            "capital restoration decision."
        )

    t4 = [a for a in assets if a.tier == 4 and a.dcs >= 70]
    if t4:
        top = sorted(t4, key=lambda a: -a.visitor_capacity_annual)[0]
        return (
            f"Launch a promotion campaign for {top.name}. "
            "This asset is in excellent condition with strong evidence. "
            "A targeted campaign will increase visitor volume and regional tourism revenue."
        )

    return (
        "Continue current management plan and invest in monitoring quality "
        "to prepare the evidence base for next-cycle capital decisions."
    )


# ── Dashboard formatting ───────────────────────────────────────────────────

def format_dashboard(dashboard: ExecutiveDashboard) -> list[str]:
    """Return formatted lines for the executive dashboard printout."""
    STATUS_ICON = {"GREEN": "[OK]", "AMBER": "[!!]", "RED": "[**]", "BLUE": "[->]"}

    lines = [
        f"TERRITORY: {dashboard.territory_name}",
        f"DATE     : {dashboard.report_date}",
        f"ASSETS   : {dashboard.n_assets} monitored",
        "",
        "HEADLINE:",
        f"  {dashboard.headline}",
        "",
        "CALL TO ACTION:",
        f"  {dashboard.call_to_action}",
        "",
        f"  {'#':<3} {'KPI NAME':<32} {'VALUE':<30} {'STATUS':<18}",
        "  " + "-" * 90,
    ]
    for kpi in dashboard.kpis:
        icon  = STATUS_ICON.get(kpi.status, "   ")
        lines.append(
            f"  {kpi.number:<3} {kpi.name:<32} {kpi.value:<30} "
            f"{icon} {kpi.status_label}"
        )
    return lines
