"""VIS-001 preregistered decision gate.

The gate is the part of the experiment most exposed to motivated reasoning, so
its behaviour is pinned exhaustively: each ADVANCE condition failing on its own,
each KILL condition firing on its own, the precedence between them, and the
refusal to issue any verdict when the evidence is incomplete.
"""

from __future__ import annotations

import pytest
from vis001.config import GATE, GATE_VERSION
from vis001.metrics import (
    ADVANCE,
    KILL_OR_REPOSITION,
    LOCAL_FINE_TUNE,
    CountingMetrics,
    DetectionMetrics,
    EvaluationResult,
    decide,
)

CLASSES = ("person", "bicycle", "car", "bus")


def _counting(wape: float | None, *, total_gt: int = 100) -> CountingMetrics:
    return CountingMetrics(
        frames=80,
        total_ground_truth=total_gt,
        total_predicted=total_gt,
        mae=0.5,
        bias=0.0,
        wape=wape,
    )


def _detection(f1_value: float) -> DetectionMetrics:
    return DetectionMetrics(
        true_positives=10,
        false_positives=1,
        false_negatives=1,
        precision=f1_value,
        recall=f1_value,
        f1=f1_value,
    )


def _result(
    *,
    class_f1: dict[str, float],
    overall_wape: float | None,
    camera_wapes: dict[str, float | None],
) -> EvaluationResult:
    per_class = {name: _detection(value) for name, value in class_f1.items()}
    return EvaluationResult(
        images_evaluated=80,
        cameras_evaluated=len(camera_wapes),
        ground_truth_boxes=100,
        predicted_boxes=100,
        per_class_detection=per_class,
        per_class_counting={name: _counting(0.1) for name in class_f1},
        per_camera_counting={
            camera: _counting(value) for camera, value in camera_wapes.items()
        },
        overall_detection=_detection(0.9),
        overall_counting=_counting(overall_wape),
        macro_f1=(sum(class_f1.values()) / len(class_f1)) if class_f1 else None,
    )


def _decide(result: EvaluationResult):
    return decide(result, thresholds=GATE, gate_version=GATE_VERSION)


# --------------------------------------------------------------------------
# ADVANCE
# --------------------------------------------------------------------------


def test_advance_when_every_condition_holds():
    result = _result(
        class_f1={name: 0.85 for name in CLASSES},
        overall_wape=0.15,
        camera_wapes={f"cam{i}": 0.20 for i in range(8)},
    )
    verdict = _decide(result)
    assert verdict.verdict == ADVANCE
    assert verdict.failed_conditions == ()
    assert verdict.gate_version == GATE_VERSION


def test_advance_at_the_exact_boundaries():
    """0.80 / 0.20 / 0.65 / 0.35 are inclusive on the passing side."""
    result = _result(
        class_f1={"person": 0.65, "bicycle": 0.95, "car": 0.80, "bus": 0.80},
        overall_wape=0.20,
        camera_wapes={"camA": 0.35, "camB": 0.10},
    )
    assert _decide(result).macro_f1 == pytest.approx(0.80)
    assert _decide(result).verdict == ADVANCE


# --------------------------------------------------------------------------
# LOCAL_FINE_TUNE — each ADVANCE condition failing on its own
# --------------------------------------------------------------------------


def test_local_fine_tune_when_macro_f1_is_in_the_middle_band():
    result = _result(
        class_f1={name: 0.70 for name in CLASSES},
        overall_wape=0.15,
        camera_wapes={"camA": 0.20},
    )
    verdict = _decide(result)
    assert verdict.verdict == LOCAL_FINE_TUNE
    assert any("A1" in condition for condition in verdict.failed_conditions)


def test_local_fine_tune_when_only_wape_misses():
    result = _result(
        class_f1={name: 0.85 for name in CLASSES},
        overall_wape=0.30,
        camera_wapes={"camA": 0.30},
    )
    verdict = _decide(result)
    assert verdict.verdict == LOCAL_FINE_TUNE
    assert any("A2" in condition for condition in verdict.failed_conditions)


def test_local_fine_tune_when_a_single_class_carries_the_error():
    result = _result(
        class_f1={"person": 0.90, "bicycle": 0.60, "car": 0.92, "bus": 0.90},
        overall_wape=0.15,
        camera_wapes={"camA": 0.20},
    )
    verdict = _decide(result)
    assert verdict.verdict == LOCAL_FINE_TUNE
    assert any("bicycle" in condition for condition in verdict.failed_conditions)


def test_local_fine_tune_when_a_single_camera_carries_the_error():
    result = _result(
        class_f1={name: 0.85 for name in CLASSES},
        overall_wape=0.15,
        camera_wapes={"camA": 0.10, "camB": 0.40},
    )
    verdict = _decide(result)
    assert verdict.verdict == LOCAL_FINE_TUNE
    assert any("camB" in condition for condition in verdict.failed_conditions)


# --------------------------------------------------------------------------
# KILL_OR_REPOSITION — each condition on its own
# --------------------------------------------------------------------------


