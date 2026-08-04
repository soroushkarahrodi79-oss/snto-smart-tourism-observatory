"""Strict, non-mutating validation for visitor-pressure datasets."""

from __future__ import annotations

import json
import math
from calendar import monthrange
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from statistics import median
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from src.visitor_pressure.contracts import (
    ENVIRONMENTAL_TARGET_NAMES,
    EvidenceStatus,
    QualityFlag,
    SourceType,
    TargetName,
    Unit,
    VisitorPressureObservation,
)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ReasonCode(str, Enum):
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    NO_REAL_OBSERVATIONS = "NO_REAL_OBSERVATIONS"
    MISSING_REQUIRED_COLUMNS = "MISSING_REQUIRED_COLUMNS"
    INVALID_RECORD = "INVALID_RECORD"
    DUPLICATE_TIMESTAMPS = "DUPLICATE_TIMESTAMPS"
    NON_MONOTONIC_CHRONOLOGY = "NON_MONOTONIC_CHRONOLOGY"
    INCONSISTENT_UNITS = "INCONSISTENT_UNITS"
    MIXED_EVIDENCE_STATUSES = "MIXED_EVIDENCE_STATUSES"
    SIMULATED_TARGET = "SIMULATED_TARGET"
    MISSING_PROVENANCE = "MISSING_PROVENANCE"
    ENVIRONMENTAL_VARIABLE_NOT_VISITOR_TARGET = (
        "ENVIRONMENTAL_VARIABLE_NOT_VISITOR_TARGET"
    )
    IRREGULAR_FREQUENCY = "IRREGULAR_FREQUENCY"
    TEMPORAL_GAPS = "TEMPORAL_GAPS"
    INSUFFICIENT_TEMPORAL_DEPTH = "INSUFFICIENT_TEMPORAL_DEPTH"
    INSUFFICIENT_SEASONAL_CYCLES = "INSUFFICIENT_SEASONAL_CYCLES"
    INSUFFICIENT_BACKTESTING_ORIGINS = "INSUFFICIENT_BACKTESTING_ORIGINS"
    STATIC_VALUES_ONLY = "STATIC_VALUES_ONLY"
    ANNUAL_SINGLE_VALUE = "ANNUAL_SINGLE_VALUE"
    TEMPORAL_LEAKAGE = "TEMPORAL_LEAKAGE"
    TIMEZONE_AWARE = "TIMEZONE_AWARE"


class Frequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ANNUAL = "annual"
    IRREGULAR = "irregular"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: ReasonCode
    message: str
    row: int | None = None
    series_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "row": self.row,
            "series_key": self.series_key,
        }


@dataclass(frozen=True)
class FrequencySummary:
    frequency: Frequency
    median_interval_seconds: float | None
    minimum_interval_seconds: float | None
    maximum_interval_seconds: float | None
    missing_expected_periods: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "frequency": self.frequency.value,
            "median_interval_seconds": self.median_interval_seconds,
            "minimum_interval_seconds": self.minimum_interval_seconds,
            "maximum_interval_seconds": self.maximum_interval_seconds,
            "missing_expected_periods": self.missing_expected_periods,
        }


@dataclass(frozen=True)
class SeriesSummary:
    key: str
    location_id: str
    target_name: str
    unit: str
    coverage_start: datetime
    coverage_end: datetime
    observations: int
    usable_observations: int
    frequency: FrequencySummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "location_id": self.location_id,
            "target_name": self.target_name,
            "unit": self.unit,
            "coverage_start": self.coverage_start.isoformat(),
            "coverage_end": self.coverage_end.isoformat(),
            "observations": self.observations,
            "usable_observations": self.usable_observations,
            **self.frequency.to_dict(),
        }


def _default_seasonal_periods() -> Mapping[Frequency, int]:
    return {
        Frequency.HOURLY: 24,
        Frequency.DAILY: 7,
        Frequency.WEEKLY: 52,
        Frequency.MONTHLY: 12,
    }


@dataclass(frozen=True)
class ReadinessPolicy:
    """Provisional experiment policy, configurable for a management context."""

    minimum_observations: int = 30
    minimum_seasonal_cycles: int = 2
    minimum_backtesting_origins: int = 5
    required_seasonal_period: int | None = None
    seasonal_periods: Mapping[Frequency, int] = field(
        default_factory=_default_seasonal_periods
    )

    def __post_init__(self) -> None:
        if self.minimum_observations < 2:
            raise ValueError("minimum_observations must be at least 2")
        if self.minimum_seasonal_cycles < 0:
            raise ValueError("minimum_seasonal_cycles cannot be negative")
        if self.minimum_backtesting_origins < 1:
            raise ValueError("minimum_backtesting_origins must be positive")
        if self.required_seasonal_period is not None and (
            self.required_seasonal_period < 2
        ):
            raise ValueError("required_seasonal_period must be at least 2")
        if any(period < 2 for period in self.seasonal_periods.values()):
            raise ValueError("seasonal periods must be at least 2")
        object.__setattr__(
            self, "seasonal_periods", MappingProxyType(dict(self.seasonal_periods))
        )


