"""Confidence & uncertainty module for the Phase 6.7c Evidenciar layer."""

from __future__ import annotations

import streamlit as st

from src.platform import methodology as method
from src.platform.confidence_explain import build_confidence_profiles


def render_tab_confidence(ranked_assets, _view) -> None:
    """Explain DCS totals without inventing non-persisted components."""
    import pandas as pd
    import plotly.graph_objects as go

    profiles = build_confidence_profiles(ranked_assets)
    by_id = {profile.asset_id: profile for profile in profiles}

    st.subheader("Confianza e incertidumbre · DCS")
    st.caption(
        "Explica cuánto puede confiarse en una recomendación, qué dimensión "
        "limita la evidencia y qué dato elevaría la confianza. El DCS no mide "
        "riesgo: mide la calidad de la evidencia que sostiene una decisión."
    )
    selected_id = st.selectbox(
        "Activo para explicar",
        options=[profile.asset_id for profile in profiles],
        format_func=lambda asset_id: by_id[asset_id].asset_name,
        key="confidence_asset",
    )
    profile = by_id[selected_id]

    if profile.exact_decomposition:
        st.markdown(
            method.type_badge("Calculada"),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            method.scenario_badge(
                "PROPAGACIÓN PENDIENTE",
                "se conserva el total; los componentes no se reconstruyen",
            ),
            unsafe_allow_html=True,
        )
        st.warning(
            "El pipeline del dashboard persiste el **DCS total**, pero todavía "
            "no sus cinco componentes. Los intervalos mostrados son únicamente "
            "los valores matemáticamente posibles dados el total y los máximos "
            "publicados; no son una decomposición estimada."
        )

    metric_cols = st.columns(4)
    metric_cols[0].metric("DCS total", f"{profile.dcs:.0f} / 100")
    metric_cols[1].metric("Banda", profile.band)
    metric_cols[2].metric(
        "Decomposición",
        "Exacta" if profile.exact_decomposition else "Pendiente",
    )
    gate_display = (
        "No verificable"
        if profile.action_gate is None
        else ("Apto" if profile.action_gate else "No superado")
    )
    metric_cols[3].metric("Gate de decisión", gate_display)

    labels = [component.label for component in profile.components][::-1]
    maxima = [component.maximum for component in profile.components][::-1]
    displayed = [
        component.score
        if component.score is not None
        else component.feasible_high
        for component in profile.components
    ][::-1]
    texts = [
        (
            f"{component.score:.0f}/{component.maximum:.0f}"
            if component.score is not None
            else (
                f"posible {component.feasible_low:.0f}–"
                f"{component.feasible_high:.0f}/{component.maximum:.0f}"
            )
        )
        for component in profile.components
    ][::-1]

    st.markdown("#### Decomposición DCS")
    decomposition_fig = go.Figure()
    decomposition_fig.add_trace(
        go.Bar(
            y=labels,
            x=maxima,
            orientation="h",
            name="Máximo del componente",
            marker_color="#e5e7eb",
            hoverinfo="skip",
        )
    )
    decomposition_fig.add_trace(
        go.Bar(
            y=labels,
            x=displayed,
            orientation="h",
            name=(
                "Puntuación calculada"
                if profile.exact_decomposition
                else "Límite superior posible"
            ),
            marker_color="#56548a",
            text=texts,
            textposition="inside",
            insidetextfont=dict(color="white"),
        )
    )
    decomposition_fig.update_layout(
        barmode="overlay",
        xaxis=dict(title="Puntos DCS", range=[0, 27]),
        legend=dict(orientation="h", y=1.12, x=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=350,
        margin=dict(l=20, r=20, t=65, b=35),
    )
    st.plotly_chart(decomposition_fig, use_container_width=True)

    st.markdown("#### Sensibilidad · qué podría elevar el DCS")
    sensitivity = sorted(
        profile.components,
        key=lambda component: component.sensitivity_upper,
    )
    sensitivity_fig = go.Figure(
        go.Bar(
            y=[component.label for component in sensitivity],
            x=[component.sensitivity_upper for component in sensitivity],
            orientation="h",
            marker_color="#5B21B6",
            text=[
                f"hasta +{component.sensitivity_upper:.0f}"
                for component in sensitivity
            ],
            textposition="outside",
        )
    )
    sensitivity_fig.update_layout(
        xaxis_title="Aumento máximo estructural (puntos DCS)",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=330,
        margin=dict(l=20, r=55, t=25, b=40),
    )
    st.plotly_chart(sensitivity_fig, use_container_width=True)
    st.caption(
        "El tornado muestra techo de mejora, no efecto esperado. Con componentes "
        "pendientes es una envolvente conservadora; solo será sensibilidad real "
        "cuando el pipeline persista cada subscore."
    )

    st.markdown("#### Qué falta para elevar y verificar la confianza")
    for component in sorted(
        profile.components,
        key=lambda item: -item.sensitivity_upper,
    ):
        st.markdown(
            f"- **{component.label}** · {component.evidence_status}: {component.gap}"
        )

    st.markdown("#### Mapa de brechas de evidencia")
    gap_rows = []
    for item in profiles:
        row = {"Activo": item.asset_name, "DCS": round(item.dcs)}
        row.update(
            {
                component.label: component.evidence_status
                for component in item.components
            }
        )
        gap_rows.append(row)
    st.dataframe(pd.DataFrame(gap_rows), use_container_width=True, hide_index=True)
