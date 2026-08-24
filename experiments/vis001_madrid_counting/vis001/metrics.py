"""Deterministic detection and counting metrics, plus the preregistered gate.

Pure standard library on purpose: this is the part of VIS-001 that decides the
verdict, so it must be runnable and testable in ordinary CI, with no PyTorch, no
model weights and no network.

Two families of metric are computed and kept separate throughout:

* **Detection** metrics (TP/FP/FN → precision/recall/F1) ask *did the model put
  a box in the right place?* They require one-to-one matching at IoU ≥ 0.50.
* **Counting** metrics (MAE, bias, WAPE) ask *did the model get the number
  right?* They compare per-frame cardinalities and are computed independently of
  matching — a frame can have a perfect count and zero correct boxes.

Both are reported because a Visual Evidence Layer would consume the *count*,
while the *detection* metrics are what tell you whether a good count was luck.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

Box = tuple[float, float, float, float]  # xyxy


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def iou(box_a: Box, box_b: Box) -> float:
    """Intersection-over-union of two ``(x1, y1, x2, y2)`` boxes.

    Returns ``0.0`` for disjoint boxes and for any box with non-positive area,
    so a degenerate input can never match anything.
    """
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    if area_a <= 0.0 or area_b <= 0.0:
        return 0.0

    inter_w = min(ax2, bx2) - max(ax1, bx1)
    inter_h = min(ay2, by2) - max(ay1, by1)
    if inter_w <= 0.0 or inter_h <= 0.0:
        return 0.0

    intersection = inter_w * inter_h
    union = area_a + area_b - intersection
    if union <= 0.0:
        return 0.0
    return intersection / union


# --------------------------------------------------------------------------
# One-to-one matching
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Prediction:
    image_id: str
    class_name: str
    box: Box
    confidence: float


@dataclass(frozen=True)
class Truth:
    image_id: str
    class_name: str
    box: Box


@dataclass(frozen=True)
class MatchResult:
    """Outcome of matching one ``(image, class)`` group."""

    true_positives: int
    false_positives: int
    false_negatives: int
    #: ``(prediction_index, truth_index, iou)`` for each accepted match.
    pairs: tuple[tuple[int, int, float], ...] = ()


def match_one_to_one(
    predictions: Sequence[Prediction],
    truths: Sequence[Truth],
    *,
    iou_threshold: float,
) -> MatchResult:
    """Greedy confidence-ordered one-to-one matching (Pascal VOC / COCO style).

    Algorithm, stated explicitly because the gate depends on it:

    1. Sort predictions by descending confidence. Ties break by the order the
       predictions were supplied, which keeps the result deterministic.
    2. Walk the sorted predictions. For each, compute the IoU against every
       ground-truth box **not yet claimed**, and take the highest.
    3. If that highest IoU is ``>= iou_threshold``, the pair is a true positive
       and the ground-truth box is removed from the available pool. Otherwise
       the prediction is a false positive.
    4. Any ground-truth box still unclaimed at the end is a false negative.

    Step 3 is what makes the matching one-to-one: a single prediction can never
    satisfy two ground-truth boxes, and two predictions can never both claim the
    same one. Duplicate detections of the same object are therefore counted as
    false positives, which is the honest behaviour for a counting benchmark —
    double-counting one pedestrian inflates the count and must be penalised.

    This is greedy, not globally optimal (a Hungarian assignment could in
    principle recover one extra match in a contrived overlap). Greedy is chosen
    because it is the standard used by COCO evaluation, so the numbers stay
    comparable with published detector results.
    """
    ordered = sorted(
        range(len(predictions)),
        key=lambda index: (-predictions[index].confidence, index),
    )
    claimed: set[int] = set()
    pairs: list[tuple[int, int, float]] = []

    for prediction_index in ordered:
        best_truth_index = -1
        best_iou = 0.0
        for truth_index, truth in enumerate(truths):
            if truth_index in claimed:
                continue
            candidate = iou(predictions[prediction_index].box, truth.box)
            if candidate > best_iou:
                best_iou = candidate
                best_truth_index = truth_index

        if best_truth_index >= 0 and best_iou >= iou_threshold:
            claimed.add(best_truth_index)
            pairs.append((prediction_index, best_truth_index, best_iou))

    true_positives = len(pairs)
    return MatchResult(
        true_positives=true_positives,
        false_positives=len(predictions) - true_positives,
        false_negatives=len(truths) - true_positives,
        pairs=tuple(pairs),
    )


# --------------------------------------------------------------------------
# Detection metrics
# --------------------------------------------------------------------------


def precision(true_positives: int, false_positives: int) -> float | None:
    """``TP / (TP + FP)``; ``None`` when the model predicted nothing at all.

    Undefined is reported as ``None`` rather than ``0.0``: a model that made no
    prediction has not been shown to be imprecise, it has simply not been
    measured. Collapsing that to zero would silently drag a macro average down.
    """
    denominator = true_positives + false_positives
    if denominator == 0:
        return None
    return true_positives / denominator


def recall(true_positives: int, false_negatives: int) -> float | None:
    """``TP / (TP + FN)``; ``None`` when there is no ground truth to recall."""
    denominator = true_positives + false_negatives
    if denominator == 0:
        return None
    return true_positives / denominator


def f1(precision_value: float | None, recall_value: float | None) -> float | None:
    """Harmonic mean of precision and recall; ``None`` if either is undefined.

    This is the *presentational* form. It is not what the gate uses, because it
    inherits precision's undefinedness: a model that predicted nothing has an
    undefined precision, which would drag F1 to ``None`` even when the misses
    are perfectly well measured. :func:`f1_from_counts` is the authoritative
    definition; the two agree exactly wherever both are defined, since
    ``2pr/(p+r)`` expands to ``2TP/(2TP+FP+FN)``.
    """
    if precision_value is None or recall_value is None:
        return None
    if precision_value + recall_value == 0.0:
        return 0.0
    return 2 * precision_value * recall_value / (precision_value + recall_value)


def f1_from_counts(
    true_positives: int, false_positives: int, false_negatives: int
) -> float | None:
    """``2TP / (2TP + FP + FN)``; ``None`` only when all three counts are zero.

    The authoritative F1 for VIS-001. Computing it from counts rather than from
    precision and recall fixes a real hole in the gate:

    * ``TP=0, FP=0, FN=10`` — the model predicted no bus and there were ten.
      Precision is undefined, so the harmonic-mean form returns ``None`` and the
      class silently leaves the gate. That is exactly backwards: this is a
      **measured total detection failure** and must score ``F1 = 0.0``, which is
      eligible for KILL. A model must never be protected from a negative verdict
      by predicting nothing.
    * ``TP=0, FP=0, FN=0`` — nothing annotated and nothing predicted. This is
      the only case with no class evidence at all, and the only one that stays
      ``None``.

    Note that ``None`` here means "no observations of any kind", which is *not*
    the same as the formal class-coverage test — see
    :func:`classes_without_ground_truth`, which requires a human-annotated
    positive (``TP + FN > 0``).
    """
    denominator = 2 * true_positives + false_positives + false_negatives
    if denominator == 0:
        return None
    return 2 * true_positives / denominator


@dataclass(frozen=True)
class DetectionMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    f1: float | None

    @property
    def ground_truth_support(self) -> int:
        """Human-annotated positives for this class: ``TP + FN``.

        The formal class-coverage quantity. Predictions contribute nothing to
        it, because a false positive is not evidence that the class was there.
        """
        return self.true_positives + self.false_negatives

    @classmethod
    def from_counts(cls, tp: int, fp: int, fn: int) -> "DetectionMetrics":
        """Build from raw counts.

        Precision and recall stay ``None`` where they are genuinely undefined,
        which is honest and useful for reading a diagnostic table. F1 is
        computed from the counts instead (:func:`f1_from_counts`), so a
        measured total miss scores ``0.0`` rather than disappearing.
        """
        return cls(
            tp, fp, fn, precision(tp, fp), recall(tp, fn), f1_from_counts(tp, fp, fn)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "tp": self.true_positives,
            "fp": self.false_positives,
            "fn": self.false_negatives,
            "ground_truth_support": self.ground_truth_support,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


# --------------------------------------------------------------------------
# Counting metrics
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CountingMetrics:
    """Cardinality error over a set of frames.

    ``wape`` is ``None`` when the frames contain no ground-truth objects at all:
    the denominator is zero and the quantity is genuinely undefined. It is never
    reported as ``0.0``, which would read as "perfect".
    """

    frames: int
    total_ground_truth: int
    total_predicted: int
    mae: float | None
    bias: float | None
    wape: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "frames": self.frames,
            "total_ground_truth": self.total_ground_truth,
            "total_predicted": self.total_predicted,
            "mae": self.mae,
            "mean_signed_error": self.bias,
            "wape": self.wape,
        }


def counting_metrics(pairs: Iterable[tuple[int, int]]) -> CountingMetrics:
    """Aggregate ``(ground_truth_count, predicted_count)`` pairs, one per frame.

    * ``MAE``   = mean over frames of ``|predicted - ground_truth|``
    * ``bias``  = mean over frames of ``predicted - ground_truth`` (signed:
      positive means the model over-counts)
    * ``WAPE``  = ``sum |predicted - ground_truth| / sum ground_truth``

    WAPE is used instead of MAPE because traffic-camera frames legitimately
    contain zero objects of a class, and MAPE divides by the per-frame truth.
    """
    materialised = list(pairs)
    if not materialised:
        return CountingMetrics(0, 0, 0, None, None, None)

    total_truth = sum(truth for truth, _ in materialised)
    total_predicted = sum(predicted for _, predicted in materialised)
    absolute_errors = [abs(predicted - truth) for truth, predicted in materialised]
    signed_errors = [predicted - truth for truth, predicted in materialised]

    return CountingMetrics(
        frames=len(materialised),
        total_ground_truth=total_truth,
        total_predicted=total_predicted,
        mae=sum(absolute_errors) / len(materialised),
        bias=sum(signed_errors) / len(materialised),
        wape=(sum(absolute_errors) / total_truth) if total_truth > 0 else None,
    )


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


def undefined_classes(
    per_class_f1: Mapping[str, float | None], required: Sequence[str]
) -> tuple[str, ...]:
    """Required classes whose F1 could not be computed at all.

    Kept for reporting a diagnostic table. It is **not** the class-coverage
    test — see :func:`classes_without_ground_truth`.
    """
    return tuple(name for name in required if per_class_f1.get(name) is None)


def classes_without_ground_truth(
    per_class_detection: Mapping[str, "DetectionMetrics"],
    required: Sequence[str],
) -> tuple[str, ...]:
    """Required classes with no human-annotated positive: ``TP + FN == 0``.

    This is the formal class-coverage test, and it is deliberately defined on
    **ground-truth support**, never on whether F1 happens to be ``None``:

    ===================  ===========  ==========================================
    Ground truth         Predictions  Outcome
    ===================  ===========  ==========================================
    ``> 0``              ``0``        Evaluable. ``F1 = 0``. A measured total
                                      miss, eligible for the normal gate.
    ``0``                ``0``        Not evaluable. Nothing was annotated, so
                                      nothing was asked of the model.
    ``0``                ``> 0``      Not evaluable. False positives are worth
                                      reporting diagnostically, but with no
                                      human positive there is nothing to assess
                                      detection against.
    ===================  ===========  ==========================================

    Using ``F1 is None`` instead would collapse row 1 into row 2 and let a model
    escape a KILL by predicting nothing at all.
    """
    return tuple(
        name
        for name in required
        if name not in per_class_detection
        or per_class_detection[name].ground_truth_support == 0
    )


def cameras_without_defined_wape(
    per_camera_counting: Mapping[str, "CountingMetrics"],
    required: Sequence[str],
) -> tuple[str, ...]:
    """Required cameras whose counting WAPE is undefined.

    A camera's WAPE is undefined when its evaluated frames hold zero
    ground-truth objects of the four target classes, so the denominator of
    ``sum|pred - gt| / sum gt`` is zero.

    The preregistered ADVANCE gate reads "every camera subgroup WAPE ≤ 0.35".
    A frozen benchmark camera cannot quietly drop out of that rule: dropping it
    would silently weaken a preregistered condition from "all eight" to "however
    many happened to have objects in them". The honest response is to preserve
    the metric and refuse the verdict.
    """
    return tuple(
        name
        for name in required
        if name not in per_camera_counting
        or per_camera_counting[name].wape is None
    )


def macro_f1(
    per_class_f1: Mapping[str, float | None],
    required: Sequence[str] | None = None,
) -> float | None:
    """Unweighted mean of the per-class F1 scores.

    When ``required`` is given, **every** named class must be defined or the
    macro score is ``None``. This is the honest behaviour for VIS-001: a
    benchmark whose evaluation set happened to contain no bus has not measured
    three-quarters of the question, it has failed to measure the question.
    Averaging the three classes it did see and reporting that as "macro F1"
    would quietly redefine the metric mid-experiment — a class that is hard to
    detect is exactly the class most likely to go undefined, so dropping it
    biases the score upward.

    With ``required`` omitted the mean is taken over whatever is defined, which
    is only appropriate for exploratory slices, never for the gate.
    """
    if required is not None:
        if undefined_classes(per_class_f1, required):
            return None
        values = [per_class_f1[name] for name in required]
        return sum(value for value in values if value is not None) / len(values)

    defined = [value for value in per_class_f1.values() if value is not None]
    if not defined:
        return None
    return sum(defined) / len(defined)


@dataclass
class EvaluationResult:
    """Everything the gate and the report need, and nothing derived twice."""

    images_evaluated: int
    cameras_evaluated: int
    ground_truth_boxes: int
    predicted_boxes: int
    per_class_detection: dict[str, DetectionMetrics] = field(default_factory=dict)
    per_class_counting: dict[str, CountingMetrics] = field(default_factory=dict)
    per_camera_counting: dict[str, CountingMetrics] = field(default_factory=dict)
    overall_detection: DetectionMetrics | None = None
    overall_counting: CountingMetrics | None = None
    macro_f1: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "images_evaluated": self.images_evaluated,
            "cameras_evaluated": self.cameras_evaluated,
            "ground_truth_boxes": self.ground_truth_boxes,
            "predicted_boxes": self.predicted_boxes,
            "macro_f1": self.macro_f1,
            "overall_detection": (
                self.overall_detection.as_dict() if self.overall_detection else None
            ),
            "overall_counting": (
                self.overall_counting.as_dict() if self.overall_counting else None
            ),
            "per_class_detection": {
                name: value.as_dict()
                for name, value in self.per_class_detection.items()
            },
            "per_class_counting": {
                name: value.as_dict() for name, value in self.per_class_counting.items()
            },
            "per_camera_counting": {
                name: value.as_dict()
                for name, value in self.per_camera_counting.items()
            },
        }


def evaluate(
    predictions: Sequence[Prediction],
    truths: Sequence[Truth],
    *,
    image_ids: Sequence[str],
    camera_of_image: Mapping[str, str],
    classes: Sequence[str],
    iou_threshold: float,
) -> EvaluationResult:
    """Run the full evaluation over a frozen image set.

    ``image_ids`` drives the whole computation: only frames listed there are
    evaluated, and every one of them contributes to the counting metrics even
    when it contains nothing. Predictions or truths for images outside the set
    are ignored, which is what keeps the evaluation set frozen.
    """
    evaluation_images = list(image_ids)
    image_set = set(evaluation_images)

    grouped_predictions: dict[tuple[str, str], list[Prediction]] = {}
    for prediction in predictions:
        if prediction.image_id in image_set and prediction.class_name in set(classes):
            grouped_predictions.setdefault(
                (prediction.image_id, prediction.class_name), []
            ).append(prediction)

    grouped_truths: dict[tuple[str, str], list[Truth]] = {}
    for truth in truths:
        if truth.image_id in image_set and truth.class_name in set(classes):
            key = (truth.image_id, truth.class_name)
            grouped_truths.setdefault(key, []).append(truth)

    per_class_detection: dict[str, DetectionMetrics] = {}
    per_class_counting: dict[str, CountingMetrics] = {}
    per_camera_pairs: dict[str, list[tuple[int, int]]] = {}
    overall_pairs: list[tuple[int, int]] = []
    total_tp = total_fp = total_fn = 0

    for class_name in classes:
        class_tp = class_fp = class_fn = 0
        class_pairs: list[tuple[int, int]] = []

        for image_id in evaluation_images:
            image_predictions = grouped_predictions.get((image_id, class_name), [])
            image_truths = grouped_truths.get((image_id, class_name), [])

            match = match_one_to_one(
                image_predictions, image_truths, iou_threshold=iou_threshold
            )
            class_tp += match.true_positives
            class_fp += match.false_positives
            class_fn += match.false_negatives

            class_pairs.append((len(image_truths), len(image_predictions)))

        per_class_detection[class_name] = DetectionMetrics.from_counts(
            class_tp, class_fp, class_fn
        )
        per_class_counting[class_name] = counting_metrics(class_pairs)
        total_tp += class_tp
        total_fp += class_fp
        total_fn += class_fn

    # Counting is aggregated per frame across all four classes: the frame-level
    # error a downstream consumer would actually experience.
    for image_id in evaluation_images:
        truth_count = sum(
            len(grouped_truths.get((image_id, name), [])) for name in classes
        )
        predicted_count = sum(
            len(grouped_predictions.get((image_id, name), [])) for name in classes
        )
        overall_pairs.append((truth_count, predicted_count))
        camera = camera_of_image.get(image_id, "")
        per_camera_pairs.setdefault(camera, []).append((truth_count, predicted_count))

    return EvaluationResult(
        images_evaluated=len(evaluation_images),
        cameras_evaluated=len(per_camera_pairs),
        ground_truth_boxes=sum(truth for truth, _ in overall_pairs),
        predicted_boxes=sum(predicted for _, predicted in overall_pairs),
        per_class_detection=per_class_detection,
        per_class_counting=per_class_counting,
        per_camera_counting={
            camera: counting_metrics(pairs)
            for camera, pairs in sorted(per_camera_pairs.items())
        },
        overall_detection=DetectionMetrics.from_counts(total_tp, total_fp, total_fn),
        overall_counting=counting_metrics(overall_pairs),
        macro_f1=(
            None
            if classes_without_ground_truth(per_class_detection, list(classes))
            else macro_f1(
                {name: value.f1 for name, value in per_class_detection.items()},
                required=list(classes),
            )
        ),
    )


# --------------------------------------------------------------------------
# Preregistered decision gate
# --------------------------------------------------------------------------

ADVANCE = "ADVANCE"
LOCAL_FINE_TUNE = "LOCAL_FINE_TUNE"
KILL_OR_REPOSITION = "KILL_OR_REPOSITION"


@dataclass(frozen=True)
class Verdict:
    """The gate's output.

    ``verdict is None`` means **NO VERDICT — MISSING EVIDENCE**: the gate was
    not run because the evidence required to run it does not exist. That is a
    legitimate and expected outcome, and it is never rendered as a soft pass.
    """

    verdict: str | None
    gate_version: str
    macro_f1: float | None
    count_wape: float | None
    failed_conditions: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "experiment_id": "VIS-001",
            "verdict": self.verdict,
            "gate_version": self.gate_version,
            "macro_f1": self.macro_f1,
            "count_wape": self.count_wape,
            "failed_conditions": list(self.failed_conditions),
            "blocking_reasons": list(self.blocking_reasons),
        }


def _camera_wapes(result: EvaluationResult) -> dict[str, float]:
    """Camera WAPEs that are actually defined.

    A camera whose evaluated frames contain zero ground-truth objects has an
    undefined WAPE and is excluded from both the per-camera ceiling and the
    spread test — it carries no information about counting accuracy either way.
    """
    return {
        camera: metrics.wape
        for camera, metrics in result.per_camera_counting.items()
        if metrics.wape is not None
    }


#: Emitted verbatim when a required class has no human-annotated positive.
INSUFFICIENT_CLASS_COVERAGE = "NO VERDICT — INSUFFICIENT CLASS COVERAGE"

#: Emitted verbatim when a frozen benchmark camera has an undefined WAPE.
INSUFFICIENT_CAMERA_COVERAGE = "NO VERDICT — INSUFFICIENT CAMERA COVERAGE"


def decide(
    result: EvaluationResult,
    *,
    thresholds,
    gate_version: str,
    blocking_reasons: Sequence[str] = (),
    required_classes: Sequence[str] = (),
    required_cameras: Sequence[str] = (),
) -> Verdict:
    """Apply the frozen gate. See ``PREREGISTRATION.md`` §Gate.

    Precedence is fixed and total:

    1. If ``blocking_reasons`` is non-empty, or the primary quantities are
       undefined, **no verdict** is issued.
    2. Otherwise, if any KILL condition holds → ``KILL_OR_REPOSITION``.
    3. Otherwise, if every ADVANCE condition holds → ``ADVANCE``.
    4. Otherwise → ``LOCAL_FINE_TUNE`` (the residual band).

    ``required_classes`` closes the class-coverage loophole: if any of the four
    frozen target classes has **no human-annotated positive** (``TP + FN == 0``),
    the gate stops at step 1 with ``NO VERDICT — INSUFFICIENT CLASS COVERAGE``.
    Coverage is measured on ground-truth support, never on ``F1 is None`` — a
    class with ten annotated buses and zero predictions scores ``F1 = 0`` and
    goes to the gate, because that is a measured failure and a model must not
    escape a KILL by predicting nothing.

    ``required_cameras`` closes the matching camera loophole: every frozen
    benchmark camera must have a defined counting WAPE, or the gate stops with
    ``NO VERDICT — INSUFFICIENT CAMERA COVERAGE``. The preregistered condition
    is "every camera subgroup WAPE ≤ 0.35"; letting an undefined camera vanish
    would quietly rewrite that as "every camera that happened to contain
    objects", which is a different and weaker rule.

    KILL is checked before ADVANCE so that the bands cannot both claim a result;
    they are disjoint by construction anyway, but the explicit order removes any
    ambiguity about which rule was applied.
    """
    macro = result.macro_f1
    overall_count = result.overall_counting
    wape = overall_count.wape if overall_count is not None else None

    reasons = list(blocking_reasons)

    unsupported_classes = classes_without_ground_truth(
        result.per_class_detection, required_classes
    )
    if unsupported_classes:
        subject = "those classes" if len(unsupported_classes) > 1 else "that class"
        reasons.append(
            f"{INSUFFICIENT_CLASS_COVERAGE}: the frozen evaluation set holds no "
            f"human-annotated instance of {', '.join(unsupported_classes)}, so "
            f"detection of {subject} cannot be assessed at all"
        )

    uncovered_cameras = cameras_without_defined_wape(
        result.per_camera_counting, required_cameras
    )
    if uncovered_cameras:
        subject = (
            "those cameras hold" if len(uncovered_cameras) > 1 else "that camera holds"
        )
        reasons.append(
            f"{INSUFFICIENT_CAMERA_COVERAGE}: counting WAPE is undefined for "
            f"{', '.join(uncovered_cameras)} — {subject} no ground-truth target "
            "objects across their frozen evaluation images, and the "
            "preregistered per-camera condition applies to all "
            f"{len(required_cameras)} frozen cameras"
        )

    if macro is None and not unsupported_classes:
        reasons.append(
            "macro F1 is undefined: no target class has both predictions and "
            "ground truth on the evaluation set"
        )
    if wape is None:
        reasons.append(
            "counting WAPE is undefined: the evaluation set contains no "
            "ground-truth objects of the four target classes"
        )

    if reasons:
        return Verdict(
            verdict=None,
            gate_version=gate_version,
            macro_f1=macro,
            count_wape=wape,
            blocking_reasons=tuple(reasons),
        )

    class_f1s = {
        name: metrics.f1
        for name, metrics in result.per_class_detection.items()
        if metrics.f1 is not None
    }
    camera_wapes = _camera_wapes(result)

    # --- KILL conditions (any is sufficient) ---
    kill: list[str] = []
    if macro < thresholds.kill_below_macro_f1:
        kill.append(
            f"C1 macro F1 {macro:.3f} < {thresholds.kill_below_macro_f1:.2f}"
        )
    if wape > thresholds.kill_above_count_wape:
        kill.append(
            f"C2 counting WAPE {wape:.3f} > {thresholds.kill_above_count_wape:.2f}"
        )
    failing_classes = sorted(
        name
        for name, value in class_f1s.items()
        if value < thresholds.kill_class_f1_below
    )
    if len(failing_classes) >= thresholds.kill_min_failing_classes:
        kill.append(
            f"C3 {len(failing_classes)} classes below F1 "
            f"{thresholds.kill_class_f1_below:.2f}: {', '.join(failing_classes)}"
        )
    if len(camera_wapes) >= 2:
        spread = max(camera_wapes.values()) - min(camera_wapes.values())
        if spread > thresholds.kill_above_camera_wape_spread:
            kill.append(
                f"C4 camera counting WAPE spread {spread:.3f} > "
                f"{thresholds.kill_above_camera_wape_spread:.2f} "
                "(aggregate performance is misleading)"
            )

    if kill:
        return Verdict(
            verdict=KILL_OR_REPOSITION,
            gate_version=gate_version,
            macro_f1=macro,
            count_wape=wape,
            failed_conditions=tuple(kill),
        )

    # --- ADVANCE conditions (all must hold) ---
    unmet: list[str] = []
    if macro < thresholds.advance_min_macro_f1:
        unmet.append(
            f"A1 macro F1 {macro:.3f} < {thresholds.advance_min_macro_f1:.2f}"
        )
    if wape > thresholds.advance_max_count_wape:
        unmet.append(
            f"A2 counting WAPE {wape:.3f} > {thresholds.advance_max_count_wape:.2f}"
        )
    weak_classes = sorted(
        name
        for name, value in class_f1s.items()
        if value < thresholds.advance_min_class_f1
    )
    if weak_classes:
        unmet.append(
            f"A3 class F1 below {thresholds.advance_min_class_f1:.2f}: "
            f"{', '.join(weak_classes)}"
        )
    weak_cameras = sorted(
        camera
        for camera, value in camera_wapes.items()
        if value > thresholds.advance_max_camera_wape
    )
    if weak_cameras:
        unmet.append(
            f"A4 camera counting WAPE above {thresholds.advance_max_camera_wape:.2f}: "
            f"{', '.join(weak_cameras)}"
        )

    if not unmet:
        return Verdict(
            verdict=ADVANCE,
            gate_version=gate_version,
            macro_f1=macro,
            count_wape=wape,
        )

    return Verdict(
        verdict=LOCAL_FINE_TUNE,
        gate_version=gate_version,
        macro_f1=macro,
        count_wape=wape,
        failed_conditions=tuple(unmet),
    )
