"""
Tab — "Acciones urgentes" (Fase 5.9 + Fase 6.2b triage wiring).

The first UI↔persistent-backend integration point (P1,
``docs/ux/ui-evolution-v2-spec.md`` §6). Reads open alerts from the
persistence layer (via ``src.ui.services.urgent_actions``) and lets a manager:

- **triage** each alert — assign / escalate / dismiss-with-reason — through the
  validated ``triage_alert`` service (same state machine + audit trail the
  ``/api/v2/alerts/{id}/triage`` endpoint uses); dismissing a false positive
  requires a reason, and a triaged alert leaves the open queue on rerun; and
- advance the underlying asset one step along its lifecycle
  (``transition_managed_asset``, Fase 5.5).

Session access is funnelled through ``_open_session`` so tests can inject an
in-memory populated session; in the app it is the real ``session_scope``
(SQLite by default — an empty backend simply shows the empty state, never an
error). In-process writes use actor ``ui`` — the API key gate (5.8) guards the
HTTP surface, not this trusted in-process caller.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.persistence.enums import AlertStatus
from src.persistence.services.alert_triage import ReasonRequiredError, triage_alert
from src.persistence.services.lifecycle import (
    IllegalTransitionError,
    transition_managed_asset,
)
from src.persistence.session import session_scope
from src.ui.services.urgent_actions import UrgentAction, list_urgent_actions

_LEVEL_EMOJI = {
    "CRITICAL_INTERVENTION": "🔴",
    "URGENT_MONITORING": "🟠",
    "PREVENTIVE_ACTION": "🟡",
    "NORMAL": "🟢",
}


@contextmanager
def _open_session() -> Iterator[Session]:
    """Session seam — real ``session_scope`` in the app, patched in tests."""
    with session_scope() as session:
        yield session


def _advance_asset(asset_id: int, target_value: str) -> None:
    from src.persistence.enums import ManagedAssetStatus

    with _open_session() as session:
        try:
            transition_managed_asset(
                session, asset_id, ManagedAssetStatus(target_value), actor="ui"
            )
        except IllegalTransitionError as exc:  # pragma: no cover - guarded in UI
            st.warning(str(exc))


def _triage(alert_id: int, target_value: str, reason_key: str | None = None) -> None:
    reason = st.session_state.get(reason_key, "") if reason_key else None
    with _open_session() as session:
        try:
            triage_alert(
                session,
                alert_id,
                AlertStatus(target_value),
                reason=reason,
                actor="ui",
            )
        except ReasonRequiredError:
            st.warning("Descartar una alerta requiere un motivo.")
        except IllegalTransitionError as exc:  # pragma: no cover - guarded in UI
            st.warning(str(exc))


def _render_action(action: UrgentAction) -> None:
    emoji = _LEVEL_EMOJI.get(action.level, "•")
    st.markdown(
        f"**{emoji} {action.asset_name}** "
        f"· riesgo {action.risk_score:.2f} · estado `{action.asset_status.value}`"
    )

    meta: list[str] = []
    if action.top_action:
        meta.append(f"Acción recomendada: {action.top_action}")
    if action.confidence is not None:
        # No spurious decimals (spec §8): integer percent.
        meta.append(f"confianza {round(action.confidence * 100)}%")
    meta.append(
        "✓ verificado en campo"
        if action.field_verified
        else "sin verificación de campo"
    )
    st.caption(" · ".join(meta))

    # Triage row: assign / escalate, plus dismiss-with-reason.
    col_assign, col_escalate = st.columns(2)
    col_assign.button(
        "Asignar",
        key=f"assign-{action.alert_id}",
        on_click=_triage,
        args=(action.alert_id, AlertStatus.ASSIGNED.value),
    )
    col_escalate.button(
        "Escalar",
        key=f"escalate-{action.alert_id}",
        on_click=_triage,
        args=(action.alert_id, AlertStatus.ESCALATED.value),
    )

    reason_key = f"dismiss-reason-{action.alert_id}"
    st.text_input(
        "Motivo de descarte (obligatorio para descartar / marcar falso positivo)",
        key=reason_key,
        label_visibility="collapsed",
        placeholder="Motivo de descarte (p. ej. «falso positivo: artefacto SCL»)",
    )
    st.button(
        "Descartar",
        key=f"dismiss-{action.alert_id}",
        on_click=_triage,
        args=(action.alert_id, AlertStatus.DISMISSED.value, reason_key),
    )

    # Asset-lifecycle advance (Fase 5.5) — orthogonal to alert triage.
    if action.next_status is not None:
        st.button(
            f"Avanzar activo a «{action.next_status.value}»",
            key=f"advance-{action.alert_id}",
            on_click=_advance_asset,
            args=(action.asset_id, action.next_status.value),
        )
    st.divider()


def render_tab_urgent_actions() -> None:
    st.subheader("🚨 Acciones urgentes")
    st.caption(
        "Alertas abiertas priorizadas por riesgo, leídas del backend persistente "
        "(la misma capa que expone /api/v2). Triaje (asignar/escalar/descartar) "
        "auditado; primer punto de integración UI↔backend (Fase 5.9 + 6.2)."
    )
    try:
        with _open_session() as session:
            actions = list_urgent_actions(session)
    except SQLAlchemyError:
        # The persistence backend isn't initialised yet (e.g. the default dev
        # SQLite file exists but Alembic migrations haven't run). Degrade
        # gracefully — this tab must never take down the rest of the dashboard.
        st.info(
            "El backend persistente aún no está inicializado. Ejecuta las "
            "migraciones (`alembic upgrade head`) o persiste alertas vía "
            "/api/v2 para poblarlo (Fase 5)."
        )
        return

    if not actions:
        st.info(
            "No hay acciones urgentes en el backend persistente. "
            "En desarrollo local el almacén SQLite arranca vacío; se pobla al "
            "persistir alertas (puente del motor, Fase 5.4) o vía /api/v2."
        )
        return

    for action in actions:
        _render_action(action)
