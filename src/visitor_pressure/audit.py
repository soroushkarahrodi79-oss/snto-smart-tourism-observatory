"""Reusable visitor-pressure readiness audit with machine-readable output."""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.visitor_pressure.contracts import (
    EvidenceStatus,
    VisitorPressureObservation,
)
from src.visitor_pressure.data_validation import (
    ReadinessPolicy,
    ReasonCode,
    Severity,
    ValidationResult,
    parse_rows,
    validate_dataset,
)

logger = logging.getLogger(__name__)


class ReadinessStatus(str, Enum):
    READY_FOR_BACKTESTING = "READY_FOR_BACKTESTING"
    PARTIALLY_READY = "PARTIALLY_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INVALID_DATASET = "INVALID_DATASET"


_INSUFFICIENT_CODES = frozenset(
    {
        ReasonCode.NO_OBSERVATIONS,
        ReasonCode.NO_REAL_OBSERVATIONS,
        ReasonCode.SIMULATED_TARGET,
        ReasonCode.INSUFFICIENT_TEMPORAL_DEPTH,
        ReasonCode.INSUFFICIENT_SEASONAL_CYCLES,
        ReasonCode.INSUFFICIENT_BACKTESTING_ORIGINS,
        ReasonCode.STATIC_VALUES_ONLY,
        ReasonCode.ANNUAL_SINGLE_VALUE,
    }
)
_PARTIAL_CODES = frozenset(
    {
        ReasonCode.IRREGULAR_FREQUENCY,
        ReasonCode.TEMPORAL_GAPS,
        ReasonCode.MIXED_EVIDENCE_STATUSES,
    }
)


@dataclass(frozen=True)
class AuditResult:
    schema_version: str
    status: ReadinessStatus
    generated_at: datetime
    dataset_id: str
    source_name: str
    validation: ValidationResult
    reason_codes: tuple[ReasonCode, ...]
    limitations: tuple[str, ...]

    @property
    def eligible_for_backtesting(self) -> bool:
        return self.status is ReadinessStatus.READY_FOR_BACKTESTING

    def to_dict(self) -> dict[str, Any]:
        records = self.validation.records
        evidence = Counter(r.evidence_status.value for r in records)
        start = min((r.timestamp for r in records), default=None)
        end = max((r.timestamp for r in records), default=None)
        issues_by_severity = {
            severity.value: [
                issue.to_dict()
                for issue in self.validation.issues
                if issue.severity is severity
            ]
            for severity in Severity
        }
        leakage = [
            issue.to_dict()
            for issue in self.validation.issues
            if issue.code is ReasonCode.TEMPORAL_LEAKAGE
        ]
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "generated_at": self.generated_at.isoformat(),
            "dataset_id": self.dataset_id,
            "source_name": self.source_name,
            "evidence_summary": {
                status.value: evidence.get(status.value, 0) for status in EvidenceStatus
            },
            "target_summary": dict(self.validation.observations_per_target),
            "locations": sorted(self.validation.observations_per_location),
            "coverage": {
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
                **self.validation.frequency.to_dict(),
                "observations": len(records),
                "observations_per_location": dict(
                    self.validation.observations_per_location
                ),
                "observations_per_target": dict(
                    self.validation.observations_per_target
                ),
                "series": [summary.to_dict() for summary in self.validation.series],
            },
            "validation": {
                "errors": issues_by_severity[Severity.ERROR.value],
                "warnings": issues_by_severity[Severity.WARNING.value],
                "info": issues_by_severity[Severity.INFO.value],
            },
            "temporal_leakage": {
                "detected": bool(leakage),
                "issues": leakage,
            },
            "readiness": {
                "eligible_for_backtesting": self.eligible_for_backtesting,
                "reason_codes": [code.value for code in self.reason_codes],
            },
            "limitations": list(self.limitations),
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True
        )


def _status_for(validation: ValidationResult) -> ReadinessStatus:
    if validation.errors:
        return ReadinessStatus.INVALID_DATASET
    codes = {issue.code for issue in validation.issues}
    if codes.intersection(_INSUFFICIENT_CODES):
        return ReadinessStatus.INSUFFICIENT_EVIDENCE
    if codes.intersection(_PARTIAL_CODES):
        return ReadinessStatus.PARTIALLY_READY
    return ReadinessStatus.READY_FOR_BACKTESTING


def _build_result(
    validation: ValidationResult,
    *,
    dataset_id: str,
    source_name: str,
    generated_at: datetime | None,
) -> AuditResult:
    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    status = _status_for(validation)
    codes = tuple(sorted({i.code for i in validation.issues}, key=lambda c: c.value))
    limitations = (
        "Decision C remains in force until a traceable real visitor-pressure "
        "series satisfies the configured temporal policy.",
        "Readiness for backtesting is not evidence of ecological causality, "
        "carrying capacity, or a Limits of Acceptable Change threshold.",
    )
    logger.info(
        "visitor-pressure audit dataset=%s status=%s observations=%d",
        dataset_id,
        status.value,
        len(validation.records),
    )
    return AuditResult(
        "1.0",
        status,
        timestamp,
        dataset_id,
        source_name,
        validation,
        codes,
        limitations,
    )


def audit_records(
    records: Sequence[VisitorPressureObservation],
    *,
    dataset_id: str,
    source_name: str,
    policy: ReadinessPolicy | None = None,
    generated_at: datetime | None = None,
) -> AuditResult:
    validation = validate_dataset(records, policy)
    return _build_result(
        validation,
        dataset_id=dataset_id,
        source_name=source_name,
        generated_at=generated_at,
    )


def audit_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    dataset_id: str,
    source_name: str,
    policy: ReadinessPolicy | None = None,
    generated_at: datetime | None = None,
) -> AuditResult:
    records, parse_issues = parse_rows(rows)
    validation = validate_dataset(records, policy, parse_issues)
    return _build_result(
        validation,
        dataset_id=dataset_id,
        source_name=source_name,
        generated_at=generated_at,
    )


def audit_csv(
    path: str | Path,
    *,
    dataset_id: str,
    source_name: str,
    policy: ReadinessPolicy | None = None,
    generated_at: datetime | None = None,
) -> AuditResult:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return audit_rows(
        rows,
        dataset_id=dataset_id,
        source_name=source_name,
        policy=policy,
        generated_at=generated_at,
    )
