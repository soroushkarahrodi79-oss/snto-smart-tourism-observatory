"""Data provenance and lineage workspace for the Evidenciar layer."""

from __future__ import annotations

import streamlit as st

from src.platform.evidence import descriptor
from src.platform.lineage import build_lineage_profiles
from src.platform.provenance import snapshot_provenance


def _lineage_diagram(profile) -> str:
    ehs = profile.records[0]
    source_label = (
        "Sentinel-2"
        if ehs.evidence_class.value == "real"
        else "Inventario curado"
    )
    return f"""
digraph lineage {{
  rankdir=LR;
  graph [bgcolor="transparent", pad="0.15", nodesep="0.30", ranksep="0.45"];
  node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10,
        color="#c7d1dc", fillcolor="#f5f7fa", fontcolor="#243447"];
  edge [color="#637487", arrowsize=0.7];
  source [label="{source_label}"];
  ehs [label="EHS\n{ehs.value}"];
  confidence [label="Riesgo + DCS"];
  tpi [label="TPI"];
  decision [label="Tier + acción", fillcolor="#eef1ff", color="#5d5f91"];
  source -> ehs -> confidence -> tpi -> decision;
}}
"""


def render_tab_provenance(
    ranked_assets,
    calibration,
    territory_key: str,
    report_date: str,
    _view,
) -> None:
    """Render per-datum source, class, transformation, and known date gaps."""
    import pandas as pd

    snapshot = snapshot_provenance(territory_key)
    profiles = build_lineage_profiles(
        ranked_assets,
        calibration,
        snapshot.scene_dates,
    )
    by_id = {profile.asset_id: profile for profile in profiles}

    st.subheader("Proveniencia de datos y linaje")
    st.caption(
        "Reconstruye qué fuente alimenta cada cifra, qué transformación aplica "
        "y cómo llega a la recomendación. Los huecos de fecha o ejecución se "
        "declaran; nunca se sustituyen por la fecha del informe."
    )
    selected_id = st.selectbox(
        "Activo para auditar",
        options=[profile.asset_id for profile in profiles],
        format_func=lambda asset_id: by_id[asset_id].asset_name,
        key="provenance_asset",
    )
    profile = by_id[selected_id]

    st.warning(
        "El runtime conserva valores y contratos de fuente, pero todavía no "
        "persiste una huella de ejecución ni una fecha de adquisición para "
        "cada valor calculado. **Fecha de informe no equivale a fecha del dato.**"
    )

    metrics = st.columns(4)
    metrics[0].metric("Registros de linaje", len(profile.records))
    metrics[1].metric("Fechas verificables", profile.dated_records)
    metrics[2].metric("Fechas pendientes", profile.missing_dates)
    metrics[3].metric("Corte del informe", report_date)

    st.markdown("#### Dato → indicador → decisión")
    st.graphviz_chart(_lineage_diagram(profile), use_container_width=True)
    st.caption(
        "La recomendación hereda la clase más débil de sus entradas. En el "
        "estado actual, TPI y acción incluyen atributos estratégicos estimados."
    )

    rows = []
    detail_rows = []
    for record in profile.records:
        evidence = descriptor(record.evidence_class)
        rows.append({
            "Etapa": record.stage,
            "Dato y valor": f"{record.datum} · {record.value}",
            "Naturaleza / clase": (
                f"{record.epistemic_type.label} · {evidence.label}"
            ),
            "Fuente": record.source,
            "Fecha del dato": record.observed_at or "No persistida",
        })
        detail = {
            "Dato": record.datum,
            "Transformación": " → ".join(record.transformations),
        }
        if _view.section(audit=True):
            detail["Código"] = record.location
        detail["Límite declarado"] = record.caveat
        detail_rows.append(detail)

    st.markdown("#### Registro por dato")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander(
        "Transformaciones, ubicaciones y límites",
        expanded=_view.section(audit=True),
    ):
        st.dataframe(
            pd.DataFrame(detail_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("#### Estado de propagación")
    if profile.missing_dates:
        st.error(
            f"PROPAGACIÓN INCOMPLETA · {profile.missing_dates} de "
            f"{len(profile.records)} registros no tienen fecha del dato "
            "persistida. Esto bloquea certificar una reproducción completa."
        )
    st.markdown(
        "- **Disponible:** valor vigente, contrato de fuente, naturaleza, clase "
        "y transformación declarada.\n"
        "- **Pendiente:** identificador de ejecución, timestamp por cálculo, "
        "versiones de entrada y hash de artefactos.\n"
        "- **Regla:** ningún hueco se interpola ni se rellena con la fecha del informe."
    )
