"""
SNTO — Smart Natural Tourism Observatory
Executive Destination Intelligence Dashboard  (Phase 7)

Levanta el servidor con:
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from src._version import __version__
from src.territorial.fixtures import build_pnsg_territory, build_territory
from src.territorial.tpi import rank_assets
from src.intervention import compare_scenarios, allocate_tis_budget
from src.platform import compute_executive_dashboard, ExecutiveDashboard
from src.platform.map_layers import (
    build_pydeck_deck, build_pydeck_deck_spectral, build_real_trails_deck,
    assets_to_geojson, LEGEND_ITEMS, TIER_COLORS,
)
from src.platform.charts import (
    build_portfolio_matrix,
    build_real_trend_chart,
    build_time_series_chart,
)
from src.platform.real_trails import (
    get_real_trails, build_real_trails_geojson, get_park_boundary,
)
from src.platform.calibration import coverage_summary, asset_trail_geometries
from src.platform.enrichment import enrich_assets_with_satellite
from src.platform.provenance import (
    data_status_badge, load_timeseries_coverage, snapshot_provenance,
)
from src.platform.satellite_trends import (
    DEFAULT_PARK,
    available_parks,
    find_trend,
    park_label,
    summarize_trends,
)
from src.platform.views import ConfidenceDetail, ViewMode, get_view, view_modes
from src.platform import methodology as method
from src.temporal import DataStatus
from src.socioeconomic.loader import load_municipalities, snapshot_exists
from src.socioeconomic.indicators import (
    aggregate_asset_risk, compute_svi, jobs_at_risk as compute_jobs_at_risk,
)
from src.ui.render_helpers import (
    _ALERT_META, _ALERT_SEVERITY, _ASSET_TYPE_EMOJI,
    _TIER_BADGE_COLOR, _TIER_INVEST_LABEL, _TIER_ROMAN,
    _alert_chip, _ehs_color, _tier_chip,
)
from src.ui.render_widgets import (
    _compute_exec_kpis, _render_banner, _render_exec_kpis, _render_live_alerts,
)
from src.ui.tabs.tab_kpis import render_tab_kpis
from src.ui.tabs.tab_method import render_tab_method

# ── Fecha global de informe ───────────────────────────────────────────────────
REPORT_DATE = "2026-06-12"


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

# Territorios VISIBLES en el selector de la UI. El PNSG es el territorio
# principal del observatorio; Sierra del Rincón se conserva en el código, los
# datos y los scripts del pipeline (raíz del proyecto), pero ya no se ofrece en
# la vista. Para volver a mostrarlo, añade "snr" a esta lista.
_VISIBLE_TERRITORIES = ["pnsg"]


# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="SNTO — Inteligencia para la decisión en espacios protegidos",
    page_icon="🏔",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            f"Smart Natural Tourism Observatory (SNTO) v{__version__} · "
            "Capa de inteligencia para la decisión en espacios naturales "
            "protegidos — se apoya en GIS y observación de la Tierra, no los "
            "sustituye · Caso activo: Parque Nacional Sierra de Guadarrama "
            "(Madrid · Segovia, España)"
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

/* ── FASE 3: TIER (estrategia, neutro) vs ALERTA (táctica, semáforo) ─────── */
/* Chip de TIER: nomenclatura estructural [TIER N], paleta índigo→pizarra,
   deliberadamente NO semafórica (no es riesgo, es prioridad de inversión). */
.snto-tier-chip {
    display: inline-block; font-size: 0.62rem; font-weight: 700;
    letter-spacing: 0.07em; padding: 2px 8px; border-radius: 3px;
    vertical-align: middle; text-transform: uppercase;
}
/* Chip de ALERTA: semáforo táctico (🔴🟡🔵🟢), forma de píldora. */
.snto-status-chip {
    display: inline-block; font-size: 0.62rem; font-weight: 600;
    padding: 2px 8px; border-radius: 11px; vertical-align: middle;
    margin-left: 4px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── Pipeline con caché ────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Calculando inteligencia territorial…")
def load_dashboard(territory_key: str):
    """Return (dashboard, assets, comps, assets_by_id, base_budget, cfg, cal) — cached per territory.

    Fase 2 — inyección satelital: antes de rankear, el EHS satelital real del
    Pipeline A sobreescribe (conservadoramente) el EHS curado donde el satélite
    observa MÁS degradación. Como rank_assets recalcula TPI/tier a partir de
    ehs, el dato real se propaga a TPI, tiers, presupuesto y los 10 KPIs.
    """
    cfg    = _TERRITORY_CONFIG[territory_key]
    raw    = _BUILD_FN[territory_key]()
    raw, cal = enrich_assets_with_satellite(territory_key, raw)
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
    return dash, assets, comps, by_id, budget, cfg, cal


@st.cache_data(show_spinner=False)
def _cached_trends(park: str = DEFAULT_PARK):
    """Tendencias satelitales reales (Mann-Kendall) cacheadas por sesión y parque.

    ``summarize_trends`` parsea el JSON ``mk_trends_<park>.json`` de
    ``clean_assets/timeseries/analysis`` en cada llamada. Sin cache se relee del
    disco en cada rerun de Streamlit (cada cambio de widget en la Pestaña 6). El
    payload es pequeño (~15 KB / 21 activos) pero el cache — clavado por ``park``
    — elimina la E/S repetida y mantiene la latencia plana al cambiar de parque.
    """
    return summarize_trends(park=park)


# ── Selector de territorio (primer bloque de barra lateral) ──────────────────
with st.sidebar:
    st.markdown("## 🏔 SNTO")
    st.markdown("**Inteligencia para la decisión  \nen espacios naturales protegidos**")
    st.divider()
    st.markdown("**Espacio protegido activo**")
    if len(_VISIBLE_TERRITORIES) > 1:
        selected_key = st.radio(
            "Territorio activo",
            options=_VISIBLE_TERRITORIES,
            format_func=lambda k: _TERRITORY_CONFIG[k]["short"],
            label_visibility="collapsed",
        )
    else:
        # Un solo territorio visible: mostrarlo como etiqueta, sin selector.
        selected_key = _VISIBLE_TERRITORIES[0]
        st.markdown(
            f'<div class="snto-side-row"><span class="snto-side-icon">🏔</span>'
            f'<span><strong>{_TERRITORY_CONFIG[selected_key]["short"]}</strong></span></div>',
            unsafe_allow_html=True,
        )
    st.divider()
    st.markdown("**Vista / audiencia**")
    _modes = view_modes()
    # Por defecto, vista Auditoría: es la que expone procedencia, fórmulas y límites,
    # la adecuada para revisión metodológica / defensa académica.
    _default_view_idx = _modes.index(ViewMode.TRIBUNAL)
    _view_mode = st.radio(
        "Vista",
        options=_modes,
        format_func=lambda m: f"{get_view(m).icon} {get_view(m).label}",
        index=_default_view_idx,
        label_visibility="collapsed",
        key="view_mode",
    )
    _view = get_view(_view_mode)
    st.caption(_view.audience)
    if _view.shows:
        st.caption(f"🔁 {_view.shows}")
    st.divider()

# ── Cargar datos ──────────────────────────────────────────────────────────────
dashboard, ranked_assets, base_comps, assets_by_id, base_budget, _terr_cfg, calibration = load_dashboard(selected_key)
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
    st.caption(f"SNTO v{__version__} · Sentinel-2 real + INE/ALMUDENA + calibración")
    st.caption(f"Territorio principal: {_terr_cfg['short']} (Madrid · Segovia)")


# ── TAREA 1: Banner dinámico con contextual badging ──────────────────────────
_render_banner(selected_key, _terr_cfg, dashboard, n_red, n_amb)

# ── F7: Banner de vista / audiencia ───────────────────────────────────────────
st.markdown(
    f'<div style="padding:7px 14px;border-radius:6px;margin:4px 0 2px;'
    f'background:#eef3f8;border-left:4px solid #33485c;font-size:0.82rem;color:#33485c">'
    f'{_view.icon} <b>{_view.label}</b> — {_view.banner} '
    f'<span style="color:#7a8899">Énfasis: {_view.emphasis}</span></div>',
    unsafe_allow_html=True,
)

# ── Autorefresh: recarga la app cada 60 s (simula polling de datos en vivo) ───
_refresh_count = st_autorefresh(interval=60_000, limit=None, key=f"live_{selected_key}")

# ── Barra de alertas en vivo ──────────────────────────────────────────────────
_alerts_placeholder = st.empty()
with _alerts_placeholder.container():
    _render_live_alerts(ranked_assets, _refresh_count)

# ── F9: Capa socioeconómica real (ALMUDENA / INE) ────────────────────────────
# Solo el PNSG tiene snapshot socioeconómico curado. Para otros territorios el
# overlay es None y el dashboard usa el modelo proxy heredado.
_socio = None
if selected_key == "pnsg" and snapshot_exists():
    _socio_snapshot = load_municipalities()
    _socio_risk = aggregate_asset_risk(
        ranked_assets, name_to_ine=_socio_snapshot.name_to_ine()
    )
    if _socio_risk:  # hay activos que cruzan con municipios del PNSG
        _socio = {
            "snapshot": _socio_snapshot,
            "risk": _socio_risk,
            "svi": compute_svi(_socio_snapshot, _socio_risk),
            "jobs": compute_jobs_at_risk(_socio_snapshot, _socio_risk),
        }

# ── TAREA 2: Tira de 4 KPIs ejecutivos ───────────────────────────────────────
_exec_kpis = _compute_exec_kpis(ranked_assets, base_budget, assets_by_id)
if _socio:  # KPI "Empleos locales en riesgo" respaldado por datos reales
    _exec_kpis["jobs_risk"] = _socio["jobs"].total
_render_exec_kpis(_exec_kpis, selected_key)
if _socio:
    st.caption(
        "ℹ️ *Empleos locales en riesgo* calculado con datos reales **ALMUDENA / INE** "
        "(afiliados a hostelería del municipio × exposición ambiental de sus activos), "
        "no con el proxy de visitantes. Detalle en la pestaña **Impacto Socioeconómico**."
    )

st.divider()

# FASE 1: el mapa espacial "above the fold" se ha retirado para liberar espacio
# cognitivo. El mapa vive ahora en la pestaña «Diagnóstico Satelital y Mapa» y
# las fichas de activos críticos en «Resumen Ejecutivo (KPIs)».

# ── TAREA 4: Suite de módulos analíticos ──────────────────────────────────────
st.markdown(
    '<div style="font-size:0.70rem;font-weight:600;color:#7a8899;'
    'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px">'
    'Módulos de análisis estratégico</div>',
    unsafe_allow_html=True,
)
# FASE 1: flujo narrativo ejecutivo → científico → táctico → financiero →
# socioeconómico → temporal → auditoría (7 pestañas).
(tab_kpis, tab_diagnostic, tab_portfolio, tab_simulator,
 tab_socioeco, tab_timeseries, tab_assets, tab_method) = st.tabs([
    "1️⃣ Resumen Ejecutivo (KPIs)",
    "2️⃣ Diagnóstico Satelital y Mapa",
    "3️⃣ Priorización y Alertas (Portafolio TPI)",
    "4️⃣ Simulador Financiero",
    "5️⃣ Impacto Socioeconómico",
    "6️⃣ Evolución Temporal (Series Espectrales)",
    "7️⃣ Catálogo de Activos y Auditoría",
    "8️⃣ Fundamento y Trazabilidad",
])


# ── Tab 1: KPIs ───────────────────────────────────────────────────────────────
with tab_kpis:
    render_tab_kpis(dashboard, ranked_assets, base_comps, calibration, _view)


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

    # ── Panel de ALERTAS (táctica) vs TIER (estrategia) ───────────────────────
    st.divider()
    st.markdown("#### Alertas activas (riesgo táctico actual)")
    st.caption(
        "Las **alertas** (semáforo 🔴🟡🔵🟢) marcan el riesgo *actual* del activo; el "
        "**TIER** (chip neutro índigo) marca su *prioridad de inversión pública*. Son "
        "ejes independientes: un activo puede ser `TIER III` (baja prioridad de inversión) "
        "y a la vez tener una alerta 🟡 por estrés inusual reciente."
    )
    _by_alert = sorted(
        [a for a in ranked_assets if a.alert_level in _ALERT_META],
        key=lambda a: (_ALERT_SEVERITY.get(a.alert_level, 9), -(a.tpi or 0)),
    )
    if not _by_alert:
        st.success("✅ Sin alertas tácticas activas en este territorio.", icon="🌿")
    else:
        for a in _by_alert:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;'
                f'border-bottom:1px solid #eef1f5">'
                f'{_tier_chip(a.tier)}{_alert_chip(a.alert_level)}'
                f'<span style="font-size:0.82rem;color:#0d1b2a;font-weight:600">'
                f'{a.name.split("—")[0].strip()}</span>'
                f'<span style="font-size:0.72rem;color:#7a8899;margin-left:auto">'
                f'EHS {a.ehs:.0f} · TPI {a.tpi:.0f} · {a.region}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Tab 3: Series Temporales Espectrales ─────────────────────────────────────
with tab_timeseries:
    st.subheader("Series Temporales Espectrales — NDVI / NDMI por Activo")
    st.caption(
        "Selecciona un activo para visualizar su evolución espectral mensual. "
        "Las bandas rojas marcan períodos de estrés hídrico crítico (Z-score NDVI < −1,5), "
        "donde la sequía coincide con el sobreuso turístico documentado."
    )

    # ── Panel: Tendencias satelitales REALES (Mann-Kendall multianual) ─────────
    # Selector de parque (v1.2.0 Red OAPN): sólo se muestra cuando hay más de un
    # parque con análisis real en disco. Con sólo PNSG, la UI no cambia.
    _parks = available_parks() or [DEFAULT_PARK]
    _selected_park = DEFAULT_PARK
    if len(_parks) > 1:
        _selected_park = st.selectbox(
            "Parque Nacional",
            options=_parks,
            index=_parks.index(DEFAULT_PARK) if DEFAULT_PARK in _parks else 0,
            format_func=park_label,
            help="Red de Parques Nacionales (OAPN). Cada parque tiene su propia "
                 "serie Sentinel-2 real analizada con Mann-Kendall.",
            key="real_trend_park",
        )
    _real_trends = _cached_trends(_selected_park)
    _park_name = park_label(_selected_park)
    if _real_trends.available:
        # Rango temporal real derivado de los datos (no hardcodeado)
        _all_years = sorted({y for a in _real_trends.assets for y in a.annual_mean_ndvi})
        _yr_lo, _yr_hi = (_all_years[0], _all_years[-1]) if _all_years else ("", "")
        st.markdown(f"#### 🛰️ Tendencias satelitales reales · Sentinel-2 {_yr_lo}–{_yr_hi}")
        st.caption(
            f"Análisis **Mann-Kendall** sobre activos reales de **{_park_name}** con "
            "imágenes Sentinel-2 (Pipeline GEE). A diferencia del gráfico mensual de más "
            "abajo (reconstrucción de validación), **estos resultados son empíricos**, "
            "calculados sobre la serie **desestacionalizada** (ver nota abajo)."
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Activos analizados", len(_real_trends.assets))
        m2.metric("Degradación ↘ (p<0,05)", _real_trends.n_degrading)
        m3.metric("Mejora ↗ (p<0,05)", _real_trends.n_improving)
        m4.metric("Estables →", _real_trends.n_stable)

        st.info(
            "**Nota metodológica (v1.1.1):** el test de Mann-Kendall se calcula sobre "
            "la serie **desestacionalizada** (descomposición armónica de 2 componentes, "
            "Julien & Sobrino 2009) con **corrección de empates** en la varianza "
            "(Hipel & McLeod 1994) y **pendiente de Sen con intervalo de confianza "
            "no paramétrico** (Gilbert 1987). Los 7 veredictos significativos superan, "
            "además, una prueba de robustez de *pre-whitening* libre de tendencia "
            "(Yue-Pilon 2002) sin ningún cambio de dirección — la autocorrelación serial "
            "no explica las tendencias detectadas. Ver `docs/nota_metodologica_temporalidad.md`.",
            icon="🔬",
        )

        if _real_trends.worst_year_global:
            st.caption(
                f"📉 **Señal climática:** {_real_trends.worst_year_global} es el peor año NDVI "
                f"en la mayoría de activos — coincide con la sequía excepcional documentada "
                f"(la peor en España desde 1945). Validación cruzada del pipeline."
            )

        if _real_trends.partial_years:
            st.caption(
                f"⏳ **Año parcial:** {', '.join(_real_trends.partial_years)} aún no tiene la "
                f"temporada completa (faltan meses de verano), por lo que se incluye en la serie "
                f"mensual pero **se excluye del ranking peor/mejor año** para una comparación justa."
            )

        for _alert in _real_trends.alerts:
            _last = list(_alert.annual_mean_ndvi.values())
            _drop = (_last[0] - _last[-1]) if len(_last) >= 2 else 0.0
            _slope_txt = (
                f", pendiente {_alert.sens_slope:.5f} NDVI/mes "
                f"[{_alert.sens_slope_ci[0]:.5f}, {_alert.sens_slope_ci[1]:.5f}] IC95%"
                if _alert.sens_slope is not None and _alert.sens_slope_ci else ""
            )
            st.warning(
                f"**Alerta de degradación · {_alert.asset_id}** — NDVI {_alert.trend_es} "
                f"significativo (τ={_alert.tau:.3f}, p={_alert.p_value:.3f}{_slope_txt}). "
                f"Peor año {_alert.worst_year}, mejor {_alert.best_year}. "
                f"Candidato a inspección de campo.",
                icon="⚠️",
            )

        with st.expander(
            f"📋 Tabla completa de tendencias reales ({len(_real_trends.assets)} activos)",
            expanded=False,
        ):
            import pandas as pd
            _df = pd.DataFrame([
                {
                    "Activo": a.asset_id,
                    "Categoría": a.category,
                    "Tendencia": a.trend_es,
                    "τ (Kendall)": round(a.tau, 3),
                    "p-valor": round(a.p_value, 3),
                    "Signif.": "✓" if a.significant else "",
                    "Pendiente Sen (NDVI/mes)": round(a.sens_slope, 5) if a.sens_slope is not None else None,
                    "Peor año": a.worst_year,
                    "Mejor año": a.best_year,
                    "Meses": a.n_observations,
                }
                for a in _real_trends.assets
            ])
            st.dataframe(_df, use_container_width=True, hide_index=True)

        # ── Gráfico multianual REAL (NDVI medio anual 2021→2026) ───────────────
        # Se elige directamente sobre los activos reales del Pipeline GEE del
        # parque seleccionado (no depende del emparejamiento difuso con los
        # activos curados, que no siempre resuelve). Serie EMPÍRICA, no simulada.
        st.markdown("##### 📈 Serie anual real por activo (Sentinel-2)")
        _real_labels = {
            f"{a.asset_id}  ·  {a.trend_es}": a for a in _real_trends.assets
        }
        _sel_real = st.selectbox(
            "Activo real (GEE) a graficar",
            options=list(_real_labels.keys()),
            index=0,
            help="Activos reales analizados con Mann-Kendall sobre NDVI 2021–2026.",
            key="real_trend_asset",
        )
        _ra = _real_labels[_sel_real]
        try:
            st.plotly_chart(build_real_trend_chart(_ra), use_container_width=True)
            if _ra.partial_years:
                st.caption(
                    f"○ El año {', '.join(_ra.partial_years)} es **parcial** (sin "
                    f"temporada completa): marcador hueco y excluido del ranking "
                    f"peor/mejor año."
                )
        except Exception as _e:
            st.warning(f"No se pudo renderizar la serie anual real: {_e}", icon="⚠️")

        st.divider()

    # ── Selector de activo (prefijo de tier NEUTRO, no semafórico) ────────────
    _TIER_PREFIX = {1: "TIER I", 2: "TIER II", 3: "TIER III", 4: "TIER IV"}

    def _asset_label(a) -> str:
        prefix = _TIER_PREFIX.get(a.tier, "TIER —")
        return f"[{prefix}] · {a.name} ({a.region})"

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
    _, tier_accent = _TIER_BADGE_COLOR.get(tier, ("#2d2f4a", "#a9adcb"))
    ehs_c = _ehs_color(selected_asset.ehs)
    st.markdown(
        f'<div style="margin-bottom:6px">{_tier_chip(selected_asset.tier)}'
        f'{_alert_chip(selected_asset.alert_level)}</div>',
        unsafe_allow_html=True,
    )
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {ehs_c};">'
            f'<div class="kpi-meta">EHS</div>'
            f'<div class="kpi-value" style="color:{ehs_c}">{selected_asset.ehs:.0f}<span style="font-size:.9rem;color:#9aa4af">/100</span></div>'
            f'</div>', unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {tier_accent};">'
            f'<div class="kpi-meta">DCS</div>'
            f'<div class="kpi-value">{selected_asset.dcs:.0f}<span style="font-size:.9rem;color:#9aa4af">/100</span></div>'
            f'</div>', unsafe_allow_html=True)
    with kpi_cols[2]:
        tpi_val = f"{selected_asset.tpi:.0f}" if selected_asset.tpi else "—"
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {tier_accent};">'
            f'<div class="kpi-meta">TPI</div>'
            f'<div class="kpi-value">{tpi_val}</div>'
            f'</div>', unsafe_allow_html=True)
    with kpi_cols[3]:
        vis = f"{selected_asset.visitor_capacity_annual:,}"
        st.markdown(
            f'<div class="kpi-card" style="border-left:4px solid {tier_accent};">'
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

    # ── Detalle modulado por vista/audiencia ──────────────────────────────────
    _trend_es = {"decreasing": "↘ deterioro", "increasing": "↗ mejora",
                 "no_trend": "→ estable"}.get(selected_asset.trend_direction, "→ estable")
    if _view.simplified:
        # GESTOR: una sola línea, sin jerga estadística.
        st.info(
            f"**Tendencia:** {_trend_es} · **Salud (EHS)** {selected_asset.ehs:.0f}/100. "
            f"{'Requiere actuación.' if (selected_asset.tier or 5) <= 2 else 'Bajo control.'}",
            icon="🧭",
        )
    if _view.technical:
        # TÉCNICA / AUDITORÍA: estadística cruda del activo.
        _sig = "significativa (p<0,05)" if selected_asset.mk_p_value < 0.05 else "no significativa"
        st.caption(
            f"🔬 **Mann-Kendall:** dirección `{selected_asset.trend_direction}` · "
            f"p-valor **{selected_asset.mk_p_value:.3f}** ({_sig}) · "
            f"**DCS** {selected_asset.dcs:.0f}/100 · "
            f"**SCM** {selected_asset.scm_classification} "
            f"(confianza {selected_asset.scm_confidence}) · "
            f"riesgo {selected_asset.risk_score:.2f}."
        )

    # ── Contraste con la tendencia satelital REAL del activo (si existe) ───────
    if _real_trends.available:
        _matched = find_trend(selected_asset.name, _real_trends.assets)
        if _matched is not None:
            _sig_es = "significativa (p<0,05)" if _matched.significant else "no significativa"
            _m_years = sorted(_matched.annual_mean_ndvi)
            _m_range = f"{_m_years[0]}–{_m_years[-1]}" if _m_years else ""
            _slope_es = (
                f", pendiente Sen {_matched.sens_slope:.5f} NDVI/mes "
                f"[{_matched.sens_slope_ci[0]:.5f}, {_matched.sens_slope_ci[1]:.5f}] IC95%"
                if _matched.sens_slope is not None and _matched.sens_slope_ci else ""
            )
            st.success(
                f"🛰️ **Dato satelital real ({_m_range}):** este activo corresponde a "
                f"`{_matched.asset_id}`. Tendencia NDVI empírica **{_matched.trend_es}** "
                f"(τ={_matched.tau:.3f}, p={_matched.p_value:.3f}, {_sig_es}{_slope_es}) "
                f"sobre {_matched.n_observations} meses, serie desestacionalizada. "
                f"Peor año {_matched.worst_year}, mejor {_matched.best_year}.",
                icon="✅",
            )

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
  TIER {_TIER_ROMAN.get(selected_asset.tier or 3, "III")} (prioridad de inversión).
  La serie mensual es una reconstrucción de validación; el EHS satelital real de su
  senda (Sentinel-2, Pipeline A) se contrasta en la pestaña *Diagnóstico Satelital*.
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
    with st.expander("ℹ️ Qué significa «Capacidad de Visitantes Protegida»", expanded=False):
        st.markdown(
            "Es la **suma de `visitor_capacity_annual`** de los activos que el presupuesto "
            "consigue financiar — es decir, la **capacidad de acogida bajo gestión/mitigación**, "
            "no un conteo de empleos salvados ni de visitantes reales contabilizados.\n\n"
            "- `visitor_capacity_annual` es un **atributo curado del activo** (parámetro de "
            "planificación), no un aforo medido. Por eso esta cifra es un **indicador de "
            "cobertura del escenario**, no una predicción de afluencia.\n"
            "- El delta compara el escenario seleccionado con la base de €100.000.\n\n"
            "Clasificación y trazabilidad en la pestaña **8️⃣ Fundamento y Trazabilidad**."
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
    st.markdown(
        method.scenario_badge(
            "MODELO PROSPECTIVO",
            "cifras de escenario, no economía observada",
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        "Vincula la salud ecológica con la resiliencia económica local. Las cifras de gasto "
        "y empleo de esta pestaña que dependen del proxy de visitantes son **estimaciones "
        "condicionales (análisis prospectivo)**, no observaciones. La **exposición económica** "
        "estima el gasto turístico que estaría en riesgo *bajo el supuesto* de que un activo "
        "Tier 1 se degrade hasta requerir cierre preventivo — no es una pérdida observada. "
        "Las cifras ALMUDENA/INE (población, empleo en hostelería) sí son dato real y se "
        "etiquetan como tal."
    )
    with st.expander("🧪 Fundamento, fórmulas e incertidumbre del modelo económico", expanded=False):
        st.markdown(
            "Este modelo responde a *«¿cuánto valor turístico estaría expuesto SI un activo "
            "crítico se degrada hasta requerir cierre?»*. Es un **escenario**, útil para "
            "comparar el coste de intervenir frente al de no hacerlo, pero condicionado por "
            "supuestos. Trazabilidad completa y sensibilidad en la pestaña "
            "**8️⃣ Fundamento y Trazabilidad**."
        )
        method.render_multiplier_table()

    # ── F9: Datos socioeconómicos reales (ALMUDENA / INE) ─────────────────────
    if _socio:
        _snap = _socio["snapshot"]
        _svi = _socio["svi"]
        _risk = _socio["risk"]
        _jobs = _socio["jobs"]

        st.markdown(
            '<div style="padding:8px 12px;border-radius:6px;margin:2px 0 10px;'
            'background:#0d2818;color:#E1F5EE;font-size:0.82rem;border-left:4px solid #0F6E56">'
            f'🟢 <b>Datos reales</b> · ALMUDENA (Banco de Datos Municipal, C. de Madrid) '
            f'+ INE (Padrón, EOATR). Snapshot {_snap.source_snapshot_date} · '
            f'{_snap.n_municipalities} municipios del PNSG ({_snap.n_full} con economía '
            f'ALMUDENA, {_snap.n_demographic_only} solo demografía — lado Segovia).</div>',
            unsafe_allow_html=True,
        )

        _muni_ids = list(_risk.keys())
        _pop = sum((_snap.municipalities[i].population or 0) for i in _muni_ids)
        _emp = sum((_snap.municipalities[i].tourism_employment or 0) for i in _muni_ids)
        _svi_vals = [_svi[i].svi for i in _muni_ids if i in _svi]
        _svi_mean = sum(_svi_vals) / len(_svi_vals) if _svi_vals else 0.0

        _rk = st.columns(4)
        for _col, _name, _val, _fg in [
            (_rk[0], "Población de la comunidad",            f"{_pop:,.0f} hab", "#1565c0"),
            (_rk[1], "Empleo en hostelería (afiliados SS)",  f"{_emp:,.0f}",     "#0F6E56"),
            (_rk[2], "Empleos locales en riesgo",            f"{_jobs.total:,.1f}", "#c62828"),
            (_rk[3], "SVI medio (comunidades con activos)",  f"{_svi_mean:.1f}/100", "#854F0B"),
        ]:
            with _col:
                st.markdown(
                    f'<div class="kpi-card" style="border-left:4px solid {_fg};">'
                    f'<div class="kpi-meta">{_name}</div>'
                    f'<div class="kpi-value" style="color:{_fg};font-size:1.4rem">{_val}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.write("")

        st.markdown(
            "**Comunidades locales en riesgo** — riesgo ambiental × dependencia económica"
        )
        _svi_rows = []
        for i in _muni_ids:
            m, s = _snap.municipalities[i], _svi[i]
            _svi_rows.append({
                "Municipio": m.name,
                "Impacto comunidad": s.community_impact,
                "SVI": s.svi,
                "Dependencia turística": s.dep,
                "Fragilidad demográfica": s.dem,
                "Exposición ambiental": s.exp,
                "Población": m.population,
                "Empleo hostelería": m.tourism_employment,
                "% ≥65 años": m.pct_over_65,
                "Δ pob. 5 años (%)": m.pop_change_5y_pct,
            })
        _svi_df = pd.DataFrame(_svi_rows).sort_values(
            "Impacto comunidad", ascending=False, na_position="last"
        )
        st.dataframe(
            _svi_df, use_container_width=True, hide_index=True,
            column_config={
                "Impacto comunidad": st.column_config.ProgressColumn(
                    "Impacto comunidad", min_value=0, max_value=100, format="%.1f"),
                "SVI": st.column_config.NumberColumn(format="%.1f"),
                "Dependencia turística": st.column_config.NumberColumn(format="%.2f"),
                "Fragilidad demográfica": st.column_config.NumberColumn(format="%.2f"),
                "Exposición ambiental": st.column_config.NumberColumn(format="%.2f"),
                "Población": st.column_config.NumberColumn(format="%d"),
                "Empleo hostelería": st.column_config.NumberColumn(format="%d"),
                "% ≥65 años": st.column_config.NumberColumn(format="%.1f"),
                "Δ pob. 5 años (%)": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        st.caption(
            "**SVI** = 0,40·Dependencia turística + 0,30·Fragilidad demográfica + "
            "0,30·Exposición ambiental (pesos renormalizados sobre los componentes "
            "disponibles). **Impacto comunidad** = exposición ambiental × dependencia "
            "económica. Fuentes: ALMUDENA (hostelería, viviendas no principales, renta), "
            "INE Padrón (población, envejecimiento, despoblación)."
        )

        if _view.confidence_detail == ConfidenceDetail.FULL:
            with st.expander("⚖️ Procedencia y límites declarados (vista auditoría)", expanded=False):
                st.markdown(
                    "**Procedencia por fuente:**\n\n"
                    f"- {_snap.sources.get('demographics', 'INE Padrón')}\n"
                    f"- {_snap.sources.get('economy_tourism', 'ALMUDENA')}\n"
                    f"- Crosswalk: {_snap.sources.get('crosswalk', '')}\n\n"
                    "**Límites declarados:**\n\n"
                    "- ALMUDENA solo cubre la Comunidad de Madrid: los municipios del lado "
                    "de Segovia tienen SVI parcial (solo fragilidad demográfica).\n"
                    "- EOATR (turismo rural) se publica por zona turística PNSG, no por municipio.\n"
                    "- Municipios diminutos (<1.000 hab): indicadores volátiles / secreto estadístico.\n"
                    "- Desfase temporal: socioeconómico (padrón 2025 / renta 2023) vs satélite "
                    "(2025-26). Es contexto de enriquecimiento, no afirmación causal."
                )
                _cav = [
                    (_snap.municipalities[i].name, c)
                    for i in _muni_ids for c in _snap.municipalities[i].caveats
                ]
                if _cav:
                    st.markdown("**Avisos por municipio:**")
                    for _nm, _c in _cav:
                        st.markdown(f"- *{_nm}*: {_c}")

        st.divider()
        st.markdown(
            '<div style="font-size:0.72rem;color:#7a8899">Modelo proxy heredado '
            '(gasto por visitante y ratio coste-beneficio) — útil para comparar '
            'escenarios presupuestarios, pero basado en estimaciones, no en ALMUDENA/INE:</div>',
            unsafe_allow_html=True,
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
        (e_col1, "Ingresos potencialmente en riesgo (escenario)",
         f"€{total_revenue_risk:,.0f}", "#c62828", "#ffebee"),
        (e_col2, "Empleos vinculados al turismo (estimación)",
         f"{total_jobs_linked:.0f} empleos", "#1565c0", "#e3f2fd"),
        (e_col3, "Empleos expuestos a degradación (escenario)",
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

    # ── Análisis de sensibilidad del parámetro de mayor influencia ────────────
    # El gasto/visitante (€22,50) es un multiplicador lineal: escala toda la
    # exposición de ingresos. En vez de presentarlo como punto único, mostramos
    # una banda ±20% (escenario bajo / central / alto) para hacer explícita la
    # incertidumbre, sin alterar el valor por defecto del modelo.
    _SENS_DELTA = 0.20
    _sens = {
        "Escenario bajo (−20% gasto/visitante)":  (total_revenue_risk * (1 - _SENS_DELTA), "#558b2f"),
        "Central (€22,50 · MITECO 2023)":          (total_revenue_risk,                     "#c62828"),
        "Escenario alto (+20% gasto/visitante)":   (total_revenue_risk * (1 + _SENS_DELTA), "#6a1b9a"),
    }
    st.markdown(
        "**Análisis de sensibilidad** — exposición total de ingresos según el gasto/visitante "
        "(€%.2f), el multiplicador más influyente del modelo:" % _SPEND_PER_VISITOR_EUR
    )
    _scol = st.columns(3)
    for _c, (_lbl, (_v, _fg)) in zip(_scol, _sens.items()):
        with _c:
            st.markdown(
                f'<div class="kpi-card" style="border-left:4px solid {_fg};">'
                f'<div class="kpi-meta">{_lbl}</div>'
                f'<div class="kpi-value" style="color:{_fg};font-size:1.25rem">€{_v:,.0f}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.caption(
        "Banda lineal ±20% sobre el gasto/visitante. Es un **análisis prospectivo de "
        "incertidumbre** sobre un parámetro estimado, no un rango de confianza estadístico. "
        "Trazabilidad y sensibilidad de todos los multiplicadores en la pestaña "
        "**8️⃣ Fundamento y Trazabilidad**."
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
        name="Ingresos potencialmente en riesgo (escenario, €/año)",
        orientation="h",
        marker=dict(color="#c62828", opacity=0.80),
        hovertemplate="<b>%{y}</b><br>Ingresos en riesgo (escenario): €%{x:,}<extra></extra>",
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
            text="Escenario de exposición económica vs coste de intervención — Tier 1 y 2",
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
        name="Empleos vinculados (estimación)",
        orientation="h",
        marker=dict(color="#1565c0", opacity=0.75),
        hovertemplate="<b>%{y}</b><br>Empleos vinculados (estimación): %{x:.1f}<extra></extra>",
    ))
    fig_jobs.add_trace(go.Bar(
        y=muni_grp["Municipio"],
        x=muni_grp["jobs_risk"],
        name="Empleos expuestos (escenario)",
        orientation="h",
        marker=dict(color="#e65100", opacity=0.85),
        hovertemplate="<b>%{y}</b><br>Empleos expuestos (escenario): %{x:.1f}<extra></extra>",
    ))
    fig_jobs.update_layout(
        title=dict(
            text="Empleos vinculados al turismo natural por municipio (estimación proxy)",
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
                    st.column_config.NumberColumn("Ingresos en riesgo · escenario (€)", format="€%d"),
                "Empleos\nVinculados":   st.column_config.NumberColumn("Empleos vinc. (est.)", format="%.1f"),
                "Empleos\nen Riesgo":    st.column_config.NumberColumn("Empleos expuestos (esc.)", format="%.2f"),
                "Coste Intervención (€)":
                    st.column_config.NumberColumn("Coste Interv. (€)", format="€%d"),
                "ROI Conservación":      st.column_config.NumberColumn("Ratio coste-beneficio (esc.)", format="%.1fx"),
            },
        )

    # ── Nota metodológica ─────────────────────────────────────────────────────
    with st.expander("ℹ️ Metodología económica (modelo prospectivo / escenario)", expanded=False):
        st.markdown(
            f"""
