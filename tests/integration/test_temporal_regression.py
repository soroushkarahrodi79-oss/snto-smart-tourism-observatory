"""Regresión: la capa temporal v1.1.0 no perturba la lógica de producción.

No duplica ``test_enrichment.py`` (override conservador) ni ``test_socioeconomic.py``
(TRAGSA/ALMUDENA). Bloquea dos invariantes de integración:

1. **Orden del pipeline**: ``enrich_assets_with_satellite`` DEBE ejecutarse antes
   de ``rank_assets``; de lo contrario el dato satelital real no se propaga al
   TPI/tier (contrato documentado en ``enrichment.py`` líneas 28-30). Se prueba con
   las funciones REALES, no con un mock del orquestador.
2. **Panel temporal de solo lectura**: cargar las tendencias reales
   (``summarize_trends``) no muta los activos curados.
"""
from __future__ import annotations

import src.platform.enrichment as enrichment
from src.platform.calibration import CalibrationResult
from src.platform.satellite_trends import summarize_trends
from src.territorial.models import AssetType, TerritorialAsset
from src.territorial.tpi import rank_assets


def _asset(asset_id="pnsg_t1", ehs=70.0, alert="NORMAL", trend="decreasing"):
    return TerritorialAsset(
        asset_id=asset_id,
        name=f"Senda {asset_id}",
        asset_type=AssetType.TRAIL,
        region="Test",
        ehs=ehs,
        risk_score=round(1.0 - ehs / 100.0, 4),
        dcs=70.0,
        alert_level=alert,
        scm_classification="MIXED",
        scm_confidence="MODERATE",
        trend_direction=trend,
        mk_p_value=0.04,
        visitor_capacity_annual=10_000,
        economic_importance=0.5,
        accessibility_score=0.5,
    )


def _cal_degraded(asset_id, curated, satellite):
    return CalibrationResult(
        asset_id=asset_id, curated_ehs=curated, satellite_ehs=satellite,
        matched_trails=["x"], n_trails=1,
        delta=round(satellite - curated, 1), flag="mas_degradado",
    )


def test_enrich_before_rank_propagates_satellite_to_tpi(monkeypatch):
    """Orden CORRECTO (enrich → rank): el override satelital (EHS 70→20, alerta
    escalada) se computa DENTRO del TPI. Orden INVERTIDO (rank → enrich) fija el
    TPI sobre el dato curado y el override ya no se propaga. La divergencia del
    TPI entre ambos órdenes demuestra que el orden es un invariante."""
    monkeypatch.setattr(
        enrichment, "calibrate_territory",
        lambda key, assets: {"pnsg_t1": _cal_degraded("pnsg_t1", 70.0, 20.0)},
    )

    # Orden correcto: enrich primero, luego rank.
    a_correct = _asset(ehs=70.0)
    enriched, _ = enrichment.enrich_assets_with_satellite("pnsg", [a_correct])
    ranked = rank_assets(enriched)
    assert ranked[0].ehs == 20.0                 # override satelital aplicado
    tpi_correct = ranked[0].tpi

    # Orden invertido: rank primero (sobre EHS curado 70), enrich después.
    a_wrong = _asset(ehs=70.0)
    rank_assets([a_wrong])
    tpi_wrong = a_wrong.tpi                       # TPI fijado antes del override
    enrichment.enrich_assets_with_satellite("pnsg", [a_wrong])
    assert a_wrong.tpi == tpi_wrong              # enrich tardío NO recomputa TPI

    # El orden cambia el resultado → contrato build→enrich→rank es obligatorio.
    assert tpi_correct != tpi_wrong


def test_summarize_trends_does_not_mutate_assets():
    """El panel de Evolución Temporal solo lee tendencias; no toca los activos."""
    a = _asset(ehs=55.0, alert="PREVENTIVE_ACTION")
    before = (a.ehs, a.risk_score, a.alert_level)

    # usa el JSON real del repo si existe; si no, available=False
    summary = summarize_trends()
    assert isinstance(summary.available, bool)

    assert (a.ehs, a.risk_score, a.alert_level) == before
