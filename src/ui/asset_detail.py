"""Central per-asset page for Fase 6.5."""

from __future__ import annotations

from html import escape

import streamlit as st

from src.platform.provenance import data_status_badge
from src.temporal import DataStatus
from src.ui.asset_navigation import clear_asset_selection
from src.ui.render_helpers import (
    _ASSET_TYPE_EMOJI,
    _alert_chip,
    _ehs_color,
    _tier_chip,
)

_TREND_LABELS = {
    "increasing": "Mejora",
    "decreasing": "Deterioro",
    "no_trend": "Sin tendencia concluyente",
}

_SCM_LABELS = {
    "LANDSCAPE_DRIVEN": "Señal compatible con dinámica del paisaje",
    "LOCALIZED_IMPACT": "Hipótesis de impacto localizado",
    "MIXED": "Hipótesis causal mixta",
}

_ASSET_TYPE_LABELS = {
    "TRAIL": "Senda",
    "VIEWPOINT": "Mirador",
    "RECREATIONAL_AREA": "Área recreativa",
    "NATURAL_PARK": "Espacio natural",
    "CYCLING_ROUTE": "Ruta ciclista",
}

_SCENARIO_LABELS = {
    "A": "No intervenir",
    "B": "Restauración",
    "C": "Refuerzo de monitorización",
    "D": "Inversión en promoción",
    "E": "Restauración y monitorización",
}

_CONFIDENCE_LABELS = {
    "HIGH": "Alta",
    "MODERATE": "Moderada",
    "LOW": "Baja",
}

_FEASIBILITY_LABELS = {
    "VIABLE": "viable",
    "MARGINAL": "marginal",
    "NOT_RECOMMENDED": "no recomendable",
}


def _physical_context(asset) -> str:
    asset_type = _ASSET_TYPE_LABELS.get(
        asset.asset_type, asset.asset_type.replace("_", " ").title()
    )
    parts = [asset.region, asset_type]
    if asset.length_km:
        parts.append(f"{asset.length_km:.1f} km")
    if asset.area_ha:
        parts.append(f"{asset.area_ha:.0f} ha")
    if asset.elevation_m:
        parts.append(f"{asset.elevation_m:.0f} m")
    return " · ".join(parts)


