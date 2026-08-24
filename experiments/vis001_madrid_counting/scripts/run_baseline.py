#!/usr/bin/env python3
"""Run the frozen zero-shot RF-DETR Small baseline over the acquired frames.

Writes ``outputs/predictions.jsonl`` (one detection per line) and
``outputs/run_manifest.json`` (the reproducibility block: commit, versions,
checkpoint, thresholds, per-image SHA-256).

Frozen parameters, not command-line options: the model, the confidence
threshold (0.35), the IoU threshold (0.50) and the class allowlist all come from
``vis001.config``. ``--threshold-sweep`` exists but writes to a *separate*
file and is labelled a secondary diagnostic — it can never feed the gate.

Predictions are model output. They are not observations, and this script never
writes ground truth.

Usage:
    python .../run_baseline.py
    python .../run_baseline.py --eval-set-only
    python .../run_baseline.py --threshold-sweep 0.25,0.35,0.50
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.inference import (  # noqa: E402
    InferenceUnavailable,
    build_run_manifest,
    detect_device,
    filter_detections,
    infer_image,
    load_detector,
    prediction_record,
)
from vis001.manifest import read_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--eval-set-only",
        action="store_true",
        help="restrict inference to the frozen evaluation set",
    )
    parser.add_argument(
        "--threshold-sweep",
        type=str,
        default=None,
        help=(
            "comma-separated thresholds for a SECONDARY diagnostic sweep. "
            "Written to outputs/threshold_sweep.jsonl and never used by the gate."
        ),
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="cap images (debugging)"
    )
    args = parser.parse_args()

    if not config.SAMPLE_MANIFEST_PATH.exists():
        raise SystemExit(f"missing frame manifest: {config.SAMPLE_MANIFEST_PATH}")
    records = read_manifest(config.SAMPLE_MANIFEST_PATH)
    if not records:
        raise SystemExit(
            "the frame manifest is empty. There is nothing to run the model on, "
            "and VIS-001 does not substitute imagery from another source."
        )

    if args.eval_set_only:
        if not config.EVAL_SET_PATH.exists():
            raise SystemExit(f"missing frozen evaluation set: {config.EVAL_SET_PATH}")
        frozen = set(
            json.loads(config.EVAL_SET_PATH.read_text(encoding="utf-8"))["image_ids"]
        )
        records = [record for record in records if record.image_id in frozen]

    if args.limit:
        records = records[: args.limit]

    missing = [
        record.image_id
        for record in records
        if not (config.EXPERIMENT_ROOT / record.local_relative_path).exists()
    ]
    if missing:
        raise SystemExit(
            f"{len(missing)} manifest rows have no image on disk "
            f"(first: {missing[0]}). Re-acquire before running the baseline."
        )

    try:
        detector = load_detector()
    except InferenceUnavailable as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 3

    device = detect_device()
    print(
        f"{config.MODEL_NAME} on {device}: {len(records)} images "
        f"@ threshold {config.CONFIDENCE_THRESHOLD}"
    )

    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    with config.PREDICTIONS_PATH.open("w", encoding="utf-8") as handle:
        for index, record in enumerate(records, start=1):
            image_path = config.EXPERIMENT_ROOT / record.local_relative_path
            raw = infer_image(
                detector, image_path, threshold=config.CONFIDENCE_THRESHOLD
            )
            kept = filter_detections(
                raw,
                allowed_classes=config.TARGET_CLASSES,
                confidence_threshold=config.CONFIDENCE_THRESHOLD,
            )
            for detection in kept:
                handle.write(
                    json.dumps(
                        prediction_record(
                            image_id=record.image_id,
                            camera_id=record.camera_id,
                            detection=detection,
                        )
                    )
                    + "\n"
                )
            written += len(kept)
            if index % 10 == 0 or index == len(records):
                print(f"  {index}/{len(records)} images, {written} detections kept")

    manifest = build_run_manifest(
        experiment_id=config.EXPERIMENT_ID,
        model_name=config.MODEL_NAME,
        model_package=config.MODEL_PACKAGE,
        checkpoint=config.MODEL_ENTRYPOINT + " (published COCO checkpoint)",
        device=device,
        confidence_threshold=config.CONFIDENCE_THRESHOLD,
        iou_threshold=config.EVAL_IOU_THRESHOLD,
        class_allowlist=config.TARGET_CLASSES,
        random_seed=config.RANDOM_SEED,
        image_sha256={record.image_id: record.sha256 for record in records},
        repo_root=config.EXPERIMENT_ROOT,
    )
    manifest.write(config.RUN_MANIFEST_PATH)

    print(f"\npredictions : {config.PREDICTIONS_PATH} ({written} rows)")
    print(f"run manifest: {config.RUN_MANIFEST_PATH}")

    if args.threshold_sweep:
        _run_sweep(detector, records, args.threshold_sweep)

    return 0


def _run_sweep(detector: object, records: list, spec: str) -> None:
    """Secondary diagnostic only. Explicitly excluded from the gate."""
    thresholds = sorted({float(value) for value in spec.split(",") if value.strip()})
    path = config.OUTPUTS_DIR / "threshold_sweep.jsonl"
    print(f"\nsecondary diagnostic — threshold sweep {thresholds}")
    print("  (NOT used by the preregistered gate, which is frozen at 0.35)")

    lowest = min(thresholds)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            image_path = config.EXPERIMENT_ROOT / record.local_relative_path
            raw = infer_image(detector, image_path, threshold=lowest)
            for threshold in thresholds:
                kept = filter_detections(
                    raw,
                    allowed_classes=config.TARGET_CLASSES,
                    confidence_threshold=threshold,
                )
                handle.write(
                    json.dumps(
                        {
                            "image_id": record.image_id,
                            "camera_id": record.camera_id,
                            "threshold": threshold,
                            "counts": {
                                name: sum(
                                    1 for d in kept if d.class_name == name
                                )
                                for name in config.TARGET_CLASSES
                            },
                            "secondary_diagnostic": True,
                        }
                    )
                    + "\n"
                )
    print(f"  written: {path}")


if __name__ == "__main__":
    raise SystemExit(main())
