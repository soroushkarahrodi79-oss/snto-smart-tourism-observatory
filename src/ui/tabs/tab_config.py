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

    st.divider()
    _render_tenancy_management()


def _render_tenancy_management() -> None:
    """Real, persisted tenancy management (v3.0) — additive, separate concept.

    The registry above is a curated, code-reviewed OAPN readiness dataset — not
    user-editable. This section is different: it operates on the actual
    persisted ``Organization``/``User``/``Territory`` rows via the tenancy
    service, so organizations, users and territories can genuinely be
    registered from the app. There is no login system yet (SSO/Entra ID is a
    deferred swap, ADR-005), so every write below takes an explicit acting
    user rather than pretending a session exists — the real authz policy is
    still enforced against whichever user is selected.
    """
    import pandas as pd

    from src.persistence.enums import UserRole
    from src.ui.services.territory_admin import (
        AdminStatus,
        add_user,
        claim_territory,
        create_organization,
        load_registry_state,
        register_territory,
    )

    st.markdown("#### Gestión de territorios y organizaciones (v3.0)")
    st.caption(
        "Capa de tenancy **real y persistida** (`Organization`/`User`/`Territory`), "
        "distinta del registro de arriba. **Sin sistema de login todavía**: "
        "elige qué usuario registrado actúa en cada acción — la política de "
        "roles (lectura/escritura/gestión) se aplica de verdad sobre esa "
        "elección, no es un simulacro."
    )

    state = load_registry_state()
    if not state.backend_available:
        st.info(
            "Backend de persistencia no inicializado todavía; la gestión de "
            "tenancy se activará cuando `/api/v2` esté en uso (ADR-012)."
        )
        return

    col_org, col_usr, col_terr = st.columns(3)
    col_org.metric("Organizaciones", len(state.organizations))
    col_usr.metric("Usuarios", len(state.users))
    col_terr.metric(
        "Territorios sin asignar",
        sum(1 for t in state.territories if t.owner_org is None),
    )

    if state.organizations:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Organización": o.name, "Slug": o.slug,
                        "Usuarios": o.n_users, "Territorios": o.n_territories,
                    }
                    for o in state.organizations
                ]
            ),
            use_container_width=True, hide_index=True,
        )
    if state.territories:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Territorio": t.name, "Slug": t.slug,
                        "Organización": t.owner_org or "— sin asignar —",
                    }
                    for t in state.territories
                ]
            ),
            use_container_width=True, hide_index=True,
        )

    _user_options = {
        f"{u.display_name} ({u.email}) · {u.role} · {u.org_name}": u.id
        for u in state.users
    }
    _org_options = {o.name: o.id for o in state.organizations}
    _unowned = {
        f"{t.name} ({t.slug})": t.id
        for t in state.territories if t.owner_org is None
    }

    with st.expander("➕ Crear organización"):
        with st.form("create_org"):
            slug = st.text_input("Slug", placeholder="oapn")
            name = st.text_input("Nombre", placeholder="OAPN")
            if st.form_submit_button("Crear") and slug and name:
                result = create_organization(slug, name)
                (st.success if result.status is AdminStatus.OK else st.warning)(
                    result.message
                )
                st.rerun()

    with st.expander("👤 Añadir usuario"):
        with st.form("add_user"):
            org_label = st.selectbox("Organización", list(_org_options) or ["—"])
            email = st.text_input("Email", placeholder="tecnico@oapn.es")
            display_name = st.text_input("Nombre", placeholder="Técnico OAPN")
            role = st.selectbox("Rol", [r.value for r in UserRole])
            acting_label = st.selectbox(
                "Actuando como (vacío = alta inicial sin admin previo)",
                ["— ninguno —", *list(_user_options)],
            )
            if st.form_submit_button("Añadir") and email and display_name:
                acting_id = _user_options.get(acting_label)
                result = add_user(
                    _org_options.get(org_label), email, display_name,
                    UserRole(role), acting_user_id=acting_id,
                )
                (st.success if result.status is AdminStatus.OK else st.warning)(
                    result.message
                )
                st.rerun()

    with st.expander("🗺️ Registrar o reclamar territorio"):
        with st.form("territory_form"):
            mode = st.radio(
                "Acción", ["Registrar nuevo", "Reclamar sin asignar"],
                horizontal=True,
            )
            org_label2 = st.selectbox(
                "Organización", list(_org_options) or ["—"], key="terr_org"
            )
            acting_label2 = st.selectbox(
                "Actuando como", ["— ninguno —", *list(_user_options)],
                key="terr_actor",
            )
            if mode == "Registrar nuevo":
                terr_slug = st.text_input("Slug del territorio")
                terr_name = st.text_input("Nombre del territorio")
                budget = st.number_input(
                    "Presupuesto (€)", min_value=0.0, value=100000.0
                )
                unowned_label = None
            else:
                terr_slug = terr_name = None
                budget = None
                unowned_label = st.selectbox(
                    "Territorio sin asignar", list(_unowned) or ["—"]
                )
            if st.form_submit_button("Confirmar"):
                acting_id2 = _user_options.get(acting_label2)
                org_id2 = _org_options.get(org_label2)
                if mode == "Registrar nuevo" and terr_slug and terr_name:
                    result = register_territory(
                        terr_slug, terr_name, budget, org_id2,
                        acting_user_id=acting_id2,
                    )
                elif mode != "Registrar nuevo" and unowned_label in _unowned:
                    result = claim_territory(
                        _unowned[unowned_label], org_id2, acting_user_id=acting_id2,
                    )
                else:
                    result = None
                if result is not None:
                    (st.success if result.status is AdminStatus.OK else st.warning)(
                        result.message
                    )
                    st.rerun()
