from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.visitor_pressure.contracts import (
    EvidenceStatus,
    QualityFlag,
    SourceType,
    TargetName,
    Unit,
    VisitorPressureObservation,
)
from src.visitor_pressure.data_validation import (
    Frequency,
    ReadinessPolicy,
    ReasonCode,
    infer_frequency,
    parse_rows,
    validate_dataset,
)

UTC = timezone.utc


def record(
    timestamp: datetime,
    value: float | None = 10,
    *,
    available_at: datetime | None = None,
    observed_at: datetime | None = None,
    unit: Unit = Unit.PERSONS,
    target_name: TargetName = TargetName.VISITOR_COUNT,
    location_id: str = "trailhead-a",
    source_type: SourceType = SourceType.MANUAL_COUNT,
    evidence_status: EvidenceStatus = EvidenceStatus.OBSERVED,
    quality_flag: QualityFlag = QualityFlag.VALID,
    data_cutoff: datetime | None = None,
) -> VisitorPressureObservation:
    return VisitorPressureObservation(
        timestamp=timestamp,
        location_id=location_id,
        target_name=target_name,
        target_value=value,
        unit=unit,
        source_name="manual-census-2026",
        source_type=source_type,
        evidence_status=evidence_status,
        observed_at=observed_at or timestamp + timedelta(hours=12),
        available_at=available_at or timestamp + timedelta(days=1),
        data_cutoff=data_cutoff or datetime(2026, 12, 31, tzinfo=UTC),
        quality_flag=quality_flag,
        measurement_interval=timedelta(days=1),
    )


def codes(result: object) -> set[ReasonCode]:
    return {issue.code for issue in result.issues}  # type: ignore[attr-defined]


def test_duplicate_timestamp_is_an_error() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset([record(timestamp), record(timestamp, 11)])

    assert ReasonCode.DUPLICATE_TIMESTAMPS in codes(result)
    assert result.errors


def test_non_monotonic_input_chronology_is_an_error() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset([record(day + timedelta(days=1)), record(day)])

    assert ReasonCode.NON_MONOTONIC_CHRONOLOGY in codes(result)


def test_irregular_frequency_is_reported() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset(
        [
            record(day),
            record(day + timedelta(days=1)),
            record(day + timedelta(days=2.5)),
        ]
    )

    assert result.frequency.frequency is Frequency.IRREGULAR
    assert ReasonCode.IRREGULAR_FREQUENCY in codes(result)


def test_missing_expected_period_is_counted() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset(
        [record(day), record(day + timedelta(days=1)), record(day + timedelta(days=3))]
    )

    assert result.frequency.frequency is Frequency.DAILY
    assert result.frequency.missing_expected_periods == 1
    assert ReasonCode.TEMPORAL_GAPS in codes(result)


def test_constant_series_is_not_longitudinal_evidence() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset([record(day + timedelta(days=i)) for i in range(3)])

    assert ReasonCode.STATIC_VALUES_ONLY in codes(result)


def test_insufficient_observations_and_backtesting_origins_are_reported() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset(
        [record(day + timedelta(days=i), float(i)) for i in range(10)]
    )

    assert ReasonCode.INSUFFICIENT_TEMPORAL_DEPTH in codes(result)
    assert ReasonCode.INSUFFICIENT_BACKTESTING_ORIGINS in codes(result)


def test_insufficient_seasonal_cycles_are_configurable() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    policy = ReadinessPolicy(
        minimum_observations=2,
        minimum_seasonal_cycles=2,
        minimum_backtesting_origins=1,
        required_seasonal_period=7,
    )
    result = validate_dataset(
        [record(day + timedelta(days=i), float(i % 7)) for i in range(10)], policy
    )

    assert ReasonCode.INSUFFICIENT_SEASONAL_CYCLES in codes(result)


def test_future_availability_at_forecast_cutoff_is_leakage() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset(
        [record(timestamp, available_at=datetime(2027, 1, 1, tzinfo=UTC))]
    )

    assert ReasonCode.TEMPORAL_LEAKAGE in codes(result)
    assert result.errors


def test_exact_availability_cutoff_boundary_is_not_leakage() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    result = validate_dataset(
        [record(timestamp, available_at=cutoff, data_cutoff=cutoff)]
    )

    assert ReasonCode.TEMPORAL_LEAKAGE not in codes(result)


