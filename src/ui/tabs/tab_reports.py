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

These are **two different asset sets** (the decision portfolio vs. the
monitoring layer); the UI labels each with its own provenance so they are
never conflated (project non-negotiable: do not blur evidence).
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
    with st.expander(
        "Vista previa del informe", expanded=_view.section(audit=True)
    ):
        st.markdown(brief_md)
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

    st.divider()

    # ── 2. Capa GIS (GeoJSON) del conjunto de monitorización real ─────────────
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
