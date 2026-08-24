"""VIS-001 detection and counting metrics.

These run in the repository's ordinary CI: the metric layer is pure standard
library, so no PyTorch, no model weights and no network are involved. Fixtures
are tiny hand-computed arrays — the point is to pin the arithmetic that decides
the verdict, not to exercise a detector.
"""

from __future__ import annotations

from vis001.metrics import (
    CountingMetrics,
    DetectionMetrics,
    Prediction,
    Truth,
    counting_metrics,
    evaluate,
    f1,
    iou,
    macro_f1,
    match_one_to_one,
    precision,
    recall,
)

# --------------------------------------------------------------------------
# IoU
# --------------------------------------------------------------------------


def test_iou_identical_boxes_is_one():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0


def test_iou_disjoint_boxes_is_zero():
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_iou_touching_edges_is_zero():
    # Sharing an edge is zero overlap area, not a match.
    assert iou((0, 0, 10, 10), (10, 0, 20, 10)) == 0.0


def test_iou_half_overlap():
    # Two 10x10 boxes offset by 5 in x: intersection 5*10=50, union 200-50=150.
    assert iou((0, 0, 10, 10), (5, 0, 15, 10)) == 50 / 150


def test_iou_degenerate_box_never_matches():
    # A zero-area box would otherwise divide by zero or match everything.
    assert iou((5, 5, 5, 5), (0, 0, 10, 10)) == 0.0
    assert iou((0, 0, 10, 0), (0, 0, 10, 10)) == 0.0


def test_iou_is_symmetric():
    a, b = (0, 0, 10, 10), (3, 4, 12, 14)
    assert iou(a, b) == iou(b, a)


# --------------------------------------------------------------------------
# One-to-one matching
# --------------------------------------------------------------------------


def _pred(box, confidence=0.9):
    return Prediction(image_id="i", class_name="car", box=box, confidence=confidence)


def _truth(box):
    return Truth(image_id="i", class_name="car", box=box)


def test_match_perfect_pairing():
    result = match_one_to_one(
        [_pred((0, 0, 10, 10)), _pred((20, 20, 30, 30))],
        [_truth((0, 0, 10, 10)), _truth((20, 20, 30, 30))],
        iou_threshold=0.5,
    )
    assert (result.true_positives, result.false_positives, result.false_negatives) == (
        2,
        0,
        0,
    )


def test_one_prediction_cannot_satisfy_two_truths():
    """The core one-to-one guarantee.

    A single box overlapping two adjacent ground-truth objects must claim at
    most one of them; the other stays a false negative.
    """
    result = match_one_to_one(
        [_pred((0, 0, 10, 10))],
        [_truth((0, 0, 10, 10)), _truth((1, 1, 11, 11))],
        iou_threshold=0.5,
    )
    assert result.true_positives == 1
    assert result.false_negatives == 1
    assert result.false_positives == 0


def test_duplicate_predictions_become_false_positives():
    """Double-counting one object inflates the count and must be penalised."""
    result = match_one_to_one(
        [_pred((0, 0, 10, 10), 0.95), _pred((0, 0, 10, 10), 0.60)],
        [_truth((0, 0, 10, 10))],
        iou_threshold=0.5,
    )
    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 0


def test_higher_confidence_prediction_claims_the_box_first():
    high = _pred((0, 0, 10, 10), 0.99)
    low = _pred((1, 1, 11, 11), 0.40)
    result = match_one_to_one([low, high], [_truth((0, 0, 10, 10))], iou_threshold=0.5)
    # The claimed pair must be the high-confidence prediction (index 1 of input).
    assert result.pairs[0][0] == 1


def test_below_threshold_overlap_is_a_false_positive_and_a_false_negative():
    result = match_one_to_one(
        [_pred((0, 0, 10, 10))],
        [_truth((8, 8, 18, 18))],  # IoU well under 0.50
        iou_threshold=0.5,
    )
    assert (result.true_positives, result.false_positives, result.false_negatives) == (
        0,
        1,
        1,
    )


def test_no_predictions_yields_all_false_negatives():
    result = match_one_to_one([], [_truth((0, 0, 10, 10))], iou_threshold=0.5)
    assert (result.true_positives, result.false_positives, result.false_negatives) == (
        0,
        0,
        1,
    )


def test_no_ground_truth_yields_all_false_positives():
    result = match_one_to_one([_pred((0, 0, 10, 10))], [], iou_threshold=0.5)
    assert (result.true_positives, result.false_positives, result.false_negatives) == (
        0,
        1,
        0,
    )


def test_empty_on_both_sides_is_all_zeros():
    result = match_one_to_one([], [], iou_threshold=0.5)
    assert (result.true_positives, result.false_positives, result.false_negatives) == (
        0,
        0,
        0,
    )


def test_matching_is_deterministic_under_confidence_ties():
    predictions = [_pred((0, 0, 10, 10), 0.5), _pred((0, 0, 10, 10), 0.5)]
    first = match_one_to_one(predictions, [_truth((0, 0, 10, 10))], iou_threshold=0.5)
    second = match_one_to_one(predictions, [_truth((0, 0, 10, 10))], iou_threshold=0.5)
    assert first.pairs == second.pairs


# --------------------------------------------------------------------------
# Precision / recall / F1
# --------------------------------------------------------------------------


def test_precision_recall_f1_basic():
    assert precision(3, 1) == 0.75
    assert recall(3, 1) == 0.75
    assert f1(0.75, 0.75) == 0.75


def test_f1_is_the_harmonic_mean():
    assert f1(1.0, 0.5) == 2 * 1.0 * 0.5 / 1.5


