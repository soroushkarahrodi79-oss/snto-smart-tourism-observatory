"""Contracts for the territorial executive brief (Fase 6.7e).

Non-negotiables under test: the brief rolls up **only** fields the dashboard
already holds, never fabricates a missing value, orders worst-first, and never
implies field validation.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.reporting.territorial_brief import (
    build_territorial_brief,
    render_territorial_brief_markdown,
)


@dataclass
class _FakeAsset:
    """Minimal stand-in exposing the TerritorialAsset fields the brief reads."""

    asset_id: str
    name: str
    ehs: float | None
    risk_score: float | None
    tier: int | None
    tier_label: str | None
    alert_level: str | None
    trend_direction: str | None
    recommended_action_label: str | None
    budget_estimate_eur: float | None


def _portfolio() -> list[_FakeAsset]:
    return [
        _FakeAsset(
            "a-low", "Mirador tranquilo", ehs=88.0, risk_score=0.12,
            tier=4, tier_label="PROMOTION READY", alert_level="NORMAL",
            trend_direction="stable", recommended_action_label="Mantener",
            budget_estimate_eur=None,
        ),
        _FakeAsset(
            "a-crit", "Laguna crítica", ehs=35.0, risk_score=0.77,
            tier=1, tier_label="IMMEDIATE ATTENTION",
            alert_level="CRITICAL_INTERVENTION", trend_direction="decreasing",
            recommended_action_label="Inspección urgente",
            budget_estimate_eur=12000.0,
        ),
    ]


def test_brief_orders_worst_first_by_tier() -> None:
    brief = build_territorial_brief(
        _portfolio(), territory_name="PNSG", report_date="2026-07-20"
    )
    ids = [e["asset_id"] for e in brief["entries"]]
    assert ids == ["a-crit", "a-low"]  # tier 1 before tier 4
    assert brief["entries"][0]["rank"] == 1


def test_missing_budget_and_action_degrade_explicitly() -> None:
    brief = build_territorial_brief(
        _portfolio(), territory_name="PNSG", report_date="2026-07-20"
    )
    low = next(e for e in brief["entries"] if e["asset_id"] == "a-low")
    assert low["budget_eur"] is None  # never fabricated
    md = render_territorial_brief_markdown(brief)
    assert "pendiente" in md  # missing budget rendered as placeholder


def test_total_budget_sums_only_present_values() -> None:
    brief = build_territorial_brief(
        _portfolio(), territory_name="PNSG", report_date="2026-07-20"
    )
    assert brief["total_indicative_budget_eur"] == 12000.0


def test_metadata_carries_territory_and_count() -> None:
    brief = build_territorial_brief(
        _portfolio(), territory_name="Parque Nacional Sierra de Guadarrama"
    )
    assert brief["metadata"]["territory"] == "Parque Nacional Sierra de Guadarrama"
    assert brief["metadata"]["assets_in_portfolio"] == 2


def test_markdown_never_claims_field_validation() -> None:
    brief = build_territorial_brief(_portfolio(), territory_name="PNSG")
    md = render_territorial_brief_markdown(brief)
    assert "Resumen ejecutivo del panel" in md
    # honesty guardrail: the evidence note explicitly denies field validation
    assert "validado en campo" in md
    for col in ["EHS", "Riesgo", "Tier", "Alerta", "Coste"]:
        assert col in md


def test_empty_portfolio_is_safe() -> None:
    brief = build_territorial_brief([], territory_name="PNSG")
    assert brief["entries"] == []
    assert brief["total_indicative_budget_eur"] is None
    md = render_territorial_brief_markdown(brief)
    assert "Cartera de decisión" in md


def test_unknown_alert_and_trend_fall_back_to_raw_not_guess() -> None:
    weird = [
        _FakeAsset(
            "a-x", "Raro", ehs=50.0, risk_score=0.5, tier=2, tier_label="X",
            alert_level="SOMETHING_NEW", trend_direction="wobbly",
            recommended_action_label=None, budget_estimate_eur=None,
        )
    ]
    brief = build_territorial_brief(weird, territory_name="PNSG")
    e = brief["entries"][0]
    assert e["alert_label"] == "SOMETHING_NEW"  # raw, not a fabricated label
    assert e["trend_label"] == "wobbly"
    assert e["recommended_action"] == "pendiente de definir"
