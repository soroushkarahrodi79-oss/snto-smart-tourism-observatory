"""
Tab 8 — Fundamento y Trazabilidad — for the SNTO dashboard shell (Fase 4, paso 3).

First tab extracted from app.py (issue #27, modularización), and the template
for the rest: the tab body becomes ``render_tab_method()``, called by app.py
inside its ``with tab_method:`` context. This tab is pure delegation to the
methodology renderers plus the canonical evidence-class legend — it reads no
page-assembly state, so it is the safest first tab to move.
"""
from __future__ import annotations

import streamlit as st

from src.platform import methodology as method
from src.platform.evidence import (
    DecisionUse,
    gating_matrix,
)
from src.platform.evidence import (
    legend as evidence_legend,
)
from src.platform.telemetry import telemetry_enabled, usage_summary
from src.platform.views import get_view, view_modes


def _render_evidence_legend() -> None:
    """Single, first-class legend of evidence classes + decision gating.

    Reads the canonical vocabulary and gating matrix from
    ``src.platform.evidence`` so UI, informes y exportadores comparten
    exactamente las mismas etiquetas y reglas. Additive labeling, not a
    redesign (non-negotiable: no blur evidence).
    """
    st.markdown("**Clases de evidencia (ADR-004): separadas, nunca difuminadas**")
    for d in evidence_legend():
        st.markdown(
            f'<div style="display:flex;gap:8px;align-items:baseline;'
            f'margin:2px 0;font-size:0.82rem">'
            f'<span style="min-width:1.4em">{d.emoji}</span>'
            f'<span><b style="color:{d.color}">{d.label}</b> — {d.definition} '
            f'<span style="color:#7a8899">{d.caveat}</span></span></div>',
            unsafe_allow_html=True,
        )
    _uses = list(DecisionUse)
    _use_es = {
        DecisionUse.MONITORING: "Monitorización",
        DecisionUse.PRIORITIZATION: "Priorización",
        DecisionUse.INTERVENTION: "Intervención",
        DecisionUse.PUBLIC_REPORTING: "Reporte público",
    }
    _labels = {d.evidence: d.label for d in evidence_legend()}
    _gm = gating_matrix()
    _head = "| Clase | " + " | ".join(_use_es[u] for u in _uses) + " |\n"
    _head += "|---|" + "|".join([":-:"] * len(_uses)) + "|\n"
    _rows = "".join(
        "| " + _labels[e] + " | "
        + " | ".join("✅" if _gm[e][u] else "🚫" for u in _uses) + " |\n"
        for e in _gm
    )
    st.caption(
        "Gating de decisión — qué clase respalda qué uso (política conservadora, "
        "ver `docs/methodology/evidence-classes.md`):"
    )
    st.markdown(_head + _rows)


