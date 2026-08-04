import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.forecasting.projection import project_trend
from src.platform.evidence import EvidenceClass
from src.visitor_pressure.audit import (
    ReadinessStatus,
    audit_csv,
    audit_records,
    audit_rows,
)
from src.visitor_pressure.contracts import (
    EvidenceStatus,
    QualityFlag,
    SourceType,
    TargetName,
    Unit,
    VisitorPressureObservation,
)
from src.visitor_pressure.data_validation import ReasonCode

UTC = timezone.utc
FIXTURE = Path(__file__).parents[1] / "fixtures" / "visitor_pressure_synthetic.csv"
GENERATED_AT = datetime(2026, 2, 1, tzinfo=UTC)


def observed_series(count: int) -> list[VisitorPressureObservation]:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        VisitorPressureObservation(
            timestamp=start + timedelta(days=index),
            location_id="counter-west",
            target_name=TargetName.VISITOR_COUNT,
            target_value=float(10 + index % 7),
            unit=Unit.PERSONS,
            source_name="certified-counter",
            source_type=SourceType.DIRECT_COUNTER,
            evidence_status=EvidenceStatus.OBSERVED,
            observed_at=start + timedelta(days=index, hours=20),
            available_at=start + timedelta(days=index + 1),
            data_cutoff=cutoff,
            quality_flag=QualityFlag.VALID,
            measurement_interval=timedelta(days=1),
        )
        for index in range(count)
    ]


def test_empty_dataset_is_insufficient_evidence() -> None:
    result = audit_records(
        [], dataset_id="empty", source_name="none", generated_at=GENERATED_AT
    )

    assert result.status is ReadinessStatus.INSUFFICIENT_EVIDENCE
    assert ReasonCode.NO_OBSERVATIONS in result.reason_codes


def test_only_simulated_csv_is_insufficient_and_disclosed() -> None:
    result = audit_csv(
        FIXTURE,
        dataset_id="synthetic-weekly-pattern",
        source_name="test fixture only",
        generated_at=GENERATED_AT,
    )

    assert result.status is ReadinessStatus.INSUFFICIENT_EVIDENCE
    assert result.to_dict()["evidence_summary"]["simulated"] == 21
    assert ReasonCode.SIMULATED_TARGET in result.reason_codes


def test_annual_single_value_is_insufficient() -> None:
    result = audit_records(
        observed_series(1),
        dataset_id="annual-static",
        source_name="annual report",
        generated_at=GENERATED_AT,
    )

    assert result.status is ReadinessStatus.INSUFFICIENT_EVIDENCE
    assert ReasonCode.ANNUAL_SINGLE_VALUE in result.reason_codes


def test_environmental_target_is_invalid_not_visitor_evidence() -> None:
    row = {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "location_id": "plot-a",
        "target_name": "ndvi",
        "target_value": "0.8",
        "unit": "percentage",
        "source_name": "Sentinel-2",
        "source_type": "environmental_observation",
        "evidence_status": "observed",
        "observed_at": "2026-01-01T10:00:00+00:00",
        "available_at": "2026-01-02T00:00:00+00:00",
        "data_cutoff": "2026-02-01T00:00:00+00:00",
        "quality_flag": "valid",
    }
    result = audit_rows(
        [row],
        dataset_id="environmental",
        source_name="satellite",
        generated_at=GENERATED_AT,
    )

    assert result.status is ReadinessStatus.INVALID_DATASET
    assert ReasonCode.ENVIRONMENTAL_VARIABLE_NOT_VISITOR_TARGET in result.reason_codes


def test_audit_json_schema_and_output_are_deterministic() -> None:
    first = audit_csv(
        FIXTURE,
        dataset_id="fixture",
        source_name="tests",
        generated_at=GENERATED_AT,
    )
    second = audit_csv(
        FIXTURE,
        dataset_id="fixture",
        source_name="tests",
        generated_at=GENERATED_AT,
    )

    assert first.to_json() == second.to_json()
    payload = json.loads(first.to_json())
    assert payload["schema_version"] == "1.0"
    assert payload["coverage"]["frequency"] == "daily"
    assert payload["coverage"]["series"][0]["unit"] == "persons"
    assert payload["coverage"]["series"][0]["usable_observations"] == 0
    assert payload["readiness"]["eligible_for_backtesting"] is False
    assert set(payload["validation"]) == {"errors", "warnings", "info"}
    assert set(payload["temporal_leakage"]) == {"detected", "issues"}


def test_real_series_can_be_ready_under_explicit_policy_defaults() -> None:
    result = audit_records(
        observed_series(35),
        dataset_id="real-counter",
        source_name="counter authority",
        generated_at=GENERATED_AT,
    )

    assert result.status is ReadinessStatus.READY_FOR_BACKTESTING
    assert result.eligible_for_backtesting


def test_existing_environmental_forecast_behavior_is_unchanged() -> None:
    forecast = project_trend([10, 11, 12, 13, 14], 2)

    assert forecast.evidence_class is EvidenceClass.SIMULATED
