"""
LAC / ROS carrying-capacity framework (v2.2).

Upgrades SNTO's capacity thinking from a single condition-scaled heuristic to
the two canonical protected-area planning frameworks:

  * **ROS — Recreation Opportunity Spectrum** (Clark & Stankey 1979): classify
    each setting along a primitive→developed spectrum from its access/development.
    The class sets *management intent* and how much change is acceptable.
  * **LAC — Limits of Acceptable Change** (Stankey et al. 1985): instead of a
    fixed "capacity number", define a **standard** on a condition indicator
    (here the ecological health score, EHS) per ROS class, monitor the asset
    against it, and flag breaches. More primitive settings hold stricter
    standards (less change tolerated).

Carrying capacity then becomes the pressure consistent with *holding the
indicator at its standard* — a threshold, estimated transparently from the
current operating point under a stated linear-headroom assumption. It is a
**planning estimate**, never a measured limit, and is labelled as such: SNTO
still has no fitted pressure→EHS dose-response (that needs the field campaign).

References
==========
  Clark, R.N. & Stankey, G.H. (1979). The Recreation Opportunity Spectrum.
    USDA Forest Service, PNW-98.
  Stankey, G.H. et al. (1985). The Limits of Acceptable Change (LAC) System.
    USDA Forest Service, INT-176.
"""
from __future__ import annotations

from enum import Enum


class ROSClass(str, Enum):
    """Recreation Opportunity Spectrum class (primitive → developed)."""

    PRIMITIVE = "primitive"
    SEMI_PRIMITIVE = "semi_primitive"
    ROADED_NATURAL = "roaded_natural"
    RURAL_DEVELOPED = "rural_developed"


_ROS_LABEL_ES: dict[ROSClass, str] = {
    ROSClass.PRIMITIVE: "Primitivo",
    ROSClass.SEMI_PRIMITIVE: "Semiprimitivo",
    ROSClass.ROADED_NATURAL: "Natural con acceso",
    ROSClass.RURAL_DEVELOPED: "Rural / desarrollado",
}

# LAC standard: the minimum acceptable EHS for each ROS class. Primitive
# settings tolerate the least change (highest required condition); developed
# settings tolerate more. These are planning standards, not empirical limits.
_LAC_STANDARD_EHS: dict[ROSClass, float] = {
    ROSClass.PRIMITIVE: 75.0,
    ROSClass.SEMI_PRIMITIVE: 65.0,
    ROSClass.ROADED_NATURAL: 55.0,
    ROSClass.RURAL_DEVELOPED: 45.0,
}

# EHS points above the standard within which the asset is "approaching" it.
_APPROACH_BUFFER = 10.0

# LAC status labels.
STATUS_WITHIN = "Dentro del estándar"
STATUS_APPROACHING = "Cerca del límite"
STATUS_EXCEEDED = "Límite superado (cambio inaceptable)"


def ros_label(ros: ROSClass) -> str:
    return _ROS_LABEL_ES[ros]


def classify_ros(accessibility_score: float | None) -> ROSClass:
    """Map an asset's accessibility (0=remote … 1=very easy access) to a ROS class.

    Access is the dominant ROS driver in a mountain protected area (remoteness
    and road access separate the classes). Missing access is treated as the
    conservative middle (SEMI_PRIMITIVE) rather than assuming a developed
    setting.
    """
    if accessibility_score is None:
        return ROSClass.SEMI_PRIMITIVE
    a = max(0.0, min(1.0, float(accessibility_score)))
    if a < 0.30:
        return ROSClass.PRIMITIVE
    if a < 0.55:
        return ROSClass.SEMI_PRIMITIVE
    if a < 0.80:
        return ROSClass.ROADED_NATURAL
    return ROSClass.RURAL_DEVELOPED


def lac_standard_ehs(ros: ROSClass) -> float:
    """Minimum acceptable EHS (the LAC standard) for a ROS class."""
    return _LAC_STANDARD_EHS[ros]


def lac_status(ehs: float, standard: float) -> str:
    """Classify current EHS against its LAC standard."""
    if ehs < standard:
        return STATUS_EXCEEDED
    if ehs < standard + _APPROACH_BUFFER:
        return STATUS_APPROACHING
    return STATUS_WITHIN


def capacity_at_standard(
    current_pressure: float,
    ehs: float,
    standard: float,
    *,
    pristine_ehs: float = 100.0,
) -> int | None:
    """Estimate the annual pressure consistent with holding EHS at ``standard``.

    Transparent planning model, NOT a fitted dose-response: assume EHS falls
    linearly with pressure from a pristine baseline (``pristine_ehs`` at zero
    pressure). The current point ``(current_pressure, ehs)`` fixes the slope, so
    the pressure at which EHS would reach ``standard`` is

        P_std = current_pressure · (pristine_ehs − standard) / (pristine_ehs − ehs)

    * EHS above the standard → headroom → ``P_std`` above current pressure.
    * EHS below the standard → over capacity → ``P_std`` below current pressure.

    Returns ``None`` when the estimate is undefined or meaningless (near-pristine
    EHS, non-positive pressure) — absence is stated, never faked.
    """
    if current_pressure <= 0:
        return None
    denom = pristine_ehs - max(0.0, min(pristine_ehs, ehs))
    if denom <= 0.5:  # near-pristine: no measurable degradation to extrapolate
        return None
    p_std = current_pressure * (pristine_ehs - standard) / denom
    if p_std <= 0:
        return 0
    return int(round(p_std, -2))  # round to hundreds, like the rest of the model
