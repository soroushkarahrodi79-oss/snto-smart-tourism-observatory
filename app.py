"""
SNTO — Smart Natural Tourism Observatory
Executive Destination Intelligence Dashboard  (Phase 7)

Levanta el servidor con:
    streamlit run app.py
"""
from __future__ import annotations

import datetime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src.territorial.models import AssetType, TerritorialAsset
from src.territorial.tpi import rank_assets
from src.intervention import compare_scenarios, allocate_tis_budget
from src.platform import compute_executive_dashboard, ExecutiveDashboard
from src.platform.map_layers import (
    build_pydeck_deck, build_pydeck_deck_spectral, build_real_trails_deck,
    assets_to_geojson, LEGEND_ITEMS, TIER_COLORS,
)
from src.platform.charts import build_portfolio_matrix, build_time_series_chart
from src.platform.real_trails import (
    get_real_trails, build_real_trails_geojson, get_park_boundary,
)
from src.platform.calibration import calibrate_territory, coverage_summary
from src.platform.provenance import (
    data_status_badge, load_timeseries_coverage, snapshot_provenance,
)
from src.temporal import DataStatus

# ── Fecha global de informe ───────────────────────────────────────────────────
REPORT_DATE = "2026-06-12"


def build_territory() -> list[TerritorialAsset]:
    """
    20 activos reales de la Reserva de la Biosfera Sierra del Rincón (Madrid).

    Distribución de tiers calibrada contra el motor TPI:
      Tier 1 (Atención Inmediata) — 5 activos: presión turística alta, EHS < 45
      Tier 2 (Acción Preventiva)  — 6 activos: señales de alerta, EHS 50-65
      Tier 3 (Monitorización)     — 5 activos: estables, TPI < 38
      Tier 4 (Promoción Activa)   — 4 activos: EHS ≥ 75, riesgo bajo, DCS ≥ 55
    """
    return [

        # ── TIER 1 · Atención Inmediata ───────────────────────────────────────
        # Activadores garantizados: alert CRITICAL/URGENT + EHS < 45 + TPI > 50
        # Para KPI-7 (Human Pressure Alerts 🔴): todos con LOCALIZED_IMPACT
        # ──────────────────────────────────────────────────────────────────────

        # TPI ≈ 95 | CU=40(CRITICAL) + ES=20.5 + SV=19.3 + CC=15
        TerritorialAsset(
            asset_id="snr-nat-001",
            name="Hayedo de Montejo — Zona Periférica",
            asset_type=AssetType.NATURAL_PARK, region="Montejo de la Sierra",
            ehs=38.0, risk_score=0.74, dcs=82.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.008,
            visitor_capacity_annual=45_000, economic_importance=0.95,
            accessibility_score=0.92,
            elevation_m=1_220, area_ha=102.0,
            description=(
                "Zona de amortiguamiento del Hayedo. Desbordamiento de visitantes "
                "fuera del sistema de reserva gestionado: pisoteo de regenerado, "
                "compactación de suelo y alteración de la regeneración natural del haya."
            ),
        ),

        # TPI ≈ 89 | CU=40(CRITICAL) + ES=19.0 + SV=14.8 + CC=15
        TerritorialAsset(
            asset_id="snr-rec-001",
            name="Área Recreativa Vado de Montejo",
            asset_type=AssetType.RECREATIONAL_AREA, region="Montejo de la Sierra",
            ehs=33.0, risk_score=0.79, dcs=76.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.004,
            visitor_capacity_annual=28_000, economic_importance=0.78,
            accessibility_score=0.88,
            elevation_m=950, area_ha=8.5,
            description=(
                "Punto de baño en el nacimiento del Jarama. Saturación extrema en "
                "verano: vertidos, compactación de ribera y deterioro de la vegetación "
                "helofítica. Sin control de aforo ni guardería ambiental."
            ),
        ),

        # TPI ≈ 86 | CU=40(URGENT+declining, EHS<40 → factor=1.0) + ES=19.75 + SV=11.7 + CC=15
        TerritorialAsset(
            asset_id="snr-trail-001",
            name="Cascada del Chorrón — La Hiruela",
            asset_type=AssetType.TRAIL, region="La Hiruela",
            ehs=36.0, risk_score=0.77, dcs=79.0,
            alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.011,
            visitor_capacity_annual=18_000, economic_importance=0.65,
            accessibility_score=0.78,
            elevation_m=1_380, length_km=2.4,
            description=(
                "Cascada descubierta por redes sociales (~2019). El sendero de acceso "
                "carece de balizamiento; erosión severa en las riberas por atajos "
                "improvisados y pisoteo directo del cauce."
            ),
        ),

        # TPI ≈ 86 | CU=40(URGENT+declining) + ES=18.25 + SV=13.1 + CC=15
        TerritorialAsset(
            asset_id="snr-view-001",
            name="Mirador del Cancho de la Cabra",
            asset_type=AssetType.VIEWPOINT, region="Puebla de la Sierra",
            ehs=41.0, risk_score=0.70, dcs=73.0,
            alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.019,
            visitor_capacity_annual=22_000, economic_importance=0.72,
            accessibility_score=0.82,
            elevation_m=1_450,
            description=(
                "Mirador rocoso en la divisoria de Puebla de la Sierra. Acceso ilegal "
                "de vehículos todoterreno que abre pistas en la ladera; erosión laminar "
                "activa en el área de aparcamiento informal."
            ),
        ),

        # TPI ≈ 92 | CU=40(URGENT+declining) + ES=20.25 + SV=16.3 + CC=15
        TerritorialAsset(
            asset_id="snr-trail-002",
            name="Senda de los Hayas — Acceso Norte Hayedo",
            asset_type=AssetType.TRAIL, region="Montejo de la Sierra",
            ehs=42.0, risk_score=0.68, dcs=81.0,
            alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.015,
            visitor_capacity_annual=32_000, economic_importance=0.88,
            accessibility_score=0.90,
            elevation_m=1_180, length_km=4.8,
            description=(
                "Principal corredor de acceso al Hayedo de Montejo por el norte. "
                "Afluencia masiva en otoño (foliación). Sendero multisendas por "
                "atajos; erosión remontante activa en al menos tres puntos críticos."
            ),
        ),

        # ── TIER 2 · Acción Preventiva ────────────────────────────────────────
        # EHS 50-65, alert PREVENTIVE_ACTION, TPI 42-62 (≥ 38, < 50 en muchos)
        # ──────────────────────────────────────────────────────────────────────

        # TPI ≈ 61 | CU=26.4(PREV+dec) + ES=17.0 + SV=7.8 + CC=10
        TerritorialAsset(
            asset_id="snr-trail-003",
            name="Senda de los Carboneros — Horcajuelo",
            asset_type=AssetType.TRAIL, region="Horcajuelo de la Sierra",
            ehs=58.0, risk_score=0.47, dcs=68.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.038,
            visitor_capacity_annual=8_000, economic_importance=0.48,
            accessibility_score=0.60,
            elevation_m=1_080, length_km=6.2,
            description=(
                "Antigua ruta de arrieros y carboneros que conecta Horcajuelo con la "
                "sierra. Señales tempranas de erosión lineal y daño en el talud. "
                "Sin intervención, escalaría a Tier 1 en 2-3 años."
            ),
        ),

        # TPI ≈ 56 | CU=22.0(PREV+dec) + ES=18.0 + SV=7.8 + CC=8
        TerritorialAsset(
            asset_id="snr-nat-002",
            name="Hayedo de Robregordo",
            asset_type=AssetType.NATURAL_PARK, region="Robregordo",
            ehs=54.0, risk_score=0.52, dcs=72.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.044,
            visitor_capacity_annual=6_500, economic_importance=0.55,
            accessibility_score=0.55,
            elevation_m=1_310, area_ha=38.0,
            description=(
                "Rodal de hayas secundario junto a Robregordo, sin régimen de reserva. "
                "Estrés térmico creciente (borde sur de distribución del haya) combinado "
                "con pisoteo difuso sin canalizar."
            ),
        ),

        # TPI ≈ 55 | CU=20.0(PREV) + ES=16.25 + SV=8.7 + CC=10
        TerritorialAsset(
            asset_id="snr-view-002",
            name="Mirador de La Hiruela — Cresta Norte",
            asset_type=AssetType.VIEWPOINT, region="La Hiruela",
            ehs=61.0, risk_score=0.44, dcs=65.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.12,
            visitor_capacity_annual=9_500, economic_importance=0.52,
            accessibility_score=0.68,
            elevation_m=1_340,
            description=(
                "Mirador sobre el pueblo más alto de la reserva con vistas al "
                "macizo de Ayllón. Presión moderada; vegetación rupícola en la "
                "plataforma de observación con señales de pisoteo."
            ),
        ),

        # TPI ≈ 47 | CU=20.0(PREV) + ES=15.25 + SV=7.0 + CC=5
        TerritorialAsset(
            asset_id="snr-trail-004",
            name="Ruta del Vértice Cabeza Mediana",
            asset_type=AssetType.TRAIL, region="Prádena del Rincón",
            ehs=63.0, risk_score=0.42, dcs=61.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.15,
            visitor_capacity_annual=7_200, economic_importance=0.44,
            accessibility_score=0.52,
            elevation_m=1_620, length_km=9.1,
            description=(
                "Ruta al punto más alto de la reserva (1 620 m). Terreno de pizarra "
                "frágil; primeras señales de apertura de caminos alternativos en la "
                "cumbre durante fines de semana con alta afluencia."
            ),
        ),

        # TPI ≈ 51 | CU=22.0(PREV+dec) + ES=14.5 + SV=10.4 + CC=4
        TerritorialAsset(
            asset_id="snr-rec-002",
            name="Fuente del Cura — Montejo de la Sierra",
            asset_type=AssetType.RECREATIONAL_AREA, region="Montejo de la Sierra",
            ehs=55.0, risk_score=0.50, dcs=58.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="LOW",
            trend_direction="decreasing", mk_p_value=0.052,
            visitor_capacity_annual=12_000, economic_importance=0.60,
            accessibility_score=0.82,
            elevation_m=1_020, area_ha=2.5,
            description=(
                "Fuente etnográfica y área de descanso muy frecuentada como punto "
                "de salida al Hayedo. Residuos, compactación del suelo y deterioro "
                "de la cubierta herbácea en el entorno inmediato."
            ),
        ),

        # TPI ≈ 52 | CU=20.0(PREV) + ES=16.0 + SV=6.2 + CC=10
        TerritorialAsset(
            asset_id="snr-heritage-001",
            name="Castro de la Edad del Hierro — La Hiruela",
            asset_type=AssetType.NATURAL_PARK, region="La Hiruela",
            ehs=52.0, risk_score=0.55, dcs=64.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.19,
            visitor_capacity_annual=4_800, economic_importance=0.42,
            accessibility_score=0.48,
            elevation_m=1_410, area_ha=4.2,
            description=(
                "Yacimiento castreño prerromano en cerro testigo con materiales "
                "en superficie. Sin protección perimetral ni señalización; visitantes "
                "entran libremente causando remoción involuntaria de piezas."
            ),
        ),

        # ── TIER 3 · Monitorización Rutinaria ────────────────────────────────
        # NORMAL alert, TPI < 38, condición moderada-buena
        # ──────────────────────────────────────────────────────────────────────

        # TPI ≈ 33 | CU=10.4(NORMAL,70) + ES=14.25 + SV=4.4 + CC=4
        TerritorialAsset(
            asset_id="snr-nat-003",
            name="Bosque de Quejigos — Horcajuelo de la Sierra",
            asset_type=AssetType.NATURAL_PARK, region="Horcajuelo de la Sierra",
            ehs=70.0, risk_score=0.34, dcs=57.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.28,
            visitor_capacity_annual=2_200, economic_importance=0.30,
            accessibility_score=0.38,
            elevation_m=1_090, area_ha=55.0,
            description=(
                "Bosque mixto de quejigo y melojo en buen estado de conservación. "
                "Presión antrópica baja; monitorización anual de fenología y cobertura "
                "suficiente con recursos actuales."
            ),
        ),

        # TPI ≈ 33 | CU=9.6(NORMAL,68) + ES=15.0 + SV=4.5 + CC=4
        TerritorialAsset(
            asset_id="snr-heritage-002",
            name="Ermita de San Blas — Montejo de la Sierra",
            asset_type=AssetType.VIEWPOINT, region="Montejo de la Sierra",
            ehs=68.0, risk_score=0.36, dcs=60.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.31,
            visitor_capacity_annual=1_800, economic_importance=0.28,
            accessibility_score=0.45,
            elevation_m=1_050,
            description=(
                "Ermita del s. XVI en alto con vistas a la sierra. Interés cultural "
                "y puntos de observación de flora rupícola. Afluencia baja y estacional; "
                "no requiere intervención activa."
            ),
        ),

        # TPI ≈ 37 | CU=10.6(NORMAL,73) + ES=14.5 + SV=3.5 + CC=8
        TerritorialAsset(
            asset_id="snr-stream-001",
            name="Arroyo de Horcajuelo — Tramo Alto",
            asset_type=AssetType.RECREATIONAL_AREA, region="Horcajuelo de la Sierra",
            ehs=73.0, risk_score=0.31, dcs=58.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="increasing", mk_p_value=0.36,
            visitor_capacity_annual=1_500, economic_importance=0.25,
            accessibility_score=0.30,
            elevation_m=1_140, area_ha=5.0,
            description=(
                "Tramo fluvial de cabecera con macroinvertebrados indicadores de "
                "calidad alta. Tendencia al alza en los índices bióticos; requiere "
                "solo monitorización hidrológica anual."
            ),
        ),

        # TPI ≈ 32 | CU=10.2(NORMAL,71) + ES=13.75 + SV=4.8 + CC=3
        TerritorialAsset(
            asset_id="snr-view-003",
            name="Mirador de Somosierra — Acceso Reserva",
            asset_type=AssetType.VIEWPOINT, region="Prádena del Rincón",
            ehs=71.0, risk_score=0.33, dcs=55.0,
            alert_level="NORMAL",
            scm_classification="MIXED", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.25,
            visitor_capacity_annual=2_800, economic_importance=0.32,
            accessibility_score=0.42,
            elevation_m=1_390,
            description=(
                "Punto panorámico en el límite norte de la reserva, junto al Puerto "
                "de Somosierra. Afluencia compartida con el paso de la A-1; sin señales "
                "de presión diferencial sobre la reserva."
            ),
        ),

        # TPI ≈ 32 | CU=9.2(NORMAL,66) + ES=14.5 + SV=3.9 + CC=4
        TerritorialAsset(
            asset_id="snr-heritage-003",
            name="Antigua Nevera — Puebla de la Sierra",
            asset_type=AssetType.VIEWPOINT, region="Puebla de la Sierra",
            ehs=66.0, risk_score=0.38, dcs=58.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.34,
            visitor_capacity_annual=1_200, economic_importance=0.26,
            accessibility_score=0.38,
            elevation_m=1_240,
            description=(
                "Nevera etnográfica del s. XVIII rehabilitada. Patrimonio cultural "
                "menor, visitas espontáneas ocasionales. Estado constructivo estable; "
                "no requiere intervención prioritaria."
            ),
        ),

        # ── TIER 4 · Promoción Activa ─────────────────────────────────────────
        # Garantía: EHS ≥ 75 AND risk ≤ 0.35 AND DCS ≥ 55 AND trend ≠ decreasing
        # Objetivo: absorber visitantes del Hayedo y diversificar la oferta
        # ──────────────────────────────────────────────────────────────────────

        TerritorialAsset(
            asset_id="snr-trail-005",
            name="Senda del Castañar — La Hiruela",
            asset_type=AssetType.TRAIL, region="La Hiruela",
            ehs=88.0, risk_score=0.18, dcs=78.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.42,
            visitor_capacity_annual=4_500, economic_importance=0.55,
            accessibility_score=0.70,
            elevation_m=1_280, length_km=5.3,
            description=(
                "Bosque de castaños centenarios poco conocido fuera del ámbito local. "
                "Excelente estado de conservación, senda bien trazada. Capacidad de "
                "absorción real de 4 500 visitantes/año sin impacto apreciable."
            ),
        ),

        TerritorialAsset(
            asset_id="snr-trail-006",
            name="Ruta de los Pueblos Negros — Prádena a Robregordo",
            asset_type=AssetType.TRAIL, region="Robregordo",
            ehs=85.0, risk_score=0.22, dcs=74.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.38,
            visitor_capacity_annual=6_800, economic_importance=0.60,
            accessibility_score=0.72,
            elevation_m=1_170, length_km=11.4,
            description=(
                "Itinerario cultural que conecta los pueblos de arquitectura negra "
                "en pizarra de la sierra. Combina patrimonio etnográfico y paisaje; "
                "infrautilizado respecto a su potencial turístico."
            ),
        ),

        TerritorialAsset(
            asset_id="snr-view-004",
            name="Mirador de la Hoya del Espino — Robregordo",
            asset_type=AssetType.VIEWPOINT, region="Robregordo",
            ehs=91.0, risk_score=0.14, dcs=82.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.48,
            visitor_capacity_annual=3_200, economic_importance=0.50,
            accessibility_score=0.62,
            elevation_m=1_460,
            description=(
                "Balcón natural sobre el valle de la Hoya del Espino prácticamente "
                "desconocido. EHS excelente, paisaje vegetal en recuperación activa "
                "tras el abandono del pastoreo extensivo."
            ),
        ),

        TerritorialAsset(
            asset_id="snr-center-001",
            name="Centro de Interpretación de la Biosfera — Montejo",
            asset_type=AssetType.RECREATIONAL_AREA, region="Montejo de la Sierra",
            ehs=82.0, risk_score=0.24, dcs=88.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.44,
            visitor_capacity_annual=8_500, economic_importance=0.72,
            accessibility_score=0.88,
            elevation_m=980, area_ha=3.0,
            description=(
                "Centro de visitantes de la reserva con jardín botánico, exposición "
                "permanente sobre el haya y la biosfera, y punto de reserva para el "
                "Hayedo. Nodo estratégico para redistribuir flujos de visitantes."
            ),
        ),

    ]


