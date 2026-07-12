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
from src.platform import compute_executive_dashboard
from src.platform.map_layers import LEGEND_ITEMS
from src.platform.enrichment import enrich_assets_with_satellite
from src.platform.views import ViewMode, get_view, view_modes
from src.socioeconomic.loader import load_municipalities, snapshot_exists
from src.socioeconomic.indicators import (
    aggregate_asset_risk, compute_svi, jobs_at_risk as compute_jobs_at_risk,
)
from src.ui.render_widgets import (
    _compute_exec_kpis, _render_banner, _render_exec_kpis, _render_live_alerts,
)
from src.ui.tabs.tab_kpis import render_tab_kpis
from src.ui.tabs.tab_method import render_tab_method
from src.ui.tabs.tab_portfolio import render_tab_portfolio
from src.ui.tabs.tab_assets import render_tab_assets
from src.ui.tabs.tab_diagnostic import render_tab_diagnostic
from src.ui.tabs.tab_simulator import render_tab_simulator
from src.ui.tabs.tab_socioeco import render_tab_socioeco
from src.ui.tabs.tab_timeseries import render_tab_timeseries

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
    render_tab_portfolio(ranked_assets)


# ── Tab 3: Series Temporales Espectrales ─────────────────────────────────────
with tab_timeseries:
    render_tab_timeseries(ranked_assets, _view)


# ── Tab 4: Simulador Financiero What-If ──────────────────────────────────────
with tab_simulator:
    render_tab_simulator(base_comps, assets_by_id, base_budget, ranked_assets)


# ── Tab 5: Impacto Socioeconómico ─────────────────────────────────────────────
with tab_socioeco:
    render_tab_socioeco(_socio, base_comps, ranked_assets, base_budget, _view)


# ── Tab 2: Diagnóstico Satelital y Mapa (corazón científico) ──────────────────
# Fusiona el mapa territorial (gestión/espectral) con las sendas reales del
# Pipeline A (Sentinel-2). El bloque del mapa se ejecuta primero (arriba) y el
# de sendas reales después (abajo), ambos dentro de la misma pestaña.
with tab_diagnostic:
    render_tab_diagnostic(selected_key, _terr_cfg, ranked_assets, _view)


# ── Tab 7: Catálogo de activos ────────────────────────────────────────────────
with tab_assets:
    render_tab_assets(calibration, ranked_assets, _view)


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
