"""
Tab — "Acciones urgentes" (Fase 5, step 5.9).

The first UI↔persistent-backend integration point (P1,
``docs/ux/ui-evolution-v2-spec.md`` §6). Reads open alerts from the
persistence layer (via ``src.ui.services.urgent_actions``) and lets a manager
advance an asset one step along its lifecycle — a write that goes through the
same validated ``transition_managed_asset`` service the ``/api/v2`` endpoint
uses, so the state machine (5.5) and audit trail (5.7) are honoured.

Session access is funnelled through ``_open_session`` so tests can inject an
in-memory populated session; in the app it is the real ``session_scope``
(SQLite by default — an empty backend simply shows the empty state, never an
error). The in-process write uses actor ``ui`` — the API key gate (5.8) guards
the HTTP surface, not this trusted in-process caller.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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


def _render_action(action: UrgentAction) -> None:
    emoji = _LEVEL_EMOJI.get(action.level, "•")
    st.markdown(
        f"**{emoji} {action.asset_name}** "
        f"· riesgo {action.risk_score:.2f} · estado `{action.asset_status.value}`"
    )
    if action.top_action:
        st.caption(f"Acción recomendada: {action.top_action}")
    if action.next_status is not None:
        st.button(
            f"Avanzar a «{action.next_status.value}»",
            key=f"advance-{action.alert_id}",
            on_click=_advance_asset,
            args=(action.asset_id, action.next_status.value),
        )
    st.divider()


def render_tab_urgent_actions() -> None:
    st.subheader("🚨 Acciones urgentes")
    st.caption(
        "Alertas abiertas priorizadas por riesgo, leídas del backend persistente "
        "(la misma capa que expone /api/v2). Primer punto de integración "
        "UI↔backend (Fase 5.9)."
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
