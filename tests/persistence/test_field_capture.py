"""Tests for the v2.5 field-plot capture service.

Pins the honest write boundary: a real impact plot persists a FieldVerification
(and becomes visible to the agreement runner); a control plot and an
unregistered asset are typed, non-destructive outcomes — never fabricated rows.
Uses the real persistence bridge against an in-memory session.
"""
from __future__ import annotations

from src.persistence.models import ManagedAsset, Territory
from src.persistence.repositories.field_verification import (
    FieldVerificationRepository,
)
from src.ui.services.field_capture import (
    CaptureStatus,
    capture_field_plot,
)
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


def _impact_plot(external_id: str, **kw) -> FieldObservation:
    base = dict(
        plot_id=f"{external_id}-P1", lat=40.8, lon=-3.9, distance_to_trail_m=1.0,
        is_control=False, asset_id=external_id, observed_at="2026-06-01",
    )
    base.update(kw)
    return FieldObservation(**base)


def test_impact_plot_is_persisted_and_visible(db_session) -> None:
    asset = _register_asset(db_session, "pnsg-001")
    result = capture_field_plot(
        _impact_plot("pnsg-001", veg_cover_pct=40.0, soil_compaction_mpa=2.4),
        verifier="Equipo PNSG", session=db_session,
    )
    assert result.status is CaptureStatus.PERSISTED
    assert result.verification_id is not None
    assert result.field_degradation is not None
    # the row is durable and attached to the same asset
    rows = FieldVerificationRepository(db_session).list_by_asset(asset.id)
    assert len(rows) == 1


def test_control_plot_is_not_persisted(db_session) -> None:
    _register_asset(db_session, "pnsg-001")
    result = capture_field_plot(
        _impact_plot("pnsg-001", is_control=True, veg_cover_pct=90.0),
        verifier="X", session=db_session,
    )
    assert result.status is CaptureStatus.CONTROL_SKIPPED
    assert result.verification_id is None


def test_unregistered_asset_is_reported_not_invented(db_session) -> None:
    result = capture_field_plot(
        _impact_plot("ghost-999", veg_cover_pct=30.0),
        verifier="X", session=db_session,
    )
    assert result.status is CaptureStatus.ASSET_UNKNOWN
    assert "ghost-999" in result.message
    # nothing was created
    assert db_session.query(ManagedAsset).count() == 0


def test_plot_with_no_measurement_still_persists_honestly(db_session) -> None:
    # No measured component → persisted with result "no measured components",
    # so degradation_index is None but the plot is durably recorded.
    _register_asset(db_session, "pnsg-001")
    result = capture_field_plot(
        _impact_plot("pnsg-001"), verifier="X", session=db_session,
    )
    assert result.status is CaptureStatus.PERSISTED
    assert result.field_degradation is None
