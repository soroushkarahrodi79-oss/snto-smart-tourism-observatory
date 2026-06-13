"""SNTO temporal layer — multi-year series scaffolding (F2).

Declarative series specification, Mann-Kendall validity gate and provenance
manifest. These structure the path from the current 2-scene PNSG snapshot to a
reproducible, auditable 2021–2026 monthly series, without yet ingesting data.
"""
from src.temporal.manifest import (
    DataStatus,
    PeriodRecord,
    SeriesManifest,
    build_manifest_from_observations,
    classify_source,
)
from src.temporal.series_spec import (
    PNSG_5Y,
    Cadence,
    Period,
    SeriesSpec,
    spec_for_territory,
)
from src.temporal.trend_gate import (
    MK_MIN_N,
    MK_ROBUST_N,
    TrendGateResult,
    TrendReadiness,
    assess_trend_readiness,
)

__all__ = [
    "PNSG_5Y",
    "Cadence",
    "Period",
    "SeriesSpec",
    "spec_for_territory",
    "MK_MIN_N",
    "MK_ROBUST_N",
    "TrendGateResult",
    "TrendReadiness",
    "assess_trend_readiness",
    "DataStatus",
    "PeriodRecord",
    "SeriesManifest",
    "build_manifest_from_observations",
    "classify_source",
]
