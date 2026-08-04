from datetime import datetime, timedelta, timezone

import pytest

from src.platform.evidence import EvidenceClass
from src.platform.methodology import DataType
from src.visitor_pressure.contracts import (
    EvidenceStatus,
    QualityFlag,
    SourceType,
    TargetName,
    Unit,
    VisitorPressureObservation,
    ensure_evidence_transition,
)

UTC = timezone.utc


def observation(**changes: object) -> VisitorPressureObservation:
    values: dict[str, object] = {
        "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        "location_id": "access-north",
        "target_name": TargetName.VISITOR_COUNT,
        "target_value": 12.0,
        "unit": Unit.PERSONS,
        "source_name": "counter-01",
        "source_type": SourceType.DIRECT_COUNTER,
        "evidence_status": EvidenceStatus.OBSERVED,
        "observed_at": datetime(2026, 1, 1, 23, tzinfo=UTC),
        "available_at": datetime(2026, 1, 2, tzinfo=UTC),
        "data_cutoff": datetime(2026, 2, 1, tzinfo=UTC),
        "quality_flag": QualityFlag.VALID,
        "measurement_interval": timedelta(days=1),
    }
    values.update(changes)
    return VisitorPressureObservation(**values)  # type: ignore[arg-type]


def test_valid_observed_record_and_native_evidence_mapping() -> None:
    record = observation()

    assert record.evidence_status is EvidenceStatus.OBSERVED
    assert record.evidence_status.data_type is DataType.OBSERVED
    assert record.evidence_status.evidence_class is EvidenceClass.REAL


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        observation(timestamp=datetime(2026, 1, 1))


def test_negative_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        observation(target_value=-1)


def test_impossible_occupancy_percentage_is_rejected() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        observation(
            target_name=TargetName.PARKING_OCCUPANCY,
            target_value=101,
            unit=Unit.PERCENTAGE,
        )


def test_target_unit_compatibility_is_enforced() -> None:
    with pytest.raises(ValueError, match="incompatible"):
        observation(unit=Unit.VEHICLES)


def test_fractional_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="integer-like"):
        observation(target_value=1.5)


def test_simulated_evidence_is_preserved() -> None:
    record = observation(
        source_type=SourceType.SYNTHETIC_FIXTURE,
        evidence_status=EvidenceStatus.SIMULATED,
    )

    assert record.evidence_status is EvidenceStatus.SIMULATED
    assert record.evidence_status.evidence_class is EvidenceClass.SIMULATED


def test_simulated_cannot_be_promoted_to_observed() -> None:
    with pytest.raises(ValueError, match="Unsupported evidence promotion"):
        ensure_evidence_transition(EvidenceStatus.SIMULATED, EvidenceStatus.OBSERVED)


def test_synthetic_fixture_cannot_be_mislabelled_as_observed() -> None:
    with pytest.raises(ValueError, match="must remain SIMULATED"):
        observation(source_type=SourceType.SYNTHETIC_FIXTURE)


def test_estimate_cannot_be_treated_as_direct_observation() -> None:
    with pytest.raises(ValueError, match="cannot be treated"):
        observation(source_type=SourceType.ESTIMATE)


def test_calculation_cannot_be_treated_as_direct_observation() -> None:
    with pytest.raises(ValueError, match="cannot be treated"):
        observation(source_type=SourceType.CALCULATED)


def test_environmental_source_cannot_be_visitor_observation() -> None:
    with pytest.raises(ValueError, match="not visitor-pressure"):
        observation(source_type=SourceType.ENVIRONMENTAL_OBSERVATION)


def test_missing_value_remains_explicit() -> None:
    record = observation(
        target_value=None,
        evidence_status=EvidenceStatus.MISSING,
        quality_flag=QualityFlag.MISSING,
    )

    assert record.target_value is None
    assert record.to_dict()["evidence_class"] == "missing"


def test_metadata_cannot_be_mutated_or_override_core_fields() -> None:
    record = observation(metadata={"location_id": "not-the-core-location"})

    with pytest.raises(TypeError):
        record.metadata["location_id"] = "changed"  # type: ignore[index]
    assert record.location_id == "access-north"
    assert record.to_dict()["metadata"]["location_id"] == "not-the-core-location"
