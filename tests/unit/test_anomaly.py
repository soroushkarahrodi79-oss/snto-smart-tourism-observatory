from __future__ import annotations

from src.time_series.anomaly import AnomalyResult, compute_anomaly


def test_very_low_value_is_anomaly_low():
    historical = [0.5, 0.51, 0.49, 0.50, 0.52, 0.50, 0.48, 0.51, 0.50, 0.49]
    current = 0.10  # far below mean
    result = compute_anomaly(current, historical)
    assert result.is_anomaly is True
    assert result.direction == "low"
    assert result.z_score < -2.0


def test_value_inside_range_not_anomaly():
    historical = [0.4, 0.5, 0.6, 0.45, 0.55]
    current = 0.50
    result = compute_anomaly(current, historical)
    assert result.is_anomaly is False
    assert result.direction == "none"


def test_very_high_value_is_anomaly_high():
    historical = [0.5, 0.51, 0.49, 0.50, 0.52, 0.50, 0.48, 0.51, 0.50, 0.49]
    current = 0.99
    result = compute_anomaly(current, historical)
    assert result.is_anomaly is True
    assert result.direction == "high"


def test_empty_historical_no_anomaly():
    result = compute_anomaly(0.3, [])
    assert result.is_anomaly is False
    assert result.z_score == 0.0


def test_zero_variance_historical_no_anomaly():
    result = compute_anomaly(0.5, [0.5, 0.5, 0.5])
    assert result.is_anomaly is False
    assert result.direction == "none"
