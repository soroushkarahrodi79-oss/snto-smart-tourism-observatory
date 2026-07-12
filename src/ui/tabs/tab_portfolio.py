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


def render_tab_portfolio(ranked_assets) -> None:
    """Render the Portafolio TPI tab (issue #27 extraction)."""
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


