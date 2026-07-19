"""SNTO Phase 6 -- Intervention Impact & Scenario Planning module."""

from src.intervention.models import (
    RESTORATION,
    MONITORING_ENHANCEMENT,
    PROMOTION,
    COMBINED,
    NO_INTERVENTION,
    SCENARIO_LABELS,
    FEASIBILITY_VIABLE,
    FEASIBILITY_MARGINAL,
    FEASIBILITY_NOT_RECOMMENDED,
    InterventionEffect,
    ScenarioResult,
    AssetScenarioComparison,
    CounterfactualYear,
    CounterfactualResult,
    TISBudgetItem,
    TISBudgetResult,
    DecisionExplanation,
    Phase6ReportSection,
    Phase6Report,
)
from src.intervention.impact import (
    compute_restoration_effect,
    compute_monitoring_effect,
    compute_promotion_effect,
    compute_tis,
    COST_RESTORATION,
    COST_MONITORING,
    COST_PROMOTION,
    COST_PROMOTION_LITE,
)
from src.intervention.scenarios import (
    compare_scenarios,
    compute_counterfactual,
    allocate_tis_budget,
)
from src.intervention.planning import (
    BudgetEnvelope,
    BudgetScenarioAssumptions,
    build_budget_envelopes,
)
from src.intervention.reporter import (
    generate_phase6_report,
    build_explanation,
)

__all__ = [
    # Constants
    "RESTORATION", "MONITORING_ENHANCEMENT", "PROMOTION", "COMBINED",
    "NO_INTERVENTION", "SCENARIO_LABELS",
    "FEASIBILITY_VIABLE", "FEASIBILITY_MARGINAL", "FEASIBILITY_NOT_RECOMMENDED",
    "COST_RESTORATION", "COST_MONITORING", "COST_PROMOTION", "COST_PROMOTION_LITE",
    # Models
    "InterventionEffect", "ScenarioResult", "AssetScenarioComparison",
    "CounterfactualYear", "CounterfactualResult",
    "TISBudgetItem", "TISBudgetResult",
    "BudgetEnvelope", "BudgetScenarioAssumptions",
    "DecisionExplanation",
    "Phase6ReportSection", "Phase6Report",
    # Functions
    "compute_restoration_effect", "compute_monitoring_effect",
    "compute_promotion_effect", "compute_tis",
    "compare_scenarios", "compute_counterfactual", "allocate_tis_budget",
    "build_budget_envelopes",
    "generate_phase6_report", "build_explanation",
]
