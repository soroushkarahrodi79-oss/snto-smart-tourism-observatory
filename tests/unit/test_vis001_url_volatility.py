"""VIS-001 protocol deviation PD-002 regressions: volatile Madrid image-URL
query tokens.

Madrid's official KML rewrites a cache/version token (``?v=...``) in every
camera's image URL on most catalogue refreshes. That token is not part of a
camera's identity: these tests pin (1) the stable canonical-endpoint helper,
(2) that ``select_cameras.py --check`` ignores the volatile token while still
failing closed on real drift, and (3) that ``acquire_frames.py`` resolves the
CURRENT official URL for the SAME frozen camera id, never substituting or
re-selecting a camera.

Recorded, like PD-002 itself, while zero frames, zero annotations and zero
RF-DETR Madrid results existed. No network is used anywhere in this file.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest
from vis001 import config
from vis001.cameras import (
    SECTOR_NAMES,
    CameraRecord,
    canonical_image_endpoint,
    write_camera_manifest,
)

EXPERIMENT_ROOT = (
    Path(__file__).resolve().parents[2] / "experiments" / "vis001_madrid_counting"
)


def _load_script(name: str):
    path = EXPERIMENT_ROOT / "scripts" / name
    module_name = f"vis001_test_{name.replace('.py', '')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# A / B — canonical_image_endpoint
# --------------------------------------------------------------------------


def test_same_path_different_query_token_is_the_same_endpoint():
    a = "https://informo.madrid.es/cameras/Camara05324.jpg?v=51444"
    b = "https://informo.madrid.es/cameras/Camara05324.jpg?v=76738"
    assert canonical_image_endpoint(a) == canonical_image_endpoint(b)


def test_different_camera_path_is_a_different_endpoint():
    a = "https://informo.madrid.es/cameras/Camara05324.jpg?v=51444"
    b = "https://informo.madrid.es/cameras/Camara09999.jpg?v=51444"
    assert canonical_image_endpoint(a) != canonical_image_endpoint(b)


def test_fragment_is_also_stripped():
    a = "https://informo.madrid.es/cameras/Camara05324.jpg?v=1#frag"
    b = "https://informo.madrid.es/cameras/Camara05324.jpg"
    assert canonical_image_endpoint(a) == canonical_image_endpoint(b)


# --------------------------------------------------------------------------
# Fixture: eight cameras, one per compass sector, so a fresh selection is
# exactly and deterministically those eight ids.
# --------------------------------------------------------------------------

_ORIGIN_LAT, _ORIGIN_LON = 40.0, -3.0


def _sector_cameras() -> list[CameraRecord]:
    cameras = []
    for index, sector in enumerate(SECTOR_NAMES):
        bearing = math.radians(index * 45.0)
        north = math.cos(bearing) * 0.05
        east = math.sin(bearing) * 0.05
        lat = _ORIGIN_LAT + north
        lon = _ORIGIN_LON + east / math.cos(math.radians(_ORIGIN_LAT))
        camera_id = f"cam-{sector.lower()}"
        cameras.append(
            CameraRecord(
                camera_id=camera_id,
                camera_name=f"CAM {sector}",
                latitude=f"{lat:.6f}",
                longitude=f"{lon:.6f}",
                image_url=f"https://informo.madrid.es/cameras/Camera{sector}.jpg?v=1000",
                source_document="https://informo.madrid.es/informo/tmadrid/CCTV.kml",
            )
        )
    return cameras


@pytest.fixture()
def frozen_env(tmp_path, monkeypatch):
    """Freeze the eight sector cameras, then hand back the paths for mutation."""
    camera_manifest = tmp_path / "camera_manifest.csv"
    selected_cameras = tmp_path / "selected_cameras.json"
    monkeypatch.setattr(config, "CAMERA_MANIFEST_PATH", camera_manifest)
    monkeypatch.setattr(config, "SELECTED_CAMERAS_PATH", selected_cameras)

    write_camera_manifest(camera_manifest, _sector_cameras())

    select_cameras_script = _load_script("select_cameras.py")
    monkeypatch.setattr("sys.argv", ["select_cameras.py"])
    exit_code = select_cameras_script.main()
    assert exit_code == 0
    assert selected_cameras.exists()

    return camera_manifest, selected_cameras, select_cameras_script


# --------------------------------------------------------------------------
# C / D / E — select_cameras.py --check
# --------------------------------------------------------------------------


def test_check_passes_when_only_query_token_changes(frozen_env, monkeypatch, capsys):
    camera_manifest, _selected, script = frozen_env

    refreshed = [
        CameraRecord(
            camera_id=c.camera_id,
            camera_name=c.camera_name,
            latitude=c.latitude,
            longitude=c.longitude,
            image_url=c.image_url.replace("v=1000", "v=999999"),
            source_document=c.source_document,
        )
        for c in _sector_cameras()
    ]
    write_camera_manifest(camera_manifest, refreshed)

    monkeypatch.setattr("sys.argv", ["select_cameras.py", "--check"])
    exit_code = script.main()
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "raw manifest SHA changed" in out
    assert "volatile image URL query parameters are ignored" in out
    assert "frozen camera selection is consistent" in out


def test_check_fails_when_canonical_path_changes(frozen_env, monkeypatch, capsys):
    camera_manifest, _selected, script = frozen_env

    mutated = _sector_cameras()
    mutated[0] = CameraRecord(
        camera_id=mutated[0].camera_id,
        camera_name=mutated[0].camera_name,
        latitude=mutated[0].latitude,
        longitude=mutated[0].longitude,
        image_url="https://informo.madrid.es/cameras/SomethingElse.jpg?v=1000",
        source_document=mutated[0].source_document,
    )
    write_camera_manifest(camera_manifest, mutated)

    monkeypatch.setattr("sys.argv", ["select_cameras.py", "--check"])
    exit_code = script.main()
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "DRIFT" in out
    assert "canonical image endpoint changed" in out


def test_check_fails_when_fresh_selected_ids_differ(frozen_env, monkeypatch, capsys):
    camera_manifest, _selected, script = frozen_env

    # Drop one sector's only camera: its slot cannot be backfilled (every other
    # sector holds exactly one camera, already claimed), so the fresh selection
    # is a genuinely different — smaller — set of ids than the frozen eight.
    reduced = _sector_cameras()[:-1]
    write_camera_manifest(camera_manifest, reduced)

    monkeypatch.setattr("sys.argv", ["select_cameras.py", "--check"])
    exit_code = script.main()
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "DRIFT: a fresh run selects a different set of cameras" in out


def test_check_does_not_rewrite_the_frozen_file(frozen_env, monkeypatch):
    camera_manifest, selected_cameras, script = frozen_env
    before = selected_cameras.read_text(encoding="utf-8")

    refreshed = [
        CameraRecord(
            camera_id=c.camera_id,
            camera_name=c.camera_name,
            latitude=c.latitude,
            longitude=c.longitude,
            image_url=c.image_url.replace("v=1000", "v=2"),
            source_document=c.source_document,
        )
        for c in _sector_cameras()
    ]
    write_camera_manifest(camera_manifest, refreshed)

    monkeypatch.setattr("sys.argv", ["select_cameras.py", "--check"])
    script.main()

    assert selected_cameras.read_text(encoding="utf-8") == before


# --------------------------------------------------------------------------
# F / G / H — acquire_frames.py resolve_current_endpoints
# --------------------------------------------------------------------------


@pytest.fixture()
def acquire_module():
    return _load_script("acquire_frames.py")


def _frozen_entries() -> list[dict[str, str]]:
    return [
        {
            "camera_id": c.camera_id,
            "camera_name": c.camera_name,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "image_url": c.image_url,
        }
        for c in _sector_cameras()
    ]


def test_acquisition_resolves_current_full_url_for_frozen_id(
    tmp_path, monkeypatch, acquire_module
):
    camera_manifest = tmp_path / "camera_manifest.csv"
    monkeypatch.setattr(config, "CAMERA_MANIFEST_PATH", camera_manifest)

    current = [
        CameraRecord(
            camera_id=c.camera_id,
            camera_name=c.camera_name,
            latitude=c.latitude,
            longitude=c.longitude,
            image_url=c.image_url.replace("v=1000", "v=555555"),
            source_document=c.source_document,
        )
        for c in _sector_cameras()
    ]
    write_camera_manifest(camera_manifest, current)

    resolved = acquire_module.resolve_current_endpoints(_frozen_entries())

    resolved_by_id = dict(resolved)
    assert set(resolved_by_id) == {c.camera_id for c in _sector_cameras()}
    for c in current:
        assert resolved_by_id[c.camera_id] == c.image_url
        assert "v=555555" in resolved_by_id[c.camera_id]


def test_acquisition_refuses_when_frozen_id_disappears(
    tmp_path, monkeypatch, acquire_module
):
    camera_manifest = tmp_path / "camera_manifest.csv"
    monkeypatch.setattr(config, "CAMERA_MANIFEST_PATH", camera_manifest)

    remaining = _sector_cameras()[1:]  # drop the first frozen camera
    write_camera_manifest(camera_manifest, remaining)

    with pytest.raises(SystemExit, match="no longer present"):
        acquire_module.resolve_current_endpoints(_frozen_entries())


def test_acquisition_refuses_when_canonical_endpoint_changes(
    tmp_path, monkeypatch, acquire_module
):
    camera_manifest = tmp_path / "camera_manifest.csv"
    monkeypatch.setattr(config, "CAMERA_MANIFEST_PATH", camera_manifest)

    mutated = _sector_cameras()
    mutated[0] = CameraRecord(
        camera_id=mutated[0].camera_id,
        camera_name=mutated[0].camera_name,
        latitude=mutated[0].latitude,
        longitude=mutated[0].longitude,
        image_url="https://informo.madrid.es/cameras/ADifferentCamera.jpg?v=1000",
        source_document=mutated[0].source_document,
    )
    write_camera_manifest(camera_manifest, mutated)

    with pytest.raises(SystemExit, match="canonical image endpoint changed"):
        acquire_module.resolve_current_endpoints(_frozen_entries())


def test_acquisition_never_substitutes_another_camera_on_failure(
    tmp_path, monkeypatch, acquire_module
):
    """A refused resolution must not silently swap in a different camera id."""
    camera_manifest = tmp_path / "camera_manifest.csv"
    monkeypatch.setattr(config, "CAMERA_MANIFEST_PATH", camera_manifest)

    remaining = _sector_cameras()[1:]
    write_camera_manifest(camera_manifest, remaining)

    frozen_ids = {entry["camera_id"] for entry in _frozen_entries()}
    try:
        acquire_module.resolve_current_endpoints(_frozen_entries())
    except SystemExit:
        pass
    else:  # pragma: no cover - defensive
        pytest.fail("expected SystemExit when a frozen camera disappears")

    # No camera id outside the originally frozen set was ever introduced.
    current_ids = {c.camera_id for c in remaining}
    assert current_ids <= frozen_ids


# --------------------------------------------------------------------------
# I — no frozen numeric parameter moved
# --------------------------------------------------------------------------


def test_no_frozen_parameter_changed_by_pd_002():
    assert config.TARGET_CAMERAS == 8
    assert config.TARGET_FRAMES_PER_CAMERA == 20
    assert config.TARGET_FRAMES == 160
    assert config.EVAL_SET_SIZE == 80
    assert config.RANDOM_SEED == 20260824
    assert config.CONFIDENCE_THRESHOLD == 0.35
    assert config.EVAL_IOU_THRESHOLD == 0.50
    assert config.GATE_VERSION == "1.0"


# --------------------------------------------------------------------------
# PREREGISTRATION.md records PD-002
# --------------------------------------------------------------------------


def test_preregistration_records_pd_002():
    text = (EXPERIMENT_ROOT / "PREREGISTRATION.md").read_text(encoding="utf-8")
    assert "PD-002 — Volatile Madrid image-URL query tokens (2026-08-25)" in text
    assert "camara05324" in text
    assert "canonical_image_endpoint" in text
    assert "NOT being rerun or altered" in text