def test_precision_undefined_when_nothing_was_predicted():
    """None, not 0.0 — an unmeasured model is not an imprecise model."""
    assert precision(0, 0) is None


def test_recall_undefined_when_there_is_no_ground_truth():
    assert recall(0, 0) is None


def test_f1_is_none_when_either_component_is_undefined():
    assert f1(None, 0.5) is None
    assert f1(0.5, None) is None


def test_f1_is_zero_when_both_components_are_zero():
    assert f1(0.0, 0.0) == 0.0


def test_detection_metrics_from_counts():
    metrics = DetectionMetrics.from_counts(3, 1, 1)
    assert metrics.precision == 0.75
    assert metrics.recall == 0.75
    assert metrics.f1 == 0.75


def test_macro_f1_excludes_undefined_classes():
    """An undefined class is dropped, not counted as zero."""
    assert macro_f1({"a": 1.0, "b": 0.5, "c": None}) == 0.75


def test_macro_f1_is_none_when_every_class_is_undefined():
    assert macro_f1({"a": None, "b": None}) is None


# --------------------------------------------------------------------------
# Counting
# --------------------------------------------------------------------------


def test_counting_metrics_perfect_counts():
    metrics = counting_metrics([(3, 3), (0, 0), (5, 5)])
    assert metrics.mae == 0.0
    assert metrics.bias == 0.0
    assert metrics.wape == 0.0
    assert metrics.total_ground_truth == 8
    assert metrics.total_predicted == 8


def test_counting_wape_formula():
    # |4-3| + |0-2| + |6-5| = 4 over a ground-truth total of 3+0+5 = 8.
    metrics = counting_metrics([(3, 4), (0, 2), (5, 6)])
    assert metrics.wape == 4 / 8
    assert metrics.mae == 4 / 3
    assert metrics.bias == (1 + 2 + 1) / 3


def test_counting_bias_is_signed():
    """Under-counting must show as a negative bias, not vanish into MAE."""
    metrics = counting_metrics([(10, 6), (10, 8)])
    assert metrics.bias == -3.0
    assert metrics.mae == 3.0


def test_counting_wape_is_none_when_no_ground_truth_exists():
    """Undefined, not zero: zero would read as a perfect score."""
    metrics = counting_metrics([(0, 0), (0, 4)])
    assert metrics.wape is None
    assert metrics.total_ground_truth == 0
    # The absolute error is still measurable even though WAPE is not.
    assert metrics.mae == 2.0


def test_counting_metrics_on_no_frames():
    metrics = counting_metrics([])
    assert metrics == CountingMetrics(0, 0, 0, None, None, None)


# --------------------------------------------------------------------------
# End-to-end evaluation
# --------------------------------------------------------------------------


def test_evaluate_end_to_end_on_two_frames():
    predictions = [
        Prediction("img1", "car", (0, 0, 10, 10), 0.9),
        Prediction("img1", "person", (50, 50, 60, 70), 0.8),
        Prediction("img2", "car", (0, 0, 10, 10), 0.7),
        # Outside the frozen classes: must be ignored entirely.
        Prediction("img1", "truck", (0, 0, 10, 10), 0.99),
    ]
    truths = [
        Truth("img1", "car", (0, 0, 10, 10)),
        Truth("img1", "person", (50, 50, 60, 70)),
        Truth("img2", "car", (100, 100, 110, 110)),  # model looked in the wrong place
        Truth("img2", "bus", (0, 0, 40, 40)),  # missed entirely
    ]

    result = evaluate(
        predictions,
        truths,
        image_ids=["img1", "img2"],
        camera_of_image={"img1": "camA", "img2": "camB"},
        classes=("person", "bicycle", "car", "bus"),
        iou_threshold=0.5,
    )

    assert result.images_evaluated == 2
    assert result.cameras_evaluated == 2
    assert result.ground_truth_boxes == 4
    assert result.predicted_boxes == 3  # the truck was filtered out

    assert result.per_class_detection["person"].f1 == 1.0
    assert result.per_class_detection["car"].true_positives == 1
    assert result.per_class_detection["car"].false_positives == 1
    assert result.per_class_detection["car"].false_negatives == 1
    assert result.per_class_detection["bus"].false_negatives == 1
    # bicycle appears nowhere: undefined, and excluded from the macro mean.
    assert result.per_class_detection["bicycle"].f1 is None

    # camB: 2 ground-truth objects, 1 prediction -> WAPE 1/2.
    assert result.per_camera_counting["camB"].wape == 0.5
    assert result.per_camera_counting["camA"].wape == 0.0


def test_evaluate_ignores_images_outside_the_frozen_set():
    """The evaluation set is frozen; stray data must not leak into the gate."""
    result = evaluate(
        [Prediction("stray", "car", (0, 0, 10, 10), 0.9)],
        [Truth("stray", "car", (0, 0, 10, 10))],
        image_ids=["img1"],
        camera_of_image={"img1": "camA"},
        classes=("person", "bicycle", "car", "bus"),
        iou_threshold=0.5,
    )
    assert result.ground_truth_boxes == 0
    assert result.predicted_boxes == 0


def test_evaluate_counts_empty_frames():
    """A frame with nothing in it is evidence about false positives."""
    result = evaluate(
        [Prediction("img1", "car", (0, 0, 10, 10), 0.9)],
        [],
        image_ids=["img1", "img2"],
        camera_of_image={"img1": "camA", "img2": "camA"},
        classes=("person", "bicycle", "car", "bus"),
        iou_threshold=0.5,
    )
    assert result.overall_counting.frames == 2
    assert result.overall_counting.total_ground_truth == 0
    assert result.overall_counting.wape is None
    assert result.overall_detection.false_positives == 1
