"""Configuración territorial (read-only) for the Gobernar layer (Fase 6.7f).

The last v2.0 module of the spec's priority table (§6, P3: "Configuration /
territorial management — prepare multi-park without overpromising"). It is a
**sober, read-only** surface: it shows the territory registry with each
territory's honest validation state and the operative thresholds — it does
**not** register/edit territories or imply production multi-tenancy (that is a
v3.0 capability, deliberately not offered here).
"""
from __future__ import annotations

import streamlit as st

from src.config.constants import (
    ALERT_CRITICAL,
    ALERT_PREVENTIVE,
    ALERT_URGENT,
    NDVI_DEGRADED_THRESHOLD,
    NDVI_HEALTHY_BASELINE,
)
from src.platform.territory_registry import (
    ValidationState,
    registry_summary,
    territory_profiles,
)

_STATE_EMOJI = {
    ValidationState.ACTIVE_PILOT: "🟢",
    ValidationState.TREND_PILOT: "🔵",
    ValidationState.CALIBRATION_ARCHIVED: "⚪",
    ValidationState.TEMPLATE_UNVALIDATED: "🟠",
}


def render_tab_config(_view) -> None:
    """Read-only territory registry + operative thresholds (no live tenancy)."""
    import pandas as pd

    st.subheader("Configuración territorial")
    st.caption(
        "Registro de territorios y umbrales operativos, en **solo lectura**. "
        "El alta/edición de territorios y el multi-parque en producción son "
        "capacidad de v3.0: aquí se prepara sin prometerla."
    )

    summary = registry_summary()
    cols = st.columns(4)
    cols[0].metric("Territorios registrados", summary.total)
    cols[1].metric("Piloto activo", summary.active)
    cols[2].metric("Pilotos de tendencia", summary.trend_pilots)
    cols[3].metric("Plantillas sin validar", summary.templates)

    st.warning(
        "Ningún territorio está **validado en campo**: la campaña de "
        "ground-truth del PNSG (#26) sigue pendiente. «Tendencia satelital "
        "real» no equivale a «validado en campo» — no se presenta como tal."
    )

    profiles = territory_profiles()
    rows = [
        {
            "Territorio": f"{_STATE_EMOJI[p.state]} {p.name}",
            "Bioma": p.biome,
            "Estado de validación": p.state_label,
            "Validado en campo": "Sí" if p.field_validated else "No",
        }
        for p in profiles
    ]
    st.markdown("#### Registro de territorios")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("Notas por territorio", expanded=_view.section(audit=True)):
        st.dataframe(
            pd.DataFrame(
                [{"Territorio": p.name, "Nota": p.note} for p in profiles]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("#### Umbrales operativos (solo lectura)")
    st.caption(
        "Definidos en `src/config/constants.py`; se muestran para auditoría, no "
        "se editan desde la interfaz."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {"Umbral": "Alerta crítica (score)", "Valor": ALERT_CRITICAL},
                {"Umbral": "Alerta urgente (score)", "Valor": ALERT_URGENT},
                {"Umbral": "Alerta preventiva (score)", "Valor": ALERT_PREVENTIVE},
                {"Umbral": "NDVI baseline saludable", "Valor": NDVI_HEALTHY_BASELINE},
                {"Umbral": "NDVI degradado", "Valor": NDVI_DEGRADED_THRESHOLD},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        "- **Disponible:** registro descriptivo y umbrales versionados en código.\n"
        "- **No ofrecido aquí:** alta/edición de territorios, roles, tenencia "
        "multi-parque en producción (v3.0).\n"
        "- **Regla:** cada territorio hereda su propio estado de validación; "
        "«sin validar» por defecto, nunca presentado como operativo."
    )
