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
from src.platform.map_layers import LEGEND_ITEMS
from src.platform.views import ViewMode, get_view, view_modes
from src.platform.telemetry import record_view, telemetry_enabled
from src.socioeconomic.indicators import (
    aggregate_asset_risk,
    compute_svi,
)
from src.socioeconomic.indicators import (
    jobs_at_risk as compute_jobs_at_risk,
)
from src.socioeconomic.loader import load_municipalities, snapshot_exists
from src.ui.layout import (
    _TERRITORY_CONFIG,
    _VISIBLE_TERRITORIES,
    configure_page,
    inject_base_styles,
    load_dashboard,
)
from src.ui.render_widgets import (
    _compute_exec_kpis,
    _render_banner,
    _render_exec_kpis,
    _render_live_alerts,
)
from src.ui.tabs.tab_assets import render_tab_assets
from src.ui.tabs.tab_diagnostic import render_tab_diagnostic
from src.ui.tabs.tab_kpis import render_tab_kpis
from src.ui.tabs.tab_method import render_tab_method
from src.ui.tabs.tab_portfolio import render_tab_portfolio
from src.ui.tabs.tab_simulator import render_tab_simulator
from src.ui.tabs.tab_socioeco import render_tab_socioeco
from src.ui.tabs.tab_timeseries import render_tab_timeseries

# ── Configuración de página ───────────────────────────────────────────────────
configure_page()

# ── Estilo institucional ──────────────────────────────────────────────────────
inject_base_styles()


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
    # F10 Fase 5: telemetría de uso de vistas — local y opt-in (SNTO_TELEMETRY=1).
    # Se registra una vez por CAMBIO de vista en la sesión, no en cada autorefresh,
    # para medir selecciones reales sin inflar el conteo.
    if (
        telemetry_enabled()
        and st.session_state.get("_telemetry_last") != _view.mode.value
    ):
        record_view(_view.mode.value)
        st.session_state["_telemetry_last"] = _view.mode.value
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
    render_tab_method(_view)


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
