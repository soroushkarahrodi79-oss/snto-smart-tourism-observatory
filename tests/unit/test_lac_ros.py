"""
Tests for the LAC/ROS carrying-capacity framework (v2.2).

Pins the ROS classification, the LAC standards/status, and the transparent
capacity-at-standard estimate — including that it stays a *planning* estimate
that declines honest answers (None) when it cannot extrapolate.
"""
from __future__ import annotations

from src.platform.lac_ros import (
    STATUS_APPROACHING,
    STATUS_EXCEEDED,
    STATUS_WITHIN,
    ROSClass,
    capacity_at_standard,
    classify_ros,
    lac_standard_ehs,
    lac_status,
)


def test_ros_class_tracks_accessibility() -> None:
    assert classify_ros(0.1) is ROSClass.PRIMITIVE
    assert classify_ros(0.45) is ROSClass.SEMI_PRIMITIVE
    assert classify_ros(0.7) is ROSClass.ROADED_NATURAL
    assert classify_ros(0.95) is ROSClass.RURAL_DEVELOPED
    # Missing access → conservative middle, not a developed assumption.
    assert classify_ros(None) is ROSClass.SEMI_PRIMITIVE


def test_primitive_standard_is_stricter_than_developed() -> None:
    assert lac_standard_ehs(ROSClass.PRIMITIVE) > lac_standard_ehs(
        ROSClass.RURAL_DEVELOPED
    )


def test_lac_status_bands() -> None:
    std = 65.0
    assert lac_status(80.0, std) == STATUS_WITHIN       # well above
    assert lac_status(70.0, std) == STATUS_APPROACHING  # within buffer
    assert lac_status(60.0, std) == STATUS_EXCEEDED      # below standard


def test_capacity_headroom_when_ehs_above_standard() -> None:
    # EHS 80 vs standard 55, current pressure 10000:
    # P_std = 10000 * (100-55)/(100-80) = 10000 * 45/20 = 22500 → headroom.
    # Only meaningful for a localized-impact trail (WP-C11 precondition).
    cap = capacity_at_standard(
        10_000, ehs=80.0, standard=55.0, attribution="LOCALIZED_IMPACT"
    )
    assert cap is not None and cap > 10_000


def test_capacity_over_when_ehs_below_standard() -> None:
    # EHS 40 vs standard 55: already exceeded → capacity below current.
    cap = capacity_at_standard(
        10_000, ehs=40.0, standard=55.0, attribution="LOCALIZED_IMPACT"
    )
    assert cap is not None and cap < 10_000


def test_capacity_declines_to_none_near_pristine() -> None:
    # No measurable degradation to extrapolate from → honest None, not a number.
    assert (
        capacity_at_standard(
            10_000, ehs=100.0, standard=55.0, attribution="LOCALIZED_IMPACT"
        )
        is None
    )


def test_capacity_none_for_nonpositive_pressure() -> None:
    assert (
        capacity_at_standard(
            0, ehs=50.0, standard=55.0, attribution="LOCALIZED_IMPACT"
        )
        is None
    )


def test_capacity_none_for_landscape_driven_attribution() -> None:
    # WP-C11: the linear model attributes the whole deficit to visitors, so a
    # climate/landscape-driven trail must not receive a capacity number even when
    # the math would otherwise yield one.
    assert (
        capacity_at_standard(
            10_000, ehs=80.0, standard=55.0, attribution="LANDSCAPE_DRIVEN"
        )
        is None
    )


def test_capacity_none_for_mixed_and_unknown_attribution() -> None:
    for attribution in ("MIXED", None, "", "localized_impact"):
        assert (
            capacity_at_standard(
                10_000, ehs=80.0, standard=55.0, attribution=attribution
            )
            is None
        ), attribution
