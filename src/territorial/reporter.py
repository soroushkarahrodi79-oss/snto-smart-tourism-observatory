"""
SNTO Phase 5 — Institutional Report Generator
===============================================
Generates structured quarterly territorial reports for:
  - Provincial governments
  - Tourism observatories (Sismotur, REDNAT, EUROPARC)
  - Destination Management Organisations (DMOs)

REPORT STRUCTURE
================
1. Executive Summary       — 3-4 bullet points for the director
2. Territorial Overview    — health distribution, trend, evidence quality
3. Priority Assets         — Tier 1 and Tier 2 with actions
4. Recommended Actions     — full action table ordered by priority
5. Budget Allocation       — funded/unfunded with cost breakdown
6. Emerging Risks          — declining trends, evidence gaps, mixed causes
7. Promotion Opportunities — Tier 4 assets with visitor potential

Each section is returned as a ReportSection (title + list of content lines)
for flexible rendering (CLI, PDF, HTML, API).

LANGUAGE POLICY
===============
All content uses manager-level language:
  - NO NDVI, NO Mann-Kendall, NO z-scores
  - YES to "environmental health", "visitor stress", "climate-driven recovery"
  - YES to specific numbers: EHS, DCS, visitor counts, EUR costs
"""

from __future__ import annotations

from .models import (
    TerritorialAsset,
    PortfolioKPIs,
    BudgetScenario,
    RecommendedAction,
    ReportSection,
    TerritorialReport,
    TIER_LABELS,
    TIER_DESCRIPTIONS,
)
from .portfolio import tier_summary, ehs_distribution, scm_distribution, asset_type_breakdown


def generate_report(
    territory_name: str,
    report_date: str,
    period: str,
    assets: list[TerritorialAsset],
    kpis: PortfolioKPIs,
    actions: dict[str, RecommendedAction],
    budget: BudgetScenario,
) -> TerritorialReport:
    """
    Generate a complete quarterly institutional report.

    Returns a TerritorialReport with all 7 sections populated.
    """
    sections = [
        _section_executive_summary(territory_name, assets, kpis, budget),
        _section_territorial_overview(assets, kpis),
        _section_priority_assets(assets),
        _section_recommended_actions(assets, actions),
        _section_budget(budget),
        _section_emerging_risks(assets, kpis),
        _section_promotion_opportunities(assets, kpis),
    ]

    return TerritorialReport(
        territory_name=territory_name,
        report_date=report_date,
        period=period,
        n_assets=len(assets),
        sections=sections,
    )


# ── Section builders ──────────────────────────────────────────────────────

def _section_executive_summary(
    territory_name: str,
    assets: list[TerritorialAsset],
    kpis: PortfolioKPIs,
    budget: BudgetScenario,
) -> ReportSection:
    tier_groups = tier_summary(assets)
    t1_names = ", ".join(a.name for a in tier_groups[1][:3])
    t4_count = kpis.assets_promotion_ready
    t1_count = kpis.assets_immediate_attention

    lines = [
        f"Territory: {territory_name} | {len(assets)} assets monitored",
        f"Overall territory health: {kpis.territory_health_score:.0f}/100 "
        f"({_health_label(kpis.territory_health_score)}) | "
        f"Trend: {kpis.territory_trend}",
        "",
        f"!! IMMEDIATE ATTENTION REQUIRED: {t1_count} asset(s) in critical condition."
        + (f" ({t1_names})" if t1_names else ""),
        f"   Recommended investment: EUR {kpis.total_investment_estimate_eur:,} "
        f"(Tier 1+2 interventions).",
        "",
        f">> PROMOTION OPPORTUNITY: {t4_count} asset(s) are healthy and evidence-backed.",
        f"   Potential visitor reach from promotional assets: "
        f"{kpis.promotion_potential_visitors:,} visitors/year.",
        "",
        f"Evidence quality: {kpis.evidence_confidence_rate:.0f}% of assets have "
        f"sufficient evidence to act on. "
        f"{kpis.data_gaps_count} asset(s) require data collection upgrade.",
        f"Human-driven degradation alerts: {kpis.human_driven_degradation_alerts} "
        f"asset(s) where visitor pressure is causing measurable damage.",
    ]
    return ReportSection(title="1. EXECUTIVE SUMMARY", content=lines)


