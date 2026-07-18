"""Contracts for the Fase 6.3 KPI ownership split."""

import pytest

from src.platform.dashboard import DashboardKPI
from src.ui.kpi_sections import (
    DECISION_KPI_NUMBERS,
    DIAGNOSTIC_KPI_NUMBERS,
    decision_kpis,
    diagnostic_kpis,
    kpi_evidence_label,
)


def _kpi(number: int) -> DashboardKPI:
    return DashboardKPI(
        number=number,
        name=f"KPI {number}",
        value=str(number),
        status="GREEN",
        status_label="OK",
        what_it_means="Meaning",
        recommended_action="Action",
        technical_basis="Basis",
    )


def test_all_ten_kpis_have_one_ui_owner() -> None:
    decision = set(DECISION_KPI_NUMBERS)
    diagnostic = set(DIAGNOSTIC_KPI_NUMBERS)
    assert decision.isdisjoint(diagnostic)
    assert decision | diagnostic == set(range(1, 11))


def test_partition_preserves_intended_order() -> None:
    source = [_kpi(number) for number in range(10, 0, -1)]
    assert [kpi.number for kpi in decision_kpis(source)] == [2, 5, 7, 10]
    assert [kpi.number for kpi in diagnostic_kpis(source)] == [1, 3, 4, 6, 8, 9]


def test_decision_figures_are_calculated_only() -> None:
    assert {
        kpi_evidence_label(number) for number in DECISION_KPI_NUMBERS
    } == {"CALCULADO"}
    assert kpi_evidence_label(3) == "ESTIMADO"
    assert kpi_evidence_label(4) == "SIMULADO"


def test_missing_or_unknown_kpi_fails_loudly() -> None:
    with pytest.raises(ValueError, match="missing KPI"):
        decision_kpis([_kpi(2)])
    with pytest.raises(ValueError, match="Unknown dashboard KPI"):
        kpi_evidence_label(11)
