"""Transparent planning model for visitor pressure and carrying capacity.

SNTO currently has no observed turnstile series for every asset.  The module
therefore keeps the curated ``visitor_capacity_annual`` field as an explicitly
estimated annual pressure proxy and derives a planning range, not a measured
limit.  The range is conditioned by ecological health and widened when DCS is
lower.  Seasonal TPI values are a visible scenario profile whose multipliers
average to one; they must never be presented as observations.
"""

from __future__ import annotations

from dataclasses import dataclass


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


def assess_pressure_capacity(assets: list) -> tuple[PressureCapacityProfile, ...]:
    """Build planning profiles sorted by territorial priority (TPI)."""
    profiles = [_assess_asset(asset) for asset in assets]
    profiles.sort(
        key=lambda item: -max(point.tpi for point in item.seasonal),
    )
    return tuple(profiles)


def _assess_asset(asset) -> PressureCapacityProfile:
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
