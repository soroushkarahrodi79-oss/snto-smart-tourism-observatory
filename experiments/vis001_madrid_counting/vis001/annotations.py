"""Human ground truth: loading and validating externally produced COCO JSON.

VIS-001 does not ship an annotation tool. Ground truth is produced **blind**, in
whatever standard COCO-capable tool the annotator prefers, without ever seeing
RF-DETR's predictions (no pre-labelled boxes, no overlays, no model counts).
This module's whole job is to refuse a file that would quietly corrupt the
evaluation: unknown images, classes outside the frozen four, degenerate boxes,
duplicate ids, or boxes that fall outside the frame they claim to describe.

The model may never write into this file. If a ground-truth file were ever
generated from predictions, every metric downstream would be measuring the model
against itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class GroundTruthBox:
    """One human-annotated object.

    ``bbox`` is COCO format: ``[x, y, width, height]`` in pixels, top-left
    origin.
    """

    annotation_id: int
    image_id: str
    class_name: str
    bbox: tuple[float, float, float, float]

    @property
    def xyxy(self) -> tuple[float, float, float, float]:
        x, y, w, h = self.bbox
        return (x, y, x + w, y + h)


class AnnotationError(ValueError):
    """Raised when a ground-truth file is structurally unreadable."""


def load_coco_ground_truth(path: Path) -> tuple[list[GroundTruthBox], dict[str, Any]]:
    """Parse a COCO detection JSON into VIS-001 boxes plus the raw document.

    Structural failures raise; *semantic* problems (unknown class, bad geometry)
    are reported by :func:`validate_ground_truth` so the operator sees all of
    them at once instead of fixing them one exception at a time.
    """
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - trivial passthrough
        raise AnnotationError(f"{path}: not valid JSON ({exc})") from exc

    if not isinstance(document, dict):
        raise AnnotationError(f"{path}: top level must be a JSON object")
    for key in ("images", "annotations", "categories"):
        if not isinstance(document.get(key), list):
            raise AnnotationError(f"{path}: missing or non-list {key!r} array")

    category_names = {
        category["id"]: str(category.get("name", "")).strip()
        for category in document["categories"]
        if isinstance(category, dict) and "id" in category
    }
    image_names = {
        image["id"]: str(image.get("file_name", "")).strip()
        for image in document["images"]
        if isinstance(image, dict) and "id" in image
    }

    boxes: list[GroundTruthBox] = []
    for raw in document["annotations"]:
        if not isinstance(raw, dict):
            raise AnnotationError(f"{path}: annotation entries must be objects")
        bbox = raw.get("bbox")
        if not isinstance(bbox, Sequence) or len(bbox) != 4:
            raise AnnotationError(
                f"{path}: annotation {raw.get('id')!r} bbox must be "
                "[x, y, width, height]"
            )
        boxes.append(
            GroundTruthBox(
                annotation_id=int(raw.get("id", -1)),
                # VIS-001 keys images by the manifest image_id. COCO's numeric
                # image ids are accepted, but the manifest id is what the
                # evaluation joins on, so it is stringified here.
                image_id=str(raw.get("image_id", "")),
                class_name=category_names.get(raw.get("category_id"), ""),
                bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
            )
        )

    document["_vis001_image_file_names"] = image_names
    return boxes, document


def validate_ground_truth(
    boxes: Iterable[GroundTruthBox],
    *,
    known_images: dict[str, tuple[int, int]],
    allowed_classes: Sequence[str],
) -> list[str]:
    """Return every problem found. Empty list means the ground truth is usable.

    ``known_images`` maps ``image_id -> (width, height)`` and comes from the
    frozen frame manifest, so an annotation can never reference an image the
    experiment did not actually acquire.
    """
    problems: list[str] = []
    seen_annotation_ids: set[int] = set()
    allowed = set(allowed_classes)

    for box in boxes:
        where = f"annotation {box.annotation_id}"

        if box.annotation_id < 0:
            problems.append(f"{where}: missing or negative annotation id")
        elif box.annotation_id in seen_annotation_ids:
            problems.append(f"{where}: duplicate annotation id")
        else:
            seen_annotation_ids.add(box.annotation_id)

        if not box.image_id:
            problems.append(f"{where}: empty image_id")
            continue
        if box.image_id not in known_images:
            problems.append(
                f"{where}: image_id {box.image_id!r} is not in the frame manifest"
            )
            continue

        if box.class_name not in allowed:
            problems.append(
                f"{where}: class {box.class_name!r} is outside the frozen "
                f"target classes {sorted(allowed)}"
            )

        x, y, width, height = box.bbox
        if width <= 0 or height <= 0:
            problems.append(
                f"{where}: degenerate box (width={width}, height={height}); "
                "both dimensions must be positive"
            )
            continue

        image_width, image_height = known_images[box.image_id]
        if x < 0 or y < 0:
            problems.append(f"{where}: box origin outside the image ({x}, {y})")
        if x + width > image_width or y + height > image_height:
            problems.append(
                f"{where}: box extends past the image bounds "
                f"({x + width:.1f}x{y + height:.1f} > {image_width}x{image_height})"
            )

    return problems


def count_by_image_and_class(
    boxes: Iterable[GroundTruthBox],
    *,
    image_ids: Iterable[str],
    classes: Sequence[str],
) -> dict[tuple[str, str], int]:
    """Dense ``(image_id, class) -> count`` table.

    Every requested ``(image, class)`` pair is present, including the zeros. A
    frame with no bus in it is evidence that the model should predict no bus,
    so the zero must survive into the counting metrics rather than being dropped
    as a missing key.
    """
    counts = {(image_id, name): 0 for image_id in image_ids for name in classes}
    for box in boxes:
        key = (box.image_id, box.class_name)
        if key in counts:
            counts[key] += 1
    return counts


def annotated_image_ids(boxes: Iterable[GroundTruthBox]) -> set[str]:
    """Image ids that carry at least one box.

    Deliberately *not* the same as "annotated images": a genuinely empty frame
    is a valid annotation with zero boxes and cannot be recovered from the boxes
    alone. Callers that need annotation coverage must read the COCO ``images``
    array, which is what :func:`declared_image_ids` returns.
    """
    return {box.image_id for box in boxes}


def declared_image_ids(document: dict[str, Any]) -> set[str]:
    """Image ids the annotator declared as reviewed, including empty frames."""
    return {
        str(image["id"])
        for image in document.get("images", [])
        if isinstance(image, dict) and "id" in image
    }
