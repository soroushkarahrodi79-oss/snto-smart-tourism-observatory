"""Contracts for the Phase 6.7b pressure/carrying-capacity model."""

from __future__ import annotations

from types import SimpleNamespace

from src.platform.pressure_capacity import assess_pressure_capacity


def _asset(**overrides):
    values = {
        "asset_id": "trail-1",
        "name": "Senda de prueba",
        "tier": 1,
        "visitor_capacity_annual": 40_000,
        "ehs": 40.0,
        "dcs": 75.0,
        "tpi": 70.0,
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
