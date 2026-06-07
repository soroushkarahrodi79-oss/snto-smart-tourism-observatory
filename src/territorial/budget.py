"""
SNTO Phase 5 — Budget Prioritisation Engine
============================================
Translates the TPI-ordered asset list and RecommendedAction costs into
a transparent, rule-based budget allocation scenario.

DESIGN PRINCIPLE
================
This is NOT a mathematical optimiser. It uses explicit decision rules
that a public administrator can follow step-by-step without software.

ALLOCATION RULES (applied in strict priority order)
====================================================
Rule 1 — SAFETY FIRST:
  Process all Tier 1 assets first, sorted by TPI descending.
  Tier 1 items can never be deferred by Tier 4 promotion items.

Rule 2 — EVIDENCE GATING:
  If a Tier 1 asset has DCS < 55 (LOW confidence), the action is
  URGENT_EVIDENCE_COLLECTION (cheaper: ~EUR 3,500) rather than full
  restoration. Capital-intensive restoration is deferred until evidence
  meets the confidence threshold.

Rule 3 — PREVENTIVE BEFORE PROMOTION:
  All Tier 2 items are allocated before any Tier 4 promotion.
  Prevention is cheaper than restoration; promotion is discretionary.

Rule 4 — PROMOTION ORDERED BY STRATEGIC VALUE:
  Among Tier 4 assets, order by visitor_capacity_annual descending.
  The asset with the most visitors to gain drives the highest promotion ROI.

Rule 5 — MONITORING LAST:
  Tier 3 DATA_COLLECTION_UPGRADE items are funded last, from remaining
  budget. ROUTINE_MONITORING items cost EUR 0 and are always included.

Rule 6 — STOP WHEN BUDGET EXHAUSTED:
  Remaining unfunded items are flagged for next budget cycle.
  No overspending; no partial funding of a single action.
"""

from __future__ import annotations

from .models import (
    TerritorialAsset,
    RecommendedAction,
    BudgetAllocation,
    BudgetScenario,
)


def allocate_budget(
    assets: list[TerritorialAsset],
    actions: dict[str, RecommendedAction],
    total_budget_eur: int,
) -> BudgetScenario:
    """
    Apply the six prioritisation rules and return a complete budget scenario.

    Args:
        assets : list of TerritorialAsset with tier and tpi set.
        actions: dict mapping asset_id → RecommendedAction.
        total_budget_eur: total available budget in EUR.

    Returns:
        BudgetScenario with per-asset allocations and summary.
    """
    # Build ordered queue following the 6 rules
    ordered = _build_priority_queue(assets)

    remaining = total_budget_eur
    allocations: list[BudgetAllocation] = []
    alloc_rank = 0

    for asset in ordered:
        action = actions.get(asset.asset_id)
        if action is None:
            continue
        cost = action.estimated_cost_eur
        alloc_rank += 1

        if cost == 0:
            # ROUTINE_MONITORING is always funded (zero cost)
            funded = True
            rationale = "Zero-cost action. Covered by standard operations budget."
        elif cost <= remaining:
            funded = True
            remaining -= cost
            rationale = _allocation_rationale(asset, action, remaining + cost, cost)
        else:
            funded = False
            rationale = (
                f"Insufficient budget remaining (EUR {remaining:,} < EUR {cost:,}). "
                "Defer to next budget cycle."
            )

        allocations.append(BudgetAllocation(
            asset_id=asset.asset_id,
            asset_name=asset.name,
            tier=asset.tier or 3,
            action_label=action.action_label,
            allocated_eur=cost if funded else 0,
            allocation_rank=alloc_rank,
            allocation_rationale=rationale,
            funded=funded,
        ))

    total_allocated = sum(a.allocated_eur for a in allocations)
    funded_count = sum(1 for a in allocations if a.funded and a.allocated_eur > 0)
    unfunded_count = sum(1 for a in allocations if not a.funded)

    coverage = _coverage_summary(allocations, total_budget_eur)

    return BudgetScenario(
        total_budget_eur=total_budget_eur,
        allocations=allocations,
        total_allocated_eur=total_allocated,
        remaining_eur=max(0, total_budget_eur - total_allocated),
        funded_assets=funded_count,
        unfunded_assets=unfunded_count,
        coverage_summary=coverage,
    )


# ── Priority queue builder ────────────────────────────────────────────────

def _build_priority_queue(assets: list[TerritorialAsset]) -> list[TerritorialAsset]:
    """
    Order assets following the 6 allocation rules.
    Returns a list from highest priority to lowest.
    """
    def sort_key(a: TerritorialAsset) -> tuple:
        tier = a.tier or 3
        # Within tier, sort by TPI descending, then by strategic value proxy
        sv = a.economic_importance * 0.5 + a.accessibility_score * 0.3
        if tier == 1:
            return (0, -(a.tpi or 0), -sv)
        elif tier == 2:
            return (1, -(a.tpi or 0), -sv)
        elif tier == 4:
            # Among Tier 4, highest visitor capacity first (Rule 4)
            return (2, -a.visitor_capacity_annual, -(a.tpi or 0))
        else:  # Tier 3
            return (3, -(a.tpi or 0), -sv)

    return sorted(assets, key=sort_key)


# ── Helper functions ──────────────────────────────────────────────────────

def _allocation_rationale(
    asset: TerritorialAsset,
    action: RecommendedAction,
    budget_before: int,
    cost: int,
) -> str:
    tier_names = {1: "Tier 1 (Immediate)", 2: "Tier 2 (Preventive)",
                  3: "Tier 3 (Monitoring)", 4: "Tier 4 (Promotion)"}
    tier_label = tier_names.get(asset.tier or 3, "Tier ?")
    return (
        f"{tier_label}, TPI={asset.tpi:.0f}/100. "
        f"DCS={asset.dcs:.0f}/100 ({action.confidence_level} confidence). "
        f"Cost EUR {cost:,} allocated from EUR {budget_before:,} remaining."
    )


def _coverage_summary(
    allocations: list[BudgetAllocation],
    total: int,
) -> str:
    t1_funded = sum(1 for a in allocations if a.tier == 1 and a.funded)
    t1_total  = sum(1 for a in allocations if a.tier == 1)
    t4_funded = sum(1 for a in allocations if a.tier == 4 and a.funded)
    t4_total  = sum(1 for a in allocations if a.tier == 4)
    allocated = sum(a.allocated_eur for a in allocations)
    pct = round(allocated / total * 100, 1) if total > 0 else 0.0
    return (
        f"Tier 1 coverage: {t1_funded}/{t1_total} assets funded. "
        f"Promotion funded: {t4_funded}/{t4_total}. "
        f"Total allocated: EUR {allocated:,} ({pct}% of budget)."
    )
