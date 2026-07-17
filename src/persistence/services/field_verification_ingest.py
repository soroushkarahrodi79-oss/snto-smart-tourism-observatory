"""
Bridge: in-memory FieldObservation -> persisted FieldVerification
(Fase 5, step 5.6).

The #26 field-validation tooling models a ground-truth plot as
``src.validation.field.FieldObservation`` (soil compaction, vegetation cover,
erosion class, and a composite ``degradation_index``), collected per the CSV
protocol in ``docs/field_validation_protocol.md``. This service turns one such
observation into a durable ``FieldVerification`` row so the campaign's evidence
outlives the CSV.

Deliberate boundaries (mirroring the alert bridge):
- Only impact plots tied to a real asset are persisted. A control plot
  (``is_control=True``) is a habitat reference, not an asset verification, and
  raises ``NotAnAssetVerificationError`` rather than being silently attached to
  some asset. An observation whose ``asset_id`` matches no ``ManagedAsset``
  raises ``AssetNotRegisteredError`` — never invents the asset.
- The composite ``degradation_index`` (stress convention, 0=pristine,
  100=degraded) is stored verbatim as ``result``; the individual measured
  components are summarised into ``notes``. Nothing is fabricated: an
  observation with no measured component yields ``result="no measured
  components"`` rather than a fake number.
- No ``AuditLogEntry`` here — that trail is added across all 5.3–5.6 writes in
  step 5.7, per the Fase 5 plan.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from src.persistence.models.field_verification import FieldVerification
from src.persistence.repositories import (
    FieldVerificationRepository,
    ManagedAssetRepository,
)
from src.persistence.services import audit
from src.persistence.services.alert_ingest import AssetNotRegisteredError
from src.validation.field import FieldObservation


class NotAnAssetVerificationError(ValueError):
    """Raised for a control plot or an observation with no linkable asset."""


def _summarise_components(observation: FieldObservation) -> str:
    parts: list[str] = [f"plot={observation.plot_id}"]
    if observation.soil_compaction_mpa is not None:
        parts.append(f"soil_compaction_mpa={observation.soil_compaction_mpa}")
    if observation.veg_cover_pct is not None:
        parts.append(f"veg_cover_pct={observation.veg_cover_pct}")
    if observation.erosion_class is not None:
        parts.append(f"erosion_class={observation.erosion_class}")
    if observation.distance_to_trail_m is not None:
        parts.append(f"distance_to_trail_m={observation.distance_to_trail_m}")
    return "; ".join(parts)


def persist_field_observation(
    session: Session,
    observation: FieldObservation,
    *,
    verifier: str,
    actor: str = audit.ACTOR_SYSTEM,
) -> FieldVerification:
    """
    Persist one impact FieldObservation as a FieldVerification for its asset.
    """
    if observation.is_control or observation.asset_id is None:
        raise NotAnAssetVerificationError(
            f"Observation plot={observation.plot_id!r} is a control plot or has "
            "no asset_id; only impact plots tied to an asset are persisted."
        )

    asset = ManagedAssetRepository(session).get_by_external_id(
        observation.asset_id
    )
    if asset is None:
        raise AssetNotRegisteredError(observation.asset_id)

    index = observation.degradation_index()
    result = str(index) if index is not None else "no measured components"

    verified_at = (
        datetime.fromisoformat(observation.observed_at)
        if observation.observed_at
        else datetime.utcnow()
    )

    verification = FieldVerificationRepository(session).add(
        FieldVerification(
            asset_id=asset.id,
            verified_at=verified_at,
            method="field_plot",
            verifier=verifier,
            result=result,
            photo_ref=observation.photo_ref,
            notes=_summarise_components(observation),
        )
    )
    audit.record(
        session,
        actor=actor,
        action=audit.FIELD_VERIFICATION_PERSISTED,
        subject_type="field_verification",
        subject_id=verification.id,
        payload={"asset_id": asset.id, "result": result},
    )
    return verification
