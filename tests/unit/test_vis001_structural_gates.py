"""VIS-001 structural gates: sample completeness, eval-set exactness, class coverage.

Regressions for the pre-data audit findings 4, 5 and 6. Each closes a way the
benchmark could report a headline number that looks right while the structure
underneath it is wrong — the failure mode that matters most here, because a
plausible-looking wrong result is worse than no result.
"""

from __future__ import annotations

import pytest
from vis001.config import (
    EVAL_IMAGES_PER_CAMERA,
    EVAL_SET_SIZE,
    GATE,
    GATE_VERSION,
    RANDOM_SEED,
    TARGET_CAMERAS,
    TARGET_CLASSES,
    TARGET_FRAMES,
    TARGET_FRAMES_PER_CAMERA,
)
from vis001.manifest import (
    FrameRecord,
    coverage,
    evaluation_set_integrity,
    select_evaluation_set,
)
from vis001.metrics import (
    INSUFFICIENT_CLASS_COVERAGE,
    CountingMetrics,
    DetectionMetrics,
    EvaluationResult,
    Prediction,
    Truth,
    decide,
    evaluate,
    macro_f1,
)

EIGHT = tuple(f"cam{index:02d}" for index in range(8))


def _frame(camera: str, index: int) -> FrameRecord:
    return FrameRecord(
        image_id=f"{camera}__f{index:03d}",
        camera_id=camera,
        camera_name="",
        source_url=f"https://informo.madrid.es/cameras/{camera}.jpg",
        retrieved_at_utc="2026-08-24T12:00:00+00:00",
        source_timestamp="",
        latitude="",
        longitude="",
        width="640",
        height="480",
        sha256=f"{abs(hash((camera, index))):064x}"[:64],
        local_relative_path=f"data/raw/{camera}/f{index}.jpg",
        licence_or_source_note="Ayuntamiento de Madrid open data",
    )


def _sample(cameras=EIGHT, per_camera=TARGET_FRAMES_PER_CAMERA) -> list[FrameRecord]:
    return [_frame(camera, i) for camera in cameras for i in range(per_camera)]


def _coverage(records, selected=EIGHT):
    return coverage(
        records,
        target_frames=TARGET_FRAMES,
        target_cameras=TARGET_CAMERAS,
        selected_cameras=selected,
        frames_per_camera=TARGET_FRAMES_PER_CAMERA,
    )


# --------------------------------------------------------------------------
# Finding 4 — completeness is structural, never a total
# --------------------------------------------------------------------------


def test_exact_structure_is_complete():
    assert _coverage(_sample()).is_complete


def test_correct_total_spread_unevenly_is_not_complete():
    """160 frames from 2 cameras is not the preregistered sample.

    This is the headline-count loophole: the total matches exactly, and the
    old check would have passed it.
    """
    records = _sample(cameras=EIGHT[:2], per_camera=80)
    state = _coverage(records)
    assert state.frames == TARGET_FRAMES
    assert not state.is_complete
    assert state.cameras_missing == EIGHT[2:]


def test_one_camera_short_by_a_single_frame_is_not_complete():
    records = _sample() + []
    records = [r for r in records if r.image_id != f"{EIGHT[3]}__f000"]
    state = _coverage(records)
    assert state.frames == TARGET_FRAMES - 1
    assert not state.is_complete
    assert EIGHT[3] in state.cameras_below_quota


def test_extra_frames_elsewhere_cannot_compensate_a_short_camera():
    """Over-sampling seven cameras must not paper over the eighth."""
    records = [r for r in _sample() if r.camera_id != EIGHT[3]]
    records += [_frame(EIGHT[0], 100 + i) for i in range(20)]
    state = _coverage(records)
    assert state.frames >= TARGET_FRAMES
    assert not state.is_complete


def test_frames_from_an_unselected_camera_break_completeness():
    records = _sample() + [_frame("cam99", 0)]
    state = _coverage(records)
    assert not state.is_complete
    assert state.cameras_unexpected == ("cam99",)


