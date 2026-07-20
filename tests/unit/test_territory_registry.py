"""Contracts for the territorial-configuration registry (Fase 6.7f).

The non-negotiable under test: the registry prepares multi-park **without
overpromising** — no territory is ever presented as field-validated, and the
OAPN template set is clearly unvalidated.
"""
from __future__ import annotations

from src.platform.territory_registry import (
    ValidationState,
    registry_summary,
    territory_profiles,
)


def test_pnsg_is_the_active_pilot_and_first() -> None:
    profiles = territory_profiles()
    assert profiles[0].slug == "pnsg"
    assert profiles[0].state is ValidationState.ACTIVE_PILOT


def test_no_territory_is_field_validated() -> None:
    # The #26 ground-truth campaign is pending; nothing may claim validation.
    assert all(not p.field_validated for p in territory_profiles())
    assert registry_summary().field_validated == 0


def test_trend_pilots_are_the_two_v12_parks_not_field_validated() -> None:
    profiles = {p.slug: p for p in territory_profiles()}
    for slug in ("tablas_daimiel", "monfrague"):
        assert profiles[slug].state is ValidationState.TREND_PILOT
        assert profiles[slug].field_validated is False


def test_oapn_templates_are_unvalidated() -> None:
    templates = [
        p
        for p in territory_profiles()
        if p.state is ValidationState.TEMPLATE_UNVALIDATED
    ]
    # 15 GEE templates minus the 2 trend pilots = 13 unvalidated templates.
    assert len(templates) == 13
    assert all("sin validar" in p.state_label.lower() for p in templates)


def test_summary_counts_are_consistent() -> None:
    summary = registry_summary()
    profiles = territory_profiles()
    assert summary.total == len(profiles)
    assert summary.active == 1  # PNSG only
    assert summary.trend_pilots == 2
    assert summary.templates == 13


def test_every_slug_is_unique() -> None:
    slugs = [p.slug for p in territory_profiles()]
    assert len(slugs) == len(set(slugs))
