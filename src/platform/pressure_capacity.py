"""Transparent planning model for visitor pressure and carrying capacity.

SNTO currently has no observed turnstile series for every asset.  The module
therefore keeps the curated ``visitor_capacity_annual`` field as an explicitly
estimated annual pressure proxy and derives a planning range, not a measured
limit.  The range is conditioned by ecological health and widened when DCS is
lower.  Seasonal TPI values are a visible scenario profile whose multipliers
average to one; they must never be presented as observations.

v2.2 adds a **LAC / ROS** layer (:mod:`src.platform.lac_ros`): each asset is
classified along the Recreation Opportunity Spectrum, given a Limits of
Acceptable Change standard on EHS, flagged against it, and given a
capacity-at-standard threshold (a planning estimate). When the real MITMA
mobility snapshot exists, the municipal inbound-trip figure is attached as
**context** — never substituted for the asset pressure proxy, because a
municipal trip count is not trail footfall (see ``src/mobility``).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.lac_ros import (
    ROSClass,
    capacity_at_standard,
    classify_ros,
    lac_standard_ehs,
    lac_status,
    ros_label,
)


@dataclass(frozen=True)
class SeasonalPressurePoint:
    """One estimated seasonal pressure/TPI planning point."""

    season: str
    flow_proxy: int
    tpi: float


@dataclass(frozen=True)
class PressureCapacityProfile:
    """Decision-facing pressure, capacity-range and SCM summary for one asset."""

    asset_id: str
    asset_name: str
    tier: int
    annual_pressure_proxy: int
    capacity_low: int
    capacity_central: int
    capacity_high: int
    capacity_status: str
    dcs: float
    scm_classification: str
    scm_confidence: str
    scm_hypothesis: str
    seasonal: tuple[SeasonalPressurePoint, ...]

    # ── LAC / ROS layer (v2.2) ────────────────────────────────────────────
    ros_class: str = ROSClass.SEMI_PRIMITIVE.value
    ros_label: str = ""
    lac_standard_ehs: float = 0.0
    lac_status: str = ""
    # Pressure consistent with holding EHS at the LAC standard (planning
    # estimate). None when undefined (near-pristine EHS).
    capacity_at_standard: int | None = None
    # Real MITMA municipal inbound mobility (mean daily trips) attached as
    # CONTEXT, or None when the real snapshot has not been ingested. A municipal
    # trip count is not trail footfall — never used as the asset proxy.
    municipal_inbound_daily: float | None = None
    pressure_source: str = "Curada (estimada)"


_SEASON_MULTIPLIERS = (
    ("Invierno", 0.55),
    ("Primavera", 0.90),
    ("Verano", 1.55),
    ("Otoño", 1.00),
)

_SCM_HYPOTHESES = {
    "LOCALIZED_IMPACT": (
        "Señal compatible con presión de uso localizada; requiere contraste "
        "de campo antes de atribuir causa."
    ),
    "LANDSCAPE_DRIVEN": (
        "Señal compatible con forzamiento climático o de paisaje compartido; "
        "no atribuirla al uso turístico."
    ),
    "MIXED": (
        "La señal no separa con claridad turismo y clima; mantener ambas "
        "hipótesis abiertas."
    ),
}


def assess_pressure_capacity(
    assets: list,
    *,
    municipal_pressure_by_region: dict[str, float] | None = None,
) -> tuple[PressureCapacityProfile, ...]:
    """Build LAC/ROS planning profiles sorted by territorial priority (TPI).

    ``municipal_pressure_by_region`` (optional) maps an asset's ``region`` to the
    real MITMA mean daily inbound trips for that municipality. When given, the
    figure is attached as context (``municipal_inbound_daily``); it is never
    used as the asset pressure proxy. ``None`` (the default, and the state until
    the mobility ETL is run) preserves the pre-v2.2 behaviour exactly.
    """
    ctx = municipal_pressure_by_region or {}

    def _ctx_for(asset: object) -> float | None:
        region = getattr(asset, "region", None)
        return ctx.get(region) if isinstance(region, str) else None

    profiles = [_assess_asset(asset, _ctx_for(asset)) for asset in assets]
    profiles.sort(
        key=lambda item: -max(point.tpi for point in item.seasonal),
    )
    return tuple(profiles)


def _assess_asset(
    asset, municipal_inbound: float | None = None
) -> PressureCapacityProfile:
    annual_proxy = max(0, int(asset.visitor_capacity_annual))
    dcs = max(0.0, min(100.0, float(asset.dcs)))

    # A conservative operating-capacity heuristic: degraded ecological state
    # reduces the central planning value.  This is intentionally not an
    # independent ecological validation and is labelled as estimated in UI.
    condition_factor = 0.65 + 0.35 * max(0.0, min(100.0, asset.ehs)) / 100
    central = _round_hundreds(annual_proxy * condition_factor)
    uncertainty = _uncertainty_for_dcs(dcs)
    low = _round_hundreds(central * (1 - uncertainty))
    high = _round_hundreds(central * (1 + uncertainty))

    if annual_proxy <= low:
        status = "Con margen en el modelo"
    elif annual_proxy <= high:
        status = "Dentro de la horquilla"
    else:
        status = "Supera la horquilla estimada"

    base_tpi = max(0.0, min(100.0, float(asset.tpi or 0.0)))
    seasonal = tuple(
        SeasonalPressurePoint(
            season=season,
            flow_proxy=_round_hundreds(annual_proxy * multiplier / 4),
            tpi=round(min(100.0, base_tpi * multiplier), 1),
        )
        for season, multiplier in _SEASON_MULTIPLIERS
    )
    scm_classification = asset.scm_classification or "MIXED"

    # ── LAC / ROS layer ───────────────────────────────────────────────────
    ehs = max(0.0, min(100.0, float(asset.ehs)))
    ros = classify_ros(getattr(asset, "accessibility_score", None))
    standard = lac_standard_ehs(ros)
    threshold = capacity_at_standard(annual_proxy, ehs, standard)
    source = (
        "Movilidad MITMA (proxy municipal)"
        if municipal_inbound is not None
        else "Curada (estimada)"
    )

    return PressureCapacityProfile(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        tier=int(asset.tier or 3),
        annual_pressure_proxy=annual_proxy,
        capacity_low=low,
        capacity_central=central,
        capacity_high=high,
        capacity_status=status,
        dcs=dcs,
        scm_classification=scm_classification,
        scm_confidence=asset.scm_confidence or "LOW",
        scm_hypothesis=_SCM_HYPOTHESES.get(
            scm_classification,
            _SCM_HYPOTHESES["MIXED"],
        ),
        seasonal=seasonal,
        ros_class=ros.value,
        ros_label=ros_label(ros),
        lac_standard_ehs=standard,
        lac_status=lac_status(ehs, standard),
        capacity_at_standard=threshold,
        municipal_inbound_daily=municipal_inbound,
        pressure_source=source,
    )


def _uncertainty_for_dcs(dcs: float) -> float:
    if dcs >= 70:
        return 0.15
    if dcs >= 55:
        return 0.25
    return 0.35


def _round_hundreds(value: float) -> int:
    if value <= 0:
        return 0
    return int(round(value, -2))
