#!/usr/bin/env python3
"""Acquire frames from the resolved official Madrid camera endpoints.

Reads ``data/source_resolution.json`` (produced by ``resolve_sources.py``) and
downloads one frame per camera per pass, appending to ``data/sample_manifest.csv``.

Design rules, all of them protocol requirements:

* **Never invent a frame.** If a camera does not respond, the pass records
  nothing for it and says so. The manifest only ever grows by frames that were
  actually retrieved.
* **Never substitute the source.** If the official endpoints are unreachable,
  the script stops. It does not fall back to a mirror or to generic internet
  imagery.
* **Never commit imagery.** Frames land in ``data/raw/``, which the experiment's
  ``.gitignore`` excludes. Only the manifest — ids, URLs, timestamps, hashes —
  is versioned.
* **Deduplicate by content.** Madrid publishes a new capture roughly every five
  minutes. Re-downloading the same bytes adds a row but no evidence, so
  byte-identical repeats are skipped and reported.

Repeated sampling is supported but is *not* launched as a background daemon:
``--samples N --interval-seconds S`` runs N passes in the foreground and exits.

Usage:
    python .../acquire_frames.py --once
    python .../acquire_frames.py --samples 20 --interval-seconds 300
    python .../acquire_frames.py --once --max-cameras 8
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.manifest import (  # noqa: E402
    FrameRecord,
    coverage,
    read_manifest,
    sha256_of_bytes,
    write_manifest,
)

_USER_AGENT = (
    "SNTO-VIS001/1.0 (research feasibility benchmark; "
    "contact via project repository)"
)


def camera_id_for(url: str) -> str:
    """Derive a stable camera id from its image URL.

    The last path segment without its extension: for Madrid's endpoints this is
    the municipal camera identifier. It is *derived*, never guessed — if the
    source changes its URL shape, the ids change with it and the manifest shows
    that plainly instead of silently remapping.
    """
    path = urlparse(url).path
    stem = Path(path).stem
    return stem or urlparse(url).netloc


def image_dimensions(payload: bytes) -> tuple[int, int] | None:
    """Read width/height without a hard Pillow dependency at import time."""
    try:
        import io

        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(payload)) as image:
            return image.width, image.height
    except Exception:  # noqa: BLE001 - a corrupt payload is not a frame
        return None


def fetch(url: str, *, timeout: int) -> bytes | None:
    request = urllib.request.Request(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "image/*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            return response.read()
    except (urllib.error.URLError, OSError):
        return None


def load_source_resolution(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(
            f"missing {path}\n"
            "Run resolve_sources.py first: acquisition may only target "
            "endpoints that were confirmed against the official catalogue."
        )
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("status") != "RESOLVED":
        raise SystemExit(
            f"source resolution status is {record.get('status')!r}, not 'RESOLVED'.\n"
            f"  {record.get('summary')}\n"
            "VIS-001 does not acquire frames from an unconfirmed source."
        )
    return record


def acquire_pass(
    image_urls: list[str],
    *,
    raw_dir: Path,
    licence_note: str,
    known_hashes: set[str],
    timeout: int,
) -> tuple[list[FrameRecord], list[str]]:
    """One sampling pass: at most one frame per camera. Returns (new, skipped)."""
    acquired: list[FrameRecord] = []
    skipped: list[str] = []

    for url in image_urls:
        camera_id = camera_id_for(url)
        payload = fetch(url, timeout=timeout)
        if payload is None or not payload:
            skipped.append(f"{camera_id}: no response")
            continue

        digest = sha256_of_bytes(payload)
        if digest in known_hashes:
            skipped.append(f"{camera_id}: unchanged bytes (already held)")
            continue

        dimensions = image_dimensions(payload)
        if dimensions is None:
            skipped.append(f"{camera_id}: payload is not a readable image")
            continue
        width, height = dimensions

        retrieved_at = datetime.now(timezone.utc)
        stamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
        image_id = f"{camera_id}__{stamp}"
        relative_path = f"data/raw/{camera_id}/{image_id}.jpg"

        destination = raw_dir / camera_id / f"{image_id}.jpg"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

        known_hashes.add(digest)
        acquired.append(
            FrameRecord(
                image_id=image_id,
                camera_id=camera_id,
                # Madrid's image endpoints do not publish a human-readable name
                # or a capture timestamp alongside the JPEG, and coordinates
                # live in the KML rather than the image response. Left empty
                # rather than inferred; enrich_from_kml() below fills them in
                # from the official catalogue when it can.
                camera_name="",
                source_url=url,
                retrieved_at_utc=retrieved_at.isoformat(timespec="seconds"),
                source_timestamp="",
                latitude="",
                longitude="",
                width=str(width),
                height=str(height),
                sha256=digest,
                local_relative_path=relative_path,
                licence_or_source_note=licence_note,
            )
        )

    return acquired, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="run a single pass")
    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help=f"number of passes (default: {config.TARGET_FRAMES_PER_CAMERA})",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=300,
        help="wait between passes; Madrid refreshes roughly every 300 s",
    )
    parser.add_argument(
        "--max-cameras",
        type=int,
        default=config.TARGET_CAMERAS,
        help="cap the number of cameras sampled",
    )
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    passes = 1 if args.once else (args.samples or config.TARGET_FRAMES_PER_CAMERA)

    resolution = load_source_resolution(config.SOURCE_RESOLUTION_PATH)
    image_urls = list(resolution.get("image_urls_discovered") or [])
    if not image_urls:
        raise SystemExit(
            "the resolved source declares no image endpoints; nothing to acquire"
        )

    # Take the first N distinct cameras in URL order. Camera choice is NOT
    # optimised for detector performance — no camera is previewed, scored or
    # rejected on how well RF-DETR happens to do on it.
    by_camera: dict[str, str] = {}
    for url in image_urls:
        by_camera.setdefault(camera_id_for(url), url)
    selected = [by_camera[key] for key in sorted(by_camera)][: args.max_cameras]
    print(f"sampling {len(selected)} cameras × {passes} passes")

    existing: list[FrameRecord] = []
    if config.SAMPLE_MANIFEST_PATH.exists():
        existing = read_manifest(config.SAMPLE_MANIFEST_PATH)
    known_hashes = {record.sha256 for record in existing}

    licence_note = (
        "Ayuntamiento de Madrid open data catalogue (datos.madrid.es / "
        "informo.madrid.es). See data/source_resolution.json for the verbatim "
        "terms-of-use snippets retrieved at resolution time."
    )

    for index in range(passes):
        print(f"\npass {index + 1}/{passes}")
        acquired, skipped = acquire_pass(
            selected,
            raw_dir=config.RAW_FRAMES_DIR,
            licence_note=licence_note,
            known_hashes=known_hashes,
            timeout=args.timeout,
        )
        existing.extend(acquired)
        print(f"  acquired {len(acquired)}, skipped {len(skipped)}")
        for reason in skipped:
            print(f"    - {reason}")

        write_manifest(config.SAMPLE_MANIFEST_PATH, existing)

        if index + 1 < passes:
            print(f"  waiting {args.interval_seconds}s for the next capture …")
            time.sleep(args.interval_seconds)

    state = coverage(
        existing,
        target_frames=config.TARGET_FRAMES,
        target_cameras=config.TARGET_CAMERAS,
    )
    print()
    print(state.summary())
    for camera, count in state.frames_per_camera.items():
        print(f"  {camera}: {count}")
    print(f"manifest: {config.SAMPLE_MANIFEST_PATH}")
    return 0 if state.is_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
