"""Unit tests for the canonical evidence-class vocabulary + gating (#10)."""

from __future__ import annotations

from src.platform.evidence import (
    DecisionUse,
    EvidenceClass,
    descriptor,
    from_data_status,
    from_data_type,
    gating_matrix,
    legend,
    supports,
)
from src.platform.methodology import DataType
from src.temporal.manifest import DataStatus


def test_four_adr004_classes_plus_missing_present():
    values = {e.value for e in EvidenceClass}
    # ADR-004's four provenance tiers must all be first-class, distinctly.
    assert {"real", "calibrated", "synthetic", "simulated"} <= values
    assert "missing" in values


def test_legend_is_complete_and_ordered():
    classes = [d.evidence for d in legend()]
    assert classes == [
        EvidenceClass.REAL, EvidenceClass.CALIBRATED, EvidenceClass.SIMULATED,
        EvidenceClass.SYNTHETIC, EvidenceClass.MISSING,
    ]
    # every class carries a non-empty label, caveat and colour for the UI
    for d in legend():
        assert d.label and d.caveat and d.color.startswith("#")


def test_real_supports_every_decision_use():
    for use in DecisionUse:
        assert supports(EvidenceClass.REAL, use) is True


def test_calibrated_gates_out_intervention_and_public_reporting():
    assert supports(EvidenceClass.CALIBRATED, DecisionUse.MONITORING) is True
    assert supports(EvidenceClass.CALIBRATED, DecisionUse.PRIORITIZATION) is True
    assert supports(EvidenceClass.CALIBRATED, DecisionUse.INTERVENTION) is False
    assert supports(
        EvidenceClass.CALIBRATED, DecisionUse.PUBLIC_REPORTING
    ) is False


def test_simulated_and_synthetic_and_missing_support_no_real_decision():
    for evidence in (
        EvidenceClass.SIMULATED, EvidenceClass.SYNTHETIC, EvidenceClass.MISSING
    ):
        for use in DecisionUse:
            assert supports(evidence, use) is False


def test_from_data_status_reconciles_temporal_tiers():
    assert from_data_status(DataStatus.REAL) is EvidenceClass.REAL
    assert from_data_status(DataStatus.CALIBRATED) is EvidenceClass.CALIBRATED
    assert from_data_status(DataStatus.SYNTHETIC) is EvidenceClass.SYNTHETIC
    assert from_data_status(DataStatus.MISSING) is EvidenceClass.MISSING


def test_from_data_type_maps_unambiguous_ends_only():
    assert from_data_type(DataType.OBSERVED) is EvidenceClass.REAL
    assert from_data_type(DataType.ESTIMATED) is EvidenceClass.CALIBRATED
    assert from_data_type(DataType.SIMULATED) is EvidenceClass.SIMULATED
    # Calculada inherits tier from inputs — must NOT be blurred into one class
    assert from_data_type(DataType.CALCULATED) is None


def test_gating_matrix_shape_and_content():
    matrix = gating_matrix()
    assert set(matrix) == set(EvidenceClass)
    assert all(set(row) == set(DecisionUse) for row in matrix.values())
    # REAL row all True; SYNTHETIC row all False
    assert all(matrix[EvidenceClass.REAL].values())
    assert not any(matrix[EvidenceClass.SYNTHETIC].values())


def test_descriptor_colours_are_distinct_per_class():
    colours = [descriptor(e).color for e in EvidenceClass]
    assert len(set(colours)) == len(colours)
