"""
SNTO — Enriquecimiento de activos con observación satelital real (Fase 2)
=========================================================================
Hace del dato satelital del Pipeline A el *núcleo* que alimenta KPIs, TPI,
tiers y alertas, en lugar de relegarlo a una pestaña-apéndice. Reutiliza la
triangulación que ya existe en ``calibration.calibrate_territory`` (join
activo→senda real + conversión de convención estrés→salud) y aplica una
política de **override conservador**.

Política de override conservador (escalar)
-------------------------------------------
El EHS curado (juicio experto de salud bajo presión antrópica) y el EHS
satelital (verdor NDVI/NDMI de la senda real) miden constructos distintos. En
alta montaña divergen de forma esperable: cumbres cuarcíticas, crestas y
canchales graníticos tienen poco NDVI por GEOLOGÍA, no por degradación
turística (ver caveats en ``calibration.py``). Por eso:

  · flag == "mas_degradado"  → el satélite detecta MÁS estrés que el experto.
                               Sobreescribimos el EHS curado con el satelital y
                               recalculamos riesgo/alerta. Solo escalamos
                               (nunca rebajamos una alerta curada existente).
  · flag == "mas_sano"       → el satélite es más verde; podría ser geología.
                               Se MANTIENE el dato curado (no se sustituye al
                               alza).
  · flag == "confirma"       → ya concuerdan; se mantiene el curado.
  · flag == "sin_dato"       → sin senda equivalente; se mantiene el curado.

Como ``TerritorialAsset`` es mutable y ``rank_assets`` recalcula TPI/tier a
partir de ``ehs``, inyectar aquí —antes de ``rank_assets``— propaga el dato
real a todo el pipeline derivado sin cablear pestaña por pestaña.
"""
from __future__ import annotations

from src.config.constants import ALERT_CRITICAL, ALERT_PREVENTIVE, ALERT_URGENT
from src.platform.calibration import CalibrationResult, calibrate_territory

# Severidad de alerta: índice menor = más severa. Espeja src/alerts/engine.py.
_ALERT_SEVERITY: dict[str, int] = {
    "CRITICAL_INTERVENTION": 0,
    "URGENT_MONITORING": 1,
    "PREVENTIVE_ACTION": 2,
    "NORMAL": 3,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _alert_from_risk(risk: float, trend_direction: str) -> str:
    """Reclasifica el nivel de alerta a partir del riesgo (0-1) y la dirección
    de tendencia, reproduciendo los umbrales de ``src/alerts/engine.py``
    (``AlertEngine._classify_level``).

    Se usa el ``trend_direction`` (string ya gated por Mann-Kendall en el
    activo) en lugar de reconstruir un ``TrendResult``: la condición de
    "declive" del nivel URGENTE equivale a ``trend_direction == "decreasing"``.
    """
    if risk > ALERT_CRITICAL:
        return "CRITICAL_INTERVENTION"
    if risk >= ALERT_URGENT and trend_direction == "decreasing":
        return "URGENT_MONITORING"
    if risk >= ALERT_PREVENTIVE:
        return "PREVENTIVE_ACTION"
    return "NORMAL"


def _more_severe(current: str, candidate: str) -> str:
    """Devuelve el nivel de alerta más severo de los dos. Garantiza que el
    override solo escala: nunca rebaja una alerta curada existente."""
    cur = _ALERT_SEVERITY.get(current, 3)
    cand = _ALERT_SEVERITY.get(candidate, 3)
    return candidate if cand < cur else current


def enrich_assets_with_satellite(
    dashboard_key: str,
    assets: list,
) -> tuple[list, dict[str, CalibrationResult]]:
    """Sobreescribe (conservadoramente) el EHS curado con el satelital real.

    Args:
        dashboard_key: "snr" | "pnsg".
        assets: lista de ``TerritorialAsset`` recién construidos (mutables),
                ANTES de ``rank_assets``.

    Returns:
        ``(assets, calibration)`` donde ``calibration`` es el dict
        ``asset_id → CalibrationResult`` para que la UI muestre procedencia y
        concordancia. Si el Pipeline A no se ha ejecutado, todos los activos
        salen con flag ``sin_dato`` y los datos curados quedan intactos.
    """
    calibration = calibrate_territory(dashboard_key, assets)

    for asset in assets:
        result = calibration.get(asset.asset_id)
        if result is None or result.satellite_ehs is None:
            continue
        if result.flag != "mas_degradado":
            # mas_sano / confirma / sin_dato → se respeta el juicio curado.
            continue

        # El satélite observa MÁS degradación que el experto → escalar.
        asset.ehs = result.satellite_ehs
        asset.risk_score = round(_clamp(1.0 - result.satellite_ehs / 100.0), 4)
        recomputed_alert = _alert_from_risk(asset.risk_score, asset.trend_direction)
        asset.alert_level = _more_severe(asset.alert_level, recomputed_alert)

    return assets, calibration


def enrichment_summary(calibration: dict[str, CalibrationResult]) -> dict[str, int]:
    """Recuento de activos efectivamente sobreescritos por el satélite vs.
    mantenidos curados, para cabeceras de procedencia en la UI."""
    overridden = sum(
        1 for r in calibration.values()
        if r.flag == "mas_degradado" and r.satellite_ehs is not None
    )
    return {
        "overridden": overridden,
        "curated": len(calibration) - overridden,
        "total": len(calibration),
    }