def build_pnsg_territory() -> list[TerritorialAsset]:
    """
    8 activos representativos del Parque Nacional Sierra de Guadarrama (Madrid/Segovia).

    Distribución de tiers calibrada contra el motor TPI:
      Tier 1 (Atención Inmediata) — 2 activos: saturación crítica, EHS < 45
      Tier 2 (Acción Preventiva)  — 3 activos: señales de alerta, EHS 50-65
      Tier 3 (Monitorización)     — 2 activos: estables, EHS 65-74
      Tier 4 (Promoción Activa)   — 1 activo:  EHS ≥ 75, riesgo bajo
    """
    return [

        # ── TIER 1 · Atención Inmediata ───────────────────────────────────────

        # TPI ≈ 91 | Laguna más visitada del PNSG — saturación documentada
        TerritorialAsset(
            asset_id="pnsg-nat-001",
            name="Laguna de Peñalara — Zona de Reserva",
            asset_type=AssetType.NATURAL_PARK, region="Rascafría",
            ehs=35.0, risk_score=0.77, dcs=79.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.006,
            visitor_capacity_annual=120_000, economic_importance=0.97,
            accessibility_score=0.88,
            elevation_m=2_020, area_ha=28.0,
            description=(
                "Laguna glaciar de alta montaña, hábitat prioritario de la rana patilarga "
                "(Rana iberica). Presión de visitantes 340% sobre la capacidad de carga "
                "en verano: pisoteo de orillas, eutrofización y alteración de anfibios. "
                "Régimen de acceso sin control efectivo en temporada alta."
            ),
        ),

        # TPI ≈ 87 | Cima masificada en fin de semana — erosión severa en crestas
        TerritorialAsset(
            asset_id="pnsg-view-001",
            name="Cumbre Siete Picos — Acceso Sur",
            asset_type=AssetType.VIEWPOINT, region="Cercedilla",
            ehs=39.0, risk_score=0.73, dcs=74.0,
            alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.009,
            visitor_capacity_annual=85_000, economic_importance=0.90,
            accessibility_score=0.92,
            elevation_m=2_138,
            description=(
                "El conjunto de las siete cumbres es destino icónico del PNSG. "
                "La combinación de fácil acceso desde Cercedilla y alta afluencia "
                "genera erosión severa en las crestas cuarcíticas: pisoteo de céspedes "
                "de alta montaña, apertura de sendas paralelas y arrastre de suelo. "
                "Degradación acelerada sin protocolo de control de afluencia."
            ),
        ),

        # ── TIER 2 · Acción Preventiva ────────────────────────────────────────

        # TPI ≈ 58 | Travesía de cresta masificada — señales de erosión lineal
        TerritorialAsset(
            asset_id="pnsg-trail-001",
            name="Cuerda Larga — Travesía Integral de Cresta",
            asset_type=AssetType.TRAIL, region="Navacerrada",
            ehs=57.0, risk_score=0.49, dcs=66.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.035,
            visitor_capacity_annual=45_000, economic_importance=0.75,
            accessibility_score=0.82,
            elevation_m=2_230, length_km=14.2,
            description=(
                "La travesía de mayor longitud del parque conecta el Ventisquero de "
                "la Condesa con el Puerto de la Morcuera. Erosión lineal incipiente "
                "en sectores de pizarra friable; sendas alternativas en tramos de cresta "
                "con afluencia concentrada en otoño e invierno."
            ),
        ),

        # TPI ≈ 55 | Área recreativa histórica con presión creciente
        TerritorialAsset(
            asset_id="pnsg-rec-001",
            name="Valle de la Fuenfría — Sector Laguna",
            asset_type=AssetType.RECREATIONAL_AREA, region="Cercedilla",
            ehs=53.0, risk_score=0.53, dcs=61.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.042,
            visitor_capacity_annual=35_000, economic_importance=0.68,
            accessibility_score=0.90,
            elevation_m=1_500, area_ha=42.0,
            description=(
                "Valle glaciar con pinar de pino silvestre y laguna artificial. "
                "Área de referencia para senderismo familiar desde Madrid. "
                "Compactación de suelo en orillas de la laguna y degradación del "
                "sotobosque en zonas de descanso no reguladas."
            ),
        ),

        # TPI ≈ 47 | Puerto de montaña con acceso rodado — conflicto vehículos/senderistas
        TerritorialAsset(
            asset_id="pnsg-view-002",
            name="Collado Ventoso — Puerto de Navacerrada",
            asset_type=AssetType.VIEWPOINT, region="Navacerrada",
            ehs=61.0, risk_score=0.45, dcs=63.0,
            alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.08,
            visitor_capacity_annual=55_000, economic_importance=0.72,
            accessibility_score=0.95,
            elevation_m=1_860,
            description=(
                "Puerto de carretera con acceso directo desde Madrid (A-6). Alta "
                "afluencia de visitantes sin objetivo de senderismo: congestión de "
                "aparcamiento, suciedad en bordes de carretera y pisoteo del cervunal "
                "en el entorno inmediato del aparcamiento. Sin gestión diferenciada "
                "respecto al parque de la estación de esquí."
            ),
        ),

        # ── TIER 3 · Monitorización Rutinaria ────────────────────────────────

        # TPI ≈ 32 | Hayedo maduro con buena cobertura de datos
        TerritorialAsset(
            asset_id="pnsg-nat-002",
            name="Hayedo del Valle de El Paular",
            asset_type=AssetType.NATURAL_PARK, region="Rascafría",
            ehs=70.0, risk_score=0.34, dcs=67.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.24,
            visitor_capacity_annual=15_000, economic_importance=0.55,
            accessibility_score=0.65,
            elevation_m=1_140, area_ha=80.0,
            description=(
                "Hayedo relicto en el fondo del Valle del Lozoya, uno de los más "
                "meridionales de la Península Ibérica. Presión antrópica controlada; "
                "estado de conservación bueno. Monitorización fenológica anual y "
                "vigilancia de la regeneración natural en el margen sureste."
            ),
        ),

        # TPI ≈ 33 | Senda menos conocida — indicador de recuperación
        TerritorialAsset(
            asset_id="pnsg-trail-002",
            name="Senda Herreros — Collado del Hornillo",
            asset_type=AssetType.TRAIL, region="Manzanares El Real",
            ehs=68.0, risk_score=0.36, dcs=55.0,
            alert_level="NORMAL",
            scm_classification="MIXED", scm_confidence="LOW",
            trend_direction="increasing", mk_p_value=0.32,
            visitor_capacity_annual=12_000, economic_importance=0.44,
            accessibility_score=0.58,
            elevation_m=1_680, length_km=8.6,
            description=(
                "Ruta circular poco frecuentada que asciende desde Manzanares El Real "
                "por el cordal de La Pedriza sur. Tendencia NDVI al alza tras la "
                "reducción del pastoreo extensivo. Cobertura de datos satelitales "
                "parcial (zona de sombra topográfica estacional); DCS bajo."
            ),
        ),

        # ── TIER 4 · Promoción Activa ─────────────────────────────────────────

        TerritorialAsset(
            asset_id="pnsg-rec-002",
            name="Centro de Visitantes El Paular — Valle del Lozoya",
            asset_type=AssetType.RECREATIONAL_AREA, region="Rascafría",
            ehs=85.0, risk_score=0.18, dcs=84.0,
            alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.46,
            visitor_capacity_annual=22_000, economic_importance=0.65,
            accessibility_score=0.85,
            elevation_m=1_120, area_ha=5.0,
            description=(
                "Centro de visitantes del PNSG en el valle del Lozoya. Excelente estado "
                "de conservación del entorno inmediato; jardín etnobotánico y sendas "
                "interpretativas accesibles. Capacidad de absorción real infrautilizada: "
                "nodo estratégico para redistribuir flujos desde Peñalara y Siete Picos."
            ),
        ),

    ]


