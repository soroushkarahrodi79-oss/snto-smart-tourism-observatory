"""Contracts for the Phase 6.7c DCS explanation layer."""

from types import SimpleNamespace

import pytest

from src.platform.confidence_explain import build_confidence_profiles


def _asset(**overrides):
    values = {
        "asset_id": "a-1",
        "name": "Activo uno",
        "dcs": 70.0,
        "dcs_components": None,
        "mk_p_value": 0.03,
        "scm_classification": "LOCALIZED_IMPACT",
        "ehs": 45.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_missing_components_produce_ranges_not_fake_scores() -> None:
    profile = build_confidence_profiles([_asset()])[0]

    assert not profile.exact_decomposition
    assert profile.action_gate is None
    assert all(component.score is None for component in profile.components)
    assert all(
        component.feasible_low <= component.feasible_high
        for component in profile.components
    )
    assert sum(component.maximum for component in profile.components) == 100


def test_partial_sources_remain_distinct_from_calculated_components() -> None:
    profile = build_confidence_profiles([_asset()])[0]
    statuses = {
        component.key: component.evidence_status
        for component in profile.components
    }

    assert statuses["data_quality"] == "Propagación pendiente"
    assert statuses["temporal_robustness"] == "Fuente parcial"
    assert statuses["spatial_consistency"] == "Fuente parcial"
    assert statuses["signal_strength"] == "Fuente parcial"


def test_exact_components_enable_the_real_quality_gate() -> None:
    components = {
        "data_quality": 18,
        "temporal_robustness": 17,
        "spatial_consistency": 14,
        "model_stability": 10,
        "signal_strength": 11,
    }
    profile = build_confidence_profiles(
        [_asset(dcs=70, dcs_components=components)]
    )[0]

    assert profile.exact_decomposition
    assert profile.action_gate is True
    assert all(component.score is not None for component in profile.components)


def test_exact_components_enforce_foundational_gate() -> None:
    components = {
        "data_quality": 8,
        "temporal_robustness": 20,
        "spatial_consistency": 18,
        "model_stability": 14,
        "signal_strength": 10,
    }
    profile = build_confidence_profiles(
        [_asset(dcs=70, dcs_components=components)]
    )[0]
    assert profile.action_gate is False


def test_invalid_or_inconsistent_components_fail_loudly() -> None:
    with pytest.raises(ValueError, match="data_quality"):
        build_confidence_profiles([_asset(dcs_components={"data_quality": 30})])
    with pytest.raises(ValueError, match="sum"):
        build_confidence_profiles(
            [
                _asset(
                    dcs=80,
                    dcs_components={
                        "data_quality": 10,
                        "temporal_robustness": 10,
                        "spatial_consistency": 10,
                        "model_stability": 10,
                        "signal_strength": 10,
                    },
                )
            ]
        )


def test_profiles_put_largest_confidence_gap_first() -> None:
    profiles = build_confidence_profiles(
        [_asset(asset_id="high", dcs=80), _asset(asset_id="low", dcs=35)]
    )
    assert [profile.asset_id for profile in profiles] == ["low", "high"]
