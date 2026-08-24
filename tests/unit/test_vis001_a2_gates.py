"""VIS-001 amendment A2: statistical correctness of the formal gate.

Three loopholes, all in the same family — a *measured* failure being mistaken
for *absent evidence*, or an absent subgroup quietly leaving a preregistered
rule:

1. ``GT > 0, predictions = 0`` scored ``F1 = None`` and left the gate. That is a
   total detection failure, not missing data: a model must never be protected
   from a KILL by predicting nothing.
2. Class coverage was defined as ``F1 is None``, which collapsed the case above
   into "no evidence". It is now ground-truth support (``TP + FN > 0``).
3. A frozen benchmark camera with an undefined WAPE silently vanished from the
   preregistered "every camera subgroup WAPE ≤ 0.35" rule, weakening it to
   "every camera that happened to contain objects".

No numeric threshold changed. Every test here asserts behaviour reachable
through the thresholds exactly as first registered.
"""

from __future__ import annotations

import pytest
from vis001.config import GATE, GATE_VERSION, TARGET_CLASSES
from vis001.metrics import (
    INSUFFICIENT_CAMERA_COVERAGE,
    INSUFFICIENT_CLASS_COVERAGE,
    KILL_OR_REPOSITION,
    CountingMetrics,
    DetectionMetrics,
    EvaluationResult,
    Prediction,
    Truth,
    cameras_without_defined_wape,
    classes_without_ground_truth,
    decide,
    evaluate,
    f1_from_counts,
)

EIGHT = tuple(f"cam{index:02d}" for index in range(8))


def _counting(wape: float | None) -> CountingMetrics:
    total = 0 if wape is None else 100
    return CountingMetrics(10, total, total, 0.5, 0.0, wape)


def _result(
    per_class: dict[str, DetectionMetrics],
    *,
    overall_wape: float = 0.10,
    camera_wapes: dict[str, float | None] | None = None,
) -> EvaluationResult:
    cameras = camera_wapes if camera_wapes is not None else {c: 0.10 for c in EIGHT}
    defined = [m.f1 for m in per_class.values() if m.f1 is not None]
    unsupported = classes_without_ground_truth(per_class, list(TARGET_CLASSES))
    return EvaluationResult(
        images_evaluated=80,
        cameras_evaluated=len(cameras),
        ground_truth_boxes=sum(m.ground_truth_support for m in per_class.values()),
        predicted_boxes=100,
        per_class_detection=per_class,
        per_class_counting={name: _counting(0.10) for name in per_class},
        per_camera_counting={
            name: _counting(value) for name, value in cameras.items()
        },
        overall_detection=DetectionMetrics.from_counts(90, 5, 5),
        overall_counting=_counting(overall_wape),
        macro_f1=(
            None
            if unsupported or len(defined) != len(TARGET_CLASSES)
            else sum(defined) / len(defined)
        ),
    )


def _decide(result: EvaluationResult, *, cameras=EIGHT):
    return decide(
        result,
        thresholds=GATE,
        gate_version=GATE_VERSION,
        required_classes=TARGET_CLASSES,
        required_cameras=cameras,
    )


# --------------------------------------------------------------------------
# A2.1 — a total miss is measured, not hidden
# --------------------------------------------------------------------------


def test_zero_predictions_against_positive_ground_truth_scores_f1_zero():
    """The headline bug: GT bus = 10, predicted bus = 0."""
    metrics = DetectionMetrics.from_counts(0, 0, 10)
    assert metrics.true_positives == 0
    assert metrics.false_positives == 0
    assert metrics.false_negatives == 10
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0


def test_precision_may_stay_undefined_while_f1_is_measured():
    """Precision is genuinely undefined with no predictions; F1 is not."""
    metrics = DetectionMetrics.from_counts(0, 0, 10)
    assert metrics.precision is None
    assert metrics.f1 == 0.0


def test_total_miss_is_not_insufficient_class_coverage():
    metrics = {name: DetectionMetrics.from_counts(40, 2, 2) for name in TARGET_CLASSES}
    metrics["bus"] = DetectionMetrics.from_counts(0, 0, 10)
    assert classes_without_ground_truth(metrics, list(TARGET_CLASSES)) == ()
    verdict = _decide(_result(metrics))
    assert not any(
        INSUFFICIENT_CLASS_COVERAGE in reason for reason in verdict.blocking_reasons
    )
    assert verdict.verdict is not None


