"""Fixture evidence-classification regression suite (Phase 0.5E · PR 0.5.5 / I-5).

Owner decision Q-01: the curated territorial fixtures are ``EvidenceClass.SYNTHETIC``
— authored demo data that may *exercise* the decision engine but authorizes no
real-world decision use. These tests lock that in machine-readably and prove the
underlying calculations still run. They read the single canonical gate
(``src.platform.evidence.supports``); they never re-declare the policy matrix.
"""
from __future__ import annotations

from src.platform.evidence import DecisionUse, EvidenceClass, supports
from src.territorial.fixtures import (
    FIXTURE_EVIDENCE_CLASS,
    build_pnsg_territory,
    build_territory,
)
from src.territorial.models import AssetType, TerritorialAsset
from src.territorial.tpi import rank_assets

_ALL_FIXTURES = build_territory() + build_pnsg_territory()


# ── A. Every fixture asset is SYNTHETIC ──────────────────────────────────────

def test_fixture_constant_is_synthetic() -> None:
    assert FIXTURE_EVIDENCE_CLASS is EvidenceClass.SYNTHETIC


def test_build_territory_all_synthetic() -> None:
    assets = build_territory()
    assert assets  # non-empty
    assert all(a.evidence_class is EvidenceClass.SYNTHETIC for a in assets)


def test_build_pnsg_territory_all_synthetic() -> None:
    assets = build_pnsg_territory()
    assert assets
    assert all(a.evidence_class is EvidenceClass.SYNTHETIC for a in assets)


# ── B. No fixture is REAL or CALIBRATED ──────────────────────────────────────

def test_no_fixture_is_real_or_calibrated() -> None:
    for a in _ALL_FIXTURES:
        assert a.evidence_class is not EvidenceClass.REAL
        assert a.evidence_class is not EvidenceClass.CALIBRATED


# ── C. The actual canonical gate denies every real-world use ─────────────────

def test_every_fixture_authorizes_no_decision_use() -> None:
    # Uses evidence.supports (the single policy source) — never a local matrix.
    for a in _ALL_FIXTURES:
        for use in DecisionUse:
            assert supports(a.evidence_class, use) is False, (
                f"{a.asset_id} must not authorize {use}"
            )


# ── D. Calculations remain operational on synthetic fixtures ─────────────────

def test_engine_still_ranks_synthetic_fixtures() -> None:
    ranked = rank_assets(build_pnsg_territory())
    assert len(ranked) == len(build_pnsg_territory())
    # TPI and tier are computed for every asset ...
    assert all(a.tpi is not None for a in ranked)
    assert all(a.tier in (1, 2, 3, 4) for a in ranked)
    # ... a ranking order exists ...
    assert all(a.priority_rank is not None for a in ranked)
    assert len({a.priority_rank for a in ranked}) == len(ranked)
    # ... and the evidence class survives the engine pass unchanged.
    assert all(a.evidence_class is EvidenceClass.SYNTHETIC for a in ranked)


def test_engine_output_is_not_authorized_for_real_use() -> None:
    # Computation is allowed; authorization is not — the ranked (still SYNTHETIC)
    # portfolio supports no real decision use.
    ranked = rank_assets(build_territory())
    assert not any(
        supports(a.evidence_class, DecisionUse.PRIORITIZATION) for a in ranked
    )


# ── E. Model default is fail-closed to SYNTHETIC ─────────────────────────────

def test_territorial_asset_defaults_to_synthetic() -> None:
    a = TerritorialAsset(
        asset_id="x", name="n", asset_type=AssetType.TRAIL, region="r",
        ehs=40.0, risk_score=0.5, dcs=70.0, alert_level="NORMAL",
        scm_classification="MIXED", scm_confidence="LOW",
        trend_direction="no_trend", mk_p_value=0.5,
        visitor_capacity_annual=1000, economic_importance=0.5,
        accessibility_score=0.5,
    )
    assert a.evidence_class is EvidenceClass.SYNTHETIC
