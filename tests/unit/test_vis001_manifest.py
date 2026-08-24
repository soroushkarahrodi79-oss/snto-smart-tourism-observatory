"""VIS-001 frame manifest: validation, round-tripping and the frozen eval draw."""

from __future__ import annotations

from vis001.config import EVAL_IMAGES_PER_CAMERA, RANDOM_SEED
from vis001.manifest import (
    MANIFEST_COLUMNS,
    FrameRecord,
    coverage,
    group_by_camera,
    read_manifest,
    select_evaluation_set,
    sha256_of,
    sha256_of_bytes,
    validate_manifest,
    write_empty_manifest,
    write_manifest,
)

_HASH_A = "a" * 64
_HASH_B = "b" * 64


def _record(**overrides) -> FrameRecord:
    base = {
        "image_id": "cam01__20260824T120000Z",
        "camera_id": "cam01",
        "camera_name": "",
        "source_url": "https://informo.madrid.es/cameras/cam01.jpg",
        "retrieved_at_utc": "2026-08-24T12:00:00+00:00",
        "source_timestamp": "",
        "latitude": "40.4168",
        "longitude": "-3.7038",
        "width": "640",
        "height": "480",
        "sha256": _HASH_A,
        "local_relative_path": "data/raw/cam01/cam01__20260824T120000Z.jpg",
        "licence_or_source_note": "Ayuntamiento de Madrid open data",
    }
    base.update(overrides)
    return FrameRecord(**base)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def test_valid_record_has_no_problems():
    assert validate_manifest([_record()]) == []


def test_optional_metadata_may_be_empty():
    """Absent is honest; the source simply does not publish these."""
    record = _record(camera_name="", source_timestamp="", latitude="", longitude="")
    assert validate_manifest([record]) == []


def test_missing_image_id_is_rejected():
    problems = validate_manifest([_record(image_id="")])
    assert any("empty image_id" in problem for problem in problems)


def test_duplicate_image_id_is_rejected():
    problems = validate_manifest([_record(), _record(sha256=_HASH_B)])
    assert any("duplicate image_id" in problem for problem in problems)


def test_duplicate_image_bytes_are_flagged_as_no_new_evidence():
    problems = validate_manifest(
        [_record(), _record(image_id="cam01__20260824T120500Z")]
    )
    assert any("duplicate frame" in problem for problem in problems)


def test_non_positive_dimensions_are_rejected():
    problems = validate_manifest([_record(width="0", height="-5")])
    assert any("width" in problem for problem in problems)
    assert any("height" in problem for problem in problems)


def test_malformed_hash_is_rejected():
    problems = validate_manifest([_record(sha256="deadbeef")])
    assert any("sha256" in problem for problem in problems)


def test_uppercase_hash_is_rejected():
    problems = validate_manifest([_record(sha256="A" * 64)])
    assert any("sha256" in problem for problem in problems)


def test_out_of_range_coordinates_are_rejected():
    problems = validate_manifest([_record(latitude="999", longitude="-500")])
    assert any("latitude out of range" in problem for problem in problems)
    assert any("longitude out of range" in problem for problem in problems)


def test_non_numeric_coordinate_is_rejected():
    """A malformed coordinate is worse than an absent one."""
    problems = validate_manifest([_record(latitude="north")])
    assert any("latitude not numeric" in problem for problem in problems)


def test_missing_provenance_fields_are_rejected():
    problems = validate_manifest([_record(source_url="", licence_or_source_note="")])
    assert any("empty source_url" in problem for problem in problems)
    assert any("empty licence_or_source_note" in problem for problem in problems)


# --------------------------------------------------------------------------
# Round trip
# --------------------------------------------------------------------------


def test_manifest_round_trips_through_csv(tmp_path):
    path = tmp_path / "sample_manifest.csv"
    records = [
        _record(),
        _record(image_id="cam02__x", camera_id="cam02", sha256=_HASH_B),
    ]
    assert write_manifest(path, records) == 2
    assert read_manifest(path) == records


def test_empty_manifest_is_header_only(tmp_path):
    path = tmp_path / "sample_manifest.csv"
    write_empty_manifest(path)
    assert path.read_text(encoding="utf-8").strip() == ",".join(MANIFEST_COLUMNS)
    assert read_manifest(path) == []


def test_sha256_helpers_agree(tmp_path):
    payload = b"not really a jpeg"
    path = tmp_path / "frame.jpg"
    path.write_bytes(payload)
    assert sha256_of(path) == sha256_of_bytes(payload)


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------


