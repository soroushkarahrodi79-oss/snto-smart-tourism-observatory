"""Typed contracts and evidence safeguards for visitor-pressure data."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from src.platform.evidence import EvidenceClass
from src.platform.methodology import DataType


class EvidenceStatus(str, Enum):
    """Epistemic status required by the visitor-pressure data contract.

    SNTO already has two related axes: :class:`DataType` describes epistemic
    nature and :class:`EvidenceClass` describes provenance.  This enum is the
    input vocabulary for this dataset only; the explicit mappings below keep
    those established axes visible instead of silently replacing either one.
    """

    OBSERVED = "observed"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"
    SIMULATED = "simulated"
    MISSING = "missing"

    @property
    def data_type(self) -> DataType | None:
        return _DATA_TYPE_MAP[self]

    @property
    def evidence_class(self) -> EvidenceClass | None:
        return _EVIDENCE_CLASS_MAP[self]


_DATA_TYPE_MAP: dict[EvidenceStatus, DataType | None] = {
    EvidenceStatus.OBSERVED: DataType.OBSERVED,
    EvidenceStatus.CALCULATED: DataType.CALCULATED,
    EvidenceStatus.ESTIMATED: DataType.ESTIMATED,
    EvidenceStatus.SIMULATED: DataType.SIMULATED,
    EvidenceStatus.MISSING: None,
}

_EVIDENCE_CLASS_MAP: dict[EvidenceStatus, EvidenceClass | None] = {
    EvidenceStatus.OBSERVED: EvidenceClass.REAL,
    # A calculation inherits provenance from its inputs (ADR-004).
    EvidenceStatus.CALCULATED: None,
    EvidenceStatus.ESTIMATED: EvidenceClass.CALIBRATED,
    EvidenceStatus.SIMULATED: EvidenceClass.SIMULATED,
    EvidenceStatus.MISSING: EvidenceClass.MISSING,
}


class TargetName(str, Enum):
    VISITOR_COUNT = "visitor_count"
    VEHICLE_COUNT = "vehicle_count"
    PARKING_OCCUPANCY = "parking_occupancy"
    RESERVATION_COUNT = "reservation_count"
    INBOUND_TRIPS = "inbound_trips"
    PEDESTRIAN_COUNT = "pedestrian_count"


class Unit(str, Enum):
    PERSONS = "persons"
    VEHICLES = "vehicles"
    OCCUPIED_SPACES = "occupied_spaces"
    PERCENTAGE = "percentage"
    RESERVATIONS = "reservations"
    TRIPS = "trips"
    PEDESTRIANS = "pedestrians"


TARGET_UNITS: dict[TargetName, frozenset[Unit]] = {
    TargetName.VISITOR_COUNT: frozenset({Unit.PERSONS}),
    TargetName.VEHICLE_COUNT: frozenset({Unit.VEHICLES}),
    TargetName.PARKING_OCCUPANCY: frozenset({Unit.OCCUPIED_SPACES, Unit.PERCENTAGE}),
    TargetName.RESERVATION_COUNT: frozenset({Unit.RESERVATIONS}),
    TargetName.INBOUND_TRIPS: frozenset({Unit.TRIPS}),
    TargetName.PEDESTRIAN_COUNT: frozenset({Unit.PEDESTRIANS}),
}

COUNT_UNITS = frozenset(
    {
        Unit.PERSONS,
        Unit.VEHICLES,
        Unit.OCCUPIED_SPACES,
        Unit.RESERVATIONS,
        Unit.TRIPS,
        Unit.PEDESTRIANS,
    }
)

ENVIRONMENTAL_TARGET_NAMES = frozenset(
    {
        "ndvi",
        "ndmi",
        "evi",
        "ehs",
        "vegetation_condition",
        "snow_cover",
        "fire_severity",
    }
)


class SourceType(str, Enum):
    DIRECT_COUNTER = "direct_counter"
    MANUAL_COUNT = "manual_count"
    PARKING_SENSOR = "parking_sensor"
    RESERVATION_SYSTEM = "reservation_system"
    MOBILITY_DATA = "mobility_data"
    CALCULATED = "calculated"
    ESTIMATE = "estimate"
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    ENVIRONMENTAL_OBSERVATION = "environmental_observation"


class QualityFlag(str, Enum):
    VALID = "valid"
    SUSPECT = "suspect"
    MISSING = "missing"


def ensure_evidence_transition(
    original: EvidenceStatus, requested: EvidenceStatus
) -> EvidenceStatus:
    """Reject unsupported promotions while allowing honest downgrades."""

    forbidden = {
        (EvidenceStatus.SIMULATED, EvidenceStatus.OBSERVED),
        (EvidenceStatus.ESTIMATED, EvidenceStatus.OBSERVED),
        (EvidenceStatus.CALCULATED, EvidenceStatus.OBSERVED),
        (EvidenceStatus.MISSING, EvidenceStatus.OBSERVED),
    }
    if (original, requested) in forbidden:
        raise ValueError(
            f"Unsupported evidence promotion: {original.value} -> {requested.value}"
        )
    return requested


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


@dataclass(frozen=True)
class VisitorPressureObservation:
    """One timestamped visitor-pressure observation or explicit missing datum."""

    timestamp: datetime
    location_id: str
    target_name: TargetName
    target_value: float | None
    unit: Unit
    source_name: str
    source_type: SourceType
    evidence_status: EvidenceStatus
    observed_at: datetime
    available_at: datetime
    data_cutoff: datetime
    quality_flag: QualityFlag
    measurement_interval: timedelta | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("timestamp", "observed_at", "available_at", "data_cutoff"):
            _require_aware(getattr(self, name), name)
        if not self.location_id.strip():
            raise ValueError("location_id is required")
        if not self.source_name.strip():
            raise ValueError("source_name is required")
        if self.unit not in TARGET_UNITS[self.target_name]:
            raise ValueError(
                f"Unit {self.unit.value!r} is incompatible with "
                f"target {self.target_name.value!r}"
            )
        if self.source_type is SourceType.ENVIRONMENTAL_OBSERVATION:
            raise ValueError(
                "Environmental observations are not visitor-pressure targets"
            )
        if (
            self.source_type is SourceType.SYNTHETIC_FIXTURE
            and self.evidence_status is not EvidenceStatus.SIMULATED
        ):
            raise ValueError("Synthetic fixtures must remain SIMULATED")
        if self.source_type is SourceType.ESTIMATE and (
            self.evidence_status is EvidenceStatus.OBSERVED
        ):
            raise ValueError(
                "Estimated values cannot be treated as direct observations"
            )
        if self.source_type is SourceType.CALCULATED and (
            self.evidence_status is EvidenceStatus.OBSERVED
        ):
            raise ValueError(
                "Calculated values cannot be treated as direct observations"
            )
        if (self.evidence_status is EvidenceStatus.MISSING) != (
            self.quality_flag is QualityFlag.MISSING
        ):
            raise ValueError(
                "MISSING evidence and quality flags must be declared together"
            )
        if self.evidence_status is EvidenceStatus.MISSING:
            if self.target_value is not None:
                raise ValueError(
                    "MISSING evidence must have an explicit null target_value"
                )
        else:
            if self.target_value is None:
                raise ValueError("A non-missing observation requires target_value")
            if isinstance(self.target_value, bool) or not isinstance(
                self.target_value, (int, float)
            ):
                raise ValueError("target_value must be numeric")
            if not math.isfinite(float(self.target_value)):
                raise ValueError("target_value must be finite")
            if self.target_value < 0:
                raise ValueError("target_value cannot be negative")
            if self.unit in COUNT_UNITS and not float(self.target_value).is_integer():
                raise ValueError("count targets require an integer-like target_value")
            if self.unit is Unit.PERCENTAGE and self.target_value > 100:
                raise ValueError("percentage occupancy must be between 0 and 100")
        if self.measurement_interval is not None and (
            self.measurement_interval <= timedelta(0)
        ):
            raise ValueError("measurement_interval must be positive")
        if self.observed_at > self.available_at:
            raise ValueError("available_at cannot precede observed_at")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation without changing semantics."""

        return {
            "timestamp": self.timestamp.isoformat(),
            "location_id": self.location_id,
            "target_name": self.target_name.value,
            "target_value": self.target_value,
            "unit": self.unit.value,
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "evidence_status": self.evidence_status.value,
            "evidence_class": (
                self.evidence_status.evidence_class.value
                if self.evidence_status.evidence_class is not None
                else None
            ),
            "observed_at": self.observed_at.isoformat(),
            "available_at": self.available_at.isoformat(),
            "data_cutoff": self.data_cutoff.isoformat(),
            "quality_flag": self.quality_flag.value,
            "measurement_interval_seconds": (
                self.measurement_interval.total_seconds()
                if self.measurement_interval is not None
                else None
            ),
            "metadata": dict(self.metadata),
        }
