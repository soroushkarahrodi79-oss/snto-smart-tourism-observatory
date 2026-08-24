#!/usr/bin/env python3
"""Validate externally produced blind COCO ground truth against the manifest.

Checks (§11 of the protocol):

* every referenced image exists in the frame manifest;
* every class is one of the four frozen target classes;
* bounding boxes are geometrically valid and have positive dimensions;
* boxes stay inside the image they claim to describe;
* annotation ids are unique;
* image ids are valid.

It also reports evaluation *coverage*: how many of the frozen evaluation images
have actually been reviewed. That number is what decides whether a verdict may
be issued at all.

Usage:
    python .../validate_annotations.py
    python .../validate_annotations.py --annotations path/to/other.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.annotations import (  # noqa: E402
    count_by_image_and_class,
    declared_image_ids,
    load_coco_ground_truth,
    validate_ground_truth,
)
from vis001.manifest import read_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=config.GROUND_TRUTH_PATH)
    args = parser.parse_args()

    if not config.SAMPLE_MANIFEST_PATH.exists():
        raise SystemExit(f"missing frame manifest: {config.SAMPLE_MANIFEST_PATH}")
    records = read_manifest(config.SAMPLE_MANIFEST_PATH)
    known_images = {
        record.image_id: (int(record.width), int(record.height))
        for record in records
        if record.width.isdigit() and record.height.isdigit()
    }

    if not args.annotations.exists():
        print(f"no ground-truth file at {args.annotations}")
        print(
            "\nGround truth must be produced blind, by a human, in an external "
            "COCO-capable tool. See data/annotations/README.md.\n"
            "Until it exists, VIS-001 can issue NO VERDICT."
        )
        return 1

    boxes, document = load_coco_ground_truth(args.annotations)
    problems = validate_ground_truth(
        boxes,
        known_images=known_images,
        allowed_classes=config.TARGET_CLASSES,
    )

    reviewed = declared_image_ids(document)
    eval_ids: set[str] = set()
    if config.EVAL_SET_PATH.exists():
        frozen = json.loads(config.EVAL_SET_PATH.read_text(encoding="utf-8"))
        eval_ids = set(frozen.get("image_ids", []))

    counts = count_by_image_and_class(
        boxes, image_ids=sorted(reviewed), classes=config.TARGET_CLASSES
    )
    per_class = {
        name: sum(value for (_, cls), value in counts.items() if cls == name)
        for name in config.TARGET_CLASSES
    }

    print(f"annotations file : {args.annotations}")
    print(f"boxes            : {len(boxes)}")
    print(f"images reviewed  : {len(reviewed)}")
    if eval_ids:
        covered = len(reviewed & eval_ids)
        print(
            f"evaluation set   : {covered}/{len(eval_ids)} frozen images annotated"
        )
        stray = sorted(reviewed - eval_ids)
        if stray:
            print(
                f"note             : {len(stray)} annotated images are outside "
                "the frozen evaluation set; they are ignored by the gate"
            )
    else:
        print("evaluation set   : not frozen yet (run select_eval_set.py)")
    print("class counts     :")
    for name, count in per_class.items():
        print(f"  {name:<8} {count}")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nvalid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