def _render_field_validation_status(ranked_assets) -> None:
    """Show the honest satellite↔field agreement verdict (v2.5 gate).

    Reads the real persisted FieldVerification rows and runs the built agreement
    analysis. Until the owner's field campaign produces >=3 co-located plots this
    shows "campaña pendiente" — never a fabricated verdict. Fails soft: if the
    persistence layer is unreachable, the tab keeps rendering.
    """
    from src.ui.services.field_agreement import compute_field_agreement

    ehs_by_id = {
        a.asset_id: float(a.ehs)
        for a in (ranked_assets or [])
        if getattr(a, "asset_id", None) and getattr(a, "ehs", None) is not None
    }
    try:
        summary = compute_field_agreement(ehs_by_id)
    except Exception:  # persistence unavailable / not migrated → degrade gracefully
        st.caption(
            "🔬 **Validación satélite↔campo:** backend de persistencia no "
            "inicializado todavía; la puerta científica se activará cuando la "
            "campaña de campo registre plots (v2.5)."
        )
        return

    with st.expander(
        "🔬 Validación satélite↔campo · puerta científica (v2.5)",
        expanded=False,
    ):
        report = summary.report
        if report is None or report.n < 3:
            st.warning(
                "**Campaña de campo pendiente.** La concordancia satélite↔campo "
                "(Spearman ρ + Cliff's δ) es la puerta que convierte SNTO de "
                "«apoyo a la decisión» en «validado para el PNSG». Requiere ≥3 "
                "plots co-localizados con medición real (penetrómetro / cobertura "
                f"/ erosión). Plots reales registrados hasta ahora: "
                f"**{summary.n_paired}**. Hasta entonces, la relación EHS↔"
                "degradación **no es defendible** (ADR-003).",
                icon="⏳",
            )
            return
        verdict_icon = "✅" if summary.gate_passed else "⚠️"
        _dir = "correcta" if report.direction_ok else "inesperada"
        st.markdown(
            f"{verdict_icon} **Concordancia satélite↔campo (datos reales):** "
            f"Spearman ρ = **{report.spearman:.3f}** sobre **{report.n}** plots "
            f"co-localizados · dirección {_dir}."
        )
        st.caption(f"Veredicto: {report.verdict}. Dato real de campo, no simulado.")
        import pandas as pd
        st.dataframe(
            pd.DataFrame([
                {
                    "Activo": p.asset_name,
                    "Degradación campo (0-100)": p.field_degradation,
                    "Estrés satélite (100−EHS)": p.satellite_stress,
                    "Fecha": p.verified_at[:10],
                }
                for p in summary.plots
            ]),
            use_container_width=True, hide_index=True,
        )


def _render_field_capture_form() -> None:
    """Capture one real ground-truth plot into persistence (v2.5 gate, write side).

    The write counterpart of the agreement status: it turns the field campaign's
    plots into durable ``FieldVerification`` rows via the honest capture service.
    Control plots and unregistered assets are reported, never fabricated. Shown
    only in the audit view — the validation-campaign audience.
    """
    from src.ui.services.field_capture import CaptureStatus, capture_field_plot
    from src.validation.field import FieldObservation

    with st.expander("📋 Registrar parcela de campo (v2.5 · escritura)"):
        st.caption(
            "Registra una observación real de terreno como `FieldVerification` "
            "persistente. Las parcelas de **control** y los activos no registrados "
            "se informan, no se inventan. Las medidas no tomadas quedan vacías "
            "(nunca cero)."
        )
        with st.form("field_capture", clear_on_submit=False):
            c1, c2 = st.columns(2)
            plot_id = c1.text_input("ID de parcela", placeholder="PNSG-P01")
            asset_id = c2.text_input("ID de activo (externo)", placeholder="pnsg-nat-1")
            c3, c4, c5 = st.columns(3)
            lat = c3.number_input("Latitud", value=40.80, format="%.5f")
            lon = c4.number_input("Longitud", value=-3.96, format="%.5f")
            dist = c5.number_input("Distancia a senda (m)", value=1.0, min_value=0.0)
            is_control = st.checkbox(
                "Parcela de control (referencia de hábitat, no se persiste)"
            )
            c6, c7, c8 = st.columns(3)
            soil = c6.number_input(
                "Compactación (MPa)", value=None, min_value=0.0, step=0.1,
                help="Penetrómetro; vacío = no medido",
            )
            veg = c7.number_input(
                "Cobertura vegetal (%)", value=None, min_value=0.0, max_value=100.0,
                help="Vacío = no medido",
            )
            erosion_label = c8.selectbox(
                "Erosión",
                ["sin dato", "0 · nula", "1 · leve", "2 · moderada", "3 · severa"],
            )
            c9, c10 = st.columns(2)
            verifier = c9.text_input("Verificador/a", placeholder="Equipo PNSG")
            observed = c10.date_input("Fecha de observación")
            submitted = st.form_submit_button("Registrar parcela")

        if not submitted:
            return
        if not plot_id or not verifier or (not asset_id and not is_control):
            st.warning("Faltan campos obligatorios: parcela, verificador/a y activo.")
            return
        erosion = None if erosion_label == "sin dato" else int(erosion_label[0])
        observation = FieldObservation(
            plot_id=plot_id, lat=float(lat), lon=float(lon),
            distance_to_trail_m=float(dist), is_control=is_control,
            asset_id=asset_id or None,
            soil_compaction_mpa=None if soil is None else float(soil),
            veg_cover_pct=None if veg is None else float(veg),
            erosion_class=erosion,
            observed_at=observed.isoformat() if observed else None,
        )
        result = capture_field_plot(observation, verifier=verifier, actor="ui")
        if result.status is CaptureStatus.PERSISTED:
            _idx = (
                f" · índice de degradación {result.field_degradation:.1f}/100"
                if result.field_degradation is not None
                else " · sin componentes medidos"
            )
            st.success(f"{result.message}{_idx}")
        elif result.status is CaptureStatus.CONTROL_SKIPPED:
            st.info(result.message)
        else:  # ASSET_UNKNOWN / NO_BACKEND / ERROR
            st.warning(result.message)


