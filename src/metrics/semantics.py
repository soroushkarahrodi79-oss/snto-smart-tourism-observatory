"""Score direction conventions used across SNTO.

The project has two legitimate 0-100 score directions:

* health: 0 = critical, 100 = healthy.
* stress: 0 = no stress, 100 = maximum degradation.

Pipeline A legacy database columns named ``ehs_*`` store stress scores. The
dashboard and territorial intelligence layers consume health scores. Keeping
the conversion here avoids silent sign inversions scattered through the app.
"""
from __future__ import annotations

from typing import Literal

ScoreConvention = Literal["health", "stress"]


def clamp_score(value: float) -> float:
    """Clamp a score to the closed 0-100 interval."""
    return max(0.0, min(100.0, float(value)))


def stress_to_health(stress_score: float | None) -> float | None:
    """Convert 0=no stress, 100=max degradation into 0=critical, 100=healthy."""
    if stress_score is None:
        return None
    return round(100.0 - clamp_score(stress_score), 4)


def health_to_stress(health_score: float | None) -> float | None:
    """Convert 0=critical, 100=healthy into 0=no stress, 100=max degradation."""
    if health_score is None:
        return None
    return round(100.0 - clamp_score(health_score), 4)


def delta_stress_to_delta_health(delta_stress: float | None) -> float | None:
    """Convert a stress delta into a health delta by reversing its sign."""
    if delta_stress is None:
        return None
    return round(-float(delta_stress), 4)
