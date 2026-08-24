#!/usr/bin/env python3
"""Freeze the evaluation set: 10 images × 8 cameras, seed 20260824.

The draw is stratified by camera and fully reproducible (see
``vis001.manifest.select_evaluation_set``). This script also records the
manifest's SHA-256 alongside the drawn ids, so that a later manifest change —
which *would* change the draw — is detectable rather than silent.

Images outside this set stay outside the baseline evaluation. They may become
development or training candidates in a *separate* experiment. Training on a
VIS-001 evaluation image without first explicitly retiring this set would
contaminate the benchmark permanently.

Usage:
    python .../select_eval_set.py
    python .../select_eval_set.py --check      # verify the frozen set still matches
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.manifest import (  # noqa: E402
    evaluation_set_integrity,
    group_by_camera,
    read_manifest,
    select_evaluation_set,
    sha256_of,
)


def load_selected_cameras() -> list[str]:
    """The frozen eight camera ids, in the order they were frozen."""
    path = config.SELECTED_CAMERAS_PATH
    if not path.exists():
        raise SystemExit(
            f"missing {path}\n"
            "Freeze the benchmark cameras first (resolve_sources.py, then "
            "select_cameras.py). The evaluation set is stratified over exactly "
            "those eight, not over whatever cameras happen to be present."
        )
    frozen = json.loads(path.read_text(encoding="utf-8"))
    return [entry["camera_id"] for entry in frozen.get("selected_cameras", [])]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the frozen set on disk disagrees with a fresh draw",
    )
    args = parser.parse_args()

    if not config.SAMPLE_MANIFEST_PATH.exists():
        raise SystemExit(
            f"missing {config.SAMPLE_MANIFEST_PATH}\n"
            "Acquire frames first; there is nothing to draw from."
        )

    records = read_manifest(config.SAMPLE_MANIFEST_PATH)
    if not records:
        raise SystemExit(
            "the frame manifest is empty (header only). No evaluation set can "
            "be drawn, and none will be fabricated."
        )

    frozen_cameras = load_selected_cameras()
    selected = select_evaluation_set(
        records,
        per_camera=config.EVAL_IMAGES_PER_CAMERA,
        seed=config.RANDOM_SEED,
        selected_cameras=frozen_cameras,
    )

    grouped = group_by_camera(records)
    camera_of_image = {record.image_id: record.camera_id for record in records}
    integrity = evaluation_set_integrity(
        selected,
        camera_of_image=camera_of_image,
        selected_cameras=frozen_cameras,
        required_per_camera=config.EVAL_IMAGES_PER_CAMERA,
        required_cameras=config.TARGET_CAMERAS,
    )

    payload = {
        "experiment_id": config.EXPERIMENT_ID,
        "drawn_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "random_seed": config.RANDOM_SEED,
        "images_per_camera": config.EVAL_IMAGES_PER_CAMERA,
        "target_size": config.EVAL_SET_SIZE,
        "actual_size": len(selected),
        "is_exact": integrity.is_exact,
        "shortfalls": integrity.shortfalls(),
        "manifest_sha256": sha256_of(config.SAMPLE_MANIFEST_PATH),
        "manifest_rows": len(records),
        "selected_cameras": frozen_cameras,
        "selected_cameras_sha256": (
            sha256_of(config.SELECTED_CAMERAS_PATH)
            if config.SELECTED_CAMERAS_PATH.exists()
            else ""
        ),
        "cameras": sorted(grouped),
        "images_per_camera_drawn": dict(sorted(integrity.per_camera.items())),
        "image_ids": sorted(selected),
    }

    if args.check:
        if not config.EVAL_SET_PATH.exists():
            raise SystemExit(f"no frozen evaluation set at {config.EVAL_SET_PATH}")
        frozen = json.loads(config.EVAL_SET_PATH.read_text(encoding="utf-8"))
        drifted: list[str] = []
        if frozen.get("manifest_sha256") != payload["manifest_sha256"]:
            drifted.append(
                "the frame manifest changed since the evaluation set was frozen"
            )
        if sorted(frozen.get("image_ids", [])) != payload["image_ids"]:
            drifted.append("a fresh draw yields a different image set")
        if frozen.get("selected_cameras") != frozen_cameras:
            drifted.append("the frozen benchmark cameras changed")
        if drifted:
            for item in drifted:
                print(f"DRIFT: {item}")
            print(
                "\nRe-drawing after annotation has begun would change what is "
                "being measured. Record a numbered protocol deviation in "
                "PREREGISTRATION.md before re-freezing."
            )
            return 1
        print("frozen evaluation set is consistent with the manifest")
        return 0

    config.EVAL_SET_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.EVAL_SET_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        f"drew {len(selected)}/{config.EVAL_SET_SIZE} images from "
        f"{len(frozen_cameras)} frozen cameras (seed {config.RANDOM_SEED})"
    )
    for camera in frozen_cameras:
        drawn = integrity.per_camera.get(camera, 0)
        marker = "" if drawn == config.EVAL_IMAGES_PER_CAMERA else "  <- short"
        print(f"  {camera}: {drawn}/{config.EVAL_IMAGES_PER_CAMERA}{marker}")
    if not integrity.is_exact:
        print("\nthe evaluation set is NOT exact; the gate will issue NO VERDICT:")
        for reason in integrity.shortfalls():
            print(f"  - {reason}")
    print(f"written: {config.EVAL_SET_PATH}")
    return 0 if integrity.is_exact else 2


if __name__ == "__main__":
    raise SystemExit(main())
