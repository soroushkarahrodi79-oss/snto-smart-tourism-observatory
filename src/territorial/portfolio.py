"""
SNTO Phase 5 — Portfolio Management
=====================================
Aggregates per-asset SNTO results into territory-level KPIs and
trend summaries for the executive dashboard.

DESIGN PRINCIPLE
================
The system must stop thinking asset-by-asset.
A destination manager needs to see the territory as a portfolio:
some assets are healthy performers, some are deteriorating, some are
urgent, some represent untapped potential.

10 ACTIONABLE KPIs (no technical indicators, no NDVI)
======================================================
1.  Territory Health Score (0-100)
    Mean EHS across all assets. Benchmark: > 70 = healthy territory.

2.  Assets Requiring Immediate Attention (count)
    Tier 1 assets. Any non-zero value demands a response at next meeting.

3.  Assets Ready for Promotion (count)
    Tier 4 assets. Directly feeds marketing and DMO budgets.

4.  Evidence Confidence Rate (%)
    % of assets where DCS >= 60. Below 60% = significant knowledge gap.

5.  Human-Driven Degradation Alerts (count)
    Tier 1+2 assets with LOCALIZED_IMPACT classification. These respond
    to management action; climate-driven degradation does not.

6.  Visitor Capacity at Risk (annual visits)
    Sum of visitor_capacity_annual for all Tier 1 and Tier 2 assets.
    Translates environmental risk into tourism economic risk.

7.  Total Investment Required (EUR)
    Sum of budget_estimate_eur for Tier 1 and Tier 2 assets.
    Feeds the annual planning budget process.

8.  Territory Trend (IMPROVING / STABLE / DECLINING)
    Based on the balance of asset trend directions.

9.  Data Gaps (count)
    Assets with DCS < 50. Cannot confidently act on these.

10. Promotion Visitor Potential (annual visits)
    Sum of visitor_capacity_annual for all Tier 4 assets.
    Quantifies the economic opportunity from healthy assets.
"""

from __future__ import annotations

import statistics
from .models import TerritorialAsset, PortfolioKPIs


def compute_portfolio_kpis(assets: list[TerritorialAsset]) -> PortfolioKPIs:
    """
    Compute the 10 territorial KPIs from a list of evaluated assets.
    All assets must have tier, tpi, and budget_estimate_eur already set.
    """
    if not assets:
        raise ValueError("Cannot compute KPIs for an empty asset list.")

    # KPI 1: Territory Health Score
    territory_health = round(statistics.mean(a.ehs for a in assets), 1)

    # KPI 2: Assets Requiring Immediate Attention
    tier1_assets = [a for a in assets if a.tier == 1]
    assets_immediate = len(tier1_assets)

    # KPI 3: Assets Ready for Promotion
    tier4_assets = [a for a in assets if a.tier == 4]
    assets_promotion = len(tier4_assets)

    # KPI 4: Evidence Confidence Rate
    confident = sum(1 for a in assets if a.dcs >= 60)
    confidence_rate = round(confident / len(assets) * 100, 1)

    # KPI 5: Human-Driven Degradation Alerts
    human_alerts = sum(
        1 for a in assets
        if a.scm_classification == "LOCALIZED_IMPACT"
        and a.tier in (1, 2)
    )

    # KPI 6: Visitor Capacity at Risk
    visitors_at_risk = sum(
        a.visitor_capacity_annual
        for a in assets
        if a.tier in (1, 2)
    )

    # KPI 7: Total Investment Required (Tier 1 + 2 only)
    investment_required = sum(
        (a.budget_estimate_eur or 0)
        for a in assets
        if a.tier in (1, 2)
    )

    # KPI 8: Territory Trend
    trend_scores = []
    for a in assets:
        if a.trend_direction == "increasing":
            trend_scores.append(1)
        elif a.trend_direction == "decreasing":
            trend_scores.append(-1)
        else:
            trend_scores.append(0)
    net_trend = sum(trend_scores)
    n = len(assets)
    if net_trend > n * 0.20:
        territory_trend = "IMPROVING"
    elif net_trend < -n * 0.20:
        territory_trend = "DECLINING"
    else:
        territory_trend = "STABLE"

    # KPI 9: Data Gaps
    data_gaps = sum(1 for a in assets if a.dcs < 50)

    # KPI 10: Promotion Visitor Potential
    promotion_visitors = sum(a.visitor_capacity_annual for a in tier4_assets)

    return PortfolioKPIs(
        territory_health_score=territory_health,
        assets_immediate_attention=assets_immediate,
        assets_promotion_ready=assets_promotion,
        evidence_confidence_rate=confidence_rate,
        human_driven_degradation_alerts=human_alerts,
        visitor_capacity_at_risk=visitors_at_risk,
        total_investment_estimate_eur=investment_required,
        territory_trend=territory_trend,
        data_gaps_count=data_gaps,
        promotion_potential_visitors=promotion_visitors,
    )


def tier_summary(assets: list[TerritorialAsset]) -> dict[int, list[TerritorialAsset]]:
    """Group assets by tier for structured reporting."""
    groups: dict[int, list[TerritorialAsset]] = {1: [], 2: [], 3: [], 4: []}
    for a in assets:
        groups[a.tier or 3].append(a)
    return groups


def ehs_distribution(assets: list[TerritorialAsset]) -> dict[str, int]:
    """Classify assets into EHS bands for portfolio overview."""
    bands: dict[str, int] = {
        "Excellent (90-100)": 0,
        "Good (75-89)":       0,
        "Moderate (60-74)":   0,
        "Poor (40-59)":       0,
        "Critical (0-39)":    0,
    }
    for a in assets:
        if a.ehs >= 90:
            bands["Excellent (90-100)"] += 1
        elif a.ehs >= 75:
            bands["Good (75-89)"] += 1
        elif a.ehs >= 60:
            bands["Moderate (60-74)"] += 1
        elif a.ehs >= 40:
            bands["Poor (40-59)"] += 1
        else:
            bands["Critical (0-39)"] += 1
    return bands


def scm_distribution(assets: list[TerritorialAsset]) -> dict[str, int]:
    """Break down territory by spatial causality classification."""
    dist: dict[str, int] = {
        "LOCALIZED_IMPACT": 0,
        "LANDSCAPE_DRIVEN": 0,
        "MIXED":            0,
    }
    for a in assets:
        dist[a.scm_classification] = dist.get(a.scm_classification, 0) + 1
    return dist


def asset_type_breakdown(
    assets: list[TerritorialAsset],
) -> dict[str, dict[str, float]]:
    """
    Per-asset-type summary: count, mean EHS, mean DCS, % Tier 1-2.
    """
    by_type: dict[str, list[TerritorialAsset]] = {}
    for a in assets:
        by_type.setdefault(a.asset_type, []).append(a)

    summary: dict[str, dict[str, float]] = {}
    for atype, group in sorted(by_type.items()):
        n = len(group)
        urgent = sum(1 for a in group if a.tier in (1, 2))
        summary[atype] = {
            "count":       n,
            "mean_ehs":    round(statistics.mean(a.ehs for a in group), 1),
            "mean_dcs":    round(statistics.mean(a.dcs for a in group), 1),
            "pct_urgent":  round(urgent / n * 100, 1),
        }
    return summary