@pytest.mark.parametrize(
    "tp,fp,fn,expected",
    [
        (0, 0, 10, 0.0),   # total miss — measured failure
        (0, 5, 0, 0.0),    # only false positives
        (0, 0, 0, None),   # nothing observed at all
        (3, 1, 1, 0.75),   # ordinary case
        (10, 0, 0, 1.0),   # perfect
    ],
)
def test_f1_from_counts(tp, fp, fn, expected):
    assert f1_from_counts(tp, fp, fn) == expected


def test_count_form_agrees_with_the_harmonic_mean_where_both_are_defined():
    """2TP/(2TP+FP+FN) expands to 2pr/(p+r); the fix changes no ordinary case."""
    from vis001.metrics import f1 as harmonic
    from vis001.metrics import precision, recall

    for tp, fp, fn in [(3, 1, 1), (10, 5, 2), (1, 9, 9), (7, 0, 3)]:
        p, r = precision(tp, fp), recall(tp, fn)
        assert f1_from_counts(tp, fp, fn) == pytest.approx(harmonic(p, r))


def test_two_total_misses_can_still_reach_kill():
    """A model that predicts nothing for two classes must be killable.

    Reached through the frozen thresholds unchanged: two classes at F1 0.00 is
    below the preregistered ``kill_class_f1_below`` of 0.50, and two such
    classes meet ``kill_min_failing_classes``.
    """
    metrics = {name: DetectionMetrics.from_counts(40, 2, 2) for name in TARGET_CLASSES}
    metrics["bus"] = DetectionMetrics.from_counts(0, 0, 12)
    metrics["bicycle"] = DetectionMetrics.from_counts(0, 0, 8)
    verdict = _decide(_result(metrics))
    assert verdict.verdict == KILL_OR_REPOSITION
    assert any("C3" in condition for condition in verdict.failed_conditions)
    assert any("bus" in condition for condition in verdict.failed_conditions)


def test_macro_f1_includes_a_measured_zero():
    """The zero must drag the macro down, not vanish from it."""
    metrics = {name: DetectionMetrics.from_counts(40, 0, 0) for name in TARGET_CLASSES}
    metrics["bus"] = DetectionMetrics.from_counts(0, 0, 10)
    result = _result(metrics)
    assert result.macro_f1 == pytest.approx(0.75)  # (1 + 1 + 1 + 0) / 4


# --------------------------------------------------------------------------
# A2.2 — class coverage is ground-truth support
# --------------------------------------------------------------------------


def test_case_a_ground_truth_without_predictions_is_evaluable():
    metrics = {name: DetectionMetrics.from_counts(40, 2, 2) for name in TARGET_CLASSES}
    metrics["bus"] = DetectionMetrics.from_counts(0, 0, 10)
    assert classes_without_ground_truth(metrics, list(TARGET_CLASSES)) == ()


def test_case_b_no_ground_truth_and_no_predictions_is_not_evaluable():
    metrics = {name: DetectionMetrics.from_counts(40, 2, 2) for name in TARGET_CLASSES}
    metrics["bus"] = DetectionMetrics.from_counts(0, 0, 0)
    assert classes_without_ground_truth(metrics, list(TARGET_CLASSES)) == ("bus",)
    verdict = _decide(_result(metrics))
    assert verdict.verdict is None
    assert any(
        INSUFFICIENT_CLASS_COVERAGE in reason for reason in verdict.blocking_reasons
    )


def test_case_c_false_positives_without_ground_truth_is_not_evaluable():
    """FPs are diagnostic; with no human positive there is nothing to assess."""
    metrics = {name: DetectionMetrics.from_counts(40, 2, 2) for name in TARGET_CLASSES}
    metrics["bus"] = DetectionMetrics.from_counts(0, 7, 0)
    assert metrics["bus"].f1 == 0.0            # defined …
    assert metrics["bus"].ground_truth_support == 0  # … but unsupported
    assert classes_without_ground_truth(metrics, list(TARGET_CLASSES)) == ("bus",)
    verdict = _decide(_result(metrics))
    assert verdict.verdict is None
    assert any(
        INSUFFICIENT_CLASS_COVERAGE in reason for reason in verdict.blocking_reasons
    )


def test_class_coverage_is_not_defined_by_f1_being_none():
    """Case A has F1 defined and is covered; Case C has F1 defined and is not.

    So ``F1 is None`` cannot be the coverage test in either direction.
    """
    case_a = DetectionMetrics.from_counts(0, 0, 10)
    case_c = DetectionMetrics.from_counts(0, 7, 0)
    assert case_a.f1 == 0.0 and case_c.f1 == 0.0
    assert case_a.ground_truth_support > 0
    assert case_c.ground_truth_support == 0


