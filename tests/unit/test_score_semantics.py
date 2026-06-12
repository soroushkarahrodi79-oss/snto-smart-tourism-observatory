from __future__ import annotations

from src.metrics.semantics import (
    clamp_score,
    delta_stress_to_delta_health,
    health_to_stress,
    stress_to_health,
)


def test_stress_to_health_reverses_direction():
    assert stress_to_health(0) == 100.0
    assert stress_to_health(40) == 60.0
    assert stress_to_health(100) == 0.0


def test_health_to_stress_reverses_direction():
    assert health_to_stress(100) == 0.0
    assert health_to_stress(65) == 35.0
    assert health_to_stress(0) == 100.0


def test_none_is_preserved_for_missing_scores():
    assert stress_to_health(None) is None
    assert health_to_stress(None) is None
    assert delta_stress_to_delta_health(None) is None


def test_scores_are_clamped_before_conversion():
    assert clamp_score(-20) == 0.0
    assert clamp_score(120) == 100.0
    assert stress_to_health(120) == 0.0
    assert health_to_stress(-5) == 100.0


def test_delta_stress_to_delta_health_reverses_sign():
    assert delta_stress_to_delta_health(12.5) == -12.5
    assert delta_stress_to_delta_health(-3.2) == 3.2
