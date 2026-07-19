"""Contracts for the Phase 6.7 decision-facing budget envelopes."""

from __future__ import annotations

import pytest

from src.intervention import (
    BudgetScenarioAssumptions,
    build_budget_envelopes,
    compare_scenarios,
)
from src.territorial.fixtures import build_territory


def _portfolio_inputs():
    assets = build_territory()
    max_visitors = max(asset.visitor_capacity_annual for asset in assets)
    comparisons = [compare_scenarios(asset, max_visitors) for asset in assets]
    return comparisons, {asset.asset_id: asset for asset in assets}


def test_budget_envelopes_compare_three_ordered_investment_levels() -> None:
    comparisons, assets_by_id = _portfolio_inputs()

    envelopes = build_budget_envelopes(
        comparisons,
        assets_by_id,
        100_000,
        BudgetScenarioAssumptions(),
    )

    assert [item.code for item in envelopes] == ["essential", "annual", "reinforced"]
    assert [item.budget_eur for item in envelopes] == [75_000, 100_000, 125_000]
    assert [item.funded_count for item in envelopes] == sorted(
        item.funded_count for item in envelopes
    )
    assert all(
        sum(count for _, count in item.funded_by_tier) == item.funded_count
        for item in envelopes
    )


def test_cost_band_and_effectiveness_assumptions_are_explicit() -> None:
    comparisons, assets_by_id = _portfolio_inputs()
    full = build_budget_envelopes(
        comparisons,
        assets_by_id,
        100_000,
        BudgetScenarioAssumptions(cost_uncertainty_pct=20, effectiveness_pct=100),
    )[1]
    half = build_budget_envelopes(
        comparisons,
        assets_by_id,
        100_000,
        BudgetScenarioAssumptions(cost_uncertainty_pct=20, effectiveness_pct=50),
    )[1]

    assert full.allocated_cost_low_eur <= full.result.total_allocated_eur
    assert full.allocated_cost_high_eur >= full.result.total_allocated_eur
    assert half.avoided_risk_delta == round(full.avoided_risk_delta / 2, 2)
    assert full.allocated_cost_low_eur % 1_000 == 0
    assert full.allocated_cost_high_eur % 1_000 == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cost_uncertainty_pct": -1},
        {"cost_uncertainty_pct": 51},
        {"effectiveness_pct": -1},
        {"effectiveness_pct": 101},
    ],
)
def test_budget_assumptions_reject_unsupported_ranges(kwargs) -> None:
    with pytest.raises(ValueError):
        BudgetScenarioAssumptions(**kwargs)
