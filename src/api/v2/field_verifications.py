"""
/api/v2 field-verification endpoints (Fase 5, 5.6).

Durable ground-truth records for a ManagedAsset, complementing the CSV
protocol in ``docs/field_validation_protocol.md`` (#26). Create is a write —
not auth-gated yet; minimal auth gates writes in step 5.8 (ADR-011).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.v2.deps import require_write_auth
from src.api.v2.schemas import (
    FieldVerificationCreate,
    FieldVerificationListResponse,
    FieldVerificationOut,
)
from src.persistence.models.field_verification import FieldVerification
from src.persistence.repositories import (
    FieldVerificationRepository,
    ManagedAssetRepository,
)
from src.persistence.services import audit
from src.persistence.session import get_db

router = APIRouter(tags=["field-verifications"])


@router.get(
    "/managed-assets/{asset_id}/field-verifications",
    response_model=FieldVerificationListResponse,
)
def list_asset_field_verifications(
    asset_id: int, db: Session = Depends(get_db)
) -> FieldVerificationListResponse:
    if ManagedAssetRepository(db).get(asset_id) is None:
        raise HTTPException(status_code=404, detail="ManagedAsset not found")
    verifications = FieldVerificationRepository(db).list_by_asset(asset_id)
    return FieldVerificationListResponse(
        total=len(verifications),
        field_verifications=[
            FieldVerificationOut.model_validate(v) for v in verifications
        ],
    )


@router.post(
    "/managed-assets/{asset_id}/field-verifications",
    response_model=FieldVerificationOut,
)
def create_field_verification(
    asset_id: int,
    body: FieldVerificationCreate,
    db: Session = Depends(get_db),
    actor: str = Depends(require_write_auth),
) -> FieldVerificationOut:
    if ManagedAssetRepository(db).get(asset_id) is None:
        raise HTTPException(status_code=404, detail="ManagedAsset not found")
    verification = FieldVerificationRepository(db).add(
        FieldVerification(
            asset_id=asset_id,
            verified_at=body.verified_at or datetime.utcnow(),
            method=body.method,
            verifier=body.verifier,
            result=body.result,
            photo_ref=body.photo_ref,
            notes=body.notes,
        )
    )
    audit.record(
        db,
        actor=actor,
        action=audit.FIELD_VERIFICATION_CREATED,
        subject_type="field_verification",
        subject_id=verification.id,
        payload={"asset_id": asset_id, "method": body.method},
    )
    db.commit()
    return FieldVerificationOut.model_validate(verification)
