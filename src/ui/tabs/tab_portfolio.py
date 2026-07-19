"""
Tab 2 — Portafolio TPI — for the SNTO dashboard shell (Fase 4, paso 5).

Extracted verbatim from app.py (issue #27, modularización). ``render_tab_portfolio``
takes the ranked assets and paints the TPI portfolio matrix, the full data table
and the tactical alerts vs strategic-tier panel.
"""
from __future__ import annotations

import streamlit as st

from src.platform import methodology as method
from src.platform.charts import build_portfolio_matrix
from src.platform.pressure_capacity import assess_pressure_capacity
from src.ui.asset_navigation import select_asset
from src.ui.render_helpers import (
    _ALERT_META,
    _ALERT_SEVERITY,
    _alert_chip,
    _tier_chip,
)


# ── F10: vista "acción primero" para Gestor ──────────────────────────────────
# Reordena la LECTURA hacia la decisión (qué intervenir primero), sin alterar
# ninguna cifra: el coste por activo es el mismo del mejor escenario TIS que ven
# las demás vistas y la pestaña de KPIs. Solo cambia el orden y el lenguaje.
def _priority_actions(assets: list, comps: list, limit: int = 5) -> list[tuple]:
    """Activos Tier 1-2 por TPI descendente, con su acción recomendada y el coste
    del mejor escenario. Devuelve (asset, etiqueta_acción, coste_eur)."""
    cost_by_id = {
        c.asset_id: c.scenarios[c.best_scenario_code].cost_eur for c in comps
    }
    prio = sorted(
        [a for a in assets if (a.tier or 5) <= 2],
        key=lambda a: -(a.tpi or 0),
    )[:limit]
    return [
        (a, a.recommended_action_label or "Intervención de conservación",
         cost_by_id.get(a.asset_id))
        for a in prio
    ]


def _render_action_first(assets: list, comps: list) -> None:
    """Plan de acción prioritario (vista Gestor) para la pestaña de Portafolio."""
    rows = _priority_actions(assets, comps)
    st.markdown("#### 🧭 Plan de acción prioritario")
    if not rows:
        st.success(
            "✅ Sin activos en prioridad de intervención (Tier 1-2) "
            "en este territorio.",
            icon="🧭",
        )
        return
    st.caption(
        "Qué intervenir primero, en orden de urgencia (TPI). Los costes son los "
        "mismos del mejor escenario TIS que ve el resto de vistas; aquí se leen "
        "como acciones, no como tabla."
    )
    for a, action, cost in rows:
        cost_txt = f"€{cost:,.0f}" if cost else "coste por confirmar"
        st.markdown(
            f'<div class="snto-ficha" style="border-left-color:#EF9F27;">'
            f'<span class="snto-ficha-ehs" style="background:#fff3e0;color:#854F0B">'
            f'{cost_txt}</span>'
            f'<div class="snto-ficha-name">{_tier_chip(a.tier)} '
            f'{a.name.split("—")[0].strip()}</div>'
            f'<div class="snto-ficha-meta">{a.region} · {action} · '
            f'EHS {a.ehs:.0f} · TPI {a.tpi:.0f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.button(
            "Abrir ficha",
            key=f"asset-page-action-{a.asset_id}",
            on_click=select_asset,
            args=(st.session_state, a.asset_id),
        )


