"""
Tab 2 — Portafolio TPI — for the SNTO dashboard shell (Fase 4, paso 5).

Extracted verbatim from app.py (issue #27, modularización). ``render_tab_portfolio``
takes the ranked assets and paints the TPI portfolio matrix, the full data table
and the tactical alerts vs strategic-tier panel.
"""
from __future__ import annotations

import streamlit as st

from src.platform.charts import build_portfolio_matrix
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
            "✅ Sin activos en prioridad de intervención (Tier 1-2) en este territorio.",
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


def render_tab_portfolio(ranked_assets, base_comps, _view) -> None:
    """Render the Portafolio TPI tab, modulated by audience (#28, F10-4).

    GESTOR lidera con el plan de acción prioritario (``_render_action_first``);
    la matriz y la tabla van debajo. Las demás vistas ven la matriz primero.
    """
    st.subheader("Matriz de Portafolio TPI — Priorización de Activos Turísticos Críticos")
    st.caption(
        "Cada activo se posiciona según su capacidad de carga antrópica (eje X) y su riesgo "
        "ecológico (eje Y = 100 − EHS). El tamaño del punto refleja la importancia económica "
        "del activo. Los cuadrantes delimitan las cuatro estrategias de gestión del modelo SNTO: "
        "la matriz fundamenta de forma objetiva qué sendas requieren intervención financiera inmediata."
    )

    # ── GESTOR: acción primero — el plan prioritario lidera; la matriz va debajo.
    if _view.section(simplified=True):
        _render_action_first(ranked_assets, base_comps)
        st.divider()

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


