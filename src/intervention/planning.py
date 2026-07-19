"""Decision-facing budget envelopes built on the existing TIS optimiser.

The optimiser keeps using its central, modelled intervention costs.  This
module adds the uncertainty and comparison layer required by the v2 UI: three
annual investment envelopes, rounded cost bands, an effectiveness assumption,
and a tier-composition summary.  It intentionally does not turn those ranges
into observed prices or probabilistic confidence intervals.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.intervention.models import TISBudgetResult
from src.intervention.scenarios import allocate_tis_budget


@dataclass(frozen=True)
class BudgetScenarioAssumptions:
    """Editable planning assumptions shared by all compared envelopes."""

    cost_uncertainty_pct: int = 20
    effectiveness_pct: int = 80

    def __post_init__(self) -> None:
        if not 0 <= self.cost_uncertainty_pct <= 50:
            raise ValueError("cost_uncertainty_pct must be between 0 and 50")
        if not 0 <= self.effectiveness_pct <= 100:
            raise ValueError("effectiveness_pct must be between 0 and 100")


@dataclass(frozen=True)
class BudgetEnvelope:
    """One simulated annual-investment envelope and its transparent outputs."""

    code: str
    label: str
    budget_eur: int
    result: TISBudgetResult
    allocated_cost_low_eur: int
    allocated_cost_high_eur: int
    avoided_risk_delta: float
    funded_by_tier: tuple[tuple[int, int], ...]

    @property
    def funded_count(self) -> int:
        return len(self.result.funded_items)


_ENVELOPES = (
    ("essential", "Esencial", 0.75),
    ("annual", "Plan anual", 1.0),
    ("reinforced", "Refuerzo", 1.25),
)


def build_budget_envelopes(
    comparisons: list,
    assets_by_id: dict,
    annual_budget_eur: int,
    assumptions: BudgetScenarioAssumptions,
) -> tuple[BudgetEnvelope, ...]:
    """Compare three budget envelopes without changing optimiser semantics.

    ``avoided_risk_delta`` is the sum of the funded interventions' modelled
    risk reductions, moderated by the editable realisation assumption.  It is
    an aggregate scenario delta, not a probability or an observed effect.
    """
    if annual_budget_eur <= 0:
        raise ValueError("annual_budget_eur must be positive")

    envelopes = []
    for code, label, multiplier in _ENVELOPES:
        budget_eur = int(round(annual_budget_eur * multiplier, -3))
        result = allocate_tis_budget(comparisons, assets_by_id, budget_eur)
        uncertainty = assumptions.cost_uncertainty_pct / 100
        central_cost = result.total_allocated_eur
        low = _round_planning_eur(central_cost * (1 - uncertainty))
        high = _round_planning_eur(central_cost * (1 + uncertainty))
        avoided_risk = round(
            max(0.0, -result.portfolio_delta_risk)
            * assumptions.effectiveness_pct
            / 100,
            2,
        )
        tier_counts = tuple(
            (tier, sum(item.tier == tier for item in result.funded_items))
            for tier in range(1, 5)
        )
        envelopes.append(
            BudgetEnvelope(
                code=code,
                label=label,
                budget_eur=budget_eur,
                result=result,
                allocated_cost_low_eur=low,
                allocated_cost_high_eur=high,
                avoided_risk_delta=avoided_risk,
                funded_by_tier=tier_counts,
            )
        )
    return tuple(envelopes)


def _round_planning_eur(value: float) -> int:
    """Round scenario money to EUR 1,000 to avoid unsupported precision."""
    if value <= 0:
        return 0
    return int(round(value, -3))