def test_kill_on_low_macro_f1():
    result = _result(
        class_f1={name: 0.60 for name in CLASSES},
        overall_wape=0.15,
        camera_wapes={"camA": 0.20},
    )
    verdict = _decide(result)
    assert verdict.verdict == KILL_OR_REPOSITION
    assert any("C1" in condition for condition in verdict.failed_conditions)


def test_kill_on_high_counting_wape():
    result = _result(
        class_f1={name: 0.90 for name in CLASSES},
        overall_wape=0.40,
        camera_wapes={"camA": 0.40},
    )
    verdict = _decide(result)
    assert verdict.verdict == KILL_OR_REPOSITION
    assert any("C2" in condition for condition in verdict.failed_conditions)


def test_kill_on_two_classes_below_half():
    """One weak class is fine-tunable; two is a structural failure."""
    result = _result(
        class_f1={"person": 0.95, "bicycle": 0.40, "car": 0.95, "bus": 0.45},
        overall_wape=0.15,
        camera_wapes={"camA": 0.20},
    )
    verdict = _decide(result)
    assert verdict.verdict == KILL_OR_REPOSITION
    assert any("C3" in condition for condition in verdict.failed_conditions)


def test_one_class_below_half_alone_does_not_kill():
    result = _result(
        class_f1={"person": 0.95, "bicycle": 0.40, "car": 0.95, "bus": 0.95},
        overall_wape=0.15,
        camera_wapes={"camA": 0.20},
    )
    assert _decide(result).verdict == LOCAL_FINE_TUNE


def test_kill_on_camera_wape_spread():
    """C4: aggregate performance is misleading when cameras diverge this far."""
    result = _result(
        class_f1={name: 0.90 for name in CLASSES},
        overall_wape=0.30,
        camera_wapes={"camA": 0.02, "camB": 0.60},
    )
    verdict = _decide(result)
    assert verdict.verdict == KILL_OR_REPOSITION
    assert any("C4" in condition for condition in verdict.failed_conditions)


def test_kill_takes_precedence_over_advance_conditions():
    """Two dead classes cannot be rescued by a strong aggregate."""
    result = _result(
        class_f1={"person": 0.99, "bicycle": 0.45, "car": 0.99, "bus": 0.45},
        overall_wape=0.05,
        camera_wapes={"camA": 0.05},
    )
    assert _decide(result).verdict == KILL_OR_REPOSITION


# --------------------------------------------------------------------------
# No verdict
# --------------------------------------------------------------------------


def test_no_verdict_when_ground_truth_is_absent():
    result = _result(
        class_f1={},
        overall_wape=None,
        camera_wapes={},
    )
    verdict = _decide(result)
    assert verdict.verdict is None
    assert verdict.blocking_reasons
    assert verdict.macro_f1 is None
    assert verdict.count_wape is None


def test_no_verdict_when_the_caller_reports_a_blocker():
    """An incomplete evaluation is never converted into a passing result."""
    result = _result(
        class_f1={name: 0.99 for name in CLASSES},
        overall_wape=0.01,
        camera_wapes={"camA": 0.01},
    )
    verdict = decide(
        result,
        thresholds=GATE,
        gate_version=GATE_VERSION,
        blocking_reasons=["only 31/80 evaluation images are annotated"],
    )
    assert verdict.verdict is None
    assert "only 31/80 evaluation images are annotated" in verdict.blocking_reasons


def test_verdict_serialises_without_fabricating_metrics():
    verdict = _decide(_result(class_f1={}, overall_wape=None, camera_wapes={}))
    payload = verdict.as_dict()
    assert payload["experiment_id"] == "VIS-001"
    assert payload["verdict"] is None
    assert payload["macro_f1"] is None
    assert payload["count_wape"] is None


# --------------------------------------------------------------------------
# Undefined slices
# --------------------------------------------------------------------------


def test_undefined_camera_wape_is_skipped_only_when_no_camera_set_is_required():
    """Arithmetic-level behaviour, with no frozen camera set supplied.

    An undefined WAPE contributes nothing to a max or a spread, so it is
    skipped here. That is *not* the formal gate: amendment A2 requires every
    frozen benchmark camera to have a defined WAPE, and
    tests/unit/test_vis001_a2_gates.py pins that a required camera with no
    ground truth forces NO VERDICT — INSUFFICIENT CAMERA COVERAGE instead of
    disappearing from the per-camera rule.
    """
    result = _result(
        class_f1={name: 0.85 for name in CLASSES},
        overall_wape=0.15,
        camera_wapes={"camA": 0.10, "camEmpty": None},
    )
    assert _decide(result).verdict == ADVANCE


def test_single_camera_cannot_trigger_the_spread_rule():
    result = _result(
        class_f1={name: 0.90 for name in CLASSES},
        overall_wape=0.15,
        camera_wapes={"camA": 0.10},
    )
    assert _decide(result).verdict == ADVANCE
