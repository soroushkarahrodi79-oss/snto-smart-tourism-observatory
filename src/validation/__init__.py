"""SNTO validation layer — ground-truth & pseudo-validation (F5).

Field-observation schema and satellite↔terrain agreement metrics (Spearman
correlation, control–impact BACI contrast) to demonstrate that the satellite
EHS tracks degradation observed on the ground.
"""
from src.validation.agreement import (
    AgreementReport,
    ContrastResult,
    cliffs_delta,
    control_impact_contrast,
    spearman_correlation,
    validate_satellite_vs_field,
)
from src.validation.field import (
    ErosionClass,
    FieldObservation,
    split_impact_control,
)

__all__ = [
    "AgreementReport",
    "ContrastResult",
    "cliffs_delta",
    "control_impact_contrast",
    "spearman_correlation",
    "validate_satellite_vs_field",
    "ErosionClass",
    "FieldObservation",
    "split_impact_control",
]
