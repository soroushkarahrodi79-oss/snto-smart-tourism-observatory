"""VIS-001 ground-truth loading and validation.

The validator is the only thing standing between a mis-exported annotation file
and a silently wrong benchmark, so every rejection path is pinned here.
"""

from __future__ import annotations

import json

import pytest
from vis001.annotations import (
    AnnotationError,
    GroundTruthBox,
    annotated_image_ids,
    count_by_image_and_class,
    declared_image_ids,
    load_coco_ground_truth,
    validate_ground_truth,
)
from vis001.config import TARGET_CLASSES

KNOWN_IMAGES = {"img1": (640, 480), "img2": (640, 480)}


def _box(**overrides) -> GroundTruthBox:
    base = {
        "annotation_id": 1,
        "image_id": "img1",
        "class_name": "car",
        "bbox": (10.0, 10.0, 50.0, 40.0),
    }
    base.update(overrides)
    return GroundTruthBox(**base)


def _coco_document(annotations, images=None, categories=None) -> dict:
    return {
        "images": images
        if images is not None
        else [{"id": "img1", "file_name": "data/raw/cam01/img1.jpg"}],
        "categories": categories
        if categories is not None
        else [
            {"id": 1, "name": "person"},
            {"id": 2, "name": "bicycle"},
            {"id": 3, "name": "car"},
            {"id": 6, "name": "bus"},
        ],
        "annotations": annotations,
    }


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------


def test_xyxy_conversion_from_coco_bbox():
    """COCO is [x, y, w, h]; the evaluator needs corners."""
    assert _box(bbox=(10.0, 20.0, 30.0, 40.0)).xyxy == (10.0, 20.0, 40.0, 60.0)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def test_valid_annotation_passes():
    assert validate_ground_truth(
        [_box()], known_images=KNOWN_IMAGES, allowed_classes=TARGET_CLASSES
    ) == []


def test_unknown_image_is_rejected():
    """An annotation can never reference an image the experiment did not acquire."""
    problems = validate_ground_truth(
        [_box(image_id="never_acquired")],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("not in the frame manifest" in problem for problem in problems)


def test_class_outside_the_frozen_four_is_rejected():
    problems = validate_ground_truth(
        [_box(class_name="motorcycle")],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("outside the frozen" in problem for problem in problems)


def test_degenerate_box_is_rejected():
    problems = validate_ground_truth(
        [_box(bbox=(10.0, 10.0, 0.0, 40.0))],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("degenerate box" in problem for problem in problems)


def test_negative_dimensions_are_rejected():
    problems = validate_ground_truth(
        [_box(bbox=(10.0, 10.0, -5.0, -5.0))],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("degenerate box" in problem for problem in problems)


def test_box_outside_image_bounds_is_rejected():
    """The classic symptom of exporting [x1,y1,x2,y2] where COCO wants [x,y,w,h]."""
    problems = validate_ground_truth(
        [_box(bbox=(600.0, 400.0, 200.0, 200.0))],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("past the image bounds" in problem for problem in problems)


def test_negative_origin_is_rejected():
    problems = validate_ground_truth(
        [_box(bbox=(-5.0, 10.0, 20.0, 20.0))],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("origin outside the image" in problem for problem in problems)


def test_box_touching_the_far_edge_is_accepted():
    assert validate_ground_truth(
        [_box(bbox=(0.0, 0.0, 640.0, 480.0))],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    ) == []


def test_duplicate_annotation_ids_are_rejected():
    problems = validate_ground_truth(
        [_box(annotation_id=7), _box(annotation_id=7, image_id="img2")],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("duplicate annotation id" in problem for problem in problems)


def test_missing_annotation_id_is_rejected():
    problems = validate_ground_truth(
        [_box(annotation_id=-1)],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("missing or negative annotation id" in problem for problem in problems)


def test_empty_image_id_is_rejected():
    problems = validate_ground_truth(
        [_box(image_id="")],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert any("empty image_id" in problem for problem in problems)


def test_all_problems_are_reported_at_once():
    """The operator should see every fix needed, not just the first."""
    problems = validate_ground_truth(
        [
            _box(annotation_id=1, class_name="truck"),
            _box(annotation_id=1, image_id="ghost"),
            _box(annotation_id=3, bbox=(0.0, 0.0, 0.0, 0.0)),
        ],
        known_images=KNOWN_IMAGES,
        allowed_classes=TARGET_CLASSES,
    )
    assert len(problems) >= 3


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def test_load_coco_ground_truth(tmp_path):
    path = tmp_path / "gt.json"
    path.write_text(
        json.dumps(
            _coco_document(
                [
                    {
                        "id": 1,
                        "image_id": "img1",
                        "category_id": 3,
                        "bbox": [10, 10, 50, 40],
                    }
                ]
            )
        ),
        encoding="utf-8",
    )
    boxes, document = load_coco_ground_truth(path)
    assert len(boxes) == 1
    assert boxes[0].class_name == "car"
    assert boxes[0].image_id == "img1"
    assert boxes[0].bbox == (10.0, 10.0, 50.0, 40.0)
    assert declared_image_ids(document) == {"img1"}


def test_numeric_image_ids_are_stringified_for_the_manifest_join(tmp_path):
    path = tmp_path / "gt.json"
    path.write_text(
        json.dumps(
            _coco_document(
                [{"id": 1, "image_id": 42, "category_id": 3, "bbox": [1, 1, 2, 2]}],
                images=[{"id": 42, "file_name": "x.jpg"}],
            )
        ),
        encoding="utf-8",
    )
    boxes, document = load_coco_ground_truth(path)
    assert boxes[0].image_id == "42"
    assert declared_image_ids(document) == {"42"}


def test_missing_arrays_raise(tmp_path):
    path = tmp_path / "gt.json"
    path.write_text(json.dumps({"images": [], "categories": []}), encoding="utf-8")
    with pytest.raises(AnnotationError, match="annotations"):
        load_coco_ground_truth(path)


def test_malformed_bbox_raises(tmp_path):
    path = tmp_path / "gt.json"
    path.write_text(
        json.dumps(
            _coco_document(
                [{"id": 1, "image_id": "img1", "category_id": 3, "bbox": [1, 2]}]
            )
        ),
        encoding="utf-8",
    )
    with pytest.raises(AnnotationError, match="bbox"):
        load_coco_ground_truth(path)


def test_non_object_top_level_raises(tmp_path):
    path = tmp_path / "gt.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(AnnotationError, match="top level"):
        load_coco_ground_truth(path)


# --------------------------------------------------------------------------
# Counting
# --------------------------------------------------------------------------


def test_count_table_is_dense_including_zeros():
    """A frame with no bus is evidence, not a missing key."""
    counts = count_by_image_and_class(
        [_box(class_name="car"), _box(annotation_id=2, class_name="car")],
        image_ids=["img1", "img2"],
        classes=TARGET_CLASSES,
    )
    assert counts[("img1", "car")] == 2
    assert counts[("img1", "bus")] == 0
    assert counts[("img2", "car")] == 0
    assert len(counts) == 2 * len(TARGET_CLASSES)


def test_count_table_ignores_images_outside_the_requested_set():
    counts = count_by_image_and_class(
        [_box(image_id="stray")], image_ids=["img1"], classes=TARGET_CLASSES
    )
    assert sum(counts.values()) == 0


def test_annotated_image_ids_only_covers_images_with_boxes():
    """Empty frames cannot be recovered from boxes alone.

    That is what declared_image_ids is for.
    """
    assert annotated_image_ids([_box(image_id="img1")]) == {"img1"}
