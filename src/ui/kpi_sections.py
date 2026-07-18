"""Fase 6.3 ownership of the ten legacy dashboard KPIs.

The executive panorama keeps only calculated figures that directly support an
approve/postpone/verify decision. The other six indicators remain available in
Diagnosticar as contextual evidence; none of the original KPIs is removed.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.platform.dashboard import DashboardKPI

DECISION_KPI_NUMBERS = (2, 5, 7, 10)
DIAGNOSTIC_KPI_NUMBERS = (1, 3, 4, 6, 8, 9)

_KPI_EVIDENCE_LABELS = {
    1: "CALCULADO",
    2: "CALCULADO",
    3: "ESTIMADO",
    4: "SIMULADO",
    5: "CALCULADO",
    6: "ESTIMADO",
    7: "CALCULADO",
    8: "SIMULADO",
    9: "CALCULADO",
    10: "CALCULADO",
}


def _select_kpis(
    kpis: Sequence[DashboardKPI], numbers: tuple[int, ...]
) -> list[DashboardKPI]:
    by_number = {kpi.number: kpi for kpi in kpis}
    missing = [number for number in numbers if number not in by_number]
    if missing:
        raise ValueError(f"Dashboard is missing KPI number(s): {missing}")
    return [by_number[number] for number in numbers]


def decision_kpis(kpis: Sequence[DashboardKPI]) -> list[DashboardKPI]:
    """Return the four calculated figures owned by the Decidir panorama."""
    return _select_kpis(kpis, DECISION_KPI_NUMBERS)


def diagnostic_kpis(kpis: Sequence[DashboardKPI]) -> list[DashboardKPI]:
    """Return the six contextual figures relocated to Diagnosticar."""
    return _select_kpis(kpis, DIAGNOSTIC_KPI_NUMBERS)


def kpi_evidence_label(number: int) -> str:
    """Return the weakest evidence class inherited by a dashboard KPI."""
    try:
        return _KPI_EVIDENCE_LABELS[number]
    except KeyError as exc:
        raise ValueError(f"Unknown dashboard KPI number: {number}") from exc