def _section_territorial_overview(
    assets: list[TerritorialAsset],
    kpis: PortfolioKPIs,
) -> ReportSection:
    ehs_dist = ehs_distribution(assets)
    scm_dist = scm_distribution(assets)
    type_break = asset_type_breakdown(assets)
    tier_groups = tier_summary(assets)

    lines = [
        f"Total assets monitored: {len(assets)}",
        f"Territory health score: {kpis.territory_health_score:.0f}/100",
        f"Territory environmental trend: {kpis.territory_trend}",
        "",
        "ENVIRONMENTAL HEALTH DISTRIBUTION:",
    ]
    for band, count in ehs_dist.items():
        bar = "#" * count + "-" * (len(assets) - count)
        lines.append(f"  {band:<22}: {count:2d} assets  [{bar}]")
    lines += [
        "",
        "PRIORITY TIER DISTRIBUTION:",
    ]
    for tier_num in [1, 2, 3, 4]:
        group = tier_groups[tier_num]
        label = TIER_LABELS[tier_num]
        lines.append(f"  Tier {tier_num} ({label:<24}): {len(group):2d} assets")
    lines += [
        "",
        "CAUSALITY BREAKDOWN (what is driving environmental change):",
        f"  Human-driven (LOCALIZED):  {scm_dist.get('LOCALIZED_IMPACT', 0):2d} assets -- "
        "respond to visitor management",
        f"  Climate-driven (LANDSCAPE): {scm_dist.get('LANDSCAPE_DRIVEN', 0):2d} assets -- "
        "respond to climate resilience measures",
        f"  Mixed / unclear:            {scm_dist.get('MIXED', 0):2d} assets -- "
        "need further investigation",
        "",
        "ASSET TYPE BREAKDOWN (mean EHS / % urgent):",
    ]
    for atype, stats in type_break.items():
        lines.append(
            f"  {atype:<22}: n={stats['count']}, "
            f"EHS={stats['mean_ehs']:.0f}/100, "
            f"DCS={stats['mean_dcs']:.0f}/100, "
            f"{stats['pct_urgent']:.0f}% urgent"
        )
    return ReportSection(title="2. TERRITORIAL HEALTH OVERVIEW", content=lines)


def _section_priority_assets(assets: list[TerritorialAsset]) -> ReportSection:
    tier_groups = tier_summary(assets)
    lines: list[str] = []

    for tier_num in [1, 2]:
        group = sorted(tier_groups[tier_num], key=lambda a: -(a.tpi or 0))
        label = TIER_LABELS[tier_num]
        lines.append(f"TIER {tier_num} — {label} ({len(group)} assets):")
        if not group:
            lines.append("  None.")
        for a in group:
            dcs_note = "(LOW EVIDENCE)" if a.dcs < 55 else ""
            lines.append(
                f"  [{a.priority_rank:2d}] {a.name:<38} "
                f"TPI={a.tpi:.0f}/100  EHS={a.ehs:.0f}/100  "
                f"DCS={a.dcs:.0f}/100 {dcs_note}"
            )
            lines.append(
                f"       Cause: {a.scm_classification} ({a.scm_confidence})  "
                f"Action: {a.recommended_action_label or 'TBD'}"
            )
        lines.append("")

    return ReportSection(title="3. PRIORITY ASSETS", content=lines)


def _section_recommended_actions(
    assets: list[TerritorialAsset],
    actions: dict[str, RecommendedAction],
) -> ReportSection:
    sorted_assets = sorted(assets, key=lambda a: a.priority_rank or 999)
    lines = [
        f"{'Rank':<5} {'Asset':<38} {'Tier':<4} {'Action':<34} "
        f"{'Confidence':<10} {'Cost (EUR)':>10}",
        "-" * 105,
    ]
    for a in sorted_assets:
        action = actions.get(a.asset_id)
        if not action:
            continue
        label = action.action_label[:33]
        cost_str = f"{action.estimated_cost_eur:>10,}" if action.estimated_cost_eur > 0 else "      0 (ops)"
        lines.append(
            f"  {a.priority_rank:<3}  {a.name:<38}  "
            f"T{a.tier}   {label:<34}  "
            f"{action.confidence_level:<10}  {cost_str}"
        )
    return ReportSection(title="4. RECOMMENDED ACTIONS (full table)", content=lines)


def _section_budget(budget: BudgetScenario) -> ReportSection:
    lines = [
        f"Available budget: EUR {budget.total_budget_eur:,}",
        f"Total allocated:  EUR {budget.total_allocated_eur:,}",
        f"Remaining:        EUR {budget.remaining_eur:,}",
        f"Assets funded: {budget.funded_assets} | Assets deferred: {budget.unfunded_assets}",
        "",
        budget.coverage_summary,
        "",
        "ALLOCATION DETAIL (funded items only):",
        f"  {'Rank':<5} {'Asset':<38} {'Tier':<4} {'Action':<30} {'EUR':>10}",
        "  " + "-" * 91,
    ]
    for alloc in sorted(budget.allocations, key=lambda a: a.allocation_rank):
        if alloc.funded and alloc.allocated_eur > 0:
            label = alloc.action_label[:29]
            lines.append(
                f"  {alloc.allocation_rank:<5} {alloc.asset_name:<38} "
                f"T{alloc.tier}   {label:<30} {alloc.allocated_eur:>10,}"
            )

    if budget.unfunded_assets > 0:
        lines += ["", "DEFERRED (insufficient budget):"]
        for alloc in budget.allocations:
            if not alloc.funded:
                lines.append(
                    f"  - {alloc.asset_name} ({alloc.action_label}, "
                    f"EUR {alloc.allocated_eur:,}) -- next budget cycle"
                )
    return ReportSection(title="5. BUDGET ALLOCATION", content=lines)


