from __future__ import annotations

import pytest

from src.persistence.enums import InterventionStatus, ManagedAssetStatus
from src.persistence.models import Intervention, ManagedAsset, Territory
from src.persistence.services.lifecycle import (
    IllegalTransitionError,
    ResourceNotFoundError,
    transition_intervention,
    transition_managed_asset,
)


def _asset(session, status: ManagedAssetStatus = ManagedAssetStatus.DETECTED):
    territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
    session.add(territory)
    session.flush()
    asset = ManagedAsset(
        territory_id=territory.id,
        external_asset_id="pnsg-trail-001",
        name="Sendero",
        asset_type="trail",
        geometry_geojson="{}",
        region="Madrid",
        status=status,
    )
    session.add(asset)
    session.flush()
    return asset


def test_managed_asset_full_forward_lifecycle(db_session) -> None:
    asset = _asset(db_session)
    chain = [
        ManagedAssetStatus.VERIFIED,
        ManagedAssetStatus.ASSIGNED,
        ManagedAssetStatus.FUNDED,
        ManagedAssetStatus.RESOLVED,
        ManagedAssetStatus.MONITORED,
    ]
    for target in chain:
        transition_managed_asset(db_session, asset.id, target)
        assert asset.status == target


def test_managed_asset_illegal_skip_raises(db_session) -> None:
    asset = _asset(db_session)
    with pytest.raises(IllegalTransitionError):
        transition_managed_asset(db_session, asset.id, ManagedAssetStatus.FUNDED)
    # Unchanged after the rejected jump.
    assert asset.status == ManagedAssetStatus.DETECTED


def test_managed_asset_monitored_is_terminal(db_session) -> None:
    asset = _asset(db_session, status=ManagedAssetStatus.MONITORED)
    with pytest.raises(IllegalTransitionError):
        transition_managed_asset(
            db_session, asset.id, ManagedAssetStatus.DETECTED
        )


def test_managed_asset_missing_raises(db_session) -> None:
    with pytest.raises(ResourceNotFoundError):
        transition_managed_asset(db_session, 999, ManagedAssetStatus.VERIFIED)


def test_intervention_forward_lifecycle(db_session) -> None:
    asset = _asset(db_session)
    intervention = Intervention(asset_id=asset.id)
    db_session.add(intervention)
    db_session.flush()

    transition_intervention(
        db_session, intervention.id, InterventionStatus.IN_PROGRESS
    )
    assert intervention.status == InterventionStatus.IN_PROGRESS
    transition_intervention(
        db_session, intervention.id, InterventionStatus.RESOLVED
    )
    assert intervention.status == InterventionStatus.RESOLVED


def test_intervention_illegal_skip_raises(db_session) -> None:
    asset = _asset(db_session)
    intervention = Intervention(asset_id=asset.id)
    db_session.add(intervention)
    db_session.flush()
    with pytest.raises(IllegalTransitionError):
        transition_intervention(
            db_session, intervention.id, InterventionStatus.RESOLVED
        )
    assert intervention.status == InterventionStatus.PLANNED


def test_intervention_missing_raises(db_session) -> None:
    with pytest.raises(ResourceNotFoundError):
        transition_intervention(db_session, 999, InterventionStatus.IN_PROGRESS)