@dataclass(frozen=True)
class ValidationResult:
    records: tuple[VisitorPressureObservation, ...]
    issues: tuple[ValidationIssue, ...]
    frequency: FrequencySummary
    series: tuple[SeriesSummary, ...]
    observations_per_location: Mapping[str, int]
    observations_per_target: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "observations_per_location",
            MappingProxyType(dict(self.observations_per_location)),
        )
        object.__setattr__(
            self,
            "observations_per_target",
            MappingProxyType(dict(self.observations_per_target)),
        )

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.WARNING)

    @property
    def info(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.INFO)


REQUIRED_COLUMNS = frozenset(
    {
        "timestamp",
        "location_id",
        "target_name",
        "target_value",
        "unit",
        "source_name",
        "source_type",
        "evidence_status",
        "observed_at",
        "available_at",
        "data_cutoff",
        "quality_flag",
    }
)


def _parse_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    else:
        raise ValueError(f"{name} is required and must be an ISO-8601 datetime")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return parsed


def _parse_interval(value: Any) -> timedelta | None:
    if value in (None, ""):
        return None
    if isinstance(value, timedelta):
        return value
    if isinstance(value, (int, float)):
        return timedelta(seconds=float(value))
    text = str(value).strip().upper()
    aliases = {
        "PT1H": timedelta(hours=1),
        "P1D": timedelta(days=1),
        "P7D": timedelta(days=7),
    }
    if text in aliases:
        return aliases[text]
    return timedelta(seconds=float(text))


