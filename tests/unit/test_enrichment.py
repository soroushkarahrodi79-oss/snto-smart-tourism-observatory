"""Tests de la Fase 2 — inyección satelital con override conservador.

Verifican que ``enrich_assets_with_satellite``:
  · sobreescribe el EHS y escala la alerta cuando el satélite ve MÁS degradación;
  · NO toca el dato curado cuando el satélite es más verde o no hay senda;
  · nunca rebaja una alerta curada existente (solo escala).
"""
from __future__ import annotations

import src.platform.enrichment as enrichment
from src.platform.calibration import CalibrationResult
from src.territorial.models import AssetType, TerritorialAsset


def _asset(asset_id: str, ehs: float, alert: str, trend: str = "decreasing") -> TerritorialAsset:
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


def _cal(asset_id: str, curated: float, satellite, flag: str) -> CalibrationResult:
    delta = None if satellite is None else round(satellite - curated, 1)
    return CalibrationResult(
        asset_id=asset_id, curated_ehs=curated, satellite_ehs=satellite,
        matched_trails=["x"] if satellite is not None else [],
        n_trails=1 if satellite is not None else 0, delta=delta, flag=flag,
    )


def _patch(monkeypatch, results: dict[str, CalibrationResult]) -> None:
    monkeypatch.setattr(enrichment, "calibrate_territory", lambda key, assets: results)


def test_mas_degradado_overrides_and_escalates(monkeypatch):
    a = _asset("t1", ehs=70.0, alert="NORMAL", trend="decreasing")
    _patch(monkeypatch, {"t1": _cal("t1", 70.0, 20.0, "mas_degradado")})

    out, cal = enrichment.enrich_assets_with_satellite("pnsg", [a])

    assert out[0].ehs == 20.0                       # EHS sobreescrito por el satélite
    assert abs(out[0].risk_score - 0.8) < 1e-6      # riesgo coherente (1 - 20/100)
    # risk 0.8 ≥ urgente (0.70) y tendencia decreciente → escala a URGENT
    assert out[0].alert_level == "URGENT_MONITORING"
    assert cal["t1"].flag == "mas_degradado"


def test_mas_sano_keeps_curated(monkeypatch):
    a = _asset("t2", ehs=40.0, alert="PREVENTIVE_ACTION")
    _patch(monkeypatch, {"t2": _cal("t2", 40.0, 85.0, "mas_sano")})

    out, _ = enrichment.enrich_assets_with_satellite("pnsg", [a])

    assert out[0].ehs == 40.0                       # se respeta el juicio experto
    assert out[0].alert_level == "PREVENTIVE_ACTION"


def test_sin_dato_keeps_curated(monkeypatch):
    a = _asset("t3", ehs=55.0, alert="NORMAL")
    _patch(monkeypatch, {"t3": _cal("t3", 55.0, None, "sin_dato")})

    out, _ = enrichment.enrich_assets_with_satellite("pnsg", [a])

    assert out[0].ehs == 55.0
    assert out[0].alert_level == "NORMAL"


def test_override_never_downgrades_alert(monkeypatch):
    # Satélite más degradado pero solo a EHS 60 (riesgo 0.4 → PREVENTIVE);
    # el activo ya estaba en CRÍTICO por juicio experto: NO debe rebajarse.
    a = _asset("t4", ehs=80.0, alert="CRITICAL_INTERVENTION", trend="no_trend")
    _patch(monkeypatch, {"t4": _cal("t4", 80.0, 60.0, "mas_degradado")})

    out, _ = enrichment.enrich_assets_with_satellite("pnsg", [a])

    assert out[0].ehs == 60.0                        # EHS sí baja
    assert out[0].alert_level == "CRITICAL_INTERVENTION"  # alerta no se rebaja


def test_enrichment_summary_counts(monkeypatch):
    cal = {
        "a": _cal("a", 70.0, 20.0, "mas_degradado"),
        "b": _cal("b", 40.0, 85.0, "mas_sano"),
        "c": _cal("c", 55.0, None, "sin_dato"),
    }
    summary = enrichment.enrichment_summary(cal)
    assert summary == {"overridden": 1, "curated": 2, "total": 3}
