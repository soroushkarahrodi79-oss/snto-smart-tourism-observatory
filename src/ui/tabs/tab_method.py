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


def render_tab_method() -> None:
    """Render the Fundamento / Trazabilidad tab (issue #27 extraction)."""
    st.subheader("Fundamento Metodológico, Trazabilidad e Incertidumbre")
    st.caption(
        "Capa de defensa académica del observatorio: qué se mide, qué se calcula, qué se "
        "estima y qué se simula — con su fuente, su fórmula y su nivel de confianza. "
        "Anexo escrito en `docs/defensibilidad_academica.md`."
    )
    method.render_fundamento()
    st.divider()
    with st.expander("🔎 Clases de evidencia y gating de decisión (ADR-004)"):
        _render_evidence_legend()
    st.divider()
    method.render_traceability_matrix()
    st.divider()
    method.render_limitations()
    st.divider()
    method.render_data_sources()