def test_duplicate_bytes_do_not_count_towards_the_quota():
    """Madrid republishes every ~5 min; identical bytes add no observation."""
    duplicated = []
    for camera in EIGHT:
        for index in range(TARGET_FRAMES_PER_CAMERA):
            frame = _frame(camera, index)
            duplicated.append(frame)
            if index == 0:
                # Same bytes, different image_id.
                duplicated.append(
                    FrameRecord(**{**frame.as_row(), "image_id": f"{camera}__dup"})
                )
    state = _coverage(duplicated)
    assert state.frames > TARGET_FRAMES
    assert all(
        count == TARGET_FRAMES_PER_CAMERA
        for count in state.frames_per_camera.values()
    )
    assert state.is_complete


def test_completeness_impossible_without_a_frozen_selection():
    state = coverage(
        _sample(),
        target_frames=TARGET_FRAMES,
        target_cameras=TARGET_CAMERAS,
        selected_cameras=(),
        frames_per_camera=TARGET_FRAMES_PER_CAMERA,
    )
    assert not state.is_complete
    assert any("have not been frozen" in reason for reason in state.shortfalls())


def test_wrong_number_of_frozen_cameras_is_not_complete():
    state = _coverage(_sample(cameras=EIGHT[:7]), selected=EIGHT[:7])
    assert not state.is_complete
    assert any("exactly 8 are required" in reason for reason in state.shortfalls())


# --------------------------------------------------------------------------
# Finding 5 — the evaluation set must be exactly 80 = 10 × 8
# --------------------------------------------------------------------------


def _integrity(image_ids, records, selected=EIGHT):
    return evaluation_set_integrity(
        image_ids,
        camera_of_image={r.image_id: r.camera_id for r in records},
        selected_cameras=selected,
        required_per_camera=EVAL_IMAGES_PER_CAMERA,
        required_cameras=TARGET_CAMERAS,
    )


def test_full_draw_is_exact():
    records = _sample()
    drawn = select_evaluation_set(
        records,
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=EIGHT,
    )
    assert len(drawn) == EVAL_SET_SIZE
    assert _integrity(drawn, records).is_exact


def test_draw_is_stratified_over_exactly_the_frozen_cameras():
    records = _sample()
    drawn = select_evaluation_set(
        records,
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=EIGHT,
    )
    integrity = _integrity(drawn, records)
    assert all(
        integrity.per_camera[camera] == EVAL_IMAGES_PER_CAMERA for camera in EIGHT
    )


def test_frames_from_unselected_cameras_never_enter_the_draw():
    records = _sample() + [_frame("cam99", i) for i in range(50)]
    drawn = select_evaluation_set(
        records,
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=EIGHT,
    )
    assert not any(image_id.startswith("cam99") for image_id in drawn)
    assert len(drawn) == EVAL_SET_SIZE


def test_short_camera_yields_an_inexact_set_and_is_not_backfilled():
    """79 images is not 80, and the missing one is not taken from elsewhere."""
    records = [r for r in _sample() if r.camera_id != EIGHT[2]]
    records += [_frame(EIGHT[2], i) for i in range(9)]
    drawn = select_evaluation_set(
        records,
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=EIGHT,
    )
    integrity = _integrity(drawn, records)
    assert len(drawn) == EVAL_SET_SIZE - 1
    assert not integrity.is_exact
    assert integrity.per_camera[EIGHT[2]] == 9
    assert any("exactly 80" in reason for reason in integrity.shortfalls())


def test_too_many_images_is_also_inexact():
    records = _sample()
    drawn = select_evaluation_set(
        records,
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=EIGHT,
    )
    extra = drawn + [f"{EIGHT[0]}__f019"]
    assert not _integrity(extra, records).is_exact


def test_seven_frozen_cameras_can_never_be_exact():
    records = _sample(cameras=EIGHT[:7])
    drawn = select_evaluation_set(
        records,
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=EIGHT[:7],
    )
    integrity = _integrity(drawn, records, selected=EIGHT[:7])
    assert not integrity.is_exact
    assert any("exactly 8" in reason for reason in integrity.shortfalls())


def test_draw_remains_reproducible():
    records = _sample()
    kwargs = dict(
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=EIGHT,
    )
    assert select_evaluation_set(records, **kwargs) == select_evaluation_set(
        records, **kwargs
    )


