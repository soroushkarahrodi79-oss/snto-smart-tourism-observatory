"""
Forward-looking projection layer (v2.2).

SNTO's first forecasting surface. Every output is a scenario
(``EvidenceClass.SIMULATED``), never an observation — see
:mod:`src.forecasting.projection`.
"""
from src.forecasting.projection import (
    FORECAST_EVIDENCE_CLASS,
    Forecast,
    ThresholdCrossing,
    ThresholdDirection,
    project_trend,
    threshold_crossing,
)

__all__ = [
    "FORECAST_EVIDENCE_CLASS",
    "Forecast",
    "ThresholdCrossing",
    "ThresholdDirection",
    "project_trend",
    "threshold_crossing",
]
