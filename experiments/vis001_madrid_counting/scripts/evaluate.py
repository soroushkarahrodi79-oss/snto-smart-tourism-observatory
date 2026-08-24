#!/usr/bin/env python3
"""Evaluate the baseline against blind human ground truth and apply the gate.

Writes ``outputs/metrics.json``, ``outputs/verdict.json`` and
``outputs/report.md``.

This script is the only place a verdict is produced, and it refuses to produce
one unless the evidence the preregistration demands is actually present:

* the frozen evaluation set exists;
* every one of its images carries a blind human annotation;
* model predictions exist for those images.

If any of that is missing, the verdict is ``null`` with explicit blocking
reasons and the report says **NO VERDICT — MISSING EVIDENCE**. Metrics are never
fabricated to fill the gap, and a partially annotated evaluation is never
reported as a partial pass.

Usage:
    python .../evaluate.py
    python .../evaluate.py --allow-partial     # diagnostic metrics, still no verdict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.annotations import declared_image_ids, load_coco_ground_truth  # noqa: E402
from vis001.manifest import (  # noqa: E402
    coverage,
    evaluation_set_integrity,
    read_manifest,
)
from vis001.metrics import Prediction, Truth, Verdict, decide, evaluate  # noqa: E402
from vis001.reporting import render_report, write_json  # noqa: E402


def _load_predictions(path: Path) -> list[Prediction]:
    predictions: list[Prediction] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            x1, y1, x2, y2 = row["bbox_xyxy"]
            predictions.append(
                Prediction(
                    image_id=str(row["image_id"]),
                    class_name=str(row["class_name"]),
                    box=(float(x1), float(y1), float(x2), float(y2)),
                    confidence=float(row["confidence"]),
                )
            )
    return predictions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help=(
            "compute diagnostic metrics over whatever is annotated. A verdict "
            "is still withheld: partial evidence never yields a gate result."
        ),
    )
    args = parser.parse_args()

    blocking: list[str] = []
    missing_evidence: list[str] = []

    # --- frozen benchmark cameras ---------------------------------------
    frozen_cameras: list[str] = []
    if config.SELECTED_CAMERAS_PATH.exists():
        frozen = json.loads(
            config.SELECTED_CAMERAS_PATH.read_text(encoding="utf-8")
        )
        frozen_cameras = [
            entry["camera_id"] for entry in frozen.get("selected_cameras", [])
        ]
    if len(frozen_cameras) != config.TARGET_CAMERAS:
        missing_evidence.append(
            f"The {config.TARGET_CAMERAS} benchmark cameras are not frozen "
            f"({len(frozen_cameras)} found). Run resolve_sources.py, then "
            "select_cameras.py."
        )
        blocking.append(
            f"exactly {config.TARGET_CAMERAS} benchmark cameras must be frozen "
            f"before inference; {len(frozen_cameras)} are"
        )

    # --- sample ---------------------------------------------------------
    records = (
        read_manifest(config.SAMPLE_MANIFEST_PATH)
        if config.SAMPLE_MANIFEST_PATH.exists()
        else []
    )
    sample = coverage(
        records,
        target_frames=config.TARGET_FRAMES,
        target_cameras=config.TARGET_CAMERAS,
        selected_cameras=frozen_cameras,
        frames_per_camera=config.TARGET_FRAMES_PER_CAMERA,
    )
    if not sample.is_complete:
        missing_evidence.append(
            f"TARGET SAMPLE NOT YET COMPLETE — {sample.frames}/"
            f"{config.TARGET_FRAMES} frames across {sample.cameras}/"
            f"{config.TARGET_CAMERAS} cameras. The preregistered structure is "
            f"at least {config.TARGET_FRAMES_PER_CAMERA} unique frames from "
            f"EACH of the {config.TARGET_CAMERAS} frozen cameras; a matching "
            "total spread unevenly does not satisfy it."
        )
        blocking.extend(sample.shortfalls())

    camera_of_image = {record.image_id: record.camera_id for record in records}

    # --- frozen evaluation set -------------------------------------------
    eval_ids: list[str] = []
    if config.EVAL_SET_PATH.exists():
        eval_ids = sorted(
            json.loads(config.EVAL_SET_PATH.read_text(encoding="utf-8"))["image_ids"]
        )
        integrity = evaluation_set_integrity(
            eval_ids,
            camera_of_image=camera_of_image,
            selected_cameras=frozen_cameras,
            required_per_camera=config.EVAL_IMAGES_PER_CAMERA,
            required_cameras=config.TARGET_CAMERAS,
        )
        if not integrity.is_exact:
            missing_evidence.append(
                f"The evaluation set is not the preregistered "
                f"{config.EVAL_SET_SIZE} images "
                f"({config.EVAL_IMAGES_PER_CAMERA} from each of the "
                f"{config.TARGET_CAMERAS} frozen cameras). No verdict can be "
                "issued on a partial evaluation set."
            )
            blocking.extend(integrity.shortfalls())
    else:
        missing_evidence.append(
            "The frozen evaluation set has not been drawn "
            "(run select_eval_set.py)."
        )
        blocking.append("no frozen evaluation set exists")

    # --- ground truth -----------------------------------------------------
    truths: list[Truth] = []
    annotated: set[str] = set()
    class_distribution: dict[str, int] = {}
    if config.GROUND_TRUTH_PATH.exists():
        boxes, document = load_coco_ground_truth(config.GROUND_TRUTH_PATH)
        annotated = declared_image_ids(document)
        truths = [
            Truth(image_id=box.image_id, class_name=box.class_name, box=box.xyxy)
            for box in boxes
        ]
        class_distribution = {
            name: sum(1 for box in boxes if box.class_name == name)
            for name in config.TARGET_CLASSES
        }
    else:
        relative = config.GROUND_TRUTH_PATH.relative_to(config.EXPERIMENT_ROOT)
        missing_evidence.append(
            f"No blind human ground truth exists ({relative} is absent). "
            "See data/annotations/README.md."
        )
        blocking.append("no human ground truth is present")

    if eval_ids:
        covered = annotated & set(eval_ids)
        if len(covered) < len(eval_ids):
            missing_evidence.append(
                f"No verdict issued: only {len(covered)}/{len(eval_ids)} "
                "preregistered evaluation images currently have blind human "
                "annotations."
            )
            blocking.append(
                f"the frozen evaluation set is only {len(covered)}/"
                f"{len(eval_ids)} annotated"
            )

    # --- predictions ------------------------------------------------------
    predictions: list[Prediction] = []
    run_manifest: dict[str, object] | None = None
    if config.PREDICTIONS_PATH.exists():
        predictions = _load_predictions(config.PREDICTIONS_PATH)
    else:
        missing_evidence.append(
            "No model predictions exist (run run_baseline.py)."
        )
        blocking.append("no model predictions are present")
    if config.RUN_MANIFEST_PATH.exists():
        run_manifest = json.loads(config.RUN_MANIFEST_PATH.read_text(encoding="utf-8"))

    # --- evaluation -------------------------------------------------------
    scored_ids = sorted(set(eval_ids) & annotated) if args.allow_partial else eval_ids
    result = None
    if scored_ids and predictions:
        result = evaluate(
            predictions,
            truths,
            image_ids=scored_ids,
            camera_of_image=camera_of_image,
            classes=config.TARGET_CLASSES,
            iou_threshold=config.EVAL_IOU_THRESHOLD,
        )

    if result is None:
        verdict = Verdict(
            verdict=None,
            gate_version=config.GATE_VERSION,
            macro_f1=None,
            count_wape=None,
            blocking_reasons=tuple(blocking)
            or ("no evaluation could be computed",),
        )
    else:
        verdict = decide(
            result,
            thresholds=config.GATE,
            gate_version=config.GATE_VERSION,
            blocking_reasons=blocking,
            required_classes=config.TARGET_CLASSES,
            required_cameras=frozen_cameras,
        )

    write_json(
        config.METRICS_PATH,
        {
            "experiment_id": config.EXPERIMENT_ID,
            "gate_version": config.GATE_VERSION,
            "confidence_threshold": config.CONFIDENCE_THRESHOLD,
            "iou_threshold": config.EVAL_IOU_THRESHOLD,
            "classes": list(config.TARGET_CLASSES),
            "sample": {
                "frames": sample.frames,
                "cameras": sample.cameras,
                "target_frames": config.TARGET_FRAMES,
                "target_cameras": config.TARGET_CAMERAS,
                "frames_per_camera": sample.frames_per_camera,
            },
            "annotation": {
                "images_annotated": len(annotated),
                "evaluation_set_size": len(eval_ids),
                "class_distribution": class_distribution,
            },
            "evaluation": result.as_dict() if result else None,
        },
    )
    write_json(config.VERDICT_PATH, verdict.as_dict())

    report = render_report(
        result=result,
        verdict=verdict,
        run_manifest=run_manifest,
        sample_frames=sample.frames,
        sample_cameras=sample.cameras,
        target_frames=config.TARGET_FRAMES,
        target_cameras=config.TARGET_CAMERAS,
        annotated_images=len(annotated),
        eval_set_size=len(eval_ids) or config.EVAL_SET_SIZE,
        class_distribution=class_distribution,
        missing_evidence=missing_evidence,
    )
    config.REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.REPORT_PATH.write_text(report, encoding="utf-8")

    print(f"metrics : {config.METRICS_PATH}")
    print(f"verdict : {config.VERDICT_PATH}")
    print(f"report  : {config.REPORT_PATH}")
    print()
    if verdict.verdict is None:
        print("VERDICT: NO VERDICT — MISSING EVIDENCE")
        for reason in verdict.blocking_reasons:
            print(f"  - {reason}")
        return 2
    print(f"VERDICT: {verdict.verdict}")
    for condition in verdict.failed_conditions:
        print(f"  - {condition}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