def test_timestamp_equal_to_cutoff_is_not_leakage() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    result = validate_dataset(
        [
            record(
                cutoff,
                observed_at=cutoff,
                available_at=cutoff,
                data_cutoff=cutoff,
            )
        ]
    )

    assert ReasonCode.TEMPORAL_LEAKAGE not in codes(result)


def test_mixed_compatible_units_are_rejected_within_one_target_series() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset(
        [
            record(
                day,
                unit=Unit.PERCENTAGE,
                target_name=TargetName.PARKING_OCCUPANCY,
            ),
            record(
                day + timedelta(days=1),
                unit=Unit.OCCUPIED_SPACES,
                target_name=TargetName.PARKING_OCCUPANCY,
            ),
        ]
    )

    assert ReasonCode.INCONSISTENT_UNITS in codes(result)
    assert result.errors


def test_month_end_and_leap_year_dates_are_monthly() -> None:
    summary = infer_frequency(
        [
            datetime(2024, 1, 31, tzinfo=UTC),
            datetime(2024, 2, 29, tzinfo=UTC),
            datetime(2024, 3, 31, tzinfo=UTC),
        ]
    )

    assert summary.frequency is Frequency.MONTHLY
    assert summary.missing_expected_periods == 0


def test_daylight_saving_transition_remains_daily() -> None:
    madrid = ZoneInfo("Europe/Madrid")
    summary = infer_frequency(
        [
            datetime(2026, 3, 28, tzinfo=madrid),
            datetime(2026, 3, 29, tzinfo=madrid),
            datetime(2026, 3, 30, tzinfo=madrid),
        ]
    )

    assert summary.frequency is Frequency.DAILY


def test_multiple_series_are_summarized_at_their_own_frequency() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    records = [record(day + timedelta(days=i), float(i + 1)) for i in range(3)] + [
        record(
            day + timedelta(weeks=i),
            float(i + 1),
            location_id="car-park-b",
            target_name=TargetName.VEHICLE_COUNT,
            unit=Unit.VEHICLES,
        )
        for i in range(3)
    ]
    result = validate_dataset(records)

    assert {summary.frequency.frequency for summary in result.series} == {
        Frequency.DAILY,
        Frequency.WEEKLY,
    }
    assert all(summary.key.count("::") == 2 for summary in result.series)
    assert result.frequency.frequency is Frequency.IRREGULAR


def test_missing_placeholders_do_not_satisfy_minimum_depth() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    records = [record(day, 1)] + [
        record(
            day + timedelta(days=i),
            None,
            evidence_status=EvidenceStatus.MISSING,
            quality_flag=QualityFlag.MISSING,
        )
        for i in range(1, 5)
    ]
    policy = ReadinessPolicy(
        minimum_observations=2,
        minimum_seasonal_cycles=0,
        minimum_backtesting_origins=1,
    )

    assert ReasonCode.INSUFFICIENT_TEMPORAL_DEPTH in codes(
        validate_dataset(records, policy)
    )


def test_mixed_evidence_is_disclosed() -> None:
    day = datetime(2026, 1, 1, tzinfo=UTC)
    result = validate_dataset(
        [
            record(day, 1),
            record(
                day + timedelta(days=1),
                2,
                evidence_status=EvidenceStatus.SIMULATED,
            ),
        ]
    )

    assert ReasonCode.MIXED_EVIDENCE_STATUSES in codes(result)
    assert ReasonCode.SIMULATED_TARGET in codes(result)


def test_raw_incompatible_target_unit_has_stable_reason_code() -> None:
    rows = [
        {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "location_id": "counter-a",
            "target_name": "visitor_count",
            "target_value": "1",
            "unit": "vehicles",
            "source_name": "counter",
            "source_type": "direct_counter",
            "evidence_status": "observed",
            "observed_at": "2026-01-01T12:00:00+00:00",
            "available_at": "2026-01-02T00:00:00+00:00",
            "data_cutoff": "2026-01-02T00:00:00+00:00",
            "quality_flag": "valid",
        }
    ]

    _, issues = parse_rows(rows)
    assert issues[0].code is ReasonCode.INCONSISTENT_UNITS
