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
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

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
    """How far the acquired sample is from the preregistered structure.

    Completeness is **structural**, not a headline count. The preregistration
    asks for 20 frames from each of 8 specific cameras; 160 frames spread
    unevenly across those cameras — or spread across twelve of them — is a
    different sample that happens to share a total, and it would break the
    per-camera stratification the gate's camera rules rest on.
    """

    frames: int
    cameras: int
    target_frames: int
    target_cameras: int
    frames_per_camera: dict[str, int]
    #: The frozen eight. Empty when the selection has not been frozen yet, in
    #: which case the sample can never be complete.
    selected_cameras: tuple[str, ...] = ()
    #: Minimum unique frames each selected camera must hold.
    frames_per_camera_required: int = 0
    #: Selected cameras that are short, mapped to what they actually hold.
    cameras_below_quota: dict[str, int] = field(default_factory=dict)
    #: Selected cameras with no frames at all.
    cameras_missing: tuple[str, ...] = ()
    #: Cameras present in the manifest that are not among the frozen eight.
    cameras_unexpected: tuple[str, ...] = ()

    @property
    def is_complete(self) -> bool:
        """True only for exactly the preregistered structure.

        Every one of these must hold; the frame total on its own satisfies
        none of them:

        * the eight cameras have been frozen at all;
        * exactly ``target_cameras`` of them are selected;
        * each holds at least ``frames_per_camera_required`` unique frames;
        * the manifest contains no frames from an unselected camera.
        """
        if not self.selected_cameras:
            return False
        if len(self.selected_cameras) != self.target_cameras:
            return False
        if self.cameras_missing or self.cameras_below_quota:
            return False
        if self.cameras_unexpected:
            return False
        return True

    def summary(self) -> str:
        state = "COMPLETE" if self.is_complete else "TARGET SAMPLE NOT YET COMPLETE"
        return (
            f"{state}: {self.frames}/{self.target_frames} frames across "
            f"{self.cameras}/{self.target_cameras} cameras"
        )

    def shortfalls(self) -> list[str]:
        """Human-readable reasons the sample is not yet complete."""
        reasons: list[str] = []
        if not self.selected_cameras:
            reasons.append(
                "the eight benchmark cameras have not been frozen "
                "(run resolve_sources.py, then select_cameras.py)"
            )
            return reasons
        if len(self.selected_cameras) != self.target_cameras:
            reasons.append(
                f"{len(self.selected_cameras)} cameras are frozen, "
                f"but exactly {self.target_cameras} are required"
            )
        if self.cameras_missing:
            reasons.append(
                "no frames acquired for selected cameras: "
                + ", ".join(self.cameras_missing)
            )
        if self.cameras_below_quota:
            listed = ", ".join(
                f"{camera} ({count}/{self.frames_per_camera_required})"
                for camera, count in sorted(self.cameras_below_quota.items())
            )
            reasons.append(f"selected cameras below the per-camera quota: {listed}")
        if self.cameras_unexpected:
            reasons.append(
                "frames present from cameras outside the frozen eight: "
                + ", ".join(self.cameras_unexpected)
            )
        return reasons


def coverage(
    records: Iterable[FrameRecord],
    *,
    target_frames: int,
    target_cameras: int,
    selected_cameras: Sequence[str] = (),
    frames_per_camera: int = 0,
) -> ManifestCoverage:
    """Measure the sample against the preregistered structure.

    Frames are counted **unique by content hash within a camera**: Madrid
    republishes a capture roughly every five minutes, so the same bytes can be
    fetched twice, and counting a byte-identical repeat towards the quota would
    inflate the sample without adding a single new observation.
    """
    materialised = list(records)
    unique_per_camera: dict[str, set[str]] = {}
    for record in materialised:
        unique_per_camera.setdefault(record.camera_id, set()).add(record.sha256)
    per_camera = {
        camera: len(hashes) for camera, hashes in unique_per_camera.items()
    }

    selected = tuple(selected_cameras)
    missing = tuple(camera for camera in selected if per_camera.get(camera, 0) == 0)
    below = {
        camera: per_camera[camera]
        for camera in selected
        if 0 < per_camera.get(camera, 0) < frames_per_camera
    }
    unexpected = tuple(
        sorted(camera for camera in per_camera if selected and camera not in selected)
    )

    return ManifestCoverage(
        frames=len(materialised),
        cameras=len(per_camera),
        target_frames=target_frames,
        target_cameras=target_cameras,
        frames_per_camera=dict(sorted(per_camera.items())),
        selected_cameras=selected,
        frames_per_camera_required=frames_per_camera,
        cameras_below_quota=below,
        cameras_missing=missing,
        cameras_unexpected=unexpected,
    )


