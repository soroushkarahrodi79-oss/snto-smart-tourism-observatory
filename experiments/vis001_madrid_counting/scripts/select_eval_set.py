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
    group_by_camera,
    read_manifest,
    select_evaluation_set,
    sha256_of,
)


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

    selected = select_evaluation_set(
        records,
        per_camera=config.EVAL_IMAGES_PER_CAMERA,
        seed=config.RANDOM_SEED,
    )

    grouped = group_by_camera(records)
    shortfalls = {
        camera: len(frames)
        for camera, frames in sorted(grouped.items())
        if len(frames) < config.EVAL_IMAGES_PER_CAMERA
    }

    payload = {
        "experiment_id": config.EXPERIMENT_ID,
        "drawn_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "random_seed": config.RANDOM_SEED,
        "images_per_camera": config.EVAL_IMAGES_PER_CAMERA,
        "target_size": config.EVAL_SET_SIZE,
        "actual_size": len(selected),
        "manifest_sha256": sha256_of(config.SAMPLE_MANIFEST_PATH),
        "manifest_rows": len(records),
        "cameras": sorted(grouped),
        "cameras_below_quota": shortfalls,
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
        f"drew {len(selected)}/{config.EVAL_SET_SIZE} images "
        f"from {len(grouped)} cameras (seed {config.RANDOM_SEED})"
    )
    if shortfalls:
        print("cameras below the per-camera quota (not back-filled from elsewhere):")
        for camera, count in shortfalls.items():
            print(f"  {camera}: {count}/{config.EVAL_IMAGES_PER_CAMERA}")
    print(f"written: {config.EVAL_SET_PATH}")
    return 0 if len(selected) == config.EVAL_SET_SIZE else 2


if __name__ == "__main__":
    raise SystemExit(main())