def _parse_target_value(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("target_value must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("target_value must be finite")
    return result


def _parse_metadata(value: Any) -> Mapping[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, Mapping):
        return value
    parsed = json.loads(str(value))
    if not isinstance(parsed, dict):
        raise ValueError("metadata must be a JSON object")
    return parsed


def parse_rows(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[list[VisitorPressureObservation], list[ValidationIssue]]:
    """Parse raw rows without silently repairing invalid values."""

    records: list[VisitorPressureObservation] = []
    issues: list[ValidationIssue] = []
    for index, row in enumerate(rows, start=2):
        missing = sorted(REQUIRED_COLUMNS.difference(row.keys()))
        if missing:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    ReasonCode.MISSING_REQUIRED_COLUMNS,
                    f"Missing required columns: {', '.join(missing)}",
                    row=index,
                )
            )
            continue
        raw_target = str(row.get("target_name", "")).strip().lower()
        if raw_target in ENVIRONMENTAL_TARGET_NAMES:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    ReasonCode.ENVIRONMENTAL_VARIABLE_NOT_VISITOR_TARGET,
                    f"Environmental variable {raw_target!r} is not a visitor target",
                    row=index,
                )
            )
            continue
        try:
            record = VisitorPressureObservation(
                timestamp=_parse_datetime(row.get("timestamp"), "timestamp"),
                location_id=str(row.get("location_id", "")),
                target_name=TargetName(raw_target),
                target_value=_parse_target_value(row.get("target_value")),
                unit=Unit(str(row.get("unit", "")).strip().lower()),
                source_name=str(row.get("source_name", "")),
                source_type=SourceType(str(row.get("source_type", "")).strip().lower()),
                evidence_status=EvidenceStatus(
                    str(row.get("evidence_status", "")).strip().lower()
                ),
                observed_at=_parse_datetime(row.get("observed_at"), "observed_at"),
                available_at=_parse_datetime(row.get("available_at"), "available_at"),
                data_cutoff=_parse_datetime(row.get("data_cutoff"), "data_cutoff"),
                quality_flag=QualityFlag(
                    str(row.get("quality_flag", "")).strip().lower()
                ),
                measurement_interval=_parse_interval(row.get("measurement_interval")),
                metadata=_parse_metadata(row.get("metadata")),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            message = str(exc)
            if "source_name is required" in message:
                code = ReasonCode.MISSING_PROVENANCE
            elif "incompatible with target" in message:
                code = ReasonCode.INCONSISTENT_UNITS
            else:
                code = ReasonCode.INVALID_RECORD
            issues.append(ValidationIssue(Severity.ERROR, code, str(exc), row=index))
            continue
        records.append(record)
    return records, issues


def _month_delta(a: datetime, b: datetime) -> int | None:
    same_clock = (a.hour, a.minute, a.second, a.microsecond) == (
        b.hour,
        b.minute,
        b.second,
        b.microsecond,
    )
    both_month_end = (
        a.day == monthrange(a.year, a.month)[1]
        and b.day == monthrange(b.year, b.month)[1]
    )
    if not same_clock or (a.day != b.day and not both_month_end):
        return None
    return (b.year - a.year) * 12 + (b.month - a.month)


def infer_frequency(timestamps: Sequence[datetime]) -> FrequencySummary:
    """Infer cadence conservatively and expose gaps separately."""

    ordered = sorted(set(timestamps))
    if len(ordered) < 2:
        return FrequencySummary(Frequency.UNKNOWN, None, None, None, 0)
    deltas = [(b - a).total_seconds() for a, b in zip(ordered, ordered[1:])]
    positive = [d for d in deltas if d > 0]
    if not positive:
        return FrequencySummary(Frequency.UNKNOWN, None, None, None, 0)
    minimum = min(positive)
    med = median(positive)
    maximum = max(positive)

    frequency = Frequency.IRREGULAR
    base_seconds: float | None = None
    ranges = (
        (Frequency.HOURLY, 3600.0, 0.75 * 3600, 1.25 * 3600),
        (Frequency.DAILY, 86400.0, 0.75 * 86400, 1.25 * 86400),
        (Frequency.WEEKLY, 7 * 86400.0, 6 * 86400.0, 8 * 86400.0),
    )
    for candidate, base, low, high in ranges:
        if low <= minimum <= high and all(
            abs((delta / base) - round(delta / base)) <= 0.08 for delta in positive
        ):
            frequency = candidate
            base_seconds = base
            break

    month_steps = [_month_delta(a, b) for a, b in zip(ordered, ordered[1:])]
    if frequency is Frequency.IRREGULAR and all(
        step is not None and step >= 1 for step in month_steps
    ):
        smallest = min(step for step in month_steps if step is not None)
        if smallest == 1:
            frequency = Frequency.MONTHLY
        elif smallest == 12 and all(step % 12 == 0 for step in month_steps if step):
            frequency = Frequency.ANNUAL

    missing = 0
    if base_seconds is not None:
        missing = sum(max(0, round(delta / base_seconds) - 1) for delta in positive)
    elif frequency is Frequency.MONTHLY:
        missing = sum(max(0, int(step or 1) - 1) for step in month_steps)
    elif frequency is Frequency.ANNUAL:
        missing = sum(max(0, int((step or 12) / 12) - 1) for step in month_steps)

    return FrequencySummary(frequency, med, minimum, maximum, missing)


def _series_key(record: VisitorPressureObservation) -> tuple[str, str, str]:
    return record.location_id, record.target_name.value, record.unit.value


def _combine_frequency(summaries: Sequence[FrequencySummary]) -> FrequencySummary:
    if not summaries:
        return FrequencySummary(Frequency.UNKNOWN, None, None, None, 0)
    frequencies = {s.frequency for s in summaries}
    frequency = (
        next(iter(frequencies)) if len(frequencies) == 1 else Frequency.IRREGULAR
    )
    medians = [
        s.median_interval_seconds for s in summaries if s.median_interval_seconds
    ]
    minimums = [
        s.minimum_interval_seconds for s in summaries if s.minimum_interval_seconds
    ]
    maximums = [
        s.maximum_interval_seconds for s in summaries if s.maximum_interval_seconds
    ]
    return FrequencySummary(
        frequency,
        median(medians) if medians else None,
        min(minimums) if minimums else None,
        max(maximums) if maximums else None,
        sum(s.missing_expected_periods for s in summaries),
    )


def validate_dataset(
    records: Sequence[VisitorPressureObservation],
    policy: ReadinessPolicy | None = None,
    initial_issues: Sequence[ValidationIssue] = (),
) -> ValidationResult:
    """Validate records as supplied; order and invalid evidence are never fixed."""

    policy = policy or ReadinessPolicy()
    issues = list(initial_issues)
    if not records:
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                ReasonCode.NO_OBSERVATIONS,
                "The dataset contains no visitor-pressure observations",
            )
        )
        return ValidationResult((), tuple(issues), infer_frequency([]), (), {}, {})

    issues.append(
        ValidationIssue(
            Severity.INFO,
            ReasonCode.TIMEZONE_AWARE,
            "All parsed timestamps are timezone-aware",
        )
    )
    observed_count = sum(
        r.evidence_status is EvidenceStatus.OBSERVED
        and r.quality_flag is QualityFlag.VALID
        and r.target_value is not None
        for r in records
    )
    if observed_count == 0:
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                ReasonCode.NO_REAL_OBSERVATIONS,
                "No valid direct observed target values are available",
            )
        )
    if any(r.evidence_status is EvidenceStatus.SIMULATED for r in records):
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                ReasonCode.SIMULATED_TARGET,
                "Simulated targets cannot establish readiness for backtesting",
            )
        )

    units_by_target: dict[tuple[str, str], set[Unit]] = defaultdict(set)
    groups: dict[tuple[str, str, str], list[VisitorPressureObservation]] = defaultdict(
        list
    )
    for record in records:
        units_by_target[(record.location_id, record.target_name.value)].add(record.unit)
        groups[_series_key(record)].append(record)

    for target_key, units in sorted(units_by_target.items()):
        if len(units) > 1:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    ReasonCode.INCONSISTENT_UNITS,
                    "A location and target use more than one compatible unit",
                    series_key=f"{target_key[0]}::{target_key[1]}",
                )
            )

    summaries: list[FrequencySummary] = []
    series_summaries: list[SeriesSummary] = []
    for key, group in sorted(groups.items()):
        label = f"{key[0]}::{key[1]}::{key[2]}"
        timestamps = [r.timestamp for r in group]
        if any(b < a for a, b in zip(timestamps, timestamps[1:])):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    ReasonCode.NON_MONOTONIC_CHRONOLOGY,
                    "Input chronology is not monotonic",
                    series_key=label,
                )
            )
        duplicates = [ts for ts, count in Counter(timestamps).items() if count > 1]
        if duplicates:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    ReasonCode.DUPLICATE_TIMESTAMPS,
                    f"Found {len(duplicates)} duplicated series timestamps",
                    series_key=label,
                )
            )
        statuses = {r.evidence_status for r in group}
        if len(statuses) > 1:
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.MIXED_EVIDENCE_STATUSES,
                    "A series mixes evidence statuses; they remain explicitly labelled",
                    series_key=label,
                )
            )

        values = [float(r.target_value) for r in group if r.target_value is not None]
        if len(values) > 1 and len(set(values)) == 1:
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.STATIC_VALUES_ONLY,
                    "The target is constant and may be a repeated static fixture",
                    series_key=label,
                )
            )
        summary = infer_frequency(timestamps)
        summaries.append(summary)
        usable_count = sum(
            r.evidence_status is EvidenceStatus.OBSERVED
            and r.quality_flag is QualityFlag.VALID
            and r.target_value is not None
            for r in group
        )
        series_summaries.append(
            SeriesSummary(
                key=label,
                location_id=key[0],
                target_name=key[1],
                unit=key[2],
                coverage_start=min(timestamps),
                coverage_end=max(timestamps),
                observations=len(group),
                usable_observations=usable_count,
                frequency=summary,
            )
        )
        if summary.frequency is Frequency.IRREGULAR:
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.IRREGULAR_FREQUENCY,
                    "No supported regular frequency can be established",
                    series_key=label,
                )
            )
        if summary.missing_expected_periods:
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.TEMPORAL_GAPS,
                    f"Missing {summary.missing_expected_periods} expected periods",
                    series_key=label,
                )
            )
        if usable_count < policy.minimum_observations:
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.INSUFFICIENT_TEMPORAL_DEPTH,
                    f"{usable_count} usable observations; policy requires "
                    f"{policy.minimum_observations}",
                    series_key=label,
                )
            )
        required_for_origins = (
            policy.minimum_observations + policy.minimum_backtesting_origins - 1
        )
        if usable_count < required_for_origins:
            available_origins = max(0, usable_count - policy.minimum_observations + 1)
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.INSUFFICIENT_BACKTESTING_ORIGINS,
                    f"{available_origins} backtesting origins are possible after "
                    f"the minimum training window; policy requires "
                    f"{policy.minimum_backtesting_origins}",
                    series_key=label,
                )
            )
        seasonal_period = (
            policy.required_seasonal_period
            if policy.required_seasonal_period is not None
            else policy.seasonal_periods.get(summary.frequency)
        )
        if seasonal_period and usable_count < (
            seasonal_period * policy.minimum_seasonal_cycles
        ):
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.INSUFFICIENT_SEASONAL_CYCLES,
                    f"Fewer than {policy.minimum_seasonal_cycles} cycles of "
                    f"{seasonal_period} periods are available",
                    series_key=label,
                )
            )
        if len(group) == 1:
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    ReasonCode.ANNUAL_SINGLE_VALUE,
                    "A single value does not establish a longitudinal series",
                    series_key=label,
                )
            )
        for record in group:
            if (
                record.available_at > record.data_cutoff
                or record.timestamp > record.data_cutoff
            ):
                issues.append(
                    ValidationIssue(
                        Severity.ERROR,
                        ReasonCode.TEMPORAL_LEAKAGE,
                        "Target information was unavailable at the stated data cutoff",
                        series_key=label,
                    )
                )

    return ValidationResult(
        tuple(records),
        tuple(issues),
        _combine_frequency(summaries),
        tuple(series_summaries),
        dict(sorted(Counter(r.location_id for r in records).items())),
        dict(sorted(Counter(r.target_name.value for r in records).items())),
    )
