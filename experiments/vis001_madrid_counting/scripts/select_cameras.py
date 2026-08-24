#!/usr/bin/env python3
"""Freeze the eight benchmark cameras, deterministically, before any inference.

Reads the camera manifest built by ``resolve_sources.py`` and applies the frozen
selection procedure (``vis001.cameras.select_cameras``): assign every published
camera to one of eight 45° compass sectors around the population centroid, then
take the median-distance camera in each sector, filling empty sectors from the
richest remaining one.

Why not "the first eight sorted camera ids": municipal ids track installation
batches, so the lowest eight tend to sit on the same few roads — one scene type,
one mounting style, one background. Compass sectors spread the sample across the
city, which is the closest thing to the pedestrian density / road type / camera
height / background variation the protocol asks for that can be derived from
published metadata alone.

Every input is geographic metadata from the official KML. No image is opened, no
model is run, and no prediction is consulted, so the choice cannot be tuned —
even accidentally — to flatter RF-DETR. The result is written to
``data/selected_cameras.json`` and must be frozen before ``run_baseline.py``.

Usage:
    python .../select_cameras.py
    python .../select_cameras.py --check     # verify the frozen set still matches
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.cameras import (  # noqa: E402
    SELECTION_PROCEDURE_VERSION,
    read_camera_manifest,
    select_cameras,
    validate_camera_manifest,
)
from vis001.manifest import sha256_of  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the frozen selection disagrees with a fresh run",
    )
    args = parser.parse_args()

    if not config.CAMERA_MANIFEST_PATH.exists():
        raise SystemExit(
            f"missing {config.CAMERA_MANIFEST_PATH}\n"
            "Run resolve_sources.py first: the eight benchmark cameras are "
            "chosen from the official KML, never invented."
        )

    cameras = read_camera_manifest(config.CAMERA_MANIFEST_PATH)
    if not cameras:
        raise SystemExit(
            "the camera manifest is empty (header only). No benchmark cameras "
            "can be selected, and none will be fabricated."
        )

    problems = validate_camera_manifest(cameras)
    if problems:
        print(f"{len(problems)} problem(s) in the camera manifest:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    selection = select_cameras(cameras, count=config.TARGET_CAMERAS)
    by_id = {camera.camera_id: camera for camera in cameras}

    payload = {
        "experiment_id": config.EXPERIMENT_ID,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "procedure_version": SELECTION_PROCEDURE_VERSION,
        "procedure": (
            "Eight 45° compass sectors around the centroid of every camera "
            "published in the official KML; the median-distance camera in each "
            "sector; empty sectors backfilled from the richest remaining "
            "sector. Geographic metadata only — no imagery, no model output."
        ),
        "camera_manifest_sha256": sha256_of(config.CAMERA_MANIFEST_PATH),
        "cameras_considered": selection.cameras_considered,
        "required_cameras": config.TARGET_CAMERAS,
        "selected_count": len(selection.camera_ids),
        "sectors_empty": list(selection.sectors_empty),
        "selected_cameras": [
            {
                "camera_id": camera_id,
                "camera_name": by_id[camera_id].camera_name,
                "latitude": by_id[camera_id].latitude,
                "longitude": by_id[camera_id].longitude,
                "image_url": by_id[camera_id].image_url,
                "sector": selection.sector_of_camera.get(camera_id, ""),
            }
            for camera_id in selection.camera_ids
        ],
    }

    if args.check:
        if not config.SELECTED_CAMERAS_PATH.exists():
            raise SystemExit(f"no frozen selection at {config.SELECTED_CAMERAS_PATH}")
        frozen = json.loads(config.SELECTED_CAMERAS_PATH.read_text(encoding="utf-8"))
        drifted: list[str] = []
        if frozen.get("camera_manifest_sha256") != payload["camera_manifest_sha256"]:
            drifted.append("the camera manifest changed since the selection was frozen")
        frozen_ids = [
            entry["camera_id"] for entry in frozen.get("selected_cameras", [])
        ]
        if frozen_ids != list(selection.camera_ids):
            drifted.append("a fresh run selects a different set of cameras")
        if frozen.get("procedure_version") != SELECTION_PROCEDURE_VERSION:
            drifted.append("the selection procedure version changed")
        if drifted:
            for item in drifted:
                print(f"DRIFT: {item}")
            print(
                "\nRe-selecting cameras after frames have been acquired would "
                "change what is being benchmarked. Record a numbered protocol "
                "deviation in PREREGISTRATION.md before re-freezing."
            )
            return 1
        print("frozen camera selection is consistent with the manifest")
        return 0

    config.SELECTED_CAMERAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.SELECTED_CAMERAS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        f"selected {len(selection.camera_ids)}/{config.TARGET_CAMERAS} cameras "
        f"from {selection.cameras_considered} published "
        f"(procedure {SELECTION_PROCEDURE_VERSION})"
    )
    for entry in payload["selected_cameras"]:
        print(
            f"  [{entry['sector']:>12}] {entry['camera_id']} — "
            f"{entry['camera_name'] or '(no published name)'}"
        )
    if selection.sectors_empty:
        print(f"empty sectors (backfilled): {', '.join(selection.sectors_empty)}")
    print(f"written: {config.SELECTED_CAMERAS_PATH}")
    return 0 if selection.is_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
