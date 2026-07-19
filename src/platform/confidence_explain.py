"""Honest DCS decomposition, sensitivity and evidence-gap contracts.

Dashboard fixtures currently persist the total DCS but not the five component
scores produced by ``decision_confidence.assessor``.  This module consumes exact
components when present.  Otherwise it derives only the mathematically feasible
component interval implied by the total and the published maxima.  It never
allocates the total heuristically or presents a reconstruction as measured.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceComponent:
    key: str
    label: str
    maximum: float
    score: float | None
    feasible_low: float
    feasible_high: float
    sensitivity_upper: float
    evidence_status: str
    gap: str


@dataclass(frozen=True)
class ConfidenceProfile:
    asset_id: str
    asset_name: str
    dcs: float
    band: str
    exact_decomposition: bool
    action_gate: bool | None
    action_gate_label: str
    components: tuple[ConfidenceComponent, ...]


_COMPONENTS = (
    ("data_quality", "Calidad de datos", 25.0),
    ("temporal_robustness", "Robustez temporal", 25.0),
    ("spatial_consistency", "Consistencia espacial", 20.0),
    ("model_stability", "Estabilidad del modelo", 15.0),
    ("signal_strength", "Fuerza de señal", 15.0),
)

_GAPS = {
    "data_quality": "Persistir cobertura, nubosidad y píxel válido.",
    "temporal_robustness": "Persistir años, observaciones y R² estacional.",
    "spatial_consistency": "Propagar el subscore calculado desde SCM.",
    "model_stability": "Persistir estabilidad NDVI/NDMI y entre años.",
    "signal_strength": "Persistir anomalías y coherencia EHS/riesgo.",
}


def build_confidence_profiles(assets: list) -> tuple[ConfidenceProfile, ...]:
    """Build profiles ordered from lowest to highest DCS (largest gap first)."""
    profiles = tuple(_build_profile(asset) for asset in assets)
    return tuple(sorted(profiles, key=lambda profile: profile.dcs))


def _build_profile(asset) -> ConfidenceProfile:
    total = max(0.0, min(100.0, float(asset.dcs)))
    supplied = getattr(asset, "dcs_components", None) or {}
    known = {}
    for key, _, maximum in _COMPONENTS:
        if key not in supplied:
            continue
        score = float(supplied[key])
        if not 0 <= score <= maximum:
            raise ValueError(f"{key} must be between 0 and {maximum:g}")
        known[key] = score

    exact = len(known) == len(_COMPONENTS)
    if exact and abs(sum(known.values()) - total) > 1.0:
        raise ValueError("DCS components must sum to the persisted total (±1 point)")

    known_sum = sum(known.values())
    missing = [(key, maximum) for key, _, maximum in _COMPONENTS if key not in known]
    remaining_total = max(0.0, total - known_sum)
    components = []
    for key, label, maximum in _COMPONENTS:
        score = known.get(key)
        if score is not None:
            low = high = score
            status = "Calculado"
            gap = "—"
        else:
            other_max = sum(
                item_max
                for item_key, item_max in missing
                if item_key != key
            )
            low = max(0.0, remaining_total - other_max)
            high = min(maximum, remaining_total)
            status = _availability_status(asset, key)
            gap = _GAPS[key]
        components.append(
            ConfidenceComponent(
                key=key,
                label=label,
                maximum=maximum,
                score=score,
                feasible_low=round(low, 1),
                feasible_high=round(high, 1),
                sensitivity_upper=round(maximum - low, 1),
                evidence_status=status,
                gap=gap,
            )
        )

    if exact:
        gate = (
            total >= 60
            and known["data_quality"] >= 10
            and known["temporal_robustness"] >= 12
        )
        gate_label = "Apto para actuar" if gate else "Gate de evidencia no superado"
    else:
        gate = None
        gate_label = "Gate no verificable: faltan componentes"

    return ConfidenceProfile(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        dcs=total,
        band=_band(total),
        exact_decomposition=exact,
        action_gate=gate,
        action_gate_label=gate_label,
        components=tuple(components),
    )


def _availability_status(asset, key: str) -> str:
    if key == "temporal_robustness" and getattr(asset, "mk_p_value", None) is not None:
        return "Fuente parcial"
    if key == "spatial_consistency" and getattr(asset, "scm_classification", None):
        return "Fuente parcial"
    if key == "signal_strength" and getattr(asset, "ehs", None) is not None:
        return "Fuente parcial"
    return "Propagación pendiente"


def _band(total: float) -> str:
    if total >= 80:
        return "Muy alta"
    if total >= 60:
        return "Alta"
    if total >= 40:
        return "Moderada"
    return "Baja"
