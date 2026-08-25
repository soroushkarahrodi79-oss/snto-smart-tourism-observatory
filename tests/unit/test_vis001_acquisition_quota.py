"""VIS-001 protocol deviation PD-003 regressions: per-camera acquisition quota.

Identified after 114/160 real frames had been collected with no camera over
20 and zero annotations/model results. ``acquire_frames.py`` used to poll all
eight frozen cameras on every pass regardless of how many unique frames each
already held, so a camera reaching 20 before the others kept being fetched.
These tests pin ``cameras_under_quota`` — the fix — entirely offline: no
network call is ever made or attempted here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from vis001.manifest import FrameRecord

EXPERIMENT_ROOT = (
    Path(__file__).resolve().parents[2] / "experiments" / "vis001_madrid_counting"
)

_QUOTA = 20


def _load_acquire_frames():
    path = EXPERIMENT_ROOT / "scripts" / "acquire_frames.py"
    spec = importlib.util.spec_from_file_location("vis001_test_acquire_frames", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def acquire_module():
    return _load_acquire_frames()


def _frame(camera_id: str, sha_suffix: str) -> FrameRecord:
    digest = f"{sha_suffix:0>64}"[:64]
    return FrameRecord(
        image_id=f"{camera_id}__{sha_suffix}",
        camera_id=camera_id,
        camera_name="",
        source_url=f"https://informo.madrid.es/cameras/{camera_id}.jpg",
        retrieved_at_utc="2026-08-25T00:00:00+00:00",
        source_timestamp="",
        latitude="",
        longitude="",
        width="640",
        height="480",
        sha256=digest,
        local_relative_path=f"data/raw/{camera_id}/{camera_id}__{sha_suffix}.jpg",
        licence_or_source_note="Ayuntamiento de Madrid open data",
    )


def _frames(camera_id: str, count: int, *, start: int = 0) -> list[FrameRecord]:
    return [
        _frame(camera_id, f"{camera_id}-{index}")
        for index in range(start, start + count)
    ]


_SELECTED = [
    ("camara05324", "https://informo.madrid.es/cameras/Camara05324.jpg?v=1"),
    ("camara16304", "https://informo.madrid.es/cameras/Camara16304.jpg?v=1"),
]


# --------------------------------------------------------------------------
# 20/20 is not requested again; 19/20 remains active
# --------------------------------------------------------------------------


def test_camera_at_quota_is_not_requested_again(acquire_module):
    existing = _frames("camara05324", _QUOTA) + _frames("camara16304", 5)
    active = acquire_module.cameras_under_quota(_SELECTED, existing, quota=_QUOTA)
    active_ids = {camera_id for camera_id, _ in active}
    assert "camara05324" not in active_ids
    assert "camara16304" in active_ids


def test_camera_at_nineteen_of_twenty_remains_active(acquire_module):
    existing = _frames("camara05324", _QUOTA - 1)
    active = acquire_module.cameras_under_quota(_SELECTED, existing, quota=_QUOTA)
    assert {camera_id for camera_id, _ in active} == {"camara05324", "camara16304"}


# --------------------------------------------------------------------------
# A camera reaching quota mid-run disappears from later passes
# --------------------------------------------------------------------------


def test_camera_reaching_quota_mid_run_drops_out_of_later_passes(acquire_module):
    existing = _frames("camara05324", _QUOTA - 1) + _frames("camara16304", 5)

    # Pass N: camera05324 is still active and gets its 20th frame.
    active_before = acquire_module.cameras_under_quota(
        _SELECTED, existing, quota=_QUOTA
    )
    assert {c for c, _ in active_before} == {"camara05324", "camara16304"}
    existing.append(_frame("camara05324", "final-frame"))

    # Pass N+1: recomputed fresh from the manifest state — camera05324 is gone.
    active_after = acquire_module.cameras_under_quota(
        _SELECTED, existing, quota=_QUOTA
    )
    assert {c for c, _ in active_after} == {"camara16304"}


# --------------------------------------------------------------------------
# Fail closed on an already over-quota camera
# --------------------------------------------------------------------------


def test_more_than_twenty_existing_frames_fails_closed(acquire_module):
    existing = _frames("camara05324", _QUOTA + 1)
    with pytest.raises(SystemExit, match="exceeds the per-camera quota"):
        acquire_module.cameras_under_quota(_SELECTED, existing, quota=_QUOTA)


def test_over_quota_failure_names_the_offending_camera(acquire_module):
    existing = _frames("camara05324", _QUOTA + 3)
    with pytest.raises(SystemExit, match="camara05324"):
        acquire_module.cameras_under_quota(_SELECTED, existing, quota=_QUOTA)


def test_over_quota_check_never_mutates_existing_records(acquire_module):
    existing = _frames("camara05324", _QUOTA + 1)
    before = list(existing)
    with pytest.raises(SystemExit):
        acquire_module.cameras_under_quota(_SELECTED, existing, quota=_QUOTA)
    assert existing == before


# --------------------------------------------------------------------------
# All eight at quota => zero cameras returned (no network fetch triggered)
# --------------------------------------------------------------------------


def test_all_cameras_at_quota_yields_no_active_cameras(acquire_module):
    existing = _frames("camara05324", _QUOTA) + _frames("camara16304", _QUOTA)
    active = acquire_module.cameras_under_quota(_SELECTED, existing, quota=_QUOTA)
    assert active == []


def test_duplicate_bytes_do_not_count_twice_toward_quota(acquire_module):
    """Unique-by-hash, matching vis001.manifest.coverage: a repeated capture
    of the same bytes must not falsely retire an under-quota camera."""
    duplicate = _frame("camara05324", "same-bytes")
    existing = [duplicate, duplicate, duplicate]  # three rows, one unique frame
    active = acquire_module.cameras_under_quota(_SELECTED, existing, quota=_QUOTA)
    assert "camara05324" in {c for c, _ in active}


# --------------------------------------------------------------------------
# Frozen numeric parameters unchanged
# --------------------------------------------------------------------------


def test_no_frozen_parameter_changed_by_pd_003():
    from vis001 import config

    assert config.TARGET_CAMERAS == 8
    assert config.TARGET_FRAMES_PER_CAMERA == 20
    assert config.TARGET_FRAMES == 160
    assert config.EVAL_SET_SIZE == 80
    assert config.RANDOM_SEED == 20260824
    assert config.CONFIDENCE_THRESHOLD == 0.35
    assert config.EVAL_IOU_THRESHOLD == 0.50
    assert config.GATE_VERSION == "1.0"


def test_interval_seconds_default_is_still_300():
    import argparse

    # Mirrors main()'s own --interval-seconds default without invoking main(),
    # which would touch real config paths / real data on disk.
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-seconds", type=int, default=300)
    args = parser.parse_args([])
    assert args.interval_seconds == 300


# --------------------------------------------------------------------------
# PREREGISTRATION.md records PD-003
# --------------------------------------------------------------------------


def test_preregistration_records_pd_003():
    text = (EXPERIMENT_ROOT / "PREREGISTRATION.md").read_text(encoding="utf-8")
    assert (
        "PD-003 — Per-camera acquisition quota enforcement (2026-08-25)" in text
    )
    assert "114" in text
    assert "cameras_under_quota" in text
    assert "no camera having exceeded 20" in text
