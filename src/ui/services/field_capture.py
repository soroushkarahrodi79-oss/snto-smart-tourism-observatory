"""Field-plot capture service (v2.5 enablement — the last code-ready gate item).

The v2.5 validation gate (`docs/roadmap/plan_v3_roadmap.md`) needs the campaign's
ground-truth plots to become durable `FieldVerification` rows. The persistence
bridge (`persist_field_observation`, Fase 5.6) and the read-side agreement runner
(`field_agreement`, v2.5 #106) already exist; what was missing is the **write**
entry point the app calls to record a plot.

This module is that wiring — pure data access, no Streamlit, so it is
unit-testable against an in-memory session and reusable by a UI form (and, later,
the existing `/api/v2` field-verifications POST). It is honest by construction:

- a **control plot** (or one with no asset) is a habitat reference, not an asset
  verification → reported as a typed, non-destructive outcome, never persisted;
- an **unregistered asset** → reported as such, never invented;
- an **unreachable backend** → a clear "no backend" result, not an exception in
  the UI.

Nothing is fabricated: it delegates entirely to `persist_field_observation`,
which stores the real composite `degradation_index` (or the literal "no measured
components" when a plot carries no measurement).
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.persistence.services.alert_ingest import AssetNotRegisteredError
from src.persistence.services.field_verification_ingest import (
    NotAnAssetVerificationError,
    persist_field_observation,
)
from src.persistence.session import session_scope
from src.validation.field import FieldObservation


class CaptureStatus(str, Enum):
    """Typed outcome of a capture attempt — every non-persist case is explicit."""

    PERSISTED = "persisted"
    CONTROL_SKIPPED = "control_skipped"   # reference plot, not an asset verification
    ASSET_UNKNOWN = "asset_unknown"       # asset_id matches no ManagedAsset
    NO_BACKEND = "no_backend"             # persistence unavailable / not migrated
    ERROR = "error"


@dataclass(frozen=True)
class CaptureResult:
    status: CaptureStatus
    message: str
    verification_id: int | None = None
    field_degradation: float | None = None


@contextmanager
def _open_session() -> Iterator[Session]:
    """Session seam — real ``session_scope`` in the app, patched in tests."""
    with session_scope() as session:
        yield session


def capture_field_plot(
    observation: FieldObservation,
    *,
    verifier: str,
    actor: str = "ui",
    session: Session | None = None,
) -> CaptureResult:
    """Persist one field plot as a ``FieldVerification``, reporting a typed outcome.

    Reuses ``persist_field_observation`` (Fase 5.6). Control plots and
    unregistered assets are non-destructive, typed outcomes — never fabricated
    writes. With no injected ``session`` the process session scope is opened and a
    persistence failure degrades to ``NO_BACKEND`` instead of raising.
    """
    if session is not None:
        return _capture(session, observation, verifier=verifier, actor=actor)
    try:
        with _open_session() as own:
            return _capture(own, observation, verifier=verifier, actor=actor)
    except SQLAlchemyError as exc:
        return CaptureResult(
            CaptureStatus.NO_BACKEND,
            "Backend de persistencia no disponible "
            f"({exc.__class__.__name__}); la parcela no se registró.",
        )


def _capture(
    session: Session,
    observation: FieldObservation,
    *,
    verifier: str,
    actor: str,
) -> CaptureResult:
    try:
        verification = persist_field_observation(
            session, observation, verifier=verifier, actor=actor,
        )
    except NotAnAssetVerificationError:
        return CaptureResult(
            CaptureStatus.CONTROL_SKIPPED,
            "Parcela de control (o sin activo): es una referencia de hábitat, "
            "no una verificación de activo — no se persiste como tal.",
        )
    except AssetNotRegisteredError:
        return CaptureResult(
            CaptureStatus.ASSET_UNKNOWN,
            f"El activo «{observation.asset_id}» no está registrado en el "
            "backend; no se inventa. Regístralo antes de asociar parcelas.",
        )
    return CaptureResult(
        CaptureStatus.PERSISTED,
        f"Parcela «{observation.plot_id}» registrada para "
        f"«{observation.asset_id}».",
        verification_id=verification.id,
        field_degradation=observation.degradation_index(),
    )
