"""Frame manifest: the frozen record of exactly which images were acquired.

The manifest is the experiment's chain of custody. Raw imagery is never
committed (see the experiment ``.gitignore``), so the manifest — image id,
source URL, retrieval time and SHA-256 — is what makes a run auditable and
re-checkable by someone who re-acquires the frames themselves.

Fields the official source does not expose are stored empty. They are never
inferred, and never back-filled from a guess.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Iterable, Iterator

MANIFEST_COLUMNS: tuple[str, ...] = (
    "image_id",
    "camera_id",
    "camera_name",
    "source_url",
    "retrieved_at_utc",
    "source_timestamp",
    "latitude",
    "longitude",
    "width",
    "height",
    "sha256",
    "local_relative_path",
    "licence_or_source_note",
)


@dataclass(frozen=True)
class FrameRecord:
    """One acquired frame.

    Every field is a string as stored on disk. ``latitude``/``longitude``/
    ``width``/``height`` are kept as strings so that "not published by the
    source" can be represented as ``""`` rather than as a fabricated ``0``.
    """

    image_id: str
    camera_id: str
    camera_name: str
    source_url: str
    retrieved_at_utc: str
    source_timestamp: str
    latitude: str
    longitude: str
    width: str
    height: str
    sha256: str
    local_relative_path: str
    licence_or_source_note: str

    def as_row(self) -> dict[str, str]:
        return asdict(self)


class ManifestError(ValueError):
    """Raised when a manifest cannot be parsed at all."""


def sha256_of(path: Path, *, chunk_size: int = 1 << 20) -> str:
    """Stream a file's SHA-256 so large image sets do not need to fit in RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_of_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_manifest(path: Path, records: Iterable[FrameRecord]) -> int:
    """Write ``records`` to ``path``. Returns the number of rows written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MANIFEST_COLUMNS))
        writer.writeheader()
        for record in records:
            writer.writerow(record.as_row())
            count += 1
    return count


def write_empty_manifest(path: Path) -> None:
    """Write a header-only manifest.

    Used when no frames have been acquired yet. A header-only manifest states
    the schema honestly; it must never be padded with placeholder rows.
    """
    write_manifest(path, [])


def read_manifest(path: Path) -> list[FrameRecord]:
    """Read a manifest CSV. Raises :class:`ManifestError` on a bad header."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if header != MANIFEST_COLUMNS:
            raise ManifestError(
                f"{path}: unexpected columns.\n"
                f"  expected: {list(MANIFEST_COLUMNS)}\n"
                f"  found:    {list(header)}"
            )
        return [_record_from_row(row) for row in reader]


def _record_from_row(row: dict[str, str | None]) -> FrameRecord:
    return FrameRecord(
        **{f.name: (row.get(f.name) or "").strip() for f in fields(FrameRecord)}
    )


def _is_positive_int(value: str) -> bool:
    return value.isdigit() and int(value) > 0


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def validate_manifest(records: Iterable[FrameRecord]) -> list[str]:
    """Return a list of human-readable problems. Empty list means valid.

    Validation is deliberately strict about the fields that make a result
    reproducible (id, camera, url, retrieval time, hash, path, dimensions) and
    deliberately permissive about the fields the official source may simply not
    publish (name, source timestamp, coordinates).
    """
    problems: list[str] = []
    seen_ids: set[str] = set()
    seen_hashes: dict[str, str] = {}

    for index, record in enumerate(records):
        where = f"row {index + 1}"

        if not record.image_id:
            problems.append(f"{where}: empty image_id")
        elif record.image_id in seen_ids:
            problems.append(f"{where}: duplicate image_id {record.image_id!r}")
        else:
            seen_ids.add(record.image_id)

        for field_name in ("camera_id", "source_url", "retrieved_at_utc",
                           "local_relative_path", "licence_or_source_note"):
            if not getattr(record, field_name):
                problems.append(f"{where}: empty {field_name}")

        if not _is_positive_int(record.width):
            problems.append(
                f"{where}: width must be a positive integer, got {record.width!r}"
            )
        if not _is_positive_int(record.height):
            problems.append(
                f"{where}: height must be a positive integer, got {record.height!r}"
            )

        is_hex = all(char in "0123456789abcdef" for char in record.sha256)
        if len(record.sha256) != 64 or not is_hex:
            problems.append(
                f"{where}: sha256 must be 64 lowercase hex chars, "
                f"got {record.sha256!r}"
            )
        elif record.sha256 in seen_hashes:
            # Not fatal in principle (a static scene can repeat), but a silent
            # duplicate would inflate the sample size without adding evidence.
            problems.append(
                f"{where}: image bytes identical to {seen_hashes[record.sha256]!r} "
                f"(sha256 {record.sha256[:12]}…) — duplicate frame, not new evidence"
            )
        else:
            seen_hashes[record.sha256] = record.image_id

        # Coordinates are optional, but if present they must be numeric and on
        # Earth. A malformed coordinate is worse than an absent one.
        if record.latitude and not _is_float(record.latitude):
            problems.append(f"{where}: latitude not numeric: {record.latitude!r}")
        elif record.latitude and not -90.0 <= float(record.latitude) <= 90.0:
            problems.append(f"{where}: latitude out of range: {record.latitude!r}")
        if record.longitude and not _is_float(record.longitude):
            problems.append(f"{where}: longitude not numeric: {record.longitude!r}")
        elif record.longitude and not -180.0 <= float(record.longitude) <= 180.0:
            problems.append(f"{where}: longitude out of range: {record.longitude!r}")

    return problems