def render_asset_page(asset, comparison, calibration_result) -> None:
    """Render state, evidence, history and action for one territorial asset."""
    st.button(
        "← Volver a la arquitectura de decisión",
        key=f"asset-page-back-{asset.asset_id}",
        on_click=clear_asset_selection,
        args=(st.session_state,),
    )
    st.caption("Diagnosticar / Catálogo de activos y sendas / Ficha del activo")

    emoji = _ASSET_TYPE_EMOJI.get(asset.asset_type, "📍")
    ehs_color = _ehs_color(asset.ehs)
    st.markdown(
        f'<div class="snto-evidence-card" style="padding:18px 20px;margin-bottom:16px">'
        f'<div style="font-size:0.68rem;color:#7a8899;text-transform:uppercase;'
        f'letter-spacing:.07em">Activo central · #{asset.priority_rank or "—"}</div>'
        f'<div style="font-size:1.55rem;font-weight:700;color:#0d1b2a;margin-top:4px">'
        f'{emoji} {escape(asset.name)}</div>'
        f'<div style="font-size:0.82rem;color:#64748b;margin-top:4px">'
        f'{escape(_physical_context(asset))}</div>'
        f'<div style="margin-top:9px">{_tier_chip(asset.tier)}'
        f'{_alert_chip(asset.alert_level)}</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Estado")
    st.caption("Qué sabemos del activo en el ciclo actual.")
    state_columns = st.columns(4)
    state_columns[0].metric("EHS · salud", f"{asset.ehs:.0f}/100")
    state_columns[1].metric("TPI · prioridad", f"{(asset.tpi or 0):.0f}/100")
    state_columns[2].metric("DCS · confianza", f"{asset.dcs:.0f}/100")
    state_columns[3].metric(
        "Presión anual", f"{asset.visitor_capacity_annual:,.0f} visitas"
    )
    st.markdown(
        f'<div class="snto-body-copy" style="border-left:4px solid {ehs_color};'
        f'padding:9px 12px;background:#f8fafc">'
        f'{escape(asset.description or "Sin descripción operativa disponible.")}</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("### Evidencia")
    st.caption("Qué dato sostiene el estado y con qué límites puede usarse.")
    curated_badge = data_status_badge(DataStatus.CALIBRATED)
    real_badge = data_status_badge(DataStatus.REAL)
    evidence_columns = st.columns(2)
    with evidence_columns[0]:
        st.markdown(
            f"**{curated_badge.emoji} {curated_badge.label}**  \n"
            f"EHS operativo: **{asset.ehs:.0f}/100** · DCS: **{asset.dcs:.0f}/100**"
        )
        st.caption(curated_badge.caveat)
    with evidence_columns[1]:
        if calibration_result and calibration_result.satellite_ehs is not None:
            validation_emoji, validation_label, _ = calibration_result.badge
            st.markdown(
                f"**{real_badge.emoji} {real_badge.label}**  \n"
                f"EHS satélite: **{calibration_result.satellite_ehs:.0f}/100** · "
                f"{validation_emoji} {validation_label}"
            )
            references = ", ".join(calibration_result.matched_trails)
            st.caption(
                f"Sentinel-2 · {calibration_result.n_trails} senda(s): {references}. "
                f"Δ {calibration_result.delta:+.0f} frente al EHS curado."
            )
        else:
            st.markdown("**— Sin senda satelital equivalente**")
            st.caption(
                "No hay observación comparable para este activo; el estado conserva "
                "la capa curada y no debe presentarse como validación satelital."
            )

    st.divider()
    st.markdown("### Historia")
    st.caption("Cómo evoluciona la señal y qué hipótesis causal está registrada.")
    history_columns = st.columns(3)
    history_columns[0].metric(
        "Trayectoria", _TREND_LABELS.get(asset.trend_direction, asset.trend_direction)
    )
    history_columns[1].metric("Mann–Kendall p", f"{asset.mk_p_value:.3f}")
    history_columns[2].metric(
        "Confianza causal",
        _CONFIDENCE_LABELS.get(asset.scm_confidence, asset.scm_confidence.title()),
    )
    st.markdown(
        f"**Hipótesis causal:** "
        f"{_SCM_LABELS.get(asset.scm_classification, asset.scm_classification)}."
    )
    st.caption(
        "La clasificación SCM es una hipótesis, no una atribución causal demostrada. "
        "La serie y sus huecos se consultan en Evidenciar → Evidencia satelital."
    )

    st.divider()
    st.markdown("### Acción")
    st.caption(
        "Qué respuesta propone el modelo, con coste y resultado como simulación."
    )
    if comparison is None:
        st.info("No hay comparación de escenarios disponible para este activo.")
    else:
        scenario = comparison.scenarios[comparison.best_scenario_code]
        st.markdown(
            '<span style="display:inline-block;padding:3px 8px;border-radius:999px;'
            'background:#ede9fe;color:#5b21b6;font-size:.72rem;font-weight:700">'
            '🎛️ ESCENARIO SIMULADO</span>',
            unsafe_allow_html=True,
        )
        action_columns = st.columns(4)
        action_columns[0].metric(
            "Escenario recomendado",
            _SCENARIO_LABELS.get(
                comparison.best_scenario_code, comparison.best_scenario_label
            ),
        )
        action_columns[1].metric("Coste estimado", f"€{scenario.cost_eur:,.0f}")
        action_columns[2].metric("Impacto TIS", f"{scenario.tis:.1f}/100")
        action_columns[3].metric("Δ EHS simulado", f"{scenario.delta_ehs:+.1f}")
        feasibility = _FEASIBILITY_LABELS.get(
            scenario.feasibility, scenario.feasibility.lower()
        )
        st.markdown(
            f"**Por qué:** el motor selecciona esta respuesta como alternativa "
            f"**{feasibility}** con TIS **{scenario.tis:.1f}/100**, respetando "
            "la prioridad territorial y la confianza disponible."
        )
        st.caption(
            "El coste y los cambios proyectados son resultados del simulador, no "
            "observaciones ni compromisos presupuestarios."
        )
        if comparison.dcs_constrained:
            st.warning(
                "La confianza disponible limita la recomendación: primero debe "
                "reforzarse la monitorización antes de una intervención de capital."
            )

    st.button(
        "← Volver al catálogo y módulos",
        key=f"asset-page-back-bottom-{asset.asset_id}",
        on_click=clear_asset_selection,
        args=(st.session_state,),
    )
