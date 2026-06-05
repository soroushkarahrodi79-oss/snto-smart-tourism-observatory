from __future__ import annotations

"""
Multi-year monthly climatological baseline and inter-annual anomaly detection.

This module constructs per-month statistics from a multi-year observation
record and computes same-month z-score anomalies — the scientifically correct
approach to identifying anomalous values relative to the expected seasonal cycle.

The anomaly module (anomaly.py) compares a value to the other months in the
same year — this is useful for within-year diagnostics but conflates seasonal
variability with inter-annual anomalies. This module performs the correct
inter-annual comparison: July 2022 vs July 2019-2021.
"""

import math
import statistics
from dataclasses import dataclass, field

from src.assets.models import AssetObservation


@dataclass
class MonthlyClimatology:
    """Descriptive statistics for a single calendar month across all years."""

    month: int
    n_years: int
    mean: float
    median: float
    std: float
    p10: float   # 10th percentile (drought boundary)
    p25: float
    p75: float
    p90: float   # 90th percentile (wet boundary)
    min_val: float
    max_val: float

    def z_score(self, value: float) -> float:
        """Standardized anomaly of a single value relative to this month's baseline."""
        if self.std == 0.0:
            return 0.0
        return (value - self.mean) / self.std

    def classify_anomaly(self, value: float) -> str:
        """
        Classify a value against its climatological baseline.

        Returns one of:
          anomaly_low_severe    : z < -2.0 (< ~p2.5)
          anomaly_low           : z in [-2, -1.5)
          below_normal          : z in [-1.5, -0.5)
          normal                : z in [-0.5, +0.5]
          above_normal          : z in (+0.5, +1.5]
          anomaly_high          : z in (1.5, 2.0]
          anomaly_high_severe   : z > 2.0
        """
        z = self.z_score(value)
        if z < -2.0:
            return "anomaly_low_severe"
        if z < -1.5:
            return "anomaly_low"
        if z < -0.5:
            return "below_normal"
        if z <= 0.5:
            return "normal"
        if z <= 1.5:
            return "above_normal"
        if z <= 2.0:
            return "anomaly_high"
        return "anomaly_high_severe"


def _percentile(data: list[float], p: float) -> float:
    """Linear interpolation percentile (equivalent to numpy percentile method='linear')."""
    n = len(data)
    if n == 0:
        return 0.0
    sorted_data = sorted(data)
    idx = (n - 1) * p / 100.0
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    frac = idx - lo
    return sorted_data[lo] * (1 - frac) + sorted_data[hi] * frac


def build_climatology(
    observations: list[AssetObservation],
    index: str = "ndvi",
) -> dict[int, MonthlyClimatology]:
    """
    Build a per-month baseline from a multi-year observation record.

    Args:
        observations: All valid observations across multiple years.
        index: Which spectral index to baseline ('ndvi' or 'ndmi').

    Returns:
        Dict mapping month number (1–12) to MonthlyClimatology.
    """
    by_month: dict[int, list[float]] = {m: [] for m in range(1, 13)}

    for obs in observations:
        val = obs.ndvi if index == "ndvi" else obs.ndmi
        by_month[obs.month].append(val)

    climatology: dict[int, MonthlyClimatology] = {}
    for month, values in by_month.items():
        if len(values) < 2:
            continue
        values.sort()
        climatology[month] = MonthlyClimatology(
            month=month,
            n_years=len(values),
            mean=round(statistics.mean(values), 5),
            median=round(statistics.median(values), 5),
            std=round(statistics.stdev(values), 5),
            p10=round(_percentile(values, 10), 5),
            p25=round(_percentile(values, 25), 5),
            p75=round(_percentile(values, 75), 5),
            p90=round(_percentile(values, 90), 5),
            min_val=round(min(values), 5),
            max_val=round(max(values), 5),
        )

    return climatology


@dataclass(frozen=True)
class AnomalyEvent:
    """A detected inter-annual anomaly for a specific month-year pair."""

    year: int
    month: int
    index: str          # "ndvi" | "ndmi"
    observed: float
    expected: float     # climatological mean
    z_score: float
    classification: str  # anomaly_low_severe | anomaly_low | ...
    delta: float        # observed - expected


def detect_anomaly_events(
    observations: list[AssetObservation],
    climatology: dict[int, MonthlyClimatology],
    index: str = "ndvi",
    z_threshold: float = 1.5,
) -> list[AnomalyEvent]:
    """
    Detect all months where the observed value is anomalous relative to the
    multi-year same-month climatological baseline.

    Uses |z| > z_threshold (default 1.5σ) to flag events.
    z = 1.5 corresponds to ~p7 or ~p93, capturing meaningful anomalies
    without excessive false positives.

    Returns events sorted by descending |z_score| (most severe first).
    """
    events: list[AnomalyEvent] = []

    for obs in observations:
        clim = climatology.get(obs.month)
        if clim is None:
            continue
        val = obs.ndvi if index == "ndvi" else obs.ndmi
        z = clim.z_score(val)
        if abs(z) >= z_threshold:
            events.append(
                AnomalyEvent(
                    year=obs.year,
                    month=obs.month,
                    index=index,
                    observed=round(val, 4),
                    expected=clim.mean,
                    z_score=round(z, 3),
                    classification=clim.classify_anomaly(val),
                    delta=round(val - clim.mean, 4),
                )
            )

    return sorted(events, key=lambda e: -abs(e.z_score))
