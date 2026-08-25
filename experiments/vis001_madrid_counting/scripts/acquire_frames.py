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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.cameras import canonical_image_endpoint, read_camera_manifest  # noqa: E402
from vis001.manifest import (  # noqa: E402
    FrameRecord,
    coverage,
    read_manifest,
    sha256_of_bytes,
    write_manifest,
)


def load_selected_cameras() -> list[dict[str, str]]:
    """The frozen eight, in the order they were frozen.

    Acquisition targets exactly these. There is no "take the first N sorted
    ids" path any more: the benchmark cameras are chosen once, before any
    inference, by the documented geographic procedure in select_cameras.py.
    """
    path = config.SELECTED_CAMERAS_PATH
    if not path.exists():
        raise SystemExit(
            f"missing {path}\n"
            "Freeze the benchmark cameras first:\n"
            "  python .../scripts/resolve_sources.py\n"
            "  python .../scripts/select_cameras.py\n"
            "VIS-001 does not acquire from an unfrozen camera set."
        )
    frozen = json.loads(path.read_text(encoding="utf-8"))
    selected = frozen.get("selected_cameras") or []
    if len(selected) != config.TARGET_CAMERAS:
        raise SystemExit(
            f"{path} freezes {len(selected)} cameras, but the preregistration "
            f"requires exactly {config.TARGET_CAMERAS}. Re-run "
            "select_cameras.py against a complete camera manifest."
        )
    return selected


def resolve_current_endpoints(
    frozen_cameras: list[dict[str, str]],
) -> list[tuple[str, str]]:
    """Resolve where to fetch each frozen camera from, right now.

    FROZEN decides *which* camera is benchmarked (``camera_id``, fixed by
    ``select_cameras.py``). The CURRENT official camera manifest decides *how*
    to retrieve that same camera today: Madrid rewrites the image URL's
    ``?v=...`` query token on essentially every catalogue refresh, so using the
    URL frozen at selection time would eventually fetch a stale/expired
    endpoint instead of the live one.

    For each frozen id, this looks the id up in the current manifest and
    checks its canonical image endpoint (scheme+host+path, query/fragment
    stripped) still matches what was frozen. Only then is the CURRENT full URL
    — including its current ``?v=`` token — used to fetch the frame. A camera
    that has disappeared from the current manifest, or whose canonical
    endpoint path has changed, fails the whole acquisition closed: no other
    camera is ever substituted or selected in its place.
    """
    cameras = read_camera_manifest(config.CAMERA_MANIFEST_PATH)
    by_id = {camera.camera_id: camera for camera in cameras}

    resolved: list[tuple[str, str]] = []
    problems: list[str] = []
    for entry in frozen_cameras:
        camera_id = entry["camera_id"]
        current = by_id.get(camera_id)
        if current is None:
            problems.append(
                f"{camera_id}: no longer present in the current camera manifest"
            )
            continue

        frozen_endpoint = canonical_image_endpoint(entry["image_url"])
        current_endpoint = canonical_image_endpoint(current.image_url)
        if frozen_endpoint != current_endpoint:
            problems.append(
                f"{camera_id}: canonical image endpoint changed "
                f"({frozen_endpoint!r} -> {current_endpoint!r})"
            )
            continue

        resolved.append((camera_id, current.image_url))

    if problems:
        raise SystemExit(
            "refusing to acquire: frozen camera identity could not be "
            "validated against the current official camera manifest.\n"
            + "\n".join(f"  - {problem}" for problem in problems)
            + "\nVIS-001 never substitutes another camera and never acquires "
            "from an endpoint that has not been validated against the frozen "
            "camera identity."
        )
    return resolved


_USER_AGENT = (
    "SNTO-VIS001/1.0 (research feasibility benchmark; "
    "contact via project repository)"
)


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
    cameras: list[tuple[str, str]],
    *,
    raw_dir: Path,
    licence_note: str,
    known_hashes: set[str],
    timeout: int,
) -> tuple[list[FrameRecord], list[str]]:
    """One sampling pass: at most one frame per camera. Returns (new, skipped).

    ``cameras`` is ``(camera_id, image_url)`` taken from the frozen selection,
    so a frame's ``camera_id`` always matches the camera that was benchmarked
    rather than being re-derived from whatever the URL happens to look like.
    """
    acquired: list[FrameRecord] = []
    skipped: list[str] = []

    for camera_id, url in cameras:
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

    load_source_resolution(config.SOURCE_RESOLUTION_PATH)
    if not config.CAMERA_MANIFEST_PATH.exists():
        raise SystemExit(
            f"missing {config.CAMERA_MANIFEST_PATH}; run resolve_sources.py first"
        )
    read_camera_manifest(config.CAMERA_MANIFEST_PATH)  # validates the CSV shape

    frozen_cameras = load_selected_cameras()
    if args.max_cameras != config.TARGET_CAMERAS:
        raise SystemExit(
            f"--max-cameras must be {config.TARGET_CAMERAS}: the preregistered "
            "sample is 20 frames from each of exactly eight frozen cameras, so "
            "sampling a subset produces an incomplete sample, not a smaller one."
        )
    selected = resolve_current_endpoints(frozen_cameras)
    print(f"sampling {len(selected)} frozen cameras × {passes} passes")

    existing: list[FrameRecord] = []
    if config.SAMPLE_MANIFEST_PATH.exists():
        existing = read_manifest(config.SAMPLE_MANIFEST_PATH)
    known_hashes = {record.sha256 for record in existing}

    licence_note = (
        "Ayuntamiento de Madrid open data (informo.madrid.es KML; licence via "
        "the datos.madrid.es catalogue, with datos.gob.es as the official "
        "national fallback). data/source_resolution.json is the authoritative "
        "provenance record: see its verbatim terms-of-use snippets and the "
        "source that supplied them."
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
        selected_cameras=[camera_id for camera_id, _ in selected],
        frames_per_camera=config.TARGET_FRAMES_PER_CAMERA,
    )
    print()
    print(state.summary())
    for camera, count in state.frames_per_camera.items():
        marker = "" if count >= config.TARGET_FRAMES_PER_CAMERA else "  <- short"
        print(f"  {camera}: {count}/{config.TARGET_FRAMES_PER_CAMERA}{marker}")
    for reason in state.shortfalls():
        print(f"  ! {reason}")
    print(f"manifest: {config.SAMPLE_MANIFEST_PATH}")
    return 0 if state.is_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
