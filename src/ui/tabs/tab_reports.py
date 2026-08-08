"""Informes y exportaciones — Gobernar layer (Fase 6.7e).

The spec's §6 "Reports / exports" surface. It does **not** compute anything
new: it packages what the observatory already holds into two shareable,
evidence-labelled artifacts a director or a GIS technician can take away:

1. **Resumen ejecutivo del panel** (Markdown) — a roll-up of the *curated
   decision portfolio* shown on the dashboard (real calibrated EHS/risk,
   tier, alert, trend, action, indicative budget), via
   ``src.reporting.territorial_brief``. Missing fields degrade to explicit
   placeholders; no field-validation is claimed.
2. **Capa GIS (GeoJSON)** — the *full real-trend monitoring set* (official
   OAPN geometry + real Sentinel-2 trend + explicit ``evidence_level``), via
   ``src.reporting.gis_export`` — the same generator as
   ``scripts/export_gis.py``, for QGIS/ArcGIS.
3. **Preparación de dosier CETS Fase I** (Markdown/JSON) — the CETS↔SNTO
   correspondence with each requirement's *live* evidence class, via
   ``src.reporting.cets_readiness``. A preparation aid for a Foro/Grupo de
   Trabajo, explicitly **not** a candidacy dossier and never a validation claim.
4. **Seguimiento del PRUG por zonas** (Markdown/JSON) — the real trail evidence
   rolled up by official OAPN management zone, via
   ``src.reporting.prug_monitoring``. Real Sentinel-2 signal on real
   cartography, but a seasonal early warning, never a plan-compliance verdict.

The first two are **different asset sets** (the decision portfolio vs. the
monitoring layer); the third and fourth are institutional-framework mappings
(CETS accreditation, the park's own PRUG) over the real evidence. The UI labels
each with its own provenance so they are never conflated (project
non-negotiable: do not blur evidence).
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.reporting.territorial_brief import (
    build_territorial_brief,
    render_territorial_brief_markdown,
)

_ROOT = Path(__file__).resolve().parents[3]
# Parks with an on-disk assets GeoJSON (mirrors scripts/export_gis._DEFAULT_ASSETS).
_ASSETS_GEOJSON = {"pnsg": _ROOT / "clean_assets/pnsg_assets.geojson"}


@st.cache_data(show_spinner=False)
def _load_gis_feature_collection(park: str) -> dict | None:
    """Build the real-trend GIS FeatureCollection for a park, or None.

    Returns None (not a fabricated layer) when the park has no assets GeoJSON
    on disk — the honest "not available" state for territories beyond PNSG.
    """
    assets_path = _ASSETS_GEOJSON.get(park)
    if assets_path is None or not assets_path.exists():
        return None
    # Imported lazily: heavy trend loading only when this tab is opened.
    from src.platform.satellite_trends import load_asset_trends
    from src.reporting.gis_export import build_feature_collection
    from src.temporal.manifest import DataStatus

    with open(assets_path, encoding="utf-8") as f:
        assets = json.load(f)
    trends = load_asset_trends(park=park)
    return build_feature_collection(
        assets, trends, evidence_level=DataStatus.REAL, park=park
    )


def render_tab_reports(
    ranked_assets,
    selected_key: str,
    territory_name: str,
    report_date: str,
    _view,
) -> None:
    """Two evidence-labelled, downloadable artifacts over existing data."""
    st.subheader("Informes y exportaciones")
    st.caption(
        "Empaqueta lo que el observatorio ya calcula en artefactos "
        "descartables y etiquetados por evidencia. No genera cifras nuevas."
    )

    # ── 1. Resumen ejecutivo del panel (cartera de decisión) ──────────────────
    st.markdown("#### 1 · Resumen ejecutivo del panel")
    st.markdown(
        '<span class="snto-evidence-badge">Cartera de decisión · '
        "EHS/riesgo calibrados</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Cartera curada del panel ({len(ranked_assets)} activos de decisión). "
        "Recoge las mismas cifras ya visibles en «Decidir»; acción y "
        "presupuesto son orientativos y no hay validación de campo (#26)."
    )
    brief = build_territorial_brief(
        list(ranked_assets),
        territory_name=territory_name,
        report_date=report_date,
    )
    brief_md = render_territorial_brief_markdown(brief)
    # Evidence gate (ADR-004 / I-5): the executive brief over the decision
    # portfolio may only be offered as an *authorized* public/institutional
    # download when the portfolio's evidence class supports public reporting.
    # The synthetic fixture portfolio does not — it is shown as a demo preview
    # with a warning, and the two download buttons are withheld. (Sections 2-4
    # below use separate real-evidence pipelines and are unaffected.)
    _public_ok = brief["metadata"].get("public_reporting_authorized", True)
    with st.expander(
        "Vista previa del informe", expanded=_view.section(audit=True)
    ):
        st.markdown(brief_md)
    if _public_ok:
        _slug = territory_name.lower().replace(" ", "_")[:40]
        st.download_button(
            "⬇️ Descargar informe ejecutivo (.md)",
            data=brief_md,
            file_name=f"snto_informe_{_slug}_{report_date}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "⬇️ Descargar informe (.json)",
            data=json.dumps(brief, ensure_ascii=False, indent=2),
            file_name=f"snto_informe_{_slug}_{report_date}.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.warning(
            brief.get(
                "demo_warning",
                "🧪 Cartera sintética de demostración: no autorizada para "
                "descarga como informe público o institucional.",
            ),
            icon="🧪",
        )

    st.divider()

    # ── 2. Capa GIS (GeoJSON) del conjunto de monitorización real ─────────────
    _render_gis_section(selected_key, _view)

    st.divider()

    # ── 3. Preparación de dosier CETS Fase I ──────────────────────────────────
    _render_cets_section(selected_key, territory_name, report_date, _view)

    st.divider()

    # ── 4. Seguimiento del PRUG por zonas ─────────────────────────────────────
    _render_prug_section(selected_key, report_date, _view)


def _render_gis_section(selected_key: str, _view) -> None:
    """Section 2: the real-trend monitoring layer, or an honest absence notice."""
    st.markdown("#### 2 · Capa GIS (GeoJSON)")
    fc = _load_gis_feature_collection(selected_key)
    if fc is None:
        st.info(
            "No hay capa GIS empaquetada para este territorio (falta el "
            "GeoJSON de activos en `clean_assets/`). Disponible para el PNSG."
        )
        return

    meta = fc["metadata"]
    st.markdown(
        '<span class="snto-evidence-badge">Evidencia: real · geometría OAPN '
        "+ tendencia Sentinel-2</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Conjunto de **monitorización** satelital real (distinto de la cartera "
        "de decisión de arriba). Cada elemento lleva su `evidence_level`, para "
        "QGIS/ArcGIS; el GeoPackage (.gpkg) se genera con "
        "`scripts/export_gis.py`."
    )
    cols = st.columns(3)
    cols[0].metric("Activos", meta["feature_count"])
    cols[1].metric("Con tendencia real", meta["features_with_trend"])
    cols[2].metric("Nivel de evidencia", meta["evidence_level"])

    st.download_button(
        "⬇️ Descargar capa GIS (.geojson)",
        data=json.dumps(fc, ensure_ascii=False, indent=2),
        file_name=f"{selected_key}_snto.geojson",
        mime="application/geo+json",
        use_container_width=True,
    )

    if _view.section(audit=True):
        with st.expander("Propiedades exportadas por elemento"):
            st.caption(
                "Cada `Feature` conserva la geometría oficial y añade: "
                "`has_trend`, `tau`, `p_value`, `trend_significant`, "
                "`is_degrading`, `sens_slope`(+IC 95%), `ehs`, `evidence_level` "
                "y `provenance`. Sin tendencia → nulos explícitos, nunca un "
                "valor inventado."
            )


def _render_cets_section(
    selected_key: str, territory_name: str, report_date: str, _view
) -> None:
    """Section 3: CETS Fase I readiness — a preparation aid, not a dossier.

    Each requirement's evidence class is resolved from live repository state, so
    this surface reports what the observatory *actually* holds today (e.g. a
    pending field campaign shows as ``missing``, never as coverage).
    """
    from src.reporting.cets_readiness import (
        build_cets_readiness,
        render_cets_readiness_markdown,
    )

    st.markdown("#### 3 · Preparación de dosier CETS Fase I")
    st.markdown(
        '<span class="snto-evidence-badge">Marco institucional · evidencia '
        "resuelta en vivo</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Correspondencia entre los requisitos de la **Fase I de la CETS** "
        "(EUROPARC) y los módulos del SNTO, con la clase de evidencia que "
        "respalda cada uno **hoy**. Es material de preparación para un Foro / "
        "Grupo de Trabajo: no es un dosier de candidatura y no acredita "
        "cumplimiento."
    )

    report = build_cets_readiness(
        territory_name=territory_name,
        park=selected_key,
        report_date=report_date,
    )
    summary = report["summary"]
    signals = report["signals"]

    cols = st.columns(3)
    cols[0].metric("Requisitos evaluados", summary["requirements_assessed"])
    cols[1].metric(
        "Con evidencia real", summary["by_evidence_class"].get("real", 0)
    )
    cols[2].metric(
        "Parcelas de campo medidas", signals["field_measured_plots"]
    )
    if not signals["field_validated"]:
        st.warning(
            "La campaña de validación de campo (#26) no se ha ejecutado: "
            "ninguna fila puede declararse validada en campo.",
            icon="⚠️",
        )

    cets_md = render_cets_readiness_markdown(report)
    with st.expander(
        "Vista previa de la correspondencia CETS",
        expanded=_view.section(audit=True),
    ):
        st.markdown(cets_md)

    _slug = territory_name.lower().replace(" ", "_")[:40]
    st.download_button(
        "⬇️ Descargar preparación CETS (.md)",
        data=cets_md,
        file_name=f"snto_cets_fase1_{_slug}_{report_date}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "⬇️ Descargar preparación CETS (.json)",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name=f"snto_cets_fase1_{_slug}_{report_date}.json",
        mime="application/json",
        use_container_width=True,
    )


def _render_prug_section(selected_key: str, report_date: str, _view) -> None:
    """Section 4: PRUG-zone monitoring roll-up over the real trail evidence.

    Reports the park through its own management instrument (the PRUG
    zonification), aggregating real Sentinel-2 signal per official OAPN zone.
    Degrades honestly to an absence notice for a territory without zonification.
    """
    from src.reporting.prug_monitoring import (
        build_prug_monitoring,
        render_prug_monitoring_markdown,
    )

    st.markdown("#### 4 · Seguimiento del PRUG por zonas")
    report = build_prug_monitoring(selected_key, report_date=report_date)

    if not report.get("available"):
        st.info(
            "No hay seguimiento PRUG para este territorio: "
            f"{report.get('reason', 'sin zonificación disponible')}"
        )
        return

    st.markdown(
        '<span class="snto-evidence-badge">Evidencia: real · zonificación OAPN '
        "+ señal Sentinel-2</span>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Cruza la **zonificación oficial PRUG** con el estado ambiental real de "
        "cada senda. Alerta temprana estacional (ΔEHS de dos escenas), no una "
        "tendencia plurianual ni un veredicto de cumplimiento del Plan; sin "
        "validación de campo (#26)."
    )

    s = report["summary"]
    cols = st.columns(3)
    cols[0].metric("Zonas PRUG", s["n_zones"])
    cols[1].metric("Sendas deteriorándose", s["n_degrading"])
    cols[2].metric("Zona prioritaria", s["priority_zone"] or "—")

    prug_md = render_prug_monitoring_markdown(report)
    with st.expander(
        "Vista previa del seguimiento PRUG", expanded=_view.section(audit=True)
    ):
        st.markdown(prug_md)

    st.download_button(
        "⬇️ Descargar seguimiento PRUG (.md)",
        data=prug_md,
        file_name=f"snto_prug_{selected_key}_{report_date}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    st.download_button(
        "⬇️ Descargar seguimiento PRUG (.json)",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name=f"snto_prug_{selected_key}_{report_date}.json",
        mime="application/json",
        use_container_width=True,
    )
