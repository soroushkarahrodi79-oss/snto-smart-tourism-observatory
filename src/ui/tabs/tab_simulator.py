"""
Tab 4 — Simulador Financiero What-If — for the SNTO dashboard shell (Fase 4, paso 6).

Extracted verbatim from app.py (issue #27, modularización). ``render_tab_simulator``
takes the scenario comparisons, the asset index, the base budget and the ranked
assets, and drives the interactive TIS budget-allocation what-if simulator.
"""
from __future__ import annotations

import streamlit as st

from src.intervention import allocate_tis_budget


def render_tab_simulator(base_comps, assets_by_id, base_budget, ranked_assets) -> None:
    """Render the Simulador Financiero What-If tab (issue #27 extraction)."""
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
