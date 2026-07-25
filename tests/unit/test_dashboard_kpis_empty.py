"""Contracts for KPI behaviour on an empty asset portfolio.

Three of the ten KPI builders divide by the asset count (territory health,
decision-confidence rate, recovery progress) and raised ``ZeroDivisionError``
on ``[]``. They are reached today only through ``compute_executive_dashboard``,
which already rejects an empty portfolio, so the crash was latent rather than
live — but the private helpers must be individually safe for any future caller
(e.g. a per-KPI view of a freshly-registered, still-empty territory).

The non-negotiable: an empty territory yields an honest **"no data"** KPI, never
a fabricated value. ``0/100`` health would read as *critically degraded* when
the truth is *nothing measured yet* — the exact evidence blur the project
forbids. So "no data" is a neutral BLUE state, never RED.
"""
from __future__ import annotations

import inspect

import pytest

from src.platform import dashboard
from src.platform.dashboard import (
    DashboardKPI,
    _kpi_decision_confidence_rate,
    _kpi_recovery_progress,
    _kpi_territory_health,
)

# The three KPIs that divide by the asset count.
_DIVIDING_KPIS = (
    _kpi_territory_health,
    _kpi_decision_confidence_rate,
    _kpi_recovery_progress,
)


def _single_arg_kpi_builders():
    """Every ``_kpi_*`` helper that takes only the asset list."""
    for name, fn in vars(dashboard).items():
        if name.startswith("_kpi_") and callable(fn):
            if len(inspect.signature(fn).parameters) == 1:
                yield name, fn


# ── No KPI crashes on an empty portfolio ─────────────────────────────────────

@pytest.mark.parametrize("kpi", _DIVIDING_KPIS)
def test_dividing_kpi_does_not_crash_on_empty(kpi) -> None:
    result = kpi([])
    assert isinstance(result, DashboardKPI)


def test_no_single_arg_kpi_builder_crashes_on_empty() -> None:
    """Locks in that the whole KPI layer tolerates an empty portfolio."""
    crashed = []
    for name, fn in _single_arg_kpi_builders():
        try:
            fn([])
        except Exception as exc:  # noqa: BLE001 - the point is to catch any crash
            crashed.append(f"{name}: {type(exc).__name__}")
    assert crashed == [], f"KPI builders crashing on []: {crashed}"


# ── The empty state is honest, not fabricated ────────────────────────────────

@pytest.mark.parametrize("kpi", _DIVIDING_KPIS)
def test_empty_kpi_is_neutral_never_red(kpi) -> None:
    """A missing measurement must not masquerade as a bad one."""
    result = kpi([])
    assert result.status != "RED"
    assert result.status == "BLUE"
    assert result.status_label == "NO DATA"


def test_empty_health_does_not_report_a_zero_score() -> None:
    """0/100 would read as critical health; absence must read as absence."""
    result = _kpi_territory_health([])
    assert "0/100" not in result.value
    assert result.value == "sin datos"
    assert "ausencia de dato" in result.what_it_means


@pytest.mark.parametrize("kpi", _DIVIDING_KPIS)
def test_empty_kpi_preserves_its_number_and_name(kpi) -> None:
    """The KPI is still identifiable so the UI can slot it correctly."""
    result = kpi([])
    assert result.number in (1, 5, 9)
    assert result.name
    assert result.technical_basis


# ── The orchestrator keeps its stricter contract ─────────────────────────────

def test_orchestrator_still_rejects_an_empty_portfolio() -> None:
    """compute_executive_dashboard documents a non-empty precondition; the
    KPI-level hardening is defence in depth, not a relaxation of that contract."""
    from src.platform.dashboard import compute_executive_dashboard

    with pytest.raises(ValueError, match="At least one asset"):
        compute_executive_dashboard(
            territory_name="Vacío",
            report_date="2026-07-25",
            assets=[],
            budget_result=None,
            comparisons=[],
        )
