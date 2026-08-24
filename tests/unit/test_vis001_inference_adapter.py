"""VIS-001 inference adapter, exercised without the CV stack.

``detections_from_supervision`` is the seam between RF-DETR's output and every
metric downstream: if it mis-resolves a class name, the whole benchmark measures
the wrong thing while looking perfectly healthy. The stubs below duck-type
``supervision.Detections`` (``xyxy`` / ``confidence`` / ``class_id`` / ``data``)
so the seam stays regression-protected in ordinary CI.

The same code paths were verified against the real ``rfdetr`` 1.9.4 and
``supervision`` 0.30.0 objects during implementation; these tests pin the
behaviour, they do not replace that check.
"""

from __future__ import annotations

from vis001.config import CONFIDENCE_THRESHOLD, TARGET_CLASSES
from vis001.inference import (
    RawDetection,
    RunManifest,
    build_run_manifest,
    detections_from_supervision,
    filter_detections,
    package_version,
    prediction_record,
)


class _StubDetections:
    """Minimal stand-in for ``supervision.Detections``."""

    def __init__(self, xyxy, confidence=None, class_id=None, data=None):
        self.xyxy = xyxy
        self.confidence = confidence
        self.class_id = class_id
        self.data = data or {}


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------


def test_class_names_are_taken_from_the_model_when_present():
    result = detections_from_supervision(
        _StubDetections(
            xyxy=[[0, 0, 10, 10], [5, 5, 20, 20]],
            confidence=[0.91, 0.40],
            class_id=[1, 6],
            data={"class_name": ["person", "bus"]},
        )
    )
    assert [d.class_name for d in result] == ["person", "bus"]
    assert [d.class_id for d in result] == [1, 6]
    assert result[0].box == (0.0, 0.0, 10.0, 10.0)


def test_sparse_coco_ids_resolve_by_lookup_not_by_position():
    """COCO ids are sparse: id 6 is `bus`, not the sixth entry of a list."""
    result = detections_from_supervision(
        _StubDetections(xyxy=[[0, 0, 1, 1]], confidence=[0.9], class_id=[6])
    )
    assert result[0].class_name == "bus"


def test_unresolvable_class_becomes_empty_and_is_dropped_by_the_allowlist():
    """A label that cannot be resolved is never guessed at."""
    result = detections_from_supervision(
        _StubDetections(xyxy=[[0, 0, 1, 1]], confidence=[0.9], class_id=[77])
    )
    assert result[0].class_name == ""
    assert filter_detections(
        result, allowed_classes=TARGET_CLASSES, confidence_threshold=0.0
    ) == []


def test_empty_detections_normalise_to_an_empty_list():
    assert detections_from_supervision(_StubDetections(xyxy=[])) == []


def test_missing_confidence_defaults_to_zero_not_to_certainty():
    result = detections_from_supervision(
        _StubDetections(xyxy=[[0, 0, 1, 1]], class_id=[3])
    )
    assert result[0].confidence == 0.0


# --------------------------------------------------------------------------
# The two frozen filters
# --------------------------------------------------------------------------


def _detection(class_name: str, confidence: float) -> RawDetection:
    return RawDetection(class_name, 0, (0.0, 0.0, 1.0, 1.0), confidence)


def test_classes_outside_the_frozen_four_are_discarded():
    kept = filter_detections(
        [
            _detection("car", 0.9),
            _detection("truck", 0.99),
            _detection("traffic light", 0.99),
            _detection("motorcycle", 0.99),
        ],
        allowed_classes=TARGET_CLASSES,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    )
    assert [d.class_name for d in kept] == ["car"]


def test_threshold_is_inclusive_at_the_frozen_value():
    kept = filter_detections(
        [_detection("car", 0.35), _detection("bus", 0.3499)],
        allowed_classes=TARGET_CLASSES,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    )
    assert [d.class_name for d in kept] == ["car"]


def test_all_four_frozen_classes_survive_the_filter():
    kept = filter_detections(
        [_detection(name, 0.9) for name in TARGET_CLASSES],
        allowed_classes=TARGET_CLASSES,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    )
    assert [d.class_name for d in kept] == list(TARGET_CLASSES)


# --------------------------------------------------------------------------
# Prediction records and the run manifest
# --------------------------------------------------------------------------


def test_every_prediction_row_is_stamped_as_model_output():
    """A prediction must never be readable back as an observation."""
    row = prediction_record(
        image_id="img1", camera_id="cam01", detection=_detection("car", 0.912345)
    )
    assert row["evidence"] == "MODEL_PREDICTION"
    assert row["image_id"] == "img1"
    assert row["camera_id"] == "cam01"
    assert row["confidence"] == 0.9123


def test_run_manifest_records_everything_needed_to_reproduce(tmp_path):
    manifest = build_run_manifest(
        experiment_id="VIS-001",
        model_name="RF-DETR Small",
        model_package="rfdetr",
        checkpoint="rfdetr.RFDETRSmall (published COCO checkpoint)",
        device="cpu",
        confidence_threshold=CONFIDENCE_THRESHOLD,
        iou_threshold=0.50,
        class_allowlist=TARGET_CLASSES,
        random_seed=20260824,
        image_sha256={"b": "1" * 64, "a": "0" * 64},
    )
    assert isinstance(manifest, RunManifest)
    assert manifest.number_of_images == 2
    assert list(manifest.image_sha256) == ["a", "b"]  # sorted for stable diffs
    assert manifest.class_allowlist == list(TARGET_CLASSES)
    assert manifest.confidence_threshold == 0.35
    assert manifest.python_version
    assert manifest.platform
    assert manifest.timestamp_utc.endswith("+00:00")

    path = tmp_path / "run_manifest.json"
    manifest.write(path)
    assert '"experiment_id": "VIS-001"' in path.read_text(encoding="utf-8")


def test_unknown_package_version_is_reported_as_unknown_not_invented():
    assert package_version("a-package-that-does-not-exist-vis001") == "unknown"
