"""
SNTO — Smart Natural Tourism Observatory
Executive Destination Intelligence Dashboard  (Phase 7)

Levanta el servidor con:
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from src.territorial.models import AssetType, TerritorialAsset
from src.territorial.tpi import rank_assets
from src.intervention import compare_scenarios, allocate_tis_budget
from src.platform import compute_executive_dashboard, ExecutiveDashboard
from src.platform.map_layers import (
    build_pydeck_deck, build_pydeck_deck_spectral,
    assets_to_geojson, LEGEND_ITEMS, TIER_COLORS,
)
from src.platform.charts import build_portfolio_matrix, build_time_series_chart

# ── Territorio ────────────────────────────────────────────────────────────────
TERRITORY_NAME = "Reserva de la Biosfera Sierra del Rincón"
REPORT_DATE    = "2026-06-09"
BUDGET_EUR     = 100_000


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
_DATA_VERSION = f"{TERRITORY_NAME}|{REPORT_DATE}"

@st.cache_data(show_spinner="Calculando inteligencia territorial…")
def load_dashboard(_v: str = _DATA_VERSION):
    """Return (dashboard, assets, comps, assets_by_id, base_budget) — all cached."""
    raw    = build_territory()
    assets = rank_assets(raw)
    by_id  = {a.asset_id: a for a in assets}
    max_v  = max(a.visitor_capacity_annual for a in assets)
    comps  = [compare_scenarios(a, max_v) for a in assets]
    budget = allocate_tis_budget(comps, by_id, BUDGET_EUR)
    dash   = compute_executive_dashboard(
        territory_name=TERRITORY_NAME,
        report_date=REPORT_DATE,
        assets=assets,
        budget_result=budget,
        comparisons=comps,
    )
    return dash, assets, comps, by_id, budget


# ── Renderizador de tarjeta KPI ───────────────────────────────────────────────
def render_kpi_card(kpi) -> None:
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
    with st.expander("Interpretación y acción recomendada"):
        st.markdown(f"**¿Qué significa?** {kpi.what_it_means}")
        st.markdown(f"**Acción recomendada:** _{kpi.recommended_action}_")
        st.caption(f"Base técnica SNTO: {kpi.technical_basis}")


# ── Cargar datos ──────────────────────────────────────────────────────────────
dashboard, ranked_assets, base_comps, assets_by_id, base_budget = load_dashboard()

n_red = sum(1 for k in dashboard.kpis if k.status == "RED")
n_amb = sum(1 for k in dashboard.kpis if k.status == "AMBER")
n_ok  = sum(1 for k in dashboard.kpis if k.status in ("GREEN", "BLUE"))


# ── Barra lateral ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏔 SNTO")
    st.markdown("**Plataforma de Inteligencia  \nEstratégica de Destinos**")
    st.divider()
    st.markdown(f"**Territorio**  \n{dashboard.territory_name}")
    st.markdown(f"**Fecha de informe**  \n{dashboard.report_date}")
    st.markdown(f"**Activos monitorizados**  \n{dashboard.n_assets}")
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
    st.caption("Piloto: Reserva de la Biosfera Sierra del Rincón (Madrid)")


# ── Encabezado ────────────────────────────────────────────────────────────────
st.title(f"🏔 Inteligencia Territorial — {dashboard.territory_name}")
st.caption(
    f"Plataforma SNTO · Informe estratégico · "
    f"{dashboard.report_date} · {dashboard.n_assets} activos monitorizados"
)

if n_red >= 3:
    st.error(dashboard.headline, icon="🚨")
elif n_red >= 1:
    st.error(dashboard.headline, icon="⚠️")
elif n_amb >= 3:
    st.warning(dashboard.headline, icon="⚠️")
else:
    st.success(dashboard.headline, icon="✅")

st.info(f"**Acción prioritaria:** {dashboard.call_to_action}", icon="📋")

st.divider()

# ── Pestañas principales ──────────────────────────────────────────────────────
tab_kpis, tab_portfolio, tab_timeseries, tab_simulator, tab_socioeco, tab_map, tab_assets = st.tabs([
    "📊 Indicadores Estratégicos",
    "📈 Portafolio TPI",
    "📉 Series Temporales",
    "💰 Simulador Financiero",
    "🏘️ Impacto Socioeconómico",
    "🗺️ Mapa Territorial",
    "🏔 Catálogo de Activos",
])


# ── Tab 1: KPIs ───────────────────────────────────────────────────────────────
with tab_kpis:
    st.subheader("Panel de Indicadores Estratégicos · 10 KPIs")
    st.caption(
        "Cada indicador responde a una pregunta de gestión concreta. "
        "Despliega cada tarjeta para ver la interpretación detallada y la acción recomendada."
    )

    kpis = dashboard.kpis
    for row_start in range(0, len(kpis), 4):
        row_kpis = kpis[row_start : row_start + 4]
        cols = st.columns(4)
        for i, kpi in enumerate(row_kpis):
            with cols[i]:
                render_kpi_card(kpi)
        st.write("")


# ── Tab 2: Portafolio TPI ─────────────────────────────────────────────────────
with tab_portfolio:
    st.subheader("Matriz de Portafolio TPI — Diagnóstico Estratégico")
    st.caption(
        "Cada activo se posiciona según su presión turística (eje X) y su riesgo ecológico "
        "(eje Y = 100 − EHS). El tamaño del punto refleja la importancia económica del activo. "
        "Los cuadrantes delimitan las cuatro estrategias de gestión del modelo SNTO."
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

    st.subheader("Simulador Financiero de Conservación — What-If")
    st.caption(
        "Ajusta el presupuesto disponible y observa en tiempo real qué activos "
        "entran o salen del plan de intervención y cuántos visitantes anuales "
        "quedan protegidos frente al riesgo de degradación."
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
        height=max(320, len(sim_df) * 26 + 80),
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

    st.subheader("Impacto Socioeconómico y Retorno de la Conservación")
    st.caption(
        "Vincula el éxito ecológico con la resiliencia económica local. "
        "Modelo de gasto turístico calibrado para reservas de la biosfera de España. "
        "**Coste de 'no actuar'** = ingresos de hostelería perdidos si un activo Tier 1 "
        "se degrada hasta requerir cierre preventivo."
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
        height=max(300, len(chart_df) * 42 + 100),
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
            if spectral_mode:
                deck = build_pydeck_deck_spectral(ranked_assets)
            else:
                deck = build_pydeck_deck(ranked_assets)
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
</div>""",
            unsafe_allow_html=True,
        )


# ── Pie de página ─────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Smart Natural Tourism Observatory (SNTO) · "
    "Plataforma de Inteligencia Estratégica de Destinos v0.1 · "
    "Sierra del Rincón, Madrid (España) · Datos sintéticos de validación "
    "(piloto Reserva de la Biosfera Sierra del Rincón)"
)