⚠️ **Naturaleza de las cifras:** este es un **modelo de escenario condicional**, no una
medición. Parte de `visitor_capacity_annual`, que es un **atributo curado del activo**
(no un aforo real de visitantes), y de parámetros de literatura. Sus resultados son
**análisis prospectivo**, no economía observada ni predicción.

**Parámetros del modelo de gasto turístico:**

| Parámetro | Valor | Origen | Tipo |
|---|---|---|---|
| Gasto medio diario por visitante | **€{_SPEND_PER_VISITOR_EUR:.2f}** | MITECO / Informe de turismo de naturaleza 2023 | Estimada |
| Visitantes por empleo directo+indirecto | **{_VISITORS_PER_JOB:,}** | Proxy para ecoturismo rural (sin cita dura) | Estimada |
| Factor de riesgo de cierre — Tier 1 (sin fondos) | **100%** | Supuesto de política (cierre preventivo) | Estimada |
| Factor de riesgo de cierre — Tier 2 (sin fondos) | **40%** | Supuesto (reducción parcial de afluencia) | Estimada |
| Factor de riesgo residual — Tier 1 **con fondos** | **15%** | Supuesto (riesgo durante restauración) | Estimada |

**Exposición económica (antes 'coste de no actuar'):** *bajo el supuesto* de que un activo
Tier 1 se degrade hasta requerir cierre preventivo, el gasto turístico local asociado
quedaría en riesgo. Se **estima** como `visitantes × €{_SPEND_PER_VISITOR_EUR:.2f} × factor_riesgo`.
No es una pérdida observada ni una predicción de pérdida.