def test_a_missing_class_entirely_is_uncovered():
    metrics = {
        name: DetectionMetrics.from_counts(40, 2, 2)
        for name in TARGET_CLASSES
        if name != "bus"
    }
    assert classes_without_ground_truth(metrics, list(TARGET_CLASSES)) == ("bus",)


def test_evaluate_gives_a_measured_zero_for_an_unpredicted_class():
    """End to end: ten annotated buses, no bus predictions."""
    truths = [Truth(f"img{i}", "bus", (0, 0, 10, 10)) for i in range(10)]
    truths += [Truth(f"img{i}", name, (20, 20, 30, 30)) for i in range(10)
               for name in ("person", "bicycle", "car")]
    predictions = [
        Prediction(f"img{i}", name, (20, 20, 30, 30), 0.9)
        for i in range(10)
        for name in ("person", "bicycle", "car")
    ]
    result = evaluate(
        predictions,
        truths,
        image_ids=[f"img{i}" for i in range(10)],
        camera_of_image={f"img{i}": EIGHT[0] for i in range(10)},
        classes=TARGET_CLASSES,
        iou_threshold=0.5,
    )
    assert result.per_class_detection["bus"].f1 == 0.0
    assert result.per_class_detection["bus"].false_negatives == 10
    assert result.macro_f1 == pytest.approx(0.75)
    assert classes_without_ground_truth(
        result.per_class_detection, list(TARGET_CLASSES)
    ) == ()


# --------------------------------------------------------------------------
# A2.3 — no frozen camera may leave the per-camera rule
# --------------------------------------------------------------------------


def _good_classes() -> dict[str, DetectionMetrics]:
    return {name: DetectionMetrics.from_counts(40, 2, 2) for name in TARGET_CLASSES}


def test_frozen_camera_with_no_ground_truth_forces_no_verdict():
    wapes: dict[str, float | None] = {camera: 0.10 for camera in EIGHT}
    wapes[EIGHT[5]] = None
    verdict = _decide(_result(_good_classes(), camera_wapes=wapes))
    assert verdict.verdict is None
    assert any(
        INSUFFICIENT_CAMERA_COVERAGE in reason for reason in verdict.blocking_reasons
    )


def test_the_affected_camera_is_named():
    wapes: dict[str, float | None] = {camera: 0.10 for camera in EIGHT}
    wapes[EIGHT[5]] = None
    verdict = _decide(_result(_good_classes(), camera_wapes=wapes))
    assert any(EIGHT[5] in reason for reason in verdict.blocking_reasons)


def test_several_uncovered_cameras_are_all_named():
    wapes: dict[str, float | None] = {camera: 0.10 for camera in EIGHT}
    wapes[EIGHT[1]] = None
    wapes[EIGHT[6]] = None
    verdict = _decide(_result(_good_classes(), camera_wapes=wapes))
    reasons = " ".join(verdict.blocking_reasons)
    assert EIGHT[1] in reasons and EIGHT[6] in reasons


def test_a_frozen_camera_absent_from_the_results_is_uncovered():
    """Silence is not coverage: a missing camera is not a passing camera."""
    wapes: dict[str, float | None] = {camera: 0.10 for camera in EIGHT[:7]}
    verdict = _decide(_result(_good_classes(), camera_wapes=wapes))
    assert verdict.verdict is None
    assert any(EIGHT[7] in reason for reason in verdict.blocking_reasons)


def test_camera_coverage_blocks_even_an_otherwise_perfect_result():
    """The gate is not weakened by a strong aggregate elsewhere."""
    wapes: dict[str, float | None] = {camera: 0.01 for camera in EIGHT}
    wapes[EIGHT[3]] = None
    result = _result(_good_classes(), overall_wape=0.01, camera_wapes=wapes)
    assert _decide(result).verdict is None


def test_all_eight_cameras_covered_yields_a_verdict():
    verdict = _decide(_result(_good_classes()))
    assert verdict.verdict is not None
    assert not any(
        INSUFFICIENT_CAMERA_COVERAGE in reason for reason in verdict.blocking_reasons
    )


def test_cameras_without_defined_wape_helper():
    counting = {
        "camA": _counting(0.2),
        "camB": _counting(None),
    }
    assert cameras_without_defined_wape(counting, ["camA", "camB"]) == ("camB",)
    assert cameras_without_defined_wape(counting, ["camA"]) == ()
    assert cameras_without_defined_wape(counting, ["camZ"]) == ("camZ",)
