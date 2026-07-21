"""
Tests for the v2.5 satellite↔field agreement runner.

Pins the honest gate: no plots → no verdict; <3 plots → "insuficiente"; and a
real, direction-correct set of plots produces a positive Spearman that passes
the gate. Uses the real persistence bridge (no fabricated rows).
"""
from __future__ import annotations

from src.persistence.models import ManagedAsset, Territory
from src.persistence.services.field_verification_ingest import (
    persist_field_observation,
)
from src.ui.services.field_agreement import compute_field_agreement
from src.validation.field import FieldObservation


def _register_asset(session, external_id: str, name: str = "Sendero") -> ManagedAsset:
    territory = session.query(Territory).filter_by(slug="pnsg").one_or_none()
    if territory is None:
        territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
        session.add(territory)
        session.flush()
    asset = ManagedAsset(
        territory_id=territory.id, external_asset_id=external_id, name=name,
        asset_type="trail", geometry_geojson="{}", region="Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def _persist_plot(session, external_id: str, veg_cover: float) -> None:
    # Lower veg cover → higher field degradation index (stress convention).
    obs = FieldObservation(
        plot_id=f"{external_id}-P", lat=40.8, lon=-3.9, distance_to_trail_m=1.0,
        is_control=False, asset_id=external_id, veg_cover_pct=veg_cover,
        observed_at="2026-06-01",
    )
    persist_field_observation(session, obs, verifier="Equipo PNSG")


def test_no_field_plots_is_honest_no_verdict(db_session) -> None:
    _register_asset(db_session, "pnsg-001")
    summary = compute_field_agreement({"pnsg-001": 70.0}, session=db_session)
    assert summary.n_verifications == 0
    assert summary.n_paired == 0
    assert summary.report is None
    assert summary.gate_passed is False


def test_two_plots_is_insufficient(db_session) -> None:
    for ext in ("pnsg-001", "pnsg-002"):
        _register_asset(db_session, ext)
        _persist_plot(db_session, ext, veg_cover=40.0)
    summary = compute_field_agreement(
        {"pnsg-001": 70.0, "pnsg-002": 60.0}, session=db_session
    )
    assert summary.n_paired == 2
    assert summary.report is not None
    assert "insuficiente" in summary.report.verdict
    assert summary.gate_passed is False  # never passes below 3 plots


def test_direction_correct_plots_pass_the_gate(db_session) -> None:
    # Build 4 plots where satellite stress (100-EHS) rises with field
    # degradation (100-veg_cover): a real positive agreement.
    data = [
        ("pnsg-001", 90.0, 90.0),  # EHS high → low stress; high cover → low degr.
        ("pnsg-002", 70.0, 65.0),
        ("pnsg-003", 45.0, 40.0),
        ("pnsg-004", 20.0, 15.0),
    ]
    ehs_map = {}
    for ext, ehs, cover in data:
        _register_asset(db_session, ext)
        _persist_plot(db_session, ext, veg_cover=cover)
        ehs_map[ext] = ehs
    summary = compute_field_agreement(ehs_map, session=db_session)
    assert summary.n_paired == 4
    assert summary.report is not None
    assert summary.report.direction_ok is True
    assert summary.report.spearman > 0
    assert summary.gate_passed is True


def test_unmeasured_plot_is_not_paired(db_session) -> None:
    # A plot with no measured component stores result="no measured components",
    # which is honestly un-pairable (not zero).
    _register_asset(db_session, "pnsg-001")
    obs = FieldObservation(
        plot_id="P0", lat=40.8, lon=-3.9, distance_to_trail_m=1.0,
        is_control=False, asset_id="pnsg-001", observed_at="2026-06-01",
    )
    persist_field_observation(db_session, obs, verifier="X")
    summary = compute_field_agreement({"pnsg-001": 70.0}, session=db_session)
    assert summary.n_verifications == 1
    assert summary.n_paired == 0
    assert summary.report is None


def test_asset_without_ehs_is_skipped(db_session) -> None:
    _register_asset(db_session, "pnsg-001")
    _persist_plot(db_session, "pnsg-001", veg_cover=40.0)
    # EHS map does not include the asset → nothing to pair.
    summary = compute_field_agreement({"other-999": 50.0}, session=db_session)
    assert summary.n_paired == 0