# --------------------------------------------------------------------------
# Finding 6 — all four classes must be evaluable
# --------------------------------------------------------------------------


def _detection(f1_value: float) -> DetectionMetrics:
    return DetectionMetrics(10, 1, 1, f1_value, f1_value, f1_value)


def _undefined() -> DetectionMetrics:
    return DetectionMetrics(0, 0, 0, None, None, None)


def _result(class_metrics: dict[str, DetectionMetrics], wape: float = 0.10):
    counting = CountingMetrics(80, 100, 100, 0.5, 0.0, wape)
    return EvaluationResult(
        images_evaluated=80,
        cameras_evaluated=8,
        ground_truth_boxes=100,
        predicted_boxes=100,
        per_class_detection=class_metrics,
        per_class_counting={name: counting for name in class_metrics},
        per_camera_counting={f"cam{i}": counting for i in range(8)},
        overall_detection=_detection(0.9),
        overall_counting=counting,
        macro_f1=macro_f1(
            {name: m.f1 for name, m in class_metrics.items()},
            required=list(TARGET_CLASSES),
        ),
    )


def _decide(result):
    return decide(
        result,
        thresholds=GATE,
        gate_version=GATE_VERSION,
        required_classes=TARGET_CLASSES,
    )


def test_all_four_classes_evaluable_yields_a_verdict():
    result = _result({name: _detection(0.90) for name in TARGET_CLASSES})
    assert _decide(result).verdict == "ADVANCE"


def test_an_undefined_class_forces_no_verdict():
    """The loophole: a never-seen bus must not vanish from the macro average."""
    metrics = {name: _detection(0.95) for name in TARGET_CLASSES}
    metrics["bus"] = _undefined()
    verdict = _decide(_result(metrics))
    assert verdict.verdict is None
    assert any(
        INSUFFICIENT_CLASS_COVERAGE in reason for reason in verdict.blocking_reasons
    )
    assert any("bus" in reason for reason in verdict.blocking_reasons)


def test_macro_f1_is_none_when_a_required_class_is_undefined():
    metrics = {name: _detection(0.95) for name in TARGET_CLASSES}
    metrics["bicycle"] = _undefined()
    assert _result(metrics).macro_f1 is None


def test_macro_f1_does_not_average_only_the_classes_that_worked():
    """Averaging 3 of 4 would silently redefine the metric mid-experiment."""
    metrics = {name: _detection(0.95) for name in TARGET_CLASSES}
    metrics["bus"] = _undefined()
    assert macro_f1(
        {name: m.f1 for name, m in metrics.items()}, required=list(TARGET_CLASSES)
    ) is None
    # Without the required contract the old permissive behaviour still exists,
    # but it is only for exploratory slices — never the gate.
    assert macro_f1(
        {name: m.f1 for name, m in metrics.items()}
    ) == pytest.approx(0.95)


def test_two_undefined_classes_are_both_named():
    metrics = {name: _detection(0.95) for name in TARGET_CLASSES}
    metrics["bus"] = _undefined()
    metrics["bicycle"] = _undefined()
    verdict = _decide(_result(metrics))
    assert verdict.verdict is None
    reason = " ".join(verdict.blocking_reasons)
    assert "bus" in reason and "bicycle" in reason


def test_class_coverage_blocks_even_a_would_be_kill():
    """Insufficient coverage is not a KILL — it is an absence of measurement."""
    metrics = {name: _detection(0.10) for name in TARGET_CLASSES}
    metrics["bus"] = _undefined()
    verdict = _decide(_result(metrics, wape=0.90))
    assert verdict.verdict is None


def test_evaluate_marks_macro_none_when_a_class_never_appears():
    predictions = [Prediction("img1", "car", (0, 0, 10, 10), 0.9)]
    truths = [Truth("img1", "car", (0, 0, 10, 10))]
    result = evaluate(
        predictions,
        truths,
        image_ids=["img1"],
        camera_of_image={"img1": "cam00"},
        classes=TARGET_CLASSES,
        iou_threshold=0.5,
    )
    assert result.per_class_detection["car"].f1 == 1.0
    assert result.per_class_detection["bus"].f1 is None
    assert result.macro_f1 is None
    assert _decide(result).verdict is None