**Ratio coste-beneficio del escenario (antes 'ROI'):** cociente entre los ingresos
*potencialmente* protegidos y el coste único de la intervención. Un ratio > 1× indica que,
*en el escenario*, la inversión equivale a más de un año de ingresos protegidos. Es un
indicador comparativo de escenario, no un retorno financiero realizado.

> Sensibilidad y trazabilidad completas en la pestaña **8️⃣ Fundamento y Trazabilidad**.
            """
        )


# ── Tab 2: Diagnóstico Satelital y Mapa (corazón científico) ──────────────────
# Fusiona el mapa territorial (gestión/espectral) con las sendas reales del
# Pipeline A (Sentinel-2). El bloque del mapa se ejecuta primero (arriba) y el
# de sendas reales después (abajo), ambos dentro de la misma pestaña.
with tab_diagnostic:
    st.subheader("Diagnóstico Satelital y Mapa — Visión Espacial del Territorio")
    st.caption(
        "Corazón científico del observatorio: el mapa territorial (gestión / "
        "diagnóstico espectral) y, debajo, las **sendas reales** medidas por "
        "Sentinel-2 (Pipeline A) con su EHS y ΔEHS observados."
    )

    with st.expander("📐 Nota metodológica — índices espectrales, EHS y convención de signo",
                     expanded=_view.technical):
        st.markdown("**Índices espectrales (Sentinel-2 L2A, tile T30TVL):**")
        st.latex(r"NDVI = \frac{NIR - RED}{NIR + RED}\ \ (B08, B04) \qquad "
                 r"NDMI = \frac{NIR - SWIR}{NIR + SWIR}\ \ (B08, B11)")
        st.markdown(
            "- **NDVI** — vigor de la vegetación.\n"
            "- **NDMI** — contenido hídrico foliar; detecta estrés que el NDVI no ve "
            "cuando el dosel aún está verde.\n"
            "- En **dosel denso** (NDVI ≥ 0,80, p. ej. hayedos) el NDVI **satura**: el peso "
            "del EHS se desplaza hacia el NDMI (y se usa EVI para la línea base) para no "
            "perder sensibilidad."
        )
        st.markdown(
            "**EHS por senda (Δ estacional):** se ancla en percentiles de la *propia "
            "escena*, no en constantes arbitrarias:"
        )
        st.latex(r"D_x = \mathrm{clamp}\!\left(\frac{P_{90} - \bar{x}}{P_{90} - P_{10}}\right)"
                 r"\qquad EHS = 100\,(w_{NDVI}\,D_{NDVI} + w_{NDMI}\,D_{NDMI})")
        st.markdown(
            "donde **P90** (`EHS_P_BASE`) es la referencia sana y **P10** (`EHS_P_FLOOR`) el "
            "suelo degradado, calculados tras excluir píxeles enmascarados por SCL y el propio "
            "buffer de 50 m de la senda (para no medir el problema dentro de la referencia).\n\n"
            "**Convención de signo (clave para auditar):** el Pipeline A calcula *estrés* "
            "(0 = sano, 100 = degradado); el dashboard habla *salud* (0 = crítico, 100 = sano). "
            "La conversión es **única**, en `src/platform/real_trails.py` (`stress_to_health`), "
            "de modo que todo el dashboard usa **alto = sano**. El **ΔEHS = salud_primavera − "
            "salud_verano**: ΔEHS negativo = deterioro estival.\n\n"
            "**Override conservador (Fase 2):** cuando el EHS satelital de la senda es *más "
            "degradado* que el juicio experto, **sobreescribe** al curado y escala tier/alerta; "
            "cuando es *más verde*, se mantiene el curado (posible geología, no degradación)."
        )

    # ── Control de modo de visualización ─────────────────────────────────────
    map_mode = st.radio(
        "Modo de visualización",
        options=["🗂️ Vista de Gestión (Tiers)", "🛰️ Vista de Diagnóstico Espectral (NDVI/NDMI)"],
        index=0,
        horizontal=True,
        help=(
            "**Vista de Gestión:** activos coloreados por tier de prioridad de inversión "
            "(escala neutra índigo→pizarra, NO semafórica). "
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

    # Geometrías reales (Pipeline A) por activo, para dibujar sobre su traza real
    _real_geoms = asset_trail_geometries(selected_key, ranked_assets)
    _n_real = sum(1 for g in _real_geoms.values() if g)
    if _n_real:
        st.caption(
            f"📍 **{_n_real} de {len(ranked_assets)}** activos se dibujan sobre su **traza "
            f"cartográfica real** (senda del Pipeline A · Sentinel-2). El resto, sin senda "
            f"OSM/OAPN equivalente, se sitúa en el **centroide municipal aproximado** "
            f"(≈, indicado en el tooltip)."
        )

    col_map, col_info = st.columns([3, 1])

    with col_map:
        try:
            _mc = _terr_cfg["map_center"]
            if spectral_mode:
                deck = build_pydeck_deck_spectral(ranked_assets, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2], real_geoms=_real_geoms)
            else:
                deck = build_pydeck_deck(ranked_assets, map_lat=_mc[0], map_lon=_mc[1], map_zoom=_mc[2], real_geoms=_real_geoms)
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
            # ── Leyenda de tiers (prioridad de inversión, escala neutra) ─────
            st.markdown("#### Distribución por tier (inversión)")
            tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            for a in ranked_assets:
                if a.tier in tier_counts:
                    tier_counts[a.tier] += 1
            for item in LEGEND_ITEMS:
                t     = item["tier"]
                count = tier_counts.get(t, 0)
                color = item["hex"]
                label = item["label"]
                st.markdown(
                    f'<div style="margin-bottom:8px;">'
                    f'<span class="legend-chip" style="background:{color};'
                    f'border:1px solid rgba(0,0,0,.12)"></span>'
                    f'<b style="color:#0d1b2a">{count}</b>'
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
            f"📍 Geometría: {_n_real}/{len(ranked_assets)} activos sobre su **traza real** "
            "(senda Pipeline A · Sentinel-2); los demás en **centroide municipal aproximado** "
            "(≈, mapeo activo↔senda en `calibration._ASSET_TRAIL_MAP`)."
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
        f'en la pestaña <i>Diagnóstico Satelital y Mapa</i>. No usar para intervención formal sin '
        f'el dato satelital de su senda.</div>',
        unsafe_allow_html=True,
    )

    # ── Validación cruzada con el satélite (Pipeline A) ───────────────────────
    # Se reutiliza la calibración calculada en load_dashboard (contra el EHS
    # curado ORIGINAL, antes del override) para no falsear la concordancia.
    # Modulada por vista: GESTOR ve solo el titular; TÉCNICA/AUDITORÍA, el detalle.
    _calib = calibration
    _cov = coverage_summary(_calib)
    if _view.simplified:
        st.caption(
            f"🛰️ Validación satelital: **{_cov['mas_degradado']}** activo(s) con override "
            f"(satélite más degradado), **{_cov['confirma']}** confirmados, "
            f"**{_cov['sin_dato']}** sin senda equivalente. Detalle metodológico en la vista "
            f"de Auditoría científica."
        )
    else:
        with st.container():
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("✓ Satélite confirma", _cov["confirma"])
            cc2.metric("⚠ Satélite más verde", _cov["mas_sano"])
            cc3.metric("⚠ Satélite más degradado (override)", _cov["mas_degradado"])
            cc4.metric("— Sin senda equivalente", _cov["sin_dato"])
        st.caption(
            "**Validación cruzada + override conservador:** cada activo curado se contrasta "
            "con el EHS satelital real de su senda concreta (Pipeline A · Sentinel-2). "
            "El EHS curado mide *salud bajo presión turística* (juicio experto); el "
            "satelital mide *verdor de la vegetación* (NDVI/NDMI). Política aplicada: cuando "
            "el satélite ve **más degradación** que el experto (*más degradado*), el dato "
            "satelital **sobreescribe** el EHS curado y escala tier/alerta en todo el "
            "dashboard. Cuando el satélite es **más verde** (*más verde*) se mantiene el "
            "juicio curado, porque en alta montaña la roca/canchal alpino tiene poco NDVI "
            "por geología, no por turismo. Así el satélite **escala**, nunca relaja, el "
            "diagnóstico experto."
        )
        if _view.audit:
            with st.expander("⚖️ Procedencia y límites declarados (vista auditoría)", expanded=False):
                _real_badge = data_status_badge(DataStatus.REAL)
                _syn_badge = data_status_badge(DataStatus.SYNTHETIC)
                st.markdown(
                    f"- {_real_badge.emoji} **EHS satelital:** {_real_badge.caveat} "
                    f"Fuente Sentinel-2 L2A, tile T30TVL (Pipeline A).\n"
                    f"- {_syn_badge.emoji} **EHS curado:** juicio experto de salud bajo presión "
                    f"turística; capa narrativa contrastada (no sustituida al alza) por el satélite.\n"
                    f"- **Override conservador:** solo escala cuando el satélite ve más "
                    f"degradación (`mas_degradado`); nunca relaja el diagnóstico experto.\n"
                    f"- **Mapeo activo↔senda:** `calibration._ASSET_TRAIL_MAP` "
                    f"(solo correspondencias toponímicas defendibles; el resto, SIN_DATO).\n"
                    f"- **Límites:** resolución ~10–30 m; sendas sin equivalente OSM/OAPN no "
                    f"calibran; concordancia con banda ±12 EHS."
                )
    st.divider()

    # Filtros
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        tier_filter = st.multiselect(
            "Filtrar por Tier (prioridad de inversión)", options=[1, 2, 3, 4],
            default=[1, 2, 3, 4],
            format_func=lambda t: f"TIER {_TIER_ROMAN[t]} — {_TIER_INVEST_LABEL[t]}",
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
        tier_fg, tier_bg = _TIER_BADGE_COLOR.get(tier, ("#2d2f4a", "#a9adcb"))
        ehs_c  = _ehs_color(asset.ehs)
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
            f"""<div class="kpi-card" style="border-left:5px solid {tier_bg};margin-bottom:0.5rem;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:1.8rem;line-height:1">{emoji}</div>
    <div style="flex:1">
      <div style="font-size:0.95rem;font-weight:700;color:#0d1b2a">
        #{rank}&ensp;{asset.name}
      </div>
      <div style="font-size:0.75rem;color:#7a8899;margin-top:2px">
        {asset.region}{physical}
      </div>
      <div style="margin-top:5px">{_tier_chip(tier)}{_alert_chip(asset.alert_level)}</div>
    </div>
    <div style="text-align:right;min-width:120px">
      <span style="font-size:1.1rem;font-weight:700;color:{ehs_c}">
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


