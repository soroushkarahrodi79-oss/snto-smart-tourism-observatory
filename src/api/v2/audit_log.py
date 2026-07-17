"""
Read-only /api/v2/audit-log endpoint (Fase 5, 5.7).

Exposes the audit trail written by every 5.3–5.6 write (via
``src.persistence.services.audit``). Optional ``subject_type`` +
``subject_id`` narrow to one resource's history; otherwise the full log is
returned newest-first with limit/offset paging. Read-only by design — the
audit log is append-only and never mutated through the API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.v2.schemas import AuditLogEntryOut, AuditLogListResponse
from src.persistence.models.audit_log import AuditLogEntry
from src.persistence.repositories import AuditLogRepository
from src.persistence.session import get_db

router = APIRouter(tags=["audit-log"])


@router.get("/", response_model=AuditLogListResponse)
def list_audit_log(
    subject_type: str | None = None,
    subject_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    if (subject_type is None) != (subject_id is None):
        raise HTTPException(
            status_code=422,
            detail="subject_type and subject_id must be provided together",
        )

    if subject_type is not None and subject_id is not None:
        entries = AuditLogRepository(db).list_by_subject(subject_type, subject_id)
    else:
        # Newest-first for the unfiltered log; paged.
        stmt = (
            select(AuditLogEntry)
            .order_by(AuditLogEntry.id.desc())
            .offset(offset)
            .limit(limit)
        )
        entries = list(db.scalars(stmt))

    return AuditLogListResponse(
        total=len(entries),
        entries=[AuditLogEntryOut.model_validate(e) for e in entries],
    )