# ── Registro de territorios ───────────────────────────────────────────────────
_TERRITORY_CONFIG: dict[str, dict] = {
    "snr": {
        "name":       "Reserva de la Biosfera Sierra del Rincón",
        "short":      "Sierra del Rincón",
        "budget":     100_000,
        "report_date": REPORT_DATE,
        "map_center": (41.130, -3.490, 11),
    },
    "pnsg": {
        "name":       "Parque Nacional Sierra de Guadarrama",
        "short":      "PN Sierra de Guadarrama",
        "budget":     150_000,
        "report_date": REPORT_DATE,
        "map_center": (40.820, -3.960, 10),
    },
}

_BUILD_FN = {
    "snr":  build_territory,
    "pnsg": build_pnsg_territory,
}


# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="SNTO — Inteligencia Territorial",
    page_icon="🏔",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "Smart Natural Tourism Observatory (SNTO) v0.1 · "
            "Plataforma de Inteligencia Estratégica de Destinos · "
            "Reserva de la Biosfera Sierra del Rincón, Madrid (España)"
        ),
    },
)

# ── Estilo institucional ──────────────────────────────────────────────────────
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] > .main { background: #f4f5f7; }

[data-testid="stSidebar"] { background: #1b2d42; }
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] hr {
    color: #c8d6e5 !important;
    border-color: #2e4560 !important;
}

/* ── TAREA 1: Contraste accesible en el selector de observatorio ──────── */
/* Opciones del st.radio — texto claro AA sobre fondo #1b2d42 */
[data-testid="stSidebar"] label[data-baseweb="radio"] p {
    color: #E0E6EE !important;
    font-size: 0.86rem !important;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] {
    padding: 5px 8px;
    border-radius: 6px;
    transition: background 0.15s ease;
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
    background: rgba(255,255,255,0.07);
}
/* Etiquetas de widgets, encabezados y negritas del sidebar */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] strong {
    color: #F2F6FA !important;
}
/* Selectbox y multiselect (futuras ampliaciones del sidebar) */
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #E0E6EE !important;
}

