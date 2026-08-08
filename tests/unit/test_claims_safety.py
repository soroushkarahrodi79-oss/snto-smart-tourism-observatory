"""Phase 0.5B — Claim-safety contracts for live executive outputs.

The governing causal/confirmatory gate is:

    REAL evidence + validated method + supported attribution
    + independent verification

All four conditions are required before SNTO may emit causal or confirmatory
language, or a restrictive management recommendation. The current live outputs
cannot programmatically demonstrate all four (there is no machine-readable
``evidence_class`` on ``TerritorialAsset``, ``evidence.supports(...)`` has no
callers, and validation/attribution/verification status is not available as a
live gate). Therefore the emitted narratives must use hypothesis / association /
absence-of-evidence framing and must not prescribe restrictive visitor controls.

These tests exercise the **constructed emitted output** of the dashboard,
call-to-action, KPI-7 drill-down caption, and the decision-confidence factor
explanation — not the raw source text — so they lock in what a manager actually
reads. They deliberately do NOT depend on any future gate field.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.platform.dashboard import (
    _generate_call_to_action,
    _kpi_human_pressure_alerts,
    _kpi_territory_health,
    _kpi_visitor_capacity_at_risk,
    compute_executive_dashboard,
)
from src.territorial.models import AssetType, TerritorialAsset


# ── Banned language ──────────────────────────────────────────────────────────
# Unsupported causal / confirmatory claims: assert a cause is *known*, *confirmed*
# or *measured* when the live path cannot satisfy the four-condition gate.
CAUSAL_CONFIRMATORY_PHRASES = (
    "caused by",
    "confirmed",
    "the cause is known",
    "cause (visitor",
    "visitor-driven",
    "measurable environmental damage",
    "irreversible",
    "driven by natural climate",
    "driven by the 2022 drought",
    "2022 drought",
)

# Restrictive management actions: prescriptive visitor-flow controls that a
# non-evidence-gated fixture decision layer must not present as authorised.
RESTRICTIVE_ACTION_PHRASES = (
    "seasonal closure",
    "visitor quota",
    "guided-only",
    "restrict visitor",
    "restrict public access",
    "visitor redirection",
)


def _assert_no_phrases(text: str, phrases, context: str) -> None:
    low = text.lower()
    hits = [p for p in phrases if p.lower() in low]
    assert not hits, f"{context} contains banned wording {hits}: {text!r}"


# ── Asset + dashboard builders ───────────────────────────────────────────────

def _asset(**overrides) -> TerritorialAsset:
    """A fully-populated TerritorialAsset with safe defaults; override per test."""
    values = dict(
        asset_id="a-1",
        name="Senda de prueba",
        asset_type=AssetType.TRAIL,
        region="PNSG",
        ehs=42.0,
        risk_score=0.6,
        dcs=70.0,
        alert_level="PREVENTIVE_ACTION",
        scm_classification="LOCALIZED_IMPACT",
        scm_confidence="MODERATE",
        trend_direction="decreasing",
        mk_p_value=0.04,
        visitor_capacity_annual=10_000,
        economic_importance=0.5,
        accessibility_score=0.5,
        tier=1,
    )
    values.update(overrides)
    return TerritorialAsset(**values)


def _emitted_kpi_text(kpi) -> str:
    return " || ".join(
        [kpi.name, kpi.value, kpi.status_label, kpi.what_it_means, kpi.recommended_action]
    )


def _build_dashboard(assets):
    budget = SimpleNamespace(
        portfolio_tis=9.0, total_allocated_eur=50_000, total_budget_eur=100_000
    )
    return compute_executive_dashboard(
        territory_name="PNSG",
        report_date="2026-08-08",
        assets=assets,
        budget_result=budget,
        comparisons=[],
    )


# ── 1. Populated KPI narratives + actions ────────────────────────────────────

def test_full_dashboard_narratives_have_no_causal_or_restrictive_wording() -> None:
    """A high-pressure portfolio (RED across health / capacity / KPI-7) must
    still read as hypothesis + monitoring, never confirmed cause + restriction."""
    assets = [
        _asset(asset_id=f"t1-{i}", name=f"Senda {i}", tier=1,
               scm_classification="LOCALIZED_IMPACT", ehs=30.0, dcs=70.0)
        for i in range(4)
    ]
    dash = _build_dashboard(assets)

    blob = " || ".join(_emitted_kpi_text(k) for k in dash.kpis)
    blob += " || " + dash.headline + " || " + dash.call_to_action
    _assert_no_phrases(blob, CAUSAL_CONFIRMATORY_PHRASES, "dashboard emitted text")
    _assert_no_phrases(blob, RESTRICTIVE_ACTION_PHRASES, "dashboard emitted text")


def test_territory_health_critical_drops_irreversible_and_restriction() -> None:
    """KPI value/tier/status are unchanged; only the wording is corrected."""
    assets = [_asset(ehs=20.0, asset_id=f"x{i}") for i in range(3)]  # mean 20 → CRITICAL
    kpi = _kpi_territory_health(assets)
    assert kpi.status == "RED"
    assert kpi.value == "20/100"
    _assert_no_phrases(_emitted_kpi_text(kpi), CAUSAL_CONFIRMATORY_PHRASES, "KPI territory health")
    _assert_no_phrases(_emitted_kpi_text(kpi), RESTRICTIVE_ACTION_PHRASES, "KPI territory health")


def test_visitor_capacity_high_risk_softens_redirection_action() -> None:
    assets = [_asset(tier=1, visitor_capacity_annual=90_000)]
    kpi = _kpi_visitor_capacity_at_risk(assets)
    assert kpi.status == "RED"
    _assert_no_phrases(kpi.recommended_action, RESTRICTIVE_ACTION_PHRASES, "KPI capacity action")


# ── 2. Call to action ────────────────────────────────────────────────────────

def test_call_to_action_localized_case_is_hypothesis_not_confirmed_cause() -> None:
    assets = [_asset(tier=1, scm_classification="LOCALIZED_IMPACT", dcs=70.0, tpi=88.0)]
    cta = _generate_call_to_action(assets)
    # The localized branch must fire (asset name present) ...
    assert "Senda de prueba" in cta
    # ... but frame the cause as an unverified hypothesis and prescribe verification.
    _assert_no_phrases(cta, CAUSAL_CONFIRMATORY_PHRASES, "call to action")
    _assert_no_phrases(cta, RESTRICTIVE_ACTION_PHRASES, "call to action")
    assert "hypothesis" in cta.lower()


def test_call_to_action_other_branches_stay_clean() -> None:
    # Evidence-gap branch (Tier-1, very low DCS)
    gap = _generate_call_to_action([_asset(tier=1, dcs=30.0, scm_classification="LANDSCAPE_DRIVEN")])
    _assert_no_phrases(gap, CAUSAL_CONFIRMATORY_PHRASES, "CTA evidence gap")
    _assert_no_phrases(gap, RESTRICTIVE_ACTION_PHRASES, "CTA evidence gap")
    # Default branch (nothing urgent)
    default = _generate_call_to_action([_asset(tier=3, dcs=70.0, scm_classification="LANDSCAPE_DRIVEN")])
    _assert_no_phrases(default, CAUSAL_CONFIRMATORY_PHRASES, "CTA default")


# ── 3. KPI 7 across SCM / tier / DCS combinations ────────────────────────────

@pytest.mark.parametrize(
    "n_localized, expected_status",
    [(0, "GREEN"), (1, "AMBER"), (2, "AMBER"), (3, "RED"), (5, "RED")],
)
def test_kpi7_paths_are_claim_safe(n_localized, expected_status) -> None:
    localized = [
        _asset(asset_id=f"loc{i}", tier=1, scm_classification="LOCALIZED_IMPACT")
        for i in range(n_localized)
    ]
    # Padding assets that must NOT count toward the alert (landscape-driven / tier 3).
    padding = [
        _asset(asset_id="pad1", tier=3, scm_classification="LANDSCAPE_DRIVEN"),
        _asset(asset_id="pad2", tier=1, scm_classification="LANDSCAPE_DRIVEN"),
    ]
    kpi = _kpi_human_pressure_alerts(localized + padding)
    assert kpi.status == expected_status
    assert kpi.value == f"{n_localized} site(s)"  # KPI count unchanged
    _assert_no_phrases(_emitted_kpi_text(kpi), CAUSAL_CONFIRMATORY_PHRASES, "KPI 7")
    _assert_no_phrases(_emitted_kpi_text(kpi), RESTRICTIVE_ACTION_PHRASES, "KPI 7")


def test_kpi7_uses_association_hypothesis_framing() -> None:
    kpi = _kpi_human_pressure_alerts(
        [_asset(asset_id=f"loc{i}", tier=1, scm_classification="LOCALIZED_IMPACT") for i in range(3)]
    )
    text = _emitted_kpi_text(kpi).lower()
    assert "hypothesis" in text
    assert "not yet independently verified" in text


# ── 6. Decision-confidence emitted text: no named-event attribution ──────────

def _dcs_explain_uncertainty(model_stability: float):
    """Drive src.decision_confidence.assessor._explain_factors to the
    model-stability branch and return the emitted (uncertainty, confidence)."""
    from src.decision_confidence.assessor import _explain_factors

    comp = SimpleNamespace(
        data_quality=20.0,
        model_stability=model_stability,
        ss_detail={"component_coherence": 5},
    )
    inp = SimpleNamespace(
        n_valid_observations=40,
        n_possible_observations=48,
        mean_cloud_cover_pct=10.0,
        n_years=4,
        mk_result=SimpleNamespace(is_significant=False, p_value=0.5, trend_direction="no_trend"),
        scm_result=SimpleNamespace(
            classification="LANDSCAPE_DRIVEN",
            confidence="HIGH",
            gradient=SimpleNamespace(spatial_impact_gradient=0.12),
        ),
        anomaly_events=[],
    )
    return _explain_factors(comp, inp)


def test_model_stability_uncertainty_has_no_named_event() -> None:
    uncertainty, _ = _dcs_explain_uncertainty(model_stability=5.0)
    joined = " ".join(uncertainty)
    # The branch fired ...
    assert "inter-annual variability" in joined
    # ... but names no causal event, and keeps uncertainty framing.
    _assert_no_phrases(joined, CAUSAL_CONFIRMATORY_PHRASES, "DCS uncertainty text")


# ── 7. Corrected KPI-7 Spanish drill-down wording ────────────────────────────

def test_kpi7_spanish_drilldown_caption_is_hypothesis_framed() -> None:
    from src.ui.render_widgets import _KPI_DRILLDOWN_CAPTION

    caption = _KPI_DRILLDOWN_CAPTION[7]
    low = caption.lower()
    assert "hipótesis" in low
    assert "no verificada de forma independiente" in low
    # The old confirmatory phrasing must be gone.
    assert "causada por presión antrópica confirmada" not in low
    assert "clasificación causal" not in low
