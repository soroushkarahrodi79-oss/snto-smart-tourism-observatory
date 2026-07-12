"""
Tab 5 — Impacto Socioeconómico — for the SNTO dashboard shell (Fase 4, paso 9).

Extracted verbatim from app.py (issue #27, modularización). ``render_tab_socioeco``
takes the socioeconomic overlay (ALMUDENA/INE, or ``None`` when unavailable), the
scenario comparisons, the ranked assets, the base budget and the active view,
and paints the community-impact, jobs-at-risk and social-vulnerability analyses.
"""
from __future__ import annotations

import streamlit as st

from src.platform import methodology as method
from src.platform.views import ConfidenceDetail


def render_tab_socioeco(_socio, base_comps, ranked_assets, base_budget, _view) -> None:
    """Render the Impacto Socioeconómico tab (issue #27 extraction)."""
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