/* Fila informativa institucional del sidebar */
.snto-side-row {
    display: flex; align-items: center; gap: 8px;
    padding: 4px 0; font-size: 0.82rem; color: #c8d6e5;
}
.snto-side-row .snto-side-icon { width: 18px; text-align: center; flex-shrink: 0; }
.snto-side-row strong { color: #F2F6FA; }

.kpi-card {
    background: #ffffff;
    border-radius: 6px;
    padding: 1rem 1.1rem 0.9rem;
    margin-bottom: 0.2rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.kpi-meta  { font-size: 0.65rem; color: #9aa4af; text-transform: uppercase; letter-spacing: 0.08em; }
.kpi-name  { font-size: 0.82rem; color: #3d4a5c; font-weight: 600; margin: 0.15rem 0 0.45rem; }
.kpi-value { font-size: 1.45rem; font-weight: 700; color: #0d1b2a; line-height: 1.2; }
.kpi-badge {
    display: inline-block;
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.07em;
    padding: 0.2rem 0.6rem; border-radius: 3px; margin-top: 0.45rem;
}

/* Map legend chip */
.legend-chip {
    display: inline-block;
    width: 12px; height: 12px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
}

/* Live alert chips */
.snto-alert-chip {
    display: flex; align-items: flex-start; gap: 8px;
    padding: 9px 12px; border-radius: 7px; border: 1px solid;
    min-width: 180px; max-width: 270px; flex-shrink: 0;
}
.snto-alert-name { font-size: 0.80rem; font-weight: 700; color: #0d1b2a; line-height: 1.2; }
.snto-alert-sub  { font-size: 0.68rem; color: #7a8899; margin-top: 1px; }
.snto-alert-bar  {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 7px;
}
.snto-alert-title {
    font-size: 0.72rem; font-weight: 700; color: #7a8899;
    text-transform: uppercase; letter-spacing: 0.08em;
}
.snto-refresh-ts { font-size: 0.68rem; color: #9aa4af; }
.snto-pulse {
    display: inline-block; width: 7px; height: 7px;
    background: #22c55e; border-radius: 50%;
    margin-right: 5px; vertical-align: middle;
    animation: snto-pulse 1.8s infinite;
}
@keyframes snto-pulse {
    0%,100% { opacity:1; transform:scale(1); }
    50%      { opacity:0.35; transform:scale(0.8); }
}

/* Tier stat row in map hero */
.snto-tier-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 6px 10px; border-radius: 5px; background: #ffffff;
    border-left: 4px solid; margin-bottom: 5px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}

/* ── TAREA 1: Dynamic territory banner ──────────────────────────── */
.snto-banner {
    border-radius: 10px;
    padding: 18px 22px 14px;
    margin-bottom: 12px;
}
.snto-banner-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 12px; border-radius: 20px;
    font-size: 0.70rem; font-weight: 600; letter-spacing: 0.05em;
    margin-right: 6px; margin-bottom: 4px;
}
.snto-banner-title {
    font-size: 1.30rem; font-weight: 600; margin: 8px 0 3px; line-height: 1.25;
}
.snto-banner-sub { font-size: 0.76rem; }

/* ── TAREA 2: Executive KPI strip ───────────────────────────────── */
.exec-kpi {
    background: #ffffff;
    border-radius: 8px;
    padding: 12px 14px 10px;
    border-top: 3px solid;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
    height: 100%;
}
.exec-kpi-label {
    font-size: 0.66rem; color: #7a8899;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 4px;
}
.exec-kpi-value { font-size: 1.45rem; font-weight: 700; line-height: 1.15; }
.exec-kpi-delta { font-size: 0.69rem; margin-top: 4px; }

/* ── TAREA 3: Fichas de alerta rápida ───────────────────────────── */
.snto-ficha {
    background: #ffffff;
    border-radius: 7px;
    padding: 9px 12px;
    border-left: 4px solid;
    margin-bottom: 7px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.snto-ficha-name {
    font-size: 0.79rem; font-weight: 600; color: #0d1b2a;
    line-height: 1.3; clear: right;
}
.snto-ficha-meta { font-size: 0.67rem; color: #7a8899; margin-top: 1px; }
.snto-ficha-ehs {
    display: inline-block; font-size: 0.67rem; font-weight: 700;
    padding: 2px 6px; border-radius: 4px; float: right; margin-left: 8px;
}
.snto-ehs-bar {
    height: 3px; border-radius: 2px; background: #e8ecf0;
    margin-top: 5px; overflow: hidden;
}
.snto-ehs-fill { height: 100%; border-radius: 2px; }
.snto-panel-title {
    font-size: 0.67rem; font-weight: 600; color: #7a8899;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 8px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Paleta de estados ─────────────────────────────────────────────────────────
_COLOR = {"GREEN": "#2e7d32", "AMBER": "#e65100", "RED": "#c62828", "BLUE": "#1565c0"}
_BG    = {"GREEN": "#e8f5e9", "AMBER": "#fff3e0", "RED": "#ffebee", "BLUE": "#e3f2fd"}
_EMOJI = {"GREEN": "🟢",      "AMBER": "🟡",      "RED": "🔴",      "BLUE": "🔵"}

_TIER_BADGE_COLOR = {
    1: ("#dc3232", "#ffebee"),
    2: ("#e68214", "#fff3e0"),
    3: ("#3278c8", "#e3f2fd"),
    4: ("#28aa50", "#e8f5e9"),
}
_ASSET_TYPE_EMOJI = {
    "TRAIL":             "🥾",
    "VIEWPOINT":         "🔭",
    "RECREATIONAL_AREA": "🌿",
    "NATURAL_PARK":      "🌲",
    "CYCLING_ROUTE":     "🚴",
}


# ── Pipeline con caché ────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Calculando inteligencia territorial…")
def load_dashboard(territory_key: str):
    """Return (dashboard, assets, comps, assets_by_id, base_budget, cfg) — cached per territory."""
    cfg    = _TERRITORY_CONFIG[territory_key]
    raw    = _BUILD_FN[territory_key]()
    assets = rank_assets(raw)
    by_id  = {a.asset_id: a for a in assets}
    max_v  = max(a.visitor_capacity_annual for a in assets)
    comps  = [compare_scenarios(a, max_v) for a in assets]
    budget = allocate_tis_budget(comps, by_id, cfg["budget"])
    dash   = compute_executive_dashboard(
        territory_name=cfg["name"],
        report_date=cfg["report_date"],
        assets=assets,
        budget_result=budget,
        comparisons=comps,
    )
    return dash, assets, comps, by_id, budget, cfg


# ── Renderizador de alertas en vivo ──────────────────────────────────────────
_ALERT_META: dict[str, tuple[str, str, str, str]] = {
    # level: (icon, label, bg, border)
    "CRITICAL_INTERVENTION": ("🔴", "Intervención Crítica",  "#fff5f5", "#feb2b2"),
    "URGENT_MONITORING":     ("🟡", "Monitorización Urgente","#fffbeb", "#fde68a"),
    "PREVENTIVE_ACTION":     ("🔵", "Acción Preventiva",     "#eff6ff", "#bfdbfe"),
}
_ALERT_SEVERITY = {
    "CRITICAL_INTERVENTION": 0,
    "URGENT_MONITORING":     1,
    "PREVENTIVE_ACTION":     2,
}

def _render_live_alerts(assets: list, refresh_count: int) -> None:
    active = sorted(
        [a for a in assets if a.alert_level in _ALERT_META],
        key=lambda a: _ALERT_SEVERITY[a.alert_level],
    )
    if not active:
        st.success("✅ Sin alertas activas en este territorio.", icon="🌿")
        return

    chips = ""
    for a in active[:8]:
        icon, label, bg, border = _ALERT_META[a.alert_level]
        name = a.name.split("—")[0].strip()[:30]
        chips += (
            f'<div class="snto-alert-chip" style="background:{bg};border-color:{border};">'
            f'  <span style="font-size:15px;line-height:1.3">{icon}</span>'
            f'  <div>'
            f'    <div class="snto-alert-name">{name}</div>'
            f'    <div class="snto-alert-sub">EHS {a.ehs:.0f} · {a.region} · {label}</div>'
            f'  </div>'
            f'</div>'
        )

    ts = datetime.datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f'<div class="snto-alert-bar">'
        f'  <span class="snto-alert-title">'
        f'    <span class="snto-pulse"></span>'
        f'    {len(active)} alerta{"s" if len(active) != 1 else ""} activa{"s" if len(active) != 1 else ""}'
        f'  </span>'
        f'  <span class="snto-refresh-ts">Actualizado: {ts} · ciclo #{refresh_count}</span>'
        f'</div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;padding-bottom:4px;">{chips}</div>',
        unsafe_allow_html=True,
    )


# ── TAREA 1: Configuración de banners dinámicos ──────────────────────────────
_BANNER_CFG: dict[str, dict] = {
    "snr": {
        "bg":          "#0d2818",
        "main_badge":  ("🌿", "Reserva de la Biosfera · UNESCO MAB", "#0F6E56", "#9FE1CB"),
        "extra_badge": None,
        "text_color":  "#E1F5EE",
        "sub_color":   "#5DCAA5",
    },
    "pnsg": {
        "bg":          "#0d1e3a",
        "main_badge":  ("⛰️", "Parque Nacional · Red de Parques Nacionales", "#185FA5", "#B5D4F4"),
        "extra_badge": ("⚠️", "Alta presión antrópica", "#EF9F27", "#412402"),
        "text_color":  "#E6F1FB",
        "sub_color":   "#85B7EB",
    },
}

# Simulated cycle-over-cycle deltas — directionally realistic for demo data
_EXEC_DELTAS: dict[str, dict] = {
    "snr":  {"ehs": -3.1, "tis": -1.8, "deuda": 12_000,  "jobs": 0.6},
    "pnsg": {"ehs": -5.3, "tis": -4.1, "deuda": 68_000,  "jobs": 2.1},
}


def _render_banner(key: str, cfg: dict, dashboard, n_red: int, n_amb: int) -> None:
    bc = _BANNER_CFG[key]
    icon_m, text_m, bg_m, fg_m = bc["main_badge"]
    main_badge = (
        f'<span class="snto-banner-badge" style="background:{bg_m};color:{fg_m};">'
        f'{icon_m} {text_m}</span>'
    )
    extra_badge = ""
    if bc["extra_badge"]:
        icon_e, text_e, bg_e, fg_e = bc["extra_badge"]
        extra_badge = (
            f'<span class="snto-banner-badge" style="background:{bg_e};color:{fg_e};">'
            f'{icon_e} {text_e}</span>'
        )
    if n_red >= 1:
        status_html = (
            f'<span style="color:#ff6b6b;font-size:0.77rem;">'
            f'⚠ {n_red} alerta(s) crítica(s)</span>'
        )
    elif n_amb >= 1:
        status_html = (
            f'<span style="color:#ffd97d;font-size:0.77rem;">'
            f'◉ {n_amb} indicador(es) en atención</span>'
        )
    else:
        status_html = (
            '<span style="color:#6ee7b7;font-size:0.77rem;">✓ Sin alertas críticas</span>'
        )
    st.markdown(
        f'<div class="snto-banner" style="background:{bc["bg"]};">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:6px;">'
        f'<div>{main_badge}{extra_badge}</div>'
        f'<div>{status_html}</div>'
        f'</div>'
        f'<div class="snto-banner-title" style="color:{bc["text_color"]};">'
        f'{dashboard.territory_name}</div>'
        f'<div class="snto-banner-sub" style="color:{bc["sub_color"]};">'
        f'Plataforma SNTO · Informe estratégico · {dashboard.report_date} · '
        f'{dashboard.n_assets} activos monitorizados · '
        f'Presupuesto base: €{cfg["budget"]:,}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── TAREA 2: Executive KPI strip ─────────────────────────────────────────────
def _compute_exec_kpis(ranked_assets, base_budget, assets_by_id) -> dict:
    ehs_medio = sum(a.ehs for a in ranked_assets) / len(ranked_assets)
    tis_portfolio = base_budget.portfolio_tis
    _base_funded = {it.asset_id for it in base_budget.funded_items}

    deuda = sum(
        item.cost_eur for item in base_budget.deferred_items
        if item.asset_id in assets_by_id
        and (assets_by_id[item.asset_id].tier or 0) <= 2
    )
    for item in base_budget.funded_items:
        a = assets_by_id.get(item.asset_id)
        if a and (a.tier or 0) == 1:
            deuda += item.cost_eur * 0.15

    _spend = 22.50
    _jobs_per = 2_500
    _risk = {1: 1.00, 2: 0.40}
    total_jobs_risk = 0.0
    for a in ranked_assets:
        t = a.tier or 0
        if t not in _risk:
            continue
        rf = _risk[t] if a.asset_id not in _base_funded else _risk[t] * 0.15
        total_jobs_risk += (a.visitor_capacity_annual / _jobs_per) * rf

    return {
        "ehs_medio":    ehs_medio,
        "tis_portfolio": tis_portfolio,
        "deuda_eur":    deuda,
        "jobs_risk":    total_jobs_risk,
    }


def _render_exec_kpis(kpis_data: dict, selected_key: str) -> None:
    ehs  = kpis_data["ehs_medio"]
    tis  = kpis_data["tis_portfolio"]
    deuda = kpis_data["deuda_eur"]
    jobs  = kpis_data["jobs_risk"]
    d = _EXEC_DELTAS.get(selected_key, {"ehs": -2.0, "tis": -1.0, "deuda": 5_000, "jobs": 0.2})

    def _delta_html(val: float, *, positive_is_bad: bool) -> str:
        is_bad = (val > 0) if positive_is_bad else (val < 0)
        color  = "#A32D2D" if is_bad else "#3B6D11"
        arrow  = "▲" if val > 0 else "▼"
        sign   = "+" if val > 0 else ""
        return (
            f'<span style="color:{color}">'
            f'{arrow} {sign}{val:g} vs ciclo anterior</span>'
        )

    ehs_color = "#0F6E56" if ehs >= 65 else ("#EF9F27" if ehs >= 50 else "#A32D2D")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f'<div class="exec-kpi" style="border-top-color:{ehs_color};">'
            f'<div class="exec-kpi-label">Salud ecológica media</div>'
            f'<div class="exec-kpi-value" style="color:{ehs_color}">'
            f'{ehs:.1f}<span style="font-size:0.85rem;color:#9aa4af">/100</span></div>'
            f'<div class="exec-kpi-delta">{_delta_html(d["ehs"], positive_is_bad=False)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="exec-kpi" style="border-top-color:#185FA5;">'
            f'<div class="exec-kpi-label">TIS portfolio</div>'
            f'<div class="exec-kpi-value" style="color:#185FA5">{tis:.1f}</div>'
            f'<div class="exec-kpi-delta">{_delta_html(d["tis"], positive_is_bad=False)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="exec-kpi" style="border-top-color:#854F0B;">'
            f'<div class="exec-kpi-label">Deuda ecológica acumulada</div>'
            f'<div class="exec-kpi-value" style="color:#854F0B">€{deuda:,.0f}</div>'
            f'<div class="exec-kpi-delta">{_delta_html(d["deuda"], positive_is_bad=True)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="exec-kpi" style="border-top-color:#A32D2D;">'
            f'<div class="exec-kpi-label">Empleos locales en riesgo</div>'
            f'<div class="exec-kpi-value" style="color:#A32D2D">{jobs:.1f}</div>'
            f'<div class="exec-kpi-delta">{_delta_html(d["jobs"], positive_is_bad=True)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── TAREA 3: Fichas de alerta rápida (map hero right panel) ─────────────────
def _render_fichas_rapidas(ranked_assets: list) -> None:
    top3 = [a for a in ranked_assets if (a.tier or 5) <= 2][:3]
    if not top3:
        top3 = ranked_assets[:3]

    st.markdown(
        '<div class="snto-panel-title">Priorización de Activos Turísticos Críticos</div>',
        unsafe_allow_html=True,
    )
    for a in top3:
        fg, bg = _TIER_BADGE_COLOR.get(a.tier or 1, ("#E24B4A", "#FCEBEB"))
        name_short = a.name.split("—")[0].strip()
        ehs_w = max(2, int(a.ehs))
        vis   = f"{a.visitor_capacity_annual:,}"
        st.markdown(
            f'<div class="snto-ficha" style="border-left-color:{fg};">'
            f'<span class="snto-ficha-ehs" style="background:{bg};color:{fg};">'
            f'EHS {a.ehs:.0f}</span>'
            f'<div class="snto-ficha-name">{name_short}</div>'
            f'<div class="snto-ficha-meta">{a.region} · {vis} visit./año</div>'
            f'<div class="snto-ehs-bar">'
            f'<div class="snto-ehs-fill" style="width:{ehs_w}%;background:{fg};"></div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    # Visitor count summary below fichas
    _visitors_t12 = sum(
        a.visitor_capacity_annual for a in ranked_assets if (a.tier or 5) <= 2
    )
    st.markdown(
        f'<div style="margin-top:6px;padding:8px 10px;background:#fff8f0;'
        f'border-radius:6px;border-left:3px solid #EF9F27;">'
        f'<div style="font-size:0.65rem;color:#854F0B;text-transform:uppercase;'
        f'letter-spacing:0.06em">Capacidad de carga antrópica comprometida (Tier 1+2)</div>'
        f'<div style="font-size:1.25rem;font-weight:700;color:#A32D2D">'
        f'{_visitors_t12:,}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── TAREA 2: Drill-down por KPI ──────────────────────────────────────────────
# Mapa nº de KPI → filtro sobre los activos clasificados. El motor de
# dashboard.py no se modifica: cada filtro replica el criterio documentado
# en technical_basis del propio KPI.
_KPI_DRILLDOWN = {
    2:  lambda assets: sorted(
            [a for a in assets if a.tier in (1, 2)],
            key=lambda a: (a.tier, -(a.tpi or 0))),
    3:  lambda assets: sorted(
            [a for a in assets if a.tier in (1, 2)],
            key=lambda a: -a.visitor_capacity_annual),
    4:  "backlog",   # orden por inversión de mitigación descendente (deuda ecológica)
    7:  lambda assets: sorted(
            [a for a in assets
             if a.scm_classification == "LOCALIZED_IMPACT" and a.tier in (1, 2)],
            key=lambda a: -(a.tpi or 0)),
    9:  lambda assets: sorted(
            [a for a in assets if a.trend_direction == "decreasing"],
            key=lambda a: a.ehs),
    10: lambda assets: sorted(
            [a for a in assets if a.dcs < 55],
            key=lambda a: a.dcs),
}

_KPI_DRILLDOWN_CAPTION = {
    2:  "Sendas y enclaves que requieren intervención financiera inmediata o preventiva, ordenados por prioridad territorial (TPI).",
    3:  "Capacidad de carga antrópica comprometida: activos Tier 1-2 ordenados por presión de visitantes.",
    4:  "Deuda ecológica por activo: la inversión de mitigación pendiente justifica administrativamente la priorización del presupuesto público.",
    7:  "Activos con degradación causada por presión antrópica confirmada (clasificación causal SCM: impacto localizado).",
    9:  "Activos en trayectoria de degradación activa (tendencia Mann-Kendall decreciente).",
    10: "Activos sin evidencia suficiente (DCS < 55): requieren refuerzo de monitorización antes de comprometer inversión de capital.",
}

_ALERT_LABEL_ES = {
    "CRITICAL_INTERVENTION": "🔴 Intervención crítica",
    "URGENT_MONITORING":     "🟡 Monitorización urgente",
    "PREVENTIVE_ACTION":     "🔵 Acción preventiva",
    "NORMAL":                "🟢 Normal",
}


def _render_kpi_drilldown(kpi, ranked_assets: list, cost_by_id: dict) -> None:
    """Tabla de drill-down con los activos que componen el indicador."""
    import pandas as pd

    spec = _KPI_DRILLDOWN.get(kpi.number)
    if spec is None:
        return

    if spec == "backlog":
        rows_src = sorted(
            [a for a in ranked_assets if a.tier in (1, 2)],
            key=lambda a: -cost_by_id.get(a.asset_id, 0),
        )
    else:
        rows_src = spec(ranked_assets)

    if not rows_src:
        st.caption("Sin activos afectados por este indicador en el ciclo actual.")
        return

    st.markdown("**Desglose de activos afectados**")
    st.caption(_KPI_DRILLDOWN_CAPTION.get(kpi.number, ""))
    df = pd.DataFrame([
        {
            "Senda / Activo":   a.name,
            "Municipio":        a.region,
            "EHS":              round(a.ehs, 0),
            "Estado de alerta": _ALERT_LABEL_ES.get(a.alert_level, a.alert_level),
            "Presión (visit./año)": a.visitor_capacity_annual,
            "Inversión de mitigación (€)": cost_by_id.get(a.asset_id, 0),
        }
        for a in rows_src
    ])
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "EHS": st.column_config.ProgressColumn(
                "EHS", min_value=0, max_value=100, format="%.0f"),
            "Presión (visit./año)": st.column_config.NumberColumn(format="%d"),
            "Inversión de mitigación (€)": st.column_config.NumberColumn(format="€%d"),
        },
    )


# ── Renderizador de tarjeta KPI ───────────────────────────────────────────────
def render_kpi_card(kpi, ranked_assets: list | None = None,
                    cost_by_id: dict | None = None) -> None:
    color = _COLOR[kpi.status]
    bg    = _BG[kpi.status]
    emoji = _EMOJI[kpi.status]
    st.markdown(
        f"""<div class="kpi-card" style="border-left:5px solid {color};">
  <div class="kpi-meta">KPI {kpi.number}</div>
  <div class="kpi-name">{kpi.name}</div>
  <div class="kpi-value">{kpi.value}</div>
  <span class="kpi-badge" style="color:{color};background:{bg};">{emoji}&thinsp;{kpi.status_label}</span>
</div>""",
        unsafe_allow_html=True,
    )
    has_drilldown = kpi.number in _KPI_DRILLDOWN and ranked_assets is not None
    label = ("Interpretación, acción recomendada y desglose de activos"
             if has_drilldown else "Interpretación y acción recomendada")
    with st.expander(label):
        st.markdown(f"**¿Qué significa?** {kpi.what_it_means}")
        st.markdown(f"**Acción recomendada:** _{kpi.recommended_action}_")
        st.caption(f"Base técnica SNTO: {kpi.technical_basis}")
        if has_drilldown:
            st.divider()
            _render_kpi_drilldown(kpi, ranked_assets, cost_by_id or {})


# ── Selector de territorio (primer bloque de barra lateral) ──────────────────
with st.sidebar:
    st.markdown("## 🏔 SNTO")
    st.markdown("**Plataforma de Inteligencia  \nEstratégica de Destinos**")
    st.divider()
    st.markdown("**Observatorio activo**")
    selected_key = st.radio(
        "Territorio activo",
        options=list(_TERRITORY_CONFIG.keys()),
        format_func=lambda k: _TERRITORY_CONFIG[k]["short"],
        label_visibility="collapsed",
    )
    st.divider()

# ── Cargar datos ──────────────────────────────────────────────────────────────
dashboard, ranked_assets, base_comps, assets_by_id, base_budget, _terr_cfg = load_dashboard(selected_key)
BUDGET_EUR = _terr_cfg["budget"]

n_red = sum(1 for k in dashboard.kpis if k.status == "RED")
n_amb = sum(1 for k in dashboard.kpis if k.status == "AMBER")
n_ok  = sum(1 for k in dashboard.kpis if k.status in ("GREEN", "BLUE"))

# ── Resto de la barra lateral ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div class="snto-side-row"><span class="snto-side-icon">🏛️</span>'
        f'<span><strong>Territorio</strong><br/>{dashboard.territory_name}</span></div>'
        f'<div class="snto-side-row"><span class="snto-side-icon">📅</span>'
        f'<span><strong>Fecha de informe</strong><br/>{dashboard.report_date}</span></div>'
        f'<div class="snto-side-row"><span class="snto-side-icon">🗂️</span>'
        f'<span><strong>Activos monitorizados</strong><br/>{dashboard.n_assets} '
        f'sendas y enclaves</span></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**Panel de alertas**")
    if n_red:
        st.markdown(f"🔴 **{n_red}** indicador(es) crítico(s)")
    if n_amb:
        st.markdown(f"🟡 **{n_amb}** indicador(es) en atención")
    if n_ok:
        st.markdown(f"🟢 **{n_ok}** indicador(es) normal / óptimo")
    st.divider()
    # ── Map legend ────────────────────────────────────────────────────────────
    st.markdown("**Leyenda del mapa**")
    for item in LEGEND_ITEMS:
        st.markdown(
            f'<span class="legend-chip" style="background:{item["hex"]}"></span>'
            f'<small>{item["label"]}</small>',
            unsafe_allow_html=True,
        )
    st.divider()
    st.caption("SNTO v0.1 · Datos sintéticos de validación")
    st.caption(f"Piloto activo: {_terr_cfg['short']} (Madrid)")


# ── TAREA 1: Banner dinámico con contextual badging ──────────────────────────
_render_banner(selected_key, _terr_cfg, dashboard, n_red, n_amb)

# ── Autorefresh: recarga la app cada 60 s (simula polling de datos en vivo) ───
_refresh_count = st_autorefresh(interval=60_000, limit=None, key=f"live_{selected_key}")

# ── Barra de alertas en vivo ──────────────────────────────────────────────────
_alerts_placeholder = st.empty()
with _alerts_placeholder.container():
    _render_live_alerts(ranked_assets, _refresh_count)

# ── TAREA 2: Tira de 4 KPIs ejecutivos ───────────────────────────────────────
_exec_kpis = _compute_exec_kpis(ranked_assets, base_budget, assets_by_id)
_render_exec_kpis(_exec_kpis, selected_key)

st.divider()

# ── TAREA 3: Split-screen 60 % mapa / 40 % fichas de alerta ──────────────────
st.markdown(
    '<div style="font-size:0.70rem;font-weight:600;color:#7a8899;'
    'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px">'
    'Vista territorial en vivo · Control de senderos vulnerables</div>',
    unsafe_allow_html=True,
)
_map_col, _stats_col = st.columns([3, 2], gap="medium")

with _stats_col:
    _render_fichas_rapidas(ranked_assets)

with _map_col:
    _mc = _terr_cfg["map_center"]
    try:
        _hero_deck = build_pydeck_deck(
            ranked_assets, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2]
        )
        st.pydeck_chart(_hero_deck, use_container_width=True, height=420)
    except ImportError:
        st.error("pydeck no instalado — `pip install pydeck`", icon="⚠️")
    st.caption(
        "🗂️ Vista de Gestión · Colores por tier de prioridad · Trazado de sendas "
        "aproximado (integración PostGIS pendiente) · "
        "Para diagnóstico espectral NDVI/NDMI → pestaña **Mapa territorial**"
    )

st.divider()

# ── TAREA 4: Suite de módulos analíticos ──────────────────────────────────────
st.markdown(
    '<div style="font-size:0.70rem;font-weight:600;color:#7a8899;'
    'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px">'
    'Módulos de análisis estratégico</div>',
    unsafe_allow_html=True,
)
(tab_kpis, tab_portfolio, tab_timeseries, tab_simulator, tab_socioeco,
 tab_map, tab_assets, tab_real) = st.tabs([
    "Indicadores",
    "Portafolio TPI",
    "Series espectrales",
    "Simulador financiero",
    "Impacto socioecon.",
    "Mapa territorial",
    "Catálogo de activos",
    "🛰 Sendas reales (satélite)",
])


# ── Tab 1: KPIs ───────────────────────────────────────────────────────────────
with tab_kpis:
    st.subheader("Panel de Indicadores Estratégicos · Gobernanza Inteligente del Territorio")
    st.caption(
        "Cada indicador responde a una pregunta de gestión pública concreta. "
        "Despliega cada tarjeta para ver la interpretación, la acción recomendada "
        "y el desglose de sendas afectadas (drill-down por indicador)."
    )

    # Coste de mitigación recomendado por activo (escenario óptimo TIS, Fase 6)
    _cost_by_id = {
        c.asset_id: c.scenarios[c.best_scenario_code].cost_eur
        for c in base_comps
    }

    kpis = dashboard.kpis
    for row_start in range(0, len(kpis), 4):
        row_kpis = kpis[row_start : row_start + 4]
        cols = st.columns(4)
        for i, kpi in enumerate(row_kpis):
            with cols[i]:
                render_kpi_card(kpi, ranked_assets, _cost_by_id)
        st.write("")


# ── Tab 2: Portafolio TPI ─────────────────────────────────────────────────────
with tab_portfolio:
    st.subheader("Matriz de Portafolio TPI — Priorización de Activos Turísticos Críticos")
    st.caption(
        "Cada activo se posiciona según su capacidad de carga antrópica (eje X) y su riesgo "
        "ecológico (eje Y = 100 − EHS). El tamaño del punto refleja la importancia económica "
        "del activo. Los cuadrantes delimitan las cuatro estrategias de gestión del modelo SNTO: "
        "la matriz fundamenta de forma objetiva qué sendas requieren intervención financiera inmediata."
    )

    try:
        portfolio_fig = build_portfolio_matrix(ranked_assets)
        st.plotly_chart(portfolio_fig, use_container_width=True)
    except Exception as _e:
        st.error(f"Error al renderizar la matriz: {_e}", icon="⚠️")

    # ── Tabla resumen debajo del gráfico ──────────────────────────────────────
    with st.expander("📋 Datos del portafolio (tabla completa)", expanded=False):
        import pandas as pd  # ya disponible en el entorno
        max_v = max(a.visitor_capacity_annual for a in ranked_assets) or 1
        table_rows = [
            {
                "Activo":          a.name,
                "Región":          a.region,
                "Tier":            a.tier,
                "EHS":             round(a.ehs, 1),
                "Riesgo (100−EHS)": round(100 - a.ehs, 1),
                "Presión (norm.)":  round(a.visitor_capacity_annual / max_v * 100, 1),
                "Visitantes/año":  a.visitor_capacity_annual,
                "DCS":             round(a.dcs, 1),
                "TPI":             round(a.tpi, 1) if a.tpi is not None else None,
                "Imp. Econ.":      f"{a.economic_importance:.0%}",
            }
            for a in ranked_assets
        ]
        df_table = pd.DataFrame(table_rows).sort_values("TPI", ascending=False)
        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "EHS":             st.column_config.ProgressColumn(
                    "EHS", min_value=0, max_value=100, format="%.0f"),
                "Riesgo (100−EHS)": st.column_config.ProgressColumn(
                    "Riesgo Ecol.", min_value=0, max_value=100, format="%.0f"),
                "TPI":             st.column_config.NumberColumn("TPI", format="%.1f"),
            },
        )


# ── Tab 3: Series Temporales Espectrales ─────────────────────────────────────
with tab_timeseries:
    st.subheader("Series Temporales Espectrales — NDVI / NDMI por Activo")
    st.caption(
        "Selecciona un activo para visualizar su evolución espectral mensual. "
        "Las bandas rojas marcan períodos de estrés hídrico crítico (Z-score NDVI < −1,5), "
        "donde la sequía coincide con el sobreuso turístico documentado."
    )

    # ── Selector de activo ────────────────────────────────────────────────────
    _TIER_PREFIX = {1: "🔴 T1", 2: "🟡 T2", 3: "🔵 T3", 4: "🟢 T4"}

    def _asset_label(a) -> str:
        prefix = _TIER_PREFIX.get(a.tier, "⚪")
        return f"{prefix} · {a.name} ({a.region})"

    asset_names   = [_asset_label(a) for a in ranked_assets]
    asset_by_label = {_asset_label(a): a for a in ranked_assets}

    col_sel, col_range = st.columns([3, 1])
    with col_sel:
        selected_label = st.selectbox(
            "Activo a analizar",
            options=asset_names,
            index=0,
            help="Los activos se muestran ordenados por TPI descendente (mayor urgencia primero).",
        )
    with col_range:
        n_months = st.select_slider(
            "Ventana temporal",
            options=[12, 24, 36],
            value=24,
            format_func=lambda v: f"{v} meses",
        )

    selected_asset = asset_by_label[selected_label]

    # ── KPI rápido del activo seleccionado ────────────────────────────────────
    tier = selected_asset.tier or 0
    fg, bg = _TIER_BADGE_COLOR.get(tier, ("#555", "#eee"))
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {fg};">'
            f'<div class="kpi-meta">EHS</div>'
            f'<div class="kpi-value" style="color:{fg}">{selected_asset.ehs:.0f}<span style="font-size:.9rem;color:#9aa4af">/100</span></div>'
            f'</div>', unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {fg};">'
            f'<div class="kpi-meta">DCS</div>'
            f'<div class="kpi-value">{selected_asset.dcs:.0f}<span style="font-size:.9rem;color:#9aa4af">/100</span></div>'
            f'</div>', unsafe_allow_html=True)
    with kpi_cols[2]:
        tpi_val = f"{selected_asset.tpi:.0f}" if selected_asset.tpi else "—"
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {fg};">'
            f'<div class="kpi-meta">TPI</div>'
            f'<div class="kpi-value">{tpi_val}</div>'
            f'</div>', unsafe_allow_html=True)
    with kpi_cols[3]:
        vis = f"{selected_asset.visitor_capacity_annual:,}"
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {fg};">'
            f'<div class="kpi-meta">Visitantes/año</div>'
            f'<div class="kpi-value">{vis}</div>'
            f'</div>', unsafe_allow_html=True)

    st.write("")

    # ── Gráfico de series temporales ──────────────────────────────────────────
    try:
        ts_fig = build_time_series_chart(selected_asset, n_months=n_months)
        st.plotly_chart(ts_fig, use_container_width=True)
    except Exception as _e:
        st.error(f"Error al renderizar el gráfico: {_e}", icon="⚠️")

    # ── Nota metodológica ─────────────────────────────────────────────────────
    with st.expander("ℹ️ Nota metodológica sobre la simulación", expanded=False):
        st.markdown(
            f"""
**Base de la simulación:** El Pipeline A de SNTO computa un EHS compuesto por activo.
La serie mensual mostrada es una simulación coherente con la ecología real de la sierra:

- **Línea verde (NDVI):** Índice de Vegetación de Diferencia Normalizada. Pico en mayo
  (brotación del haya), mínimo en enero-febrero (senescencia). Rango calibrado para
  vegetación caducifolia de montaña en el Sistema Central (0.15 – 0.82).

- **Línea azul punteada (NDMI):** Índice de Humedad de Diferencia Normalizada. Desfase
  de ~1 mes respecto al NDVI; refleja la respuesta del contenido hídrico foliar al ciclo
  de lluvias primaverales y la sequía estival.

- **Bandas rojas (Anomalías):** Meses donde el Z-score del NDVI es < −1.5.
  Umbral estándar para estrés hídrico moderado-severo en la monitorización de
  la cubierta vegetal mediterránea. Activos **Tier 1-2 con EHS < 60** muestran una
  depresión adicional en julio-agosto que modela la co-ocurrencia de sequía y
  sobreuso turístico documentada en los informes de campo de la reserva.

- **Activo seleccionado — {selected_asset.name}:** EHS = {selected_asset.ehs:.0f},
  Tier {selected_asset.tier}. Los datos son sintéticos de validación; la integración
  con datos reales Sentinel-2 se realiza a través del módulo `src/ingestion/gee_adapter.py`.
            """
        )


# ── Tab 4: Simulador Financiero What-If ──────────────────────────────────────
with tab_simulator:
    import pandas as pd

    st.subheader("Simulador Financiero — Mitigación de Impacto en Ecosistemas Vulnerables")
    st.caption(
        "Ajusta el presupuesto público disponible y observa en tiempo real qué sendas "
        "entran o salen del plan de mitigación y cuánta capacidad de carga antrópica "
        "anual queda protegida frente al riesgo de degradación. La asignación se "
        "optimiza por TIS con verificación de evidencia (DCS Gate)."
    )

    # ── Slider de presupuesto ─────────────────────────────────────────────────
    sim_budget = st.slider(
        "Presupuesto de Conservación Disponible (€)",
        min_value=10_000,
        max_value=300_000,
        value=100_000,
        step=10_000,
        format="€%d",
    )

    # ── Recalcular asignación en tiempo real (sin caché) ──────────────────────
    live_budget = allocate_tis_budget(base_comps, assets_by_id, sim_budget)

    # Conjuntos de IDs financiados en el escenario base (100K) y en el live
    base_funded_ids = {item.asset_id for item in base_budget.funded_items}
    live_funded_ids = {item.asset_id for item in live_budget.funded_items}

    # Activos que GANAN financiación respecto al base
    newly_funded_ids   = live_funded_ids - base_funded_ids
    # Activos que PIERDEN financiación respecto al base
    defunded_ids       = base_funded_ids - live_funded_ids

    visitors_protected = sum(
        a.visitor_capacity_annual for a in ranked_assets
        if a.asset_id in live_funded_ids
    )
    visitors_gained = sum(
        a.visitor_capacity_annual for a in ranked_assets
        if a.asset_id in newly_funded_ids
    )
    visitors_lost = sum(
        a.visitor_capacity_annual for a in ranked_assets
        if a.asset_id in defunded_ids
    )

    # ── KPI gigante — Visitantes Protegidos ───────────────────────────────────
    delta_sign  = "+" if visitors_gained >= visitors_lost else ""
    delta_val   = visitors_gained - visitors_lost
    delta_color = "#2e7d32" if delta_val >= 0 else "#c62828"
    delta_text  = f"{delta_sign}{delta_val:,} vs €100K base"

    st.markdown(
        f"""
<div class="kpi-card" style="border-left:6px solid #1565c0;padding:1.4rem 1.5rem;">
  <div class="kpi-meta">KPI Principal · Simulador Financiero</div>
  <div class="kpi-name" style="font-size:1rem;">
      Capacidad de Visitantes Protegida / Salvada del Riesgo
  </div>
  <div style="display:flex;align-items:baseline;gap:1rem;margin-top:0.3rem;">
    <div class="kpi-value" style="font-size:2.2rem;color:#1565c0">
        {visitors_protected:,}
        <span style="font-size:1rem;font-weight:400;color:#9aa4af"> visit./año</span>
    </div>
    <div style="font-size:1rem;font-weight:700;color:{delta_color}">
        {delta_text}
    </div>
  </div>
  <div style="font-size:0.78rem;color:#7a8899;margin-top:0.5rem;">
      Suma de <code>visitor_capacity_annual</code> de todos los activos financiados
      con el presupuesto seleccionado · Base de referencia: €100,000
  </div>
</div>""",
        unsafe_allow_html=True,
    )
    st.write("")

    # ── KPIs secundarios ──────────────────────────────────────────────────────
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    kpi_data = [
        (s_col1, "Presupuesto Asignado",  f"€{live_budget.total_allocated_eur:,}",
         "#1565c0", "#e3f2fd"),
        (s_col2, "Presupuesto Restante",  f"€{live_budget.remaining_eur:,}",
         "#2e7d32" if live_budget.remaining_eur > 0 else "#c62828",
         "#e8f5e9" if live_budget.remaining_eur > 0 else "#ffebee"),
        (s_col3, "Activos Financiados",
         f"{len(live_budget.funded_items)} / {len(ranked_assets)}",
         "#e65100", "#fff3e0"),
        (s_col4, "TIS Medio Portafolio",  f"{live_budget.portfolio_tis:.1f}",
         "#4a148c", "#f3e5f5"),
    ]
    for col, name, val, fg, bg in kpi_data:
        with col:
            st.markdown(
                f'<div class="kpi-card" style="border-left:4px solid {fg};">'
                f'<div class="kpi-meta">{name}</div>'
                f'<div class="kpi-value" style="color:{fg};font-size:1.5rem">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.write("")

    # ── Gráfico de asignación ─────────────────────────────────────────────────
    import plotly.graph_objects as go

    # Construir DataFrame con todos los activos y su estado de financiación
    sim_rows = []
    all_items = {item.asset_id: item for item in live_budget.funded_items + live_budget.deferred_items}
    for a in ranked_assets:
        item = all_items.get(a.asset_id)
        if item is None:
            continue
        sim_rows.append({
            "Activo":    a.name.split("—")[0].strip()[:32],
            "Coste (€)": item.cost_eur,
            "TIS":       round(item.tis, 1),
            "Tier":      a.tier,
            "Financiado": item.funded,
            "color":     "#2e7d32" if item.funded else "#c62828",
            "alpha":     0.85 if item.funded else 0.5,
        })

    sim_df = pd.DataFrame(sim_rows).sort_values("TIS", ascending=True)

    bar_fig = go.Figure()
    for funded_flag, label, color, opacity in [
        (True,  "Financiado ✅", "#2e7d32", 0.85),
        (False, "Diferido ❌",   "#c62828", 0.55),
    ]:
        sub = sim_df[sim_df["Financiado"] == funded_flag]
        if sub.empty:
            continue
        bar_fig.add_trace(go.Bar(
            y=sub["Activo"],
            x=sub["Coste (€)"],
            name=label,
            orientation="h",
            marker=dict(color=color, opacity=opacity,
                        line=dict(width=0.8, color="white")),
            text=sub["TIS"].apply(lambda t: f"TIS {t}"),
            textposition="inside",
            insidetextfont=dict(color="white", size=10),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Coste: €%{x:,}<br>"
                "TIS: %{text}<extra></extra>"
            ),
        ))

    bar_fig.update_layout(
        title=dict(
            text=f"Asignación presupuestaria · €{sim_budget:,} disponibles",
            font=dict(size=13, color="#0d1b2a"), x=0.0,
        ),
        xaxis=dict(
            title="Coste de Intervención (€)",
            tickprefix="€", showgrid=True,
            gridcolor="rgba(180,190,200,0.3)",
        ),
        yaxis=dict(automargin=True),
        barmode="stack",
        legend=dict(orientation="h", y=1.05, x=0),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=40),
        height=max(300, len(sim_df) * 30 + 80),
        hoverlabel=dict(bgcolor="#1b2d42", font_color="white",
                        font_size=12, bordercolor="#2e4560"),
    )
    try:
        st.plotly_chart(bar_fig, use_container_width=True)
    except Exception as _e:
        st.error(f"Error al renderizar el gráfico: {_e}", icon="⚠️")

    # ── Tabla detallada ───────────────────────────────────────────────────────
    with st.expander("📋 Detalle completo de la asignación", expanded=False):
        detail_rows = []
        for item in sorted(
            live_budget.funded_items + live_budget.deferred_items,
            key=lambda x: (-x.tis, x.tier),
        ):
            a = assets_by_id[item.asset_id]
            detail_rows.append({
                "Estado":        "✅ Financiado" if item.funded else "❌ Diferido",
                "Activo":        item.asset_name,
                "Tier":          item.tier,
                "Escenario":     item.scenario_code,
                "Intervención":  item.intervention_label.split("--")[-1].strip()[:35],
                "Coste (€)":     item.cost_eur,
                "TIS":           round(item.tis, 1),
                "Visit./año":    a.visitor_capacity_annual,
            })
        detail_df = pd.DataFrame(detail_rows)
        st.dataframe(
            detail_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "TIS":      st.column_config.NumberColumn("TIS", format="%.1f"),
                "Coste (€)": st.column_config.NumberColumn("Coste (€)", format="€%d"),
                "Visit./año": st.column_config.NumberColumn(
                    "Visitas/año", format="%d"),
            },
        )

        # Totales rápidos
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1:
            st.metric("Total asignado", f"€{live_budget.total_allocated_eur:,}")
        with t_col2:
            st.metric("Delta EHS portafolio", f"+{live_budget.portfolio_delta_ehs:.1f} pts")
        with t_col3:
            st.metric("Delta visitantes", f"+{live_budget.portfolio_delta_visitors:,}")


# ── Tab 5: Impacto Socioeconómico ─────────────────────────────────────────────
with tab_socioeco:
    import pandas as pd
    import plotly.graph_objects as go

    st.subheader("Impacto Socioeconómico — Economía Regenerativa del Destino")
    st.caption(
        "Vincula el éxito ecológico con la resiliencia económica local bajo el principio "
        "de economía regenerativa. Modelo de gasto turístico calibrado para reservas de la "
        "biosfera de España. **Coste de 'no actuar'** = ingresos de hostelería perdidos si "
        "un activo Tier 1 se degrada hasta requerir cierre preventivo."
    )

    # ── Constantes del modelo económico ──────────────────────────────────────
    _SPEND_PER_VISITOR_EUR  = 22.50   # gasto medio diario en restauración/comercio local
    _VISITORS_PER_JOB       = 2_500   # visitantes anuales que sustentan 1 empleo
    # Factores de riesgo de cierre por tier (porcentaje de visitantes afectados)
    _CLOSURE_RISK_FACTOR    = {1: 1.00, 2: 0.40, 3: 0.05, 4: 0.00}

    # IDs financiados con el presupuesto base (100K) — determina qué activos
    # Tier 1/2 están "protegidos" vs "en riesgo" en el escenario de referencia
    _base_funded = {item.asset_id for item in base_budget.funded_items}

    # ── Calcular métricas por activo ──────────────────────────────────────────
    eco_rows = []
    for a in ranked_assets:
        tier          = a.tier or 0
        risk_factor   = _CLOSURE_RISK_FACTOR.get(tier, 0.0)
        is_funded     = a.asset_id in _base_funded
        # Revenue at risk: solo si NO está financiado (sin restauración = degradación libre)
        effective_risk = risk_factor if not is_funded else risk_factor * 0.15
        revenue_at_risk = round(a.visitor_capacity_annual * _SPEND_PER_VISITOR_EUR * effective_risk)
        jobs_linked     = round(a.visitor_capacity_annual / _VISITORS_PER_JOB, 2)
        jobs_at_risk    = round(jobs_linked * effective_risk, 2)

        # Coste de intervención recomendada para este activo
        comp = next((c for c in base_comps if c.asset_id == a.asset_id), None)
        interv_cost = 0
        if comp:
            interv_cost = comp.scenarios[comp.best_scenario_code].cost_eur

        # ROI: cuántas veces se recupera la inversión en ingresos protegidos (anual)
        roi_ratio = round(revenue_at_risk / interv_cost, 1) if interv_cost > 0 else None

        eco_rows.append({
            "asset_id":         a.asset_id,
            "Activo":           a.name,
            "Municipio":        a.region,
            "Tier":             tier,
            "Financiado":       is_funded,
            "Visitantes/año":   a.visitor_capacity_annual,
            "Ingresos Hostelería\nen Riesgo (€)": revenue_at_risk,
            "Empleos\nVinculados": jobs_linked,
            "Empleos\nen Riesgo":  jobs_at_risk,
            "Coste Intervención (€)": interv_cost,
            "ROI Conservación":  roi_ratio,
        })

    eco_df = pd.DataFrame(eco_rows)

    # ── KPIs territoriales ────────────────────────────────────────────────────
    total_revenue_risk = eco_df["Ingresos Hostelería\nen Riesgo (€)"].sum()
    total_jobs_linked  = eco_df["Empleos\nVinculados"].sum()
    total_jobs_risk    = eco_df["Empleos\nen Riesgo"].sum()
    tier1_unfunded     = len(eco_df[(eco_df["Tier"] == 1) & (~eco_df["Financiado"])])

    e_col1, e_col2, e_col3, e_col4 = st.columns(4)
    kpi_eco = [
        (e_col1, "Ingresos Hostelería en Riesgo",
         f"€{total_revenue_risk:,.0f}", "#c62828", "#ffebee"),
        (e_col2, "Empleos Locales Vinculados",
         f"{total_jobs_linked:.0f} empleos", "#1565c0", "#e3f2fd"),
        (e_col3, "Empleos en Riesgo (Tier 1-2 sin fondos)",
         f"{total_jobs_risk:.1f} empleos", "#e65100", "#fff3e0"),
        (e_col4, "Activos Tier 1 sin Financiar",
         f"{tier1_unfunded} activos", "#6a1b9a", "#f3e5f5"),
    ]
    for col, name, val, fg, bg in kpi_eco:
        with col:
            st.markdown(
                f'<div class="kpi-card" style="border-left:4px solid {fg};">'
                f'<div class="kpi-meta">{name}</div>'
                f'<div class="kpi-value" style="color:{fg};font-size:1.4rem">{val}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.write("")

    # ── Filtro por municipio ──────────────────────────────────────────────────
    municipios = ["Todos los municipios"] + sorted(eco_df["Municipio"].unique().tolist())
    sel_muni = st.selectbox("Filtrar por municipio", municipios, index=0)
    view_df = eco_df if sel_muni == "Todos los municipios" \
              else eco_df[eco_df["Municipio"] == sel_muni]

    # ── Gráfico 1: Ingresos en riesgo vs coste de intervención por activo ────
    chart_df = view_df[view_df["Tier"].isin([1, 2])].sort_values(
        "Ingresos Hostelería\nen Riesgo (€)", ascending=True
    )

    fig_roi = go.Figure()
    fig_roi.add_trace(go.Bar(
        y=chart_df["Activo"].apply(lambda n: n.split("—")[0].strip()[:30]),
        x=chart_df["Ingresos Hostelería\nen Riesgo (€)"],
        name="Ingresos en Riesgo (€/año)",
        orientation="h",
        marker=dict(color="#c62828", opacity=0.80),
        hovertemplate="<b>%{y}</b><br>Ingresos en riesgo: €%{x:,}<extra></extra>",
    ))
    fig_roi.add_trace(go.Bar(
        y=chart_df["Activo"].apply(lambda n: n.split("—")[0].strip()[:30]),
        x=chart_df["Coste Intervención (€)"],
        name="Coste de Intervención (€)",
        orientation="h",
        marker=dict(color="#1565c0", opacity=0.75),
        hovertemplate="<b>%{y}</b><br>Intervención: €%{x:,}<extra></extra>",
    ))
    fig_roi.update_layout(
        title=dict(
            text="Coste de 'No Actuar' vs Inversión en Conservación — Activos Tier 1 y 2",
            font=dict(size=13, color="#0d1b2a"), x=0.0,
        ),
        xaxis=dict(title="Euros (€)", tickprefix="€",
                   showgrid=True, gridcolor="rgba(180,190,200,0.3)"),
        yaxis=dict(automargin=True),
        barmode="group",
        legend=dict(orientation="h", y=1.05, x=0),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=20, r=20, t=65, b=40),
        height=max(260, len(chart_df) * 48 + 80),
        hoverlabel=dict(bgcolor="#1b2d42", font_color="white",
                        font_size=12, bordercolor="#2e4560"),
    )
    try:
        st.plotly_chart(fig_roi, use_container_width=True)
    except Exception as _e:
        st.error(f"Error al renderizar el gráfico: {_e}", icon="⚠️")

    # ── Gráfico 2: Empleos vinculados y en riesgo por municipio ──────────────
    muni_grp = eco_df.groupby("Municipio").agg(
        jobs_total=("Empleos\nVinculados", "sum"),
        jobs_risk= ("Empleos\nen Riesgo",  "sum"),
        revenue_risk=("Ingresos Hostelería\nen Riesgo (€)", "sum"),
    ).reset_index().sort_values("jobs_total", ascending=True)

    fig_jobs = go.Figure()
    fig_jobs.add_trace(go.Bar(
        y=muni_grp["Municipio"],
        x=muni_grp["jobs_total"],
        name="Empleos Vinculados",
        orientation="h",
        marker=dict(color="#1565c0", opacity=0.75),
        hovertemplate="<b>%{y}</b><br>Empleos vinculados: %{x:.1f}<extra></extra>",
    ))
    fig_jobs.add_trace(go.Bar(
        y=muni_grp["Municipio"],
        x=muni_grp["jobs_risk"],
        name="Empleos en Riesgo",
        orientation="h",
        marker=dict(color="#e65100", opacity=0.85),
        hovertemplate="<b>%{y}</b><br>Empleos en riesgo: %{x:.1f}<extra></extra>",
    ))
    fig_jobs.update_layout(
        title=dict(
            text="Empleos Locales Vinculados al Turismo Natural por Municipio",
            font=dict(size=13, color="#0d1b2a"), x=0.0,
        ),
        xaxis=dict(title="Empleos (directos + indirectos)",
                   showgrid=True, gridcolor="rgba(180,190,200,0.3)"),
        yaxis=dict(automargin=True),
        barmode="overlay",
        legend=dict(orientation="h", y=1.05, x=0),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=20, r=20, t=65, b=40),
        height=340,
        hoverlabel=dict(bgcolor="#1b2d42", font_color="white",
                        font_size=12, bordercolor="#2e4560"),
    )
    try:
        st.plotly_chart(fig_jobs, use_container_width=True)
    except Exception as _e:
        st.error(f"Error al renderizar el gráfico: {_e}", icon="⚠️")

    # ── Tabla detallada ───────────────────────────────────────────────────────
    with st.expander("📋 Tabla completa de impacto socioeconómico por activo", expanded=False):
        display_cols = [
            "Activo", "Municipio", "Tier", "Visitantes/año",
            "Ingresos Hostelería\nen Riesgo (€)",
            "Empleos\nVinculados", "Empleos\nen Riesgo",
            "Coste Intervención (€)", "ROI Conservación",
        ]
        st.dataframe(
            view_df[display_cols].sort_values("Ingresos Hostelería\nen Riesgo (€)", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Visitantes/año":        st.column_config.NumberColumn(format="%d"),
                "Ingresos Hostelería\nen Riesgo (€)":
                    st.column_config.NumberColumn("Ingresos en Riesgo (€)", format="€%d"),
                "Empleos\nVinculados":   st.column_config.NumberColumn("Empleos Vinc.", format="%.1f"),
                "Empleos\nen Riesgo":    st.column_config.NumberColumn("Empleos Riesgo", format="%.2f"),
                "Coste Intervención (€)":
                    st.column_config.NumberColumn("Coste Interv. (€)", format="€%d"),
                "ROI Conservación":      st.column_config.NumberColumn("ROI (x)", format="%.1fx"),
            },
        )

    # ── Nota metodológica ─────────────────────────────────────────────────────
    with st.expander("ℹ️ Metodología económica", expanded=False):
        st.markdown(
            f"""
**Modelo de gasto turístico** (calibrado para reservas de biosfera españolas, 2024):

| Parámetro | Valor | Fuente |
|---|---|---|
| Gasto medio diario por visitante | **€{_SPEND_PER_VISITOR_EUR:.2f}** | MITECO / Informe de turismo de naturaleza 2023 |
| Visitantes por empleo directo+indirecto | **{_VISITORS_PER_JOB:,}** | Estimación proxy para ecoturismo rural |
| Factor de riesgo de cierre — Tier 1 (sin fondos) | **100%** | Cierre preventivo por degradación crítica |
| Factor de riesgo de cierre — Tier 2 (sin fondos) | **40%** | Reducción parcial de afluencia |
| Factor de riesgo residual — Tier 1 **con fondos** | **15%** | Riesgo durante período de restauración |

**Coste de 'no actuar':** Si un activo Tier 1 se degrada hasta requerir cierre preventivo,
los ingresos de hostelería local (restauración + comercio) cesan completamente durante
el período de cierre. La pérdida se estima como `visitantes × €{_SPEND_PER_VISITOR_EUR:.2f}`.

**ROI de conservación:** Ratio entre ingresos anuales protegidos y coste único de la intervención.
Un ROI > 1× significa que la inversión se recupera en menos de un año en ingresos protegidos.
            """
        )


