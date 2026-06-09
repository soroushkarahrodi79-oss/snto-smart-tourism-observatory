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
        # Nota: ajustado para quedar < 38 con LANDSCAPE_DRIVEN+MODERATE (CC=8)
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
</style>
""",
    unsafe_allow_html=True,
)

# ── Paleta de estados ─────────────────────────────────────────────────────────
_COLOR = {"GREEN": "#2e7d32", "AMBER": "#e65100", "RED": "#c62828", "BLUE": "#1565c0"}
_BG    = {"GREEN": "#e8f5e9", "AMBER": "#fff3e0", "RED": "#ffebee", "BLUE": "#e3f2fd"}
_EMOJI = {"GREEN": "🟢",      "AMBER": "🟡",      "RED": "🔴",      "BLUE": "🔵"}


# ── Pipeline con caché ────────────────────────────────────────────────────────
# Cambia _DATA_VERSION cada vez que modifiques build_territory()
# para forzar invalidación del caché sin reiniciar el servidor.
_DATA_VERSION = f"{TERRITORY_NAME}|{REPORT_DATE}"

@st.cache_data(show_spinner="Calculando inteligencia territorial…")
def load_dashboard(_v: str = _DATA_VERSION) -> ExecutiveDashboard:
    raw    = build_territory()
    assets = rank_assets(raw)
    by_id  = {a.asset_id: a for a in assets}
    max_v  = max(a.visitor_capacity_annual for a in assets)
    comps  = [compare_scenarios(a, max_v) for a in assets]
    budget = allocate_tis_budget(comps, by_id, BUDGET_EUR)
    return compute_executive_dashboard(
        territory_name=TERRITORY_NAME,
        report_date=REPORT_DATE,
        assets=assets,
        budget_result=budget,
        comparisons=comps,
    )


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
dashboard = load_dashboard()

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

# ── Panel de KPIs ─────────────────────────────────────────────────────────────
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

st.divider()
st.caption(
    "Smart Natural Tourism Observatory (SNTO) · "
    "Plataforma de Inteligencia Estratégica de Destinos v0.1 · "
    "Sierra del Rincón, Madrid (España) · Datos sintéticos de validación "
    "(piloto Reserva de la Biosfera Sierra del Rincón)"
)