def _section_emerging_risks(
    assets: list[TerritorialAsset],
    kpis: PortfolioKPIs,
) -> ReportSection:
    declining = [a for a in assets if a.trend_direction == "decreasing"]
    evidence_gaps = [a for a in assets if a.dcs < 50]
    mixed_cause = [a for a in assets if a.scm_classification == "MIXED"]
    borderline = [a for a in assets if 50 <= a.ehs < 60 and a.tier == 3]

    lines: list[str] = []

    if declining:
        lines += [
            f"DECLINING TREND DETECTED ({len(declining)} assets):",
            "  These assets are showing worsening environmental health year-over-year.",
            "  If unaddressed, they will escalate to Tier 1 within 2-3 seasons.",
        ]
        for a in sorted(declining, key=lambda x: x.ehs):
            lines.append(
                f"  - {a.name}: EHS={a.ehs:.0f}/100, "
                f"Tier {a.tier} ({a.tier_label})"
            )
        lines.append("")

    if evidence_gaps:
        lines += [
            f"EVIDENCE GAPS ({len(evidence_gaps)} assets with DCS < 50):",
            "  These assets cannot be confidently managed until data improves.",
            "  Consider data collection upgrades as a low-cost risk mitigation.",
        ]
        for a in sorted(evidence_gaps, key=lambda x: x.dcs):
            lines.append(
                f"  - {a.name}: DCS={a.dcs:.0f}/100 "
                f"(EHS={a.ehs:.0f}/100, Tier {a.tier})"
            )
        lines.append("")

    if mixed_cause:
        lines += [
            f"UNCLEAR CAUSALITY ({len(mixed_cause)} assets with MIXED classification):",
            "  Cannot distinguish climate stress from visitor pressure.",
            "  Multi-buffer satellite analysis or field survey recommended.",
        ]
        for a in mixed_cause:
            lines.append(f"  - {a.name}: EHS={a.ehs:.0f}/100")
        lines.append("")

    if borderline:
        lines += [
            f"BORDERLINE ASSETS ({len(borderline)} assets in EHS 50-60 monitoring):",
            "  These are not yet urgent but one bad drought season could tip them.",
        ]
        for a in borderline:
            lines.append(f"  - {a.name}: EHS={a.ehs:.0f}/100")
        lines.append("")

    if not lines:
        lines = ["No significant emerging risks detected in this reporting period."]

    return ReportSection(title="6. EMERGING RISKS", content=lines)


def _section_promotion_opportunities(
    assets: list[TerritorialAsset],
    kpis: PortfolioKPIs,
) -> ReportSection:
    tier4 = sorted(
        [a for a in assets if a.tier == 4],
        key=lambda a: -a.visitor_capacity_annual,
    )

    lines = [
        f"PROMOTION-READY ASSETS: {len(tier4)} assets qualify for active marketing.",
        f"Combined visitor reach: {kpis.promotion_potential_visitors:,} visitors/year.",
        "",
    ]

    if tier4:
        lines.append(
            f"  {'Asset':<38} {'EHS':>5} {'DCS':>5} "
            f"{'Visitors/yr':>12} {'Action'}"
        )
        lines.append("  " + "-" * 80)
        for a in tier4:
            action_label = (a.recommended_action_label or "")[:22]
            lines.append(
                f"  {a.name:<38} {a.ehs:>5.0f} {a.dcs:>5.0f} "
                f"{a.visitor_capacity_annual:>12,}  {action_label}"
            )
        lines += [
            "",
            "PROMOTION INVESTMENT GUIDANCE:",
            "  Priority 1: Flagship assets (EHS >= 88 AND DCS >= 80)",
            "    -> Full campaign: EUR 12,000-18,000 per asset",
            "  Priority 2: High-strategic assets (visitors > 20,000/yr)",
            "    -> Targeted digital campaign: EUR 8,000-12,000",
            "  Priority 3: Remaining Tier 4 assets",
            "    -> Inclusion in destination brochures: EUR 1,500-3,000",
        ]
    else:
        lines.append(
            "No assets currently qualify for promotion. "
            "Improve environmental health of high-EHS assets and extend "
            "monitoring records to reach DCS >= 55."
        )

    return ReportSection(title="7. PROMOTION OPPORTUNITIES", content=lines)


# ── Utility ───────────────────────────────────────────────────────────────

def _health_label(score: float) -> str:
    if score >= 80:
        return "HEALTHY"
    if score >= 65:
        return "MODERATE"
    if score >= 50:
        return "AT RISK"
    return "DEGRADED"
