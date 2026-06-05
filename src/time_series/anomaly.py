from __future__ import annotations

import math
from dataclasses import dataclass

from src.config.constants import ANOMALY_Z_THRESHOLD


@dataclass(frozen=True)
class AnomalyResult:
    z_score: float
    is_anomaly: bool
    direction: str  # "low" | "high" | "none"


def compute_anomaly(
    current_value: float,
    historical_series: list[float],
    z_threshold: float = ANOMALY_Z_THRESHOLD,
) -> AnomalyResult:
    """
    Z-score anomaly detection relative to historical baseline.
    Returns direction='none' when the series has zero variance.
    """
    n = len(historical_series)
    if n == 0:
        return AnomalyResult(z_score=0.0, is_anomaly=False, direction="none")

    mean = sum(historical_series) / n
    variance = sum((x - mean) ** 2 for x in historical_series) / n
    std = math.sqrt(variance)

    if std == 0.0:
        return AnomalyResult(z_score=0.0, is_anomaly=False, direction="none")

    z = (current_value - mean) / std
    is_anomaly = abs(z) > z_threshold
    direction = "none"
    if is_anomaly:
        direction = "low" if z < 0 else "high"

    return AnomalyResult(z_score=z, is_anomaly=is_anomaly, direction=direction)
