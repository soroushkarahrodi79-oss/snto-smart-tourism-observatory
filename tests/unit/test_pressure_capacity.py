"""Contracts for the Phase 6.7b pressure/carrying-capacity model."""

from __future__ import annotations

from types import SimpleNamespace

from src.platform.pressure_capacity import assess_pressure_capacity


def _asset(**overrides):
    values = {
        "asset_id": "trail-1",
        "name": "Senda de prueba",
        "region": "Rascafría",
        "tier": 1,
        "visitor_capacity_annual": 40_000,
        "ehs": 40.0,
        "dcs": 75.0,
        "tpi": 70.0,
        "accessibility_score": 0.9,
        "scm_classification": "LOCALIZED_IMPACT",
        "scm_confidence": "HIGH",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_capacity_is_a_rounded_range_not_a_point_claim() -> None:
    profile = assess_pressure_capacity([_asset()])[0]

    assert profile.capacity_low < profile.capacity_central < profile.capacity_high
    assert profile.capacity_low % 100 == 0
    assert profile.capacity_high % 100 == 0
    assert profile.capacity_status == "Supera la horquilla estimada"


def test_lower_dcs_widens_the_planning_range() -> None:
    high = assess_pressure_capacity([_asset(dcs=80)])[0]
    low = assess_pressure_capacity([_asset(dcs=35)])[0]

    high_width = high.capacity_high - high.capacity_low
    low_width = low.capacity_high - low.capacity_low
    assert low_width > high_width


def test_seasonal_profile_is_explicit_and_summer_peaks() -> None:
    profile = assess_pressure_capacity([_asset()])[0]

    assert [point.season for point in profile.seasonal] == [
        "Invierno",
        "Primavera",
        "Verano",
        "Otoño",
    ]
    summer = next(point for point in profile.seasonal if point.season == "Verano")
    assert summer.tpi == max(point.tpi for point in profile.seasonal)
    assert summer.flow_proxy == max(point.flow_proxy for point in profile.seasonal)


def test_tpi_is_clamped_and_profiles_are_sorted_by_peak_pressure() -> None:
    profiles = assess_pressure_capacity(
        [_asset(asset_id="low", tpi=30), _asset(asset_id="high", tpi=90)]
    )

    assert [profile.asset_id for profile in profiles] == ["high", "low"]
    assert max(point.tpi for point in profiles[0].seasonal) == 100.0


def test_scm_wording_keeps_attribution_as_a_hypothesis() -> None:
    localized = assess_pressure_capacity([_asset()])[0]
    landscape = assess_pressure_capacity(
        [_asset(scm_classification="LANDSCAPE_DRIVEN")]
    )[0]
    mixed = assess_pressure_capacity([_asset(scm_classification="MIXED")])[0]

    assert "compatible" in localized.scm_hypothesis.lower()
    assert "contraste de campo" in localized.scm_hypothesis.lower()
    assert "no atribuirla" in landscape.scm_hypothesis.lower()
    assert "hipótesis" in mixed.scm_hypothesis.lower()


# ── LAC / ROS layer (v2.2) ─────────────────────────────────────────────────


def test_ros_and_lac_are_populated() -> None:
    # accessibility 0.9 → rural/developed; EHS 40 < its standard 45 → exceeded.
    profile = assess_pressure_capacity([_asset()])[0]
    assert profile.ros_class == "rural_developed"
    assert profile.ros_label
    assert profile.lac_standard_ehs == 45.0
    assert "superado" in profile.lac_status.lower()
    assert profile.capacity_at_standard is not None


def test_remote_asset_gets_stricter_standard() -> None:
    remote = assess_pressure_capacity([_asset(accessibility_score=0.1)])[0]
    developed = assess_pressure_capacity([_asset(accessibility_score=0.95)])[0]
    assert remote.ros_class == "primitive"
    assert remote.lac_standard_ehs > developed.lac_standard_ehs


def test_pressure_source_defaults_to_curated_and_no_real_context() -> None:
    profile = assess_pressure_capacity([_asset()])[0]
    assert profile.pressure_source == "Curada (estimada)"
    assert profile.municipal_inbound_daily is None


def test_real_mobility_is_attached_as_context_not_as_proxy() -> None:
    # Real municipal inbound trips are attached as context; the asset pressure
    # proxy stays the curated 40_000 (a municipal trip count is not footfall).
    profile = assess_pressure_capacity(
        [_asset()], municipal_pressure_by_region={"Rascafría": 1234.0}
    )[0]
    assert profile.municipal_inbound_daily == 1234.0
    assert profile.pressure_source == "Movilidad MITMA (proxy municipal)"
    assert profile.annual_pressure_proxy == 40_000  # unchanged by mobility


def test_unmatched_region_leaves_context_none() -> None:
    profile = assess_pressure_capacity(
        [_asset(region="Otro")], municipal_pressure_by_region={"Rascafría": 9.0}
    )[0]
    assert profile.municipal_inbound_daily is None
    assert profile.pressure_source == "Curada (estimada)"