# ── Tab 6: Mapa PyDeck (WebGL) ────────────────────────────────────────────────
with tab_map:
    st.subheader("Mapa Territorial — Visión Espacial del Portfolio")

    # ── Control de modo de visualización ─────────────────────────────────────
    map_mode = st.radio(
        "Modo de visualización",
        options=["🗂️ Vista de Gestión (Tiers)", "🛰️ Vista de Diagnóstico Espectral (NDVI/NDMI)"],
        index=0,
        horizontal=True,
        help=(
            "**Vista de Gestión:** activos coloreados por tier de prioridad (Rojo/Naranja/Azul/Verde). "
            "**Vista Espectral:** gradiente continuo RdYlGn derivado del EHS real del activo — "
            "simula el contraste espacial de degradación difusa visible en imágenes Sentinel-2."
        ),
    )

    spectral_mode = "Espectral" in map_mode

    if spectral_mode:
        st.caption(
            "🛰️ Color = gradiente RdYlGn (ColorBrewer) anclado en el EHS real del activo. "
            "**Rojo intenso** → EHS < 30 (degradación crítica) · "
            "**Amarillo** → EHS ≈ 60 (zona de transición) · "
            "**Verde saturado** → EHS > 80 (salud óptima). "
            "Reproduce el contraste espectral NDVI/NDMI a lo largo del corredor del sendero."
        )
    else:
        st.caption(
            "Renderizado WebGL vía Deck.gl / PyDeck. "
            "La carga computacional es constante — todo el rendering ocurre en la GPU del cliente. "
            "Haz clic en cualquier activo para ver su ficha completa."
        )

    col_map, col_info = st.columns([3, 1])

    with col_map:
        try:
            _mc = _terr_cfg["map_center"]
            if spectral_mode:
                deck = build_pydeck_deck_spectral(ranked_assets, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2])
            else:
                deck = build_pydeck_deck(ranked_assets, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2])
            st.pydeck_chart(deck, use_container_width=True, height=540)
        except ImportError:
            st.error(
                "**pydeck no instalado.** Ejecuta `pip install pydeck` y reinicia el servidor.",
                icon="⚠️",
            )

    with col_info:
        if spectral_mode:
            # ── Leyenda espectral continua ────────────────────────────────────
            st.markdown("#### Escala EHS Espectral")
            _spectral_legend = [
                ("#a50026", "EHS < 30 — Crítico"),
                ("#d73027", "EHS 30-45 — Degradado"),
                ("#fdae61", "EHS 45-60 — Alerta"),
                ("#ffffbf", "EHS 60-75 — Moderado"),
                ("#a6d96a", "EHS 75-85 — Bueno"),
                ("#1a9850", "EHS > 85 — Óptimo"),
            ]
            for hex_c, label in _spectral_legend:
                st.markdown(
                    f'<div style="margin-bottom:7px;">'
                    f'<span class="legend-chip" style="background:{hex_c};'
                    f'border:1px solid rgba(0,0,0,.15)"></span>'
                    f'<small style="color:#444">{label}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.divider()
            # EHS estadísticas rápidas
            ehs_vals = [a.ehs for a in ranked_assets]
            st.caption(f"EHS medio: **{sum(ehs_vals)/len(ehs_vals):.1f}**")
            st.caption(f"EHS mín: **{min(ehs_vals):.0f}** · máx: **{max(ehs_vals):.0f}**")
            st.caption(
                f"Activos en zona crítica (EHS<45): "
                f"**{sum(1 for v in ehs_vals if v < 45)}**"
            )
        else:
            # ── Leyenda de tiers (vista original) ────────────────────────────
            st.markdown("#### Distribución por tier")
            tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            for a in ranked_assets:
                if a.tier in tier_counts:
                    tier_counts[a.tier] += 1
            for item in LEGEND_ITEMS:
                t     = item["tier"]
                count = tier_counts.get(t, 0)
                color = item["hex"]
                label = item["label"].split(" — ")[1]
                st.markdown(
                    f'<div style="margin-bottom:8px;">'
                    f'<span class="legend-chip" style="background:{color}"></span>'
                    f'<b style="color:{color}">{count}</b>'
                    f'<small style="color:#555;margin-left:6px">{label}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.divider()
        st.markdown("#### Cobertura territorial")
        regions = sorted({a.region for a in ranked_assets})
        for r in regions:
            n = sum(1 for a in ranked_assets if a.region == r)
            st.caption(f"· {r} ({n})")

        st.divider()
        st.caption(
            "⚠️ Las geometrías son **aproximadas** (centroides municipales). "
            "Para coordenadas reales conectar con PostGIS / hiking_trails.geojson."
        )


# ── Tab 7: Catálogo de activos ────────────────────────────────────────────────
with tab_assets:
    st.subheader("Catálogo de Activos — Ranking por Índice de Prioridad Territorial (TPI)")
    st.caption(
        f"{len(ranked_assets)} activos monitorizados · "
        "Ordenados por TPI descendente (mayor urgencia primero)"
    )
    _cur_badge = data_status_badge(DataStatus.CALIBRATED)
    st.markdown(
        f'<div style="font-size:0.8rem;color:{_cur_badge.color};margin:-4px 0 8px">'
        f'{_cur_badge.emoji} <b>{_cur_badge.label}</b> · estos activos son una capa '
        f'narrativa de juicio experto, contrastada (no sustituida) por el satélite '
        f'en la pestaña <i>Sendas Reales</i>. No usar para intervención formal sin '
        f'el dato satelital de su senda.</div>',
        unsafe_allow_html=True,
    )

    # ── Validación cruzada con el satélite (Pipeline A) ───────────────────────
    _calib = calibrate_territory(selected_key, ranked_assets)
    _cov = coverage_summary(_calib)
    with st.container():
        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric("✓ Satélite confirma", _cov["confirma"])
        cc2.metric("⚠ Satélite más verde", _cov["mas_sano"])
        cc3.metric("⚠ Satélite más degradado", _cov["mas_degradado"])
        cc4.metric("— Sin senda equivalente", _cov["sin_dato"])
    st.caption(
        "**Validación cruzada (triangulación):** cada activo curado se contrasta con "
        "el EHS satelital real de su senda concreta (Pipeline A · Sentinel-2). "
        "El EHS curado mide *salud bajo presión turística* (juicio experto); el "
        "satelital mide *verdor de la vegetación* (NDVI/NDMI). Divergen de forma "
        "esperable en alta montaña (roca/canchal alpino tienen poco NDVI por geología, "
        "no por turismo): por eso el satélite **valida**, no sustituye, el juicio experto."
    )
    st.divider()

    # Filtros
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        tier_filter = st.multiselect(
            "Filtrar por Tier", options=[1, 2, 3, 4],
            default=[1, 2, 3, 4],
            format_func=lambda t: {1:"Tier 1 — Atención Inmediata",
                                   2:"Tier 2 — Acción Preventiva",
                                   3:"Tier 3 — Monitorización",
                                   4:"Tier 4 — Promoción Activa"}[t],
        )
    with f_col2:
        type_options = sorted({a.asset_type for a in ranked_assets})
        type_filter = st.multiselect(
            "Filtrar por tipo", options=type_options,
            default=type_options,
            format_func=lambda t: f"{_ASSET_TYPE_EMOJI.get(t,'📍')} {t.replace('_',' ').title()}",
        )
    with f_col3:
        region_options = sorted({a.region for a in ranked_assets})
        region_filter = st.multiselect(
            "Filtrar por municipio", options=region_options,
            default=region_options,
        )

    filtered = [
        a for a in ranked_assets
        if (a.tier in tier_filter)
        and (a.asset_type in type_filter)
        and (a.region in region_filter)
    ]

    st.caption(f"Mostrando {len(filtered)} de {len(ranked_assets)} activos")
    st.write("")

    # Render each asset as a styled card
    for asset in filtered:
        tier   = asset.tier or 0
        tpi    = asset.tpi or 0.0
        fg, bg = _TIER_BADGE_COLOR.get(tier, ("#555", "#eee"))
        emoji  = _ASSET_TYPE_EMOJI.get(asset.asset_type, "📍")
        rank   = asset.priority_rank or "—"
        physical = ""
        if asset.length_km:
            physical = f"&nbsp;·&nbsp; {asset.length_km:.1f} km"
        elif asset.area_ha:
            physical = f"&nbsp;·&nbsp; {asset.area_ha:.0f} ha"
        if asset.elevation_m:
            physical += f"&nbsp;·&nbsp; {asset.elevation_m:.0f} m"

        # ── Sello de validación satelital ─────────────────────────────────────
        _cal = _calib.get(asset.asset_id)
        if _cal is not None:
            _vemoji, _vlabel, _vcolor = _cal.badge
            if _cal.satellite_ehs is not None:
                _refs = "; ".join(_cal.matched_trails[:2])
                if len(_cal.matched_trails) > 2:
                    _refs += f" (+{len(_cal.matched_trails) - 2})"
                _val_html = (
                    f'<div style="margin-top:6px;font-size:0.72rem;color:{_vcolor}">'
                    f'<b>{_vemoji} {_vlabel}</b> · EHS satélite '
                    f'<b>{_cal.satellite_ehs:.0f}</b>/100 '
                    f'(Δ {_cal.delta:+.0f} vs curado) '
                    f'<span style="color:#9aa4af">← {_refs}</span></div>'
                )
            else:
                _val_html = (
                    f'<div style="margin-top:6px;font-size:0.72rem;color:{_vcolor}">'
                    f'{_vemoji} {_vlabel} · sin senda satelital comparable</div>'
                )
        else:
            _val_html = ""

        st.markdown(
            f"""<div class="kpi-card" style="border-left:5px solid {fg};margin-bottom:0.5rem;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:1.8rem;line-height:1">{emoji}</div>
    <div style="flex:1">
      <div style="font-size:0.95rem;font-weight:700;color:#0d1b2a">
        #{rank}&ensp;{asset.name}
      </div>
      <div style="font-size:0.75rem;color:#7a8899;margin-top:2px">
        {asset.region}{physical}
      </div>
    </div>
    <div style="text-align:right;min-width:120px">
      <span class="kpi-badge" style="color:{fg};background:{bg};">
        Tier {tier}
      </span><br/>
      <span style="font-size:1.1rem;font-weight:700;color:{fg}">
        EHS&thinsp;{asset.ehs:.0f}
      </span>
      <span style="font-size:0.75rem;color:#9aa4af">/100</span>
    </div>
    <div style="text-align:right;min-width:80px">
      <div style="font-size:0.65rem;color:#9aa4af;text-transform:uppercase">TPI</div>
      <div style="font-size:1.3rem;font-weight:700;color:#0d1b2a">{tpi:.0f}</div>
    </div>
  </div>
  <div style="font-size:0.75rem;color:#555;margin-top:8px;padding-top:6px;
              border-top:1px solid #e8ecf0">
    {asset.description[:160]}{'…' if len(asset.description) > 160 else ''}
  </div>
  {_val_html}
</div>""",
            unsafe_allow_html=True,
        )


# ── Tab 8: Sendas reales (salida del Pipeline A sobre Sentinel-2) ────────────
with tab_real:
    st.subheader("Sendas Reales — Análisis Satelital del Pipeline A")
    st.caption(
        "Esta capa NO usa datos curados: muestra exactamente lo que la ciencia "
        "produce a partir de la **cartografía real de senderos × Sentinel-2** "
        "(NDVI/NDMI) aplicando las fórmulas EHS / ΔEHS / SCM del proyecto. "
        "Cada línea es el trazado cartográfico verdadero, coloreado por su Salud "
        "Ecológica (EHS) de verano."
    )

    _real = get_real_trails(selected_key)

    if not _real.available:
        st.info(
            "Aún no hay resultados del Pipeline A para este territorio.\n\n"
            "Genera la salida ejecutando en la raíz del proyecto:\n\n"
            "```\npython run_pipeline_a_filemode.py --territory all\n```\n\n"
            "Esto cruza la cartografía de senderos con el ráster Sentinel-2 y "
            "escribe `data/outputs/<territorio>/pipeline_a_results.geojson`.",
            icon="🛰",
        )
    else:
        s = _real.summary
        import pandas as pd

        # ── Calidad y trazabilidad del dato (F3) ──────────────────────────────
        _prov = snapshot_provenance(selected_key)
        _badge = data_status_badge(_prov.status)
        _scenes = (" · ".join(_prov.scene_dates)
                   if _prov.scene_dates else f"{_prov.n_scenes} escenas estacionales")
        st.markdown(
            f'<div style="padding:10px 14px;border-radius:8px;'
            f'background:#f3f8f6;border-left:4px solid {_badge.color};margin-bottom:6px;">'
            f'<span style="font-weight:700;color:{_badge.color}">'
            f'{_badge.emoji} {_badge.label}</span> '
            f'<span style="font-size:0.8rem;color:#5a6b7a">· {_badge.caveat}</span><br/>'
            f'<span style="font-size:0.8rem;color:#33485c">'
            f'<b>Escenas Sentinel-2:</b> {_scenes} &nbsp;·&nbsp; '
            f'<b>Composición:</b> percentiles de escena (P90/P10) &nbsp;·&nbsp; '
            f'<b>Tile:</b> T30TVL</span><br/>'
            f'<span style="font-size:0.8rem;color:#33485c">'
            f'<b>Profundidad temporal:</b> {_prov.inference_label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _cov = load_timeseries_coverage(selected_key)
        if _cov is not None:
            st.caption(
                f"📈 Serie multi-anual: cobertura **{_cov['fraction']*100:.0f}%** "
                f"({_cov['n_present']}/{_cov['n_expected']} periodos) · "
                f"estado dominante: **{_cov['dominant_status']}** · "
                f"huecos: {_cov['n_gaps']}."
            )
        st.warning(_prov.caveat, icon="⚠️")

        # ── Tira de KPIs reales ──
        k1, k2, k3, k4, k5 = st.columns(5)
        _ehs_mean = s.get("ehs_summer_mean")
        _ehs_color = ("#0F6E56" if (_ehs_mean or 0) >= 60
                      else "#EF9F27" if (_ehs_mean or 0) >= 45 else "#A32D2D")
        with k1:
            st.metric("Sendas analizadas", s.get("n_trails", len(_real.trails)))
        with k2:
            st.metric("Longitud total", f"{s.get('total_length_km', 0):.0f} km")
        with k3:
            st.markdown(
                f'<div style="font-size:0.78rem;color:#7a8899">EHS verano medio</div>'
                f'<div style="font-size:1.6rem;font-weight:700;color:{_ehs_color}">'
                f'{_ehs_mean if _ehs_mean is not None else "—"}'
                f'<span style="font-size:0.8rem;color:#9aa4af">/100</span></div>',
                unsafe_allow_html=True,
            )
        with k4:
            st.metric("Sendas en deterioro", s.get("n_degrading_positive_delta", 0),
                      help="Sendas cuya salud ecológica cae de primavera a verano "
                           "(ΔEHS de salud < 0, equivalente a un aumento del estrés).")
        with k5:
            st.metric("Presupuesto indicativo",
                      f"€{s.get('total_budget_eur', 0):,.0f}",
                      help="Σ longitud × coste/m × (EHS/100) × factor causal SCM.")

        st.divider()

        # ── Mapa real + leyenda EHS ──
        _mc = _terr_cfg["map_center"]
        _map_c, _leg_c = st.columns([4, 1], gap="medium")
        with _map_c:
            try:
                _geo = build_real_trails_geojson(_real)
                _boundary = get_park_boundary(selected_key)
                _deck = build_real_trails_deck(
                    _geo, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2],
                    boundary_geojson=_boundary,
                )
                st.pydeck_chart(_deck, use_container_width=True, height=460)
            except ImportError:
                st.error("pydeck no instalado — `pip install pydeck`", icon="⚠️")
        with _leg_c:
            st.markdown("**EHS (Salud Ecológica)**")
            _legend = [
                ("#1a9850", "≥ 75 · Saludable"),
                ("#a6d96a", "60–75 · Estable"),
                ("#ffffbf", "45–60 · Alerta"),
                ("#fdae61", "30–45 · Estrés"),
                ("#d73027", "< 30 · Crítico"),
                ("#9e9e9e", "Sin dato"),
            ]
            for hexc, lbl in _legend:
                st.markdown(
                    f'<span class="legend-chip" style="background:{hexc};'
                    f'border:1px solid #ccc"></span><small>{lbl}</small>',
                    unsafe_allow_html=True,
                )
            st.caption(
                "Color = NDVI/NDMI real del píxel sobre el buffer de 50 m de cada senda."
            )

        # ── Zonificación PRUG (solo PNSG) ──
        if _real.has_prug:
            from collections import Counter
            _zc = Counter(t.prug_zone for t in _real.trails if t.prug_zone)
            _prot = sum(1 for t in _real.trails
                        if t.prug_zone in ("Zona de Reserva", "Zona de Uso Restringido"))
            st.markdown(
                f'<div style="margin-top:8px;padding:10px 12px;background:#fffdf5;'
                f'border-radius:6px;border-left:3px solid #d4a017;">'
                f'<span style="font-size:0.72rem;color:#8a6d1a;text-transform:uppercase;'
                f'letter-spacing:0.06em;font-weight:700">⛰ Zonificación PRUG oficial</span><br/>'
                f'<span style="font-size:0.80rem;color:#444">'
                f'{_prot} de {len(_real.trails)} sendas discurren por zonas de alta protección '
                f'(Reserva / Uso Restringido). La prioridad de intervención pondera la '
                f'degradación por el nivel de protección del PRUG.</span></div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Tabla priorizada ──
        _has_prug = _real.has_prug
        if _has_prug:
            st.markdown("**Ranking de intervención · degradación × protección PRUG (prioridad combinada)**")
            _ranked = _real.ranked_by_priority_index()
        else:
            st.markdown("**Ranking de intervención · peor salud ecológica primero**")
            _ranked = _real.ranked_by_priority()

        _rows = []
        for t in _ranked:
            row = {
                "Senda":          t.name,
                "Long. (km)":     t.length_km,
                "EHS primavera":  round(t.health_spring, 1) if t.health_spring is not None else None,
                "EHS verano":     round(t.health_summer, 1) if t.health_summer is not None else None,
                "ΔEHS":           round(t.delta_health, 1) if t.delta_health is not None else None,
                "Prioridad":      t.priority_label,
                "Causa (SCM)":    t.scm_label_es,
                "Presupuesto (€)": round(t.budget_eur, 0) if t.budget_eur is not None else None,
            }
            if _has_prug:
                row["Zona PRUG"] = (t.prug_zone or "—").replace("Zona de ", "")
                row["Prioridad PRUG"] = t.priority_index
            _rows.append(row)
        _df = pd.DataFrame(_rows)

        _colcfg = {
            "EHS verano": st.column_config.ProgressColumn(
                "EHS verano", min_value=0, max_value=100, format="%.0f"),
            "EHS primavera": st.column_config.NumberColumn(format="%.0f"),
            "ΔEHS": st.column_config.NumberColumn(
                "ΔEHS", format="%.1f",
                help="Negativo = empeora en verano (caída de NDVI estacional)."),
            "Presupuesto (€)": st.column_config.NumberColumn(format="€%d"),
        }
        if _has_prug:
            _colcfg["Prioridad PRUG"] = st.column_config.ProgressColumn(
                "Prioridad PRUG", min_value=0, max_value=100, format="%.0f",
                help="(100 − salud) × peso de protección PRUG. Mayor = más urgente.")
        st.dataframe(_df, use_container_width=True, hide_index=True, column_config=_colcfg)
        _terr_folder = "sierra_del_rincon" if selected_key == "snr" else "pnsg"
        _carto = ("Cartografía oficial OAPN (sendas homologadas + límite + zonificación PRUG)"
                  if selected_key == "pnsg" else "Cartografía OpenStreetMap")
        st.caption(
            f"Fuente: Pipeline A · Sentinel-2 tile T30TVL · {_carto} · "
            "Salida real, sin datos sintéticos. Provenance: "
            f"`data/outputs/{_terr_folder}/pipeline_a_results.geojson`"
        )


# ── Pie de página ─────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f'<div style="font-size:0.72rem;color:#9aa4af;text-align:center;padding:4px 0 8px;">'
    f'Smart Natural Tourism Observatory (SNTO) v0.1 · '
    f'Plataforma de Inteligencia Estratégica de Destinos · '
    f'{dashboard.territory_name} · Madrid (España) · '
    f'Datos sintéticos de validación'
    f'</div>',
    unsafe_allow_html=True,
)