def test_coverage_reports_incompleteness_honestly():
    records = [
        _record(
            image_id=f"cam0{c}__{i}",
            camera_id=f"cam0{c}",
            sha256=f"{c}{i}" + "0" * 62,
        )
        for c in range(1, 3)
        for i in range(3)
    ]
    state = coverage(
        records,
        target_frames=160,
        target_cameras=8,
        selected_cameras=[f"cam0{c}" for c in range(1, 3)],
        frames_per_camera=20,
    )
    assert not state.is_complete
    assert state.frames == 6
    assert state.cameras == 2
    assert "TARGET SAMPLE NOT YET COMPLETE" in state.summary()


def test_coverage_reports_completeness():
    records = [
        _record(
            image_id=f"c{c}_{i}",
            camera_id=f"c{c}",
            sha256=f"{c:02d}{i:02d}" + "0" * 60,
        )
        for c in range(8)
        for i in range(20)
    ]
    state = coverage(
        records,
        target_frames=160,
        target_cameras=8,
        selected_cameras=[f"c{c}" for c in range(8)],
        frames_per_camera=20,
    )
    assert state.is_complete
    assert state.summary().startswith("COMPLETE")


def test_group_by_camera_preserves_manifest_order():
    a = _record(image_id="a", camera_id="c1", sha256="1" + "0" * 63)
    b = _record(image_id="b", camera_id="c1", sha256="2" + "0" * 63)
    grouped = group_by_camera([a, b])
    assert [record.image_id for record in grouped["c1"]] == ["a", "b"]


# --------------------------------------------------------------------------
# Frozen evaluation-set draw
# --------------------------------------------------------------------------


def _sample(cameras: int = 8, per_camera: int = 20) -> list[FrameRecord]:
    return [
        _record(
            image_id=f"cam{c:02d}__frame{i:02d}",
            camera_id=f"cam{c:02d}",
            sha256=f"{c:02d}{i:02d}" + "0" * 60,
        )
        for c in range(cameras)
        for i in range(per_camera)
    ]


def _camera_ids(cameras: int = 8) -> list[str]:
    return [f"cam{c:02d}" for c in range(cameras)]


def test_eval_draw_is_stratified_by_camera():
    selected = select_evaluation_set(
        _sample(),
        per_camera=EVAL_IMAGES_PER_CAMERA,
        seed=RANDOM_SEED,
        selected_cameras=_camera_ids(),
    )
    assert len(selected) == 80
    per_camera = {}
    for image_id in selected:
        per_camera.setdefault(image_id.split("__")[0], []).append(image_id)
    assert len(per_camera) == 8
    assert all(len(ids) == EVAL_IMAGES_PER_CAMERA for ids in per_camera.values())


def test_eval_draw_is_reproducible():
    records = _sample()
    kwargs = dict(per_camera=10, seed=RANDOM_SEED, selected_cameras=_camera_ids())
    assert select_evaluation_set(records, **kwargs) == select_evaluation_set(
        records, **kwargs
    )


def test_eval_draw_is_independent_of_manifest_row_order():
    """Re-ordering rows must not silently change what is being evaluated."""
    records = _sample()
    kwargs = dict(per_camera=10, seed=RANDOM_SEED, selected_cameras=_camera_ids())
    forward = select_evaluation_set(records, **kwargs)
    backward = select_evaluation_set(list(reversed(records)), **kwargs)
    assert sorted(forward) == sorted(backward)


def test_eval_draw_selects_only_real_image_ids():
    records = _sample()
    known = {record.image_id for record in records}
    drawn = select_evaluation_set(
        records, per_camera=10, seed=RANDOM_SEED, selected_cameras=_camera_ids()
    )
    assert set(drawn) <= known


def test_a_different_seed_gives_a_different_draw():
    records = _sample()
    cameras = _camera_ids()
    assert select_evaluation_set(
        records, per_camera=10, seed=RANDOM_SEED, selected_cameras=cameras
    ) != select_evaluation_set(
        records, per_camera=10, seed=RANDOM_SEED + 1, selected_cameras=cameras
    )


def test_short_camera_contributes_everything_it_has_without_backfilling():
    """Stratification is preserved: a shortfall stays a shortfall."""
    records = _sample(cameras=2, per_camera=20)[:20] + [
        _record(image_id="cam09__only", camera_id="cam09", sha256="9" * 64)
    ]
    selected = select_evaluation_set(
        records,
        per_camera=10,
        seed=RANDOM_SEED,
        selected_cameras=["cam00", "cam09"],
    )
    assert "cam09__only" in selected
    assert sum(1 for image_id in selected if image_id.startswith("cam09")) == 1
