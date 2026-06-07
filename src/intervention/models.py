"""
SNTO Phase 6 -- Intervention Impact & Scenario Planning: Data Models
=====================================================================
All data classes for the intervention impact and scenario planning layer.

This module defines the immutable value objects that flow through the
Phase 6 pipeline:

  InterventionEffect    -- delta estimates for one intervention on one asset
  ScenarioResult        -- outcome of one scenario (A-E) for one asset
  AssetScenarioComparison -- all 5 scenarios + recommended choice
  CounterfactualYear    -- one-year snapshot in the no-intervention trajectory
  CounterfactualResult  -- full 3-year no-intervention projection
  TISBudgetItem         -- one allocation line in the TIS-optimised budget
  TISBudgetResult       -- complete TIS-optimised budget scenario
  DecisionExplanation   -- full transparency record for one asset
  Phase6ReportSection   -- one titled section of the institutional report
  Phase6Report          -- complete Phase 6 report
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Intervention type constants ────────────────────────────────────────────

RESTORATION            = "RESTORATION"
MONITORING_ENHANCEMENT = "MONITORING_ENHANCEMENT"
PROMOTION              = "PROMOTION"
COMBINED               = "COMBINED_OPTIMAL"
NO_INTERVENTION        = "NO_INTERVENTION"

# ── Scenario codes and labels ──────────────────────────────────────────────

SCENARIO_LABELS: dict[str, str] = {
    "A": "No Intervention",
    "B": "Restoration",
    "C": "Monitoring Enhancement",
    "D": "Promotion Investment",
    "E": "Combined Optimal",
}

SCENARIO_INTERVENTION: dict[str, str] = {
    "A": NO_INTERVENTION,
    "B": RESTORATION,
    "C": MONITORING_ENHANCEMENT,
    "D": PROMOTION,
    "E": COMBINED,
}

# ── Feasibility bands ──────────────────────────────────────────────────────

FEASIBILITY_VIABLE           = "VIABLE"
FEASIBILITY_MARGINAL         = "MARGINAL"
FEASIBILITY_NOT_RECOMMENDED  = "NOT_RECOMMENDED"


# ── Impact effect ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InterventionEffect:
    """
    Rule-based delta estimates for one intervention type applied to one asset.

    All deltas represent *expected change* if the intervention is executed:
      delta_ehs      : change in Environmental Health Score (can be negative)
      delta_risk     : change in risk_score -- negative means reduction
      delta_dcs      : change in Decision Confidence Score
      delta_visitors : change in annual visitor volume (can be negative)
      cost_eur       : total estimated investment in EUR

    feasibility classifies whether the intervention is appropriate for this
    asset given its current condition, tier, and evidence quality.
    """
    asset_id: str
    intervention_type: str
    delta_ehs: float
    delta_risk: float
    delta_dcs: float
    delta_visitors: int
    cost_eur: int
    feasibility: str           # VIABLE | MARGINAL | NOT_RECOMMENDED
    feasibility_reason: str


# ── Scenario result ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ScenarioResult:
    """
    Projected outcome of applying one scenario (A-E) to one asset.

    projected_* fields are post-intervention values (current + delta, clamped).
    tis is the Territorial Impact Score (0-100): benefit per euro invested.
    """
    asset_id: str
    scenario_code: str         # "A" | "B" | "C" | "D" | "E"
    scenario_label: str
    intervention_type: str
    delta_ehs: float
    delta_risk: float
    delta_dcs: float
    delta_visitors: int
    projected_ehs: float       # clamped to [0, 100]
    projected_risk: float      # clamped to [0, 1]
    projected_dcs: float       # clamped to [0, 100]
    projected_visitors: int    # non-negative
    cost_eur: int
    tis: float                 # Territorial Impact Score 0-100
    feasibility: str


# ── Per-asset scenario comparison ──────────────────────────────────────────

@dataclass(frozen=True)
class AssetScenarioComparison:
    """
    All 5 scenarios for one asset plus the recommended choice.

    dcs_constrained is True when DCS < 55 forced the recommendation to
    monitoring-only regardless of which intervention would score highest.
    """
    asset_id: str
    asset_name: str
    current_tier: int
    current_ehs: float
    current_dcs: float
    scenarios: dict            # scenario_code (str) -> ScenarioResult
    best_scenario_code: str
    best_scenario_label: str
    best_scenario_reason: str
    dcs_constrained: bool


# ── Counterfactual projection ──────────────────────────────────────────────

@dataclass(frozen=True)
class CounterfactualYear:
    """One annual snapshot in the no-intervention environmental trajectory."""
    year: int                       # 1, 2, or 3
    ehs: float                      # projected EHS at end of year
    risk: float                     # projected risk at end of year
    visitor_pct_change: float       # cumulative % change from baseline (neg = loss)
    alert_escalation: str           # "" if unchanged, else escalated alert code


@dataclass(frozen=True)
class CounterfactualResult:
    """
    3-year no-intervention projection for one asset.

    Answers: "What happens if we do nothing here?"

    cumulative_visitor_loss : total visitors lost across 3 years
    estimated_inaction_cost_eur : visitor revenue loss + future restoration premium
    uncertainty : HIGH (DCS<50) | MODERATE (50-70) | LOW (DCS>=70)
    narrative   : plain-language explanation for institutional reports
    """
    asset_id: str
    asset_name: str
    years: list                     # list[CounterfactualYear]
    ehs_trajectory: str            # STABLE | DECLINING | ACCELERATING_DECLINE
    risk_trajectory: str           # STABLE | RISING | RAPIDLY_RISING
    cumulative_visitor_loss: int
    estimated_inaction_cost_eur: int
    uncertainty: str
    narrative: str


# ── TIS-optimised budget ───────────────────────────────────────────────────

@dataclass(frozen=True)
class TISBudgetItem:
    """One line in the TIS-optimised budget allocation."""
    asset_id: str
    asset_name: str
    tier: int
    scenario_code: str
    intervention_label: str
    cost_eur: int
    tis: float
    funded: bool
    fund_rationale: str            # why this was funded (empty if deferred)
    defer_reason: str              # why this was deferred (empty if funded)


@dataclass(frozen=True)
class TISBudgetResult:
    """
    Complete TIS-optimised budget scenario.

    Allocates the available budget to maximise total territorial benefit
    (TIS), subject to the DCS evidence gate (DCS < 55 -> monitoring only).

    portfolio_tis is the budget-weighted average TIS across funded items.
    """
    total_budget_eur: int
    total_allocated_eur: int
    remaining_eur: int
    funded_items: list             # list[TISBudgetItem]
    deferred_items: list           # list[TISBudgetItem]
    portfolio_delta_ehs: float     # total DELTA_EHS across all funded items
    portfolio_delta_risk: float    # total DELTA_RISK (negative = reduction)
    portfolio_delta_visitors: int  # total DELTA_VISITORS across funded items
    portfolio_delta_dcs: float     # total DELTA_DCS across funded items
    portfolio_tis: float           # budget-weighted average TIS


# ── Decision explanation ───────────────────────────────────────────────────

@dataclass(frozen=True)
class DecisionExplanation:
    """
    Full transparency record for one asset's recommended intervention.

    Provides the institutionally required "why" narrative:
      - What was chosen and why
      - What was considered and rejected (and why)
      - Trade-offs the decision-maker should be aware of
      - Confidence level and evidence basis
      - Counterfactual headline (inaction cost)
    """
    asset_id: str
    asset_name: str
    chosen_scenario: str           # "A"-"E"
    chosen_intervention: str
    chosen_cost_eur: int
    chosen_tis: float
    chosen_rationale: str
    rejected: list                 # list of dicts: {code, label, tis, reason}
    trade_offs: str
    confidence_level: str          # HIGH | MODERATE | LOW
    confidence_note: str
    counterfactual_headline: str   # e.g. "Without action: EHS drops to 27 by year 3"


# ── Report container ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Phase6ReportSection:
    title: str
    content: list                  # list[str]


@dataclass(frozen=True)
class Phase6Report:
    """Complete Phase 6 intervention impact and scenario planning report."""
    territory_name: str
    report_date: str
    n_assets: int
    sections: list                 # list[Phase6ReportSection]