# ── Tab 2 (continúa): Sendas reales del Pipeline A, debajo del mapa ───────────
with tab_diagnostic:
    st.divider()
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
        # Confianza modulada por la vista/audiencia activa (F7).
        if _view.confidence_detail is ConfidenceDetail.FULL:
            st.warning(_prov.caveat, icon="⚠️")
            st.caption(
                f"🔎 Trazabilidad: {_prov.inference_label} "
                "Metodología y límites en docs/temporal_series_design.md y "
                "docs/baselines_uncertainty_design.md."
            )
        elif _view.confidence_detail is ConfidenceDetail.CONCISE:
            _ok = "usar como prioridad, no como orden de gasto"
            st.caption(f"⚠️ Confianza: señal de alerta temprana — {_ok}.")
        else:  # RAW (técnica): el dato crudo va en los KPIs y la tabla de abajo
            st.caption(f"⚠️ {_prov.caveat}")

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


# ── Tab 8: Fundamento y Trazabilidad ──────────────────────────────────────────
with tab_method:
    render_tab_method()


# ── Pie de página ─────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f'<div style="font-size:0.72rem;color:#9aa4af;text-align:center;padding:4px 0 2px;">'
    f'Smart Natural Tourism Observatory (SNTO) v{__version__} · '
    f'Capa de inteligencia para la decisión en espacios naturales protegidos · '
    f'{dashboard.territory_name} · Madrid (España) · '
    f'Sentinel-2 real (PNSG) + capa socioeconómica INE/ALMUDENA + activos de calibración'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div style="font-size:0.66rem;color:#9aa4af;text-align:center;padding:0 0 8px;">'
    'Fuentes de datos: Contiene datos Copernicus Sentinel-2 modificados (ESA) · '
    'cartografía © OpenStreetMap (ODbL) y OAPN (Red de Parques Nacionales) · '
    'INE (Padrón, EOATR) · ALMUDENA, Comunidad de Madrid · '
    'Procedencia y licencias en la pestaña «Fundamento y Trazabilidad».'
    '</div>',
    unsafe_allow_html=True,
)
