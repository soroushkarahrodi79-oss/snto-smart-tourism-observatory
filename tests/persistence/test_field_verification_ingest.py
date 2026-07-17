from __future__ import annotations

import pytest

from src.persistence.models import ManagedAsset, Territory
from src.persistence.repositories import FieldVerificationRepository
from src.persistence.services.alert_ingest import AssetNotRegisteredError
from src.persistence.services.field_verification_ingest import (
    NotAnAssetVerificationError,
    persist_field_observation,
)
from src.validation.field import FieldObservation


def _register_asset(session, external_id: str = "pnsg-trail-001") -> ManagedAsset:
    territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
    session.add(territory)
    session.flush()
    asset = ManagedAsset(
        territory_id=territory.id,
        external_asset_id=external_id,
        name="Sendero",
        asset_type="trail",
        geometry_geojson="{}",
        region="Madrid",
    )
    session.add(asset)
    session.flush()
    return asset


def test_persist_impact_observation(db_session) -> None:
    asset = _register_asset(db_session)
    obs = FieldObservation(
        plot_id="P1",
        lat=40.8,
        lon=-3.9,
        distance_to_trail_m=1.0,
        is_control=False,
        asset_id="pnsg-trail-001",
        soil_compaction_mpa=3.0,
        veg_cover_pct=40.0,
        erosion_class=2,
        photo_ref="s3://p1.jpg",
        observed_at="2026-06-01",
    )

    fv = persist_field_observation(db_session, obs, verifier="Equipo PNSG")

    assert fv.asset_id == asset.id
    assert fv.method == "field_plot"
    assert fv.verifier == "Equipo PNSG"
    # degradation_index stored verbatim as result (not fabricated).
    assert fv.result == str(obs.degradation_index())
    assert fv.photo_ref == "s3://p1.jpg"
    assert "soil_compaction_mpa=3.0" in fv.notes
    assert fv.verified_at.year == 2026

    stored = FieldVerificationRepository(db_session).list_by_asset(asset.id)
    assert stored == [fv]


def test_persist_observation_without_components(db_session) -> None:
    _register_asset(db_session)
    obs = FieldObservation(
        plot_id="P2",
        lat=40.8,
        lon=-3.9,
        distance_to_trail_m=1.0,
        is_control=False,
        asset_id="pnsg-trail-001",
    )
    fv = persist_field_observation(db_session, obs, verifier="Equipo PNSG")
    assert fv.result == "no measured components"


def test_control_plot_rejected(db_session) -> None:
    _register_asset(db_session)
    obs = FieldObservation(
        plot_id="C1",
        lat=40.8,
        lon=-3.9,
        distance_to_trail_m=50.0,
        is_control=True,
        asset_id="pnsg-trail-001",
    )
    with pytest.raises(NotAnAssetVerificationError):
        persist_field_observation(db_session, obs, verifier="Equipo PNSG")


def test_observation_without_asset_id_rejected(db_session) -> None:
    obs = FieldObservation(
        plot_id="P3",
        lat=40.8,
        lon=-3.9,
        distance_to_trail_m=1.0,
        is_control=False,
        asset_id=None,
    )
    with pytest.raises(NotAnAssetVerificationError):
        persist_field_observation(db_session, obs, verifier="Equipo PNSG")


def test_unknown_asset_rejected(db_session) -> None:
    obs = FieldObservation(
        plot_id="P4",
        lat=40.8,
        lon=-3.9,
        distance_to_trail_m=1.0,
        is_control=False,
        asset_id="does-not-exist",
    )
    with pytest.raises(AssetNotRegisteredError):
        persist_field_observation(db_session, obs, verifier="Equipo PNSG")