def _render_pressure_capacity(assets: list) -> None:
    """Render the v2 temporal-pressure, capacity-range and SCM contract."""
    import pandas as pd
    import plotly.graph_objects as go

    profiles = assess_pressure_capacity(assets)
    st.markdown(
        method.scenario_badge(
            "MODELO DE PLANIFICACIÓN",
            "perfil estacional y capacidad estimados; no aforos observados",
        ),
        unsafe_allow_html=True,
    )
    st.warning(
        "**Correlación ≠ causa.** El SCM expresa hipótesis compatibles con la "
        "señal espacial, no atribución causal demostrada. Cualquier regulación "
        "de flujos requiere contraste de campo y aforos independientes."
    )

    total_low = sum(profile.capacity_low for profile in profiles)
    total_high = sum(profile.capacity_high for profile in profiles)
    above_range = sum(
        profile.capacity_status == "Supera la horquilla estimada"
        for profile in profiles
    )
    localized = sum(
        profile.scm_classification == "LOCALIZED_IMPACT"
        for profile in profiles
    )
    metric_cols = st.columns(4)
    metric_cols[0].metric("Activos sobre horquilla", f"{above_range} / {len(profiles)}")
    metric_cols[1].metric(
        "Capacidad operativa estimada",
        f"{round(total_low / 1_000):,}k–{round(total_high / 1_000):,}k",
        help=(
            f"Rango exacto agregado: {total_low:,}–{total_high:,} visitas/año. "
            "Suma de horquillas por activo; proxy de planificación."
        ),
    )
    metric_cols[2].metric("Hipótesis SCM localizada", f"{localized} activos")
    metric_cols[3].metric("Pico estacional modelado", "Verano")

    st.markdown("#### TPI estacional estimado · cinco activos prioritarios")
    st.caption(
        "Perfil trimestral prospectivo: los multiplicadores estacionales promedian "
        "1,0 y se aplican al TPI vigente. Sirve para planificar campañas; no es una "
        "serie de conteos ni una tendencia observada."
    )
    tier_colors = {1: "#312e5c", 2: "#56548a", 3: "#a9adcb", 4: "#d6d9e8"}
    seasonal_fig = go.Figure()
    for profile in profiles[:5]:
        seasonal_fig.add_trace(
            go.Scatter(
                x=[point.season for point in profile.seasonal],
                y=[point.tpi for point in profile.seasonal],
                mode="lines+markers",
                name=profile.asset_name.split("—")[0].strip()[:28],
                line=dict(color=tier_colors[profile.tier], width=2.5),
                marker=dict(size=7),
                customdata=[point.flow_proxy for point in profile.seasonal],
                hovertemplate=(
                    "%{x}<br>TPI estimado: %{y:.1f}<br>"
                    "Volumen estacional proxy: %{customdata:,}"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
    seasonal_fig.update_layout(
        yaxis=dict(title="TPI estacional estimado", range=[0, 105]),
        xaxis_title="Estación",
        legend=dict(orientation="h", y=1.12, x=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=390,
        margin=dict(l=20, r=20, t=70, b=35),
    )
    st.plotly_chart(seasonal_fig, use_container_width=True)

    st.markdown("#### Horquilla de capacidad y presión anual")
    capacity_rows = [
        {
            "Activo": profile.asset_name,
            "Tier": profile.tier,
            "Presión anual (proxy)": profile.annual_pressure_proxy,
            "Capacidad baja": profile.capacity_low,
            "Capacidad central": profile.capacity_central,
            "Capacidad alta": profile.capacity_high,
            "Lectura": profile.capacity_status,
            "DCS": round(profile.dcs),
        }
        for profile in profiles
    ]
    st.dataframe(
        pd.DataFrame(capacity_rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Presión anual (proxy)": st.column_config.NumberColumn(format="%d"),
            "Capacidad baja": st.column_config.NumberColumn(format="%d"),
            "Capacidad central": st.column_config.NumberColumn(format="%d"),
            "Capacidad alta": st.column_config.NumberColumn(format="%d"),
            "DCS": st.column_config.NumberColumn(format="%d"),
        },
    )
    st.caption(
        "La capacidad central es una heurística de planificación condicionada por "
        "EHS; la horquilla se amplía con menor DCS. No sustituye un estudio LAC, "
        "aforos ni validación ecológica independiente."
    )

    st.markdown("#### Hipótesis turismo vs clima · SCM")
    scm_rows = [
        {
            "Activo": profile.asset_name,
            "Clasificación": profile.scm_classification,
            "Confianza": profile.scm_confidence,
            "Hipótesis (no causa demostrada)": profile.scm_hypothesis,
        }
        for profile in profiles
    ]
    st.dataframe(pd.DataFrame(scm_rows), use_container_width=True, hide_index=True)
    st.divider()


def render_tab_portfolio(ranked_assets, base_comps, _view) -> None:
    """Render the Portafolio TPI tab, modulated by audience (#28, F10-4).

    GESTOR lidera con el plan de acción prioritario (``_render_action_first``);
    la matriz y la tabla van debajo. Las demás vistas ven la matriz primero.
    """
    st.subheader("Presión turística y capacidad de carga")
    st.caption(
        "Relaciona el volumen anual estimado, el TPI estacional y el estado "
        "ecológico para orientar campañas de aforo y regulación. Las horquillas "
        "son planificación conservadora: no son límites legales ni aforos medidos."
    )
    _render_pressure_capacity(ranked_assets)

    # ── GESTOR: acción primero — el plan prioritario lidera; la matriz va debajo.
    if _view.section(simplified=True):
        _render_action_first(ranked_assets, base_comps)
        st.divider()

    st.markdown("#### Matriz territorial de presión y riesgo")
    st.caption(
        "Eje X: volumen anual estimado normalizado dentro del territorio. Eje Y: "
        "riesgo ecológico (100 − EHS). La matriz prioriza inspección; no demuestra "
        "que la presión turística sea la causa de la degradación."
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
                "Presión proxy (norm.)": round(
                    a.visitor_capacity_annual / max_v * 100,
                    1,
                ),
                "Volumen anual estimado": a.visitor_capacity_annual,
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
        "ejes independientes: un activo puede ser `TIER III` "
        "(baja prioridad de inversión) "
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
            st.button(
                "Abrir ficha",
                key=f"asset-page-alert-{a.asset_id}",
                on_click=select_asset,
                args=(st.session_state, a.asset_id),
            )