def render_tab_method(_view, ranked_assets=None) -> None:
    """Render the Fundamento / Trazabilidad tab, modulated by audience (#28, F10-4).

    * GESTOR (``simplified``): one-screen reliability summary; the dense detail
      (fundamento, matrix, evidence legend, licences) folds into an expander.
    * TÉCNICA / AUDITORÍA: full detail; licences shown outright only for the
      audit view, folded for the technical one.
    """
    st.subheader("Fundamento Metodológico, Trazabilidad e Incertidumbre")
    st.caption(
        "Capa de defensa académica del observatorio: qué se mide, qué se calcula, qué se "
        "estima y qué se simula — con su fuente, su fórmula y su nivel de confianza. "
        "Anexo escrito en `docs/defensibilidad_academica.md`."
    )

    # v2.5 — estado de la validación satélite↔campo (la puerta científica).
    if _view.section(technical=True):
        _render_field_validation_status(ranked_assets)
    # v2.5 (escritura) — captura de parcelas de campo, solo audiencia de auditoría.
    if _view.section(audit=True):
        _render_field_capture_form()

    if _view.section(simplified=True):
        method.render_executive_summary()
        with st.expander(
            "📚 Ver fundamento, matriz de trazabilidad, clases de evidencia y licencias"
        ):
            method.render_fundamento()
            st.divider()
            # Nested expanders are not allowed, so the legend renders inline here.
            _render_evidence_legend()
            st.divider()
            method.render_traceability_matrix()
            st.divider()
            method.render_limitations()
            st.divider()
            method.render_data_sources()
    else:
        method.render_fundamento()
        st.divider()
        with st.expander("🔎 Clases de evidencia y gating de decisión (ADR-004)"):
            _render_evidence_legend()
        st.divider()
        method.render_traceability_matrix()
        st.divider()
        method.render_limitations()
        st.divider()
        if _view.section(audit=True):
            method.render_data_sources()
        else:
            with st.expander("D · Fuentes de datos y licencias"):
                method.render_data_sources(show_heading=False)

    # ── F10 Fase 5: panel de uso de vistas (telemetría local, solo Auditoría) ──
    # Meta-panel de mantenimiento: mide qué audiencia se usa más para priorizar
    # dónde profundizar. Solo si la telemetría está activada (opt-in) y hay datos;
    # 100% local y sin PII.
    if _view.section(audit=True) and telemetry_enabled():
        _usage = usage_summary()
        if _usage:
            st.divider()
            with st.expander("📊 Uso de vistas (telemetría local · opt-in)"):
                _total = sum(_usage.values())
                st.caption(
                    "Selecciones de vista registradas localmente en esta instancia "
                    f"(sin PII, sin red). Total: **{_total}**."
                )
                for _m in view_modes():
                    _p = get_view(_m)
                    _n = _usage.get(_m.value, 0)
                    _pct = (_n / _total * 100) if _total else 0.0
                    st.markdown(f"- {_p.icon} **{_p.label}** — {_n} ({_pct:.0f}%)")
