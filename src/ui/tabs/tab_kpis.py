"""
Tab 1 — Resumen Ejecutivo (KPIs) — for the SNTO dashboard shell (Fase 4, paso 4).

Extracted verbatim from app.py (issue #27, modularización). ``render_tab_kpis``
takes every page-assembly input it reads as an explicit parameter — the
executive dashboard, the ranked assets, the scenario comparisons, the
calibration record and the active view — and paints the KPI cards, the critical
asset cards and the satellite-override provenance note.
"""
from __future__ import annotations

import streamlit as st

from src.platform.enrichment import enrichment_summary
from src.platform.provenance import data_status_badge
from src.temporal import DataStatus
from src.ui.asset_navigation import select_asset
from src.ui.kpi_sections import decision_kpis
from src.ui.render_widgets import _render_fichas_rapidas, render_kpi_grid


def render_tab_kpis(dashboard, ranked_assets, base_comps, calibration, _view) -> None:
    """Render the Resumen Ejecutivo (KPIs) tab (issue #27 extraction)."""
    st.subheader("Panorama de decisión ejecutivo")
    st.caption(
        "Cuatro cifras calculadas para decidir esta semana: intervenir, posponer "
        "o solicitar verificación. Los seis indicadores de contexto permanecen en "
        "**Diagnosticar → Diagnóstico espacial**; no se elimina ninguna métrica."
    )

    # Coste de mitigación recomendado por activo (escenario óptimo TIS, Fase 6)
    _cost_by_id = {
        c.asset_id: c.scenarios[c.best_scenario_code].cost_eur
        for c in base_comps
    }

    # ── Vista GESTOR: acción prioritaria en lenguaje de dirección ─────────────
    if _view.section(simplified=True):
        _priority = next((a for a in ranked_assets if (a.tier or 5) <= 2), None)
        if _priority is not None:
            _act = _priority.recommended_action_label or "intervención de conservación"
            _cost = _cost_by_id.get(_priority.asset_id)
            _cost_txt = f" · coste estimado **€{_cost:,.0f}**" if _cost else ""
            st.markdown(
                f'<div style="padding:12px 16px;border-radius:8px;margin-bottom:10px;'
                f'background:#fff8f0;border-left:5px solid #EF9F27;">'
                f'<div style="font-size:0.66rem;text-transform:uppercase;letter-spacing:.06em;'
                f'color:#854F0B;font-weight:700">Acción prioritaria del territorio</div>'
                f'<div style="font-size:0.95rem;color:#0d1b2a;margin-top:3px">'
                f'<b>{_priority.name.split("—")[0].strip()}</b> ({_priority.region}) — '
                f'{_act}{_cost_txt}</div></div>',
                unsafe_allow_html=True,
            )
            st.button(
                "Abrir ficha del activo prioritario",
                key=f"asset-page-manager-priority-{_priority.asset_id}",
                on_click=select_asset,
                args=(st.session_state, _priority.asset_id),
            )

    render_kpi_grid(
        decision_kpis(dashboard.kpis),
        ranked_assets,
        _cost_by_id,
        columns=4,
    )
    st.caption(
        "La base técnica EHS/TPI/DCS y sus límites están a un clic en "
        "**Gobernar → Metodología y auditoría**."
    )

    st.divider()
    # ── Fichas de activos críticos (reubicadas desde el antiguo mapa hero) ─────
    st.markdown(
        '<div style="font-size:0.70rem;font-weight:600;color:#7a8899;'
        'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:6px">'
        'Activos turísticos críticos · prioridad de actuación</div>',
        unsafe_allow_html=True,
    )
    _render_fichas_rapidas(ranked_assets)
    st.caption(
        "Cada ficha separa **estrategia** (chip neutro `TIER`, prioridad de inversión) "
        "de **táctica** (chip semafórico de alerta, riesgo actual). La barra colorea el "
        "EHS por su propia escala de salud. El mapa espacial vive en "
        "**Diagnosticar → Diagnóstico espacial**."
    )
    # ── Procedencia: cuántos KPIs reflejan dato satelital real (override F2) ───
    _enr = enrichment_summary(calibration)
    if _enr["overridden"] > 0:
        _real_badge = data_status_badge(DataStatus.REAL)
        st.caption(
            f"{_real_badge.emoji} **{_enr['overridden']} de {_enr['total']}** activos "
            f"tienen su EHS **sobreescrito por observación satelital real** (Sentinel-2, "
            f"Pipeline A) donde el satélite detectó más degradación que el juicio experto; "
            f"estos KPIs, tiers y alertas reflejan el dato real. El resto mantiene el dato "
            f"curado (validado, no sustituido). Trazabilidad completa en "
            f"**Diagnosticar → Catálogo de activos y sendas**."
        )
    else:
        st.caption(
            "ℹ️ Ningún activo requiere override satelital en este territorio (el satélite "
            "confirma o es más verde que el juicio experto). Los KPIs usan el dato curado, "
            "contrastado con Sentinel-2 en "
            "**Diagnosticar → Catálogo de activos y sendas**."
        )
