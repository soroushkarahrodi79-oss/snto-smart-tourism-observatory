"""
Tab 6 — Evolución Temporal (Series Espectrales) — SNTO dashboard shell (Fase 4, paso 8).

Extracted verbatim from app.py (issue #27, modularización). ``render_tab_timeseries``
takes the ranked assets and the active view and paints the multi-year Mann-Kendall
trend charts and the spectral time series per asset. The per-session, per-park
``_cached_trends`` loader moves here with it (used only by this tab).
"""
from __future__ import annotations

import streamlit as st

from src.platform.charts import build_real_trend_chart, build_time_series_chart
from src.platform.satellite_trends import (
    DEFAULT_PARK,
    available_parks,
    find_trend,
    park_label,
    summarize_trends,
)
from src.ui.render_helpers import (
    _TIER_BADGE_COLOR,
    _TIER_ROMAN,
    _alert_chip,
    _ehs_color,
    _tier_chip,
)


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


def render_tab_timeseries(ranked_assets, _view) -> None:
    """Render the Evolución Temporal (Series Espectrales) tab (issue #27)."""
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
    if _view.section(simplified=True):
        # GESTOR: una sola línea, sin jerga estadística.
        st.info(
            f"**Tendencia:** {_trend_es} · **Salud (EHS)** {selected_asset.ehs:.0f}/100. "
            f"{'Requiere actuación.' if (selected_asset.tier or 5) <= 2 else 'Bajo control.'}",
            icon="🧭",
        )
    if _view.section(technical=True):
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