# --------------------------------------------------------------------------
# Evaluation-set draw (preregistered, §10 of the protocol)
# --------------------------------------------------------------------------


def select_evaluation_set(
    records: Iterable[FrameRecord],
    *,
    per_camera: int,
    seed: int,
    selected_cameras: Sequence[str],
) -> list[str]:
    """Draw the frozen evaluation set: ``per_camera`` images from each of the
    frozen benchmark cameras.

    The draw is stratified over **exactly** ``selected_cameras`` — the eight
    frozen before any inference — not over whatever cameras happen to appear in
    the manifest. Frames from an unselected camera are ignored entirely, so a
    stray acquisition cannot dilute or enlarge the evaluation set.

    The draw is fully reproducible: cameras are visited in the order they were
    frozen, each camera's frames are sorted by ``image_id``, and a single
    :class:`random.Random` seeded with ``seed`` samples them. Given the same
    manifest, the same frozen cameras and the same seed, the result is
    byte-identical on any machine.

    Because the draw is a function of the *whole* manifest, adding frames later
    changes the selection. The manifest must therefore be frozen before this is
    called, and the caller is expected to store the manifest's SHA-256 alongside
    the drawn ids so that drift is detectable rather than silent.

    A camera with fewer than ``per_camera`` frames contributes all of them. The
    shortfall is reported by the caller and forces NO VERDICT; it is never
    back-filled from another camera, which would break stratification while
    leaving the headline count looking correct.
    """
    import random

    rng = random.Random(seed)
    grouped = group_by_camera(records)
    selected: list[str] = []
    for camera_id in selected_cameras:
        image_ids = sorted(
            record.image_id for record in grouped.get(camera_id, [])
        )
        take = min(per_camera, len(image_ids))
        selected.extend(rng.sample(image_ids, take))
    return selected


@dataclass(frozen=True)
class EvaluationSetIntegrity:
    """Whether the drawn evaluation set matches the preregistered structure."""

    size: int
    required_size: int
    per_camera: dict[str, int]
    required_per_camera: int
    selected_cameras: tuple[str, ...]
    required_cameras: int

    @property
    def is_exact(self) -> bool:
        """True only for exactly N images from each of exactly the frozen eight."""
        if len(self.selected_cameras) != self.required_cameras:
            return False
        if self.size != self.required_size:
            return False
        return all(
            self.per_camera.get(camera, 0) == self.required_per_camera
            for camera in self.selected_cameras
        )

    def shortfalls(self) -> list[str]:
        reasons: list[str] = []
        if len(self.selected_cameras) != self.required_cameras:
            reasons.append(
                f"{len(self.selected_cameras)} benchmark cameras are frozen, "
                f"but the gate requires exactly {self.required_cameras}"
            )
        if self.size != self.required_size:
            reasons.append(
                f"the evaluation set holds {self.size} images, but the gate "
                f"requires exactly {self.required_size}"
            )
        short = {
            camera: self.per_camera.get(camera, 0)
            for camera in self.selected_cameras
            if self.per_camera.get(camera, 0) != self.required_per_camera
        }
        if short:
            listed = ", ".join(
                f"{camera} ({count}/{self.required_per_camera})"
                for camera, count in sorted(short.items())
            )
            reasons.append(f"cameras not contributing exactly their quota: {listed}")
        return reasons


def evaluation_set_integrity(
    image_ids: Sequence[str],
    *,
    camera_of_image: Mapping[str, str],
    selected_cameras: Sequence[str],
    required_per_camera: int,
    required_cameras: int,
) -> EvaluationSetIntegrity:
    """Check a drawn evaluation set against the frozen structure."""
    per_camera: dict[str, int] = {}
    for image_id in image_ids:
        camera = camera_of_image.get(image_id, "")
        per_camera[camera] = per_camera.get(camera, 0) + 1
    return EvaluationSetIntegrity(
        size=len(image_ids),
        required_size=required_cameras * required_per_camera,
        per_camera=per_camera,
        required_per_camera=required_per_camera,
        selected_cameras=tuple(selected_cameras),
        required_cameras=required_cameras,
    )