def group_by_camera(records: Iterable[FrameRecord]) -> dict[str, list[FrameRecord]]:
    """Group frames by ``camera_id``, preserving manifest order within a camera."""
    grouped: dict[str, list[FrameRecord]] = {}
    for record in records:
        grouped.setdefault(record.camera_id, []).append(record)
    return grouped


def iter_camera_ids(records: Iterable[FrameRecord]) -> Iterator[str]:
    """Yield distinct camera ids in sorted order (the canonical draw order)."""
    yield from sorted({record.camera_id for record in records})


@dataclass(frozen=True)
class ManifestCoverage:
    """How far the acquired sample is from the preregistered target."""

    frames: int
    cameras: int
    target_frames: int
    target_cameras: int
    frames_per_camera: dict[str, int]

    @property
    def is_complete(self) -> bool:
        return self.frames >= self.target_frames and self.cameras >= self.target_cameras

    def summary(self) -> str:
        state = "COMPLETE" if self.is_complete else "TARGET SAMPLE NOT YET COMPLETE"
        return (
            f"{state}: {self.frames}/{self.target_frames} frames across "
            f"{self.cameras}/{self.target_cameras} cameras"
        )


def coverage(
    records: Iterable[FrameRecord],
    *,
    target_frames: int,
    target_cameras: int,
) -> ManifestCoverage:
    materialised = list(records)
    per_camera = {
        camera: len(frames) for camera, frames in group_by_camera(materialised).items()
    }
    return ManifestCoverage(
        frames=len(materialised),
        cameras=len(per_camera),
        target_frames=target_frames,
        target_cameras=target_cameras,
        frames_per_camera=dict(sorted(per_camera.items())),
    )


# --------------------------------------------------------------------------
# Evaluation-set draw (preregistered, §10 of the protocol)
# --------------------------------------------------------------------------


def select_evaluation_set(
    records: Iterable[FrameRecord],
    *,
    per_camera: int,
    seed: int,
) -> list[str]:
    """Draw the frozen evaluation set: ``per_camera`` image ids from each camera.

    The draw is stratified by camera and fully reproducible: cameras are visited
    in sorted ``camera_id`` order, each camera's frames are sorted by
    ``image_id``, and a single :class:`random.Random` seeded with ``seed`` draws
    the sample. Given the same manifest and the same seed, the result is
    byte-identical on any machine.

    Because the draw is a function of the *whole* manifest, adding frames later
    changes the selection. The manifest must therefore be frozen before this is
    called, and the caller is expected to store the manifest's SHA-256 alongside
    the drawn ids so that drift is detectable rather than silent.

    A camera with fewer than ``per_camera`` frames contributes all of them; the
    shortfall is reported by the caller rather than back-filled from another
    camera, which would break stratification.
    """
    import random

    rng = random.Random(seed)
    grouped = group_by_camera(records)
    selected: list[str] = []
    for camera_id in sorted(grouped):
        image_ids = sorted(record.image_id for record in grouped[camera_id])
        take = min(per_camera, len(image_ids))
        selected.extend(rng.sample(image_ids, take))
    return selected
