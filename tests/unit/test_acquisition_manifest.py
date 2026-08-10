"""Paper-1 satellite acquisition manifest — schema, lifecycle, round-trip (B-06)."""
from __future__ import annotations

import json

import pytest

from src.validation import (
    AcquisitionManifest,
    ManifestStatus,
    SCL_EXCLUDE_BASELINE,
    SCL_EXCLUDE_PLOT_EXTRACTION,
    check_against_extraction,
    load_manifest,
    new_planned_manifest,
    validate_manifest,
    write_manifest,
)
from src.validation.acquisition_manifest import (
    DEFAULT_CLOUD_THRESHOLD_PCT,
    DEFAULT_COMPOSITE_METHOD,
    DEFAULT_MAX_OFFSET_DAYS_MAX,
    DEFAULT_MAX_OFFSET_DAYS_PRIMARY,
    DEFAULT_MIN_SCENES_IN_COMPOSITE,
    DEFAULT_TILE,
    DEFAULT_VALID_PIXEL_FLAG_PCT,
    DEFAULT_VALID_PIXEL_MIN_PCT,
)


# ── Frozen matching-plan constants (SATELLITE_FIELD_MATCHING_PLAN.md §2) ───

def test_defaults_match_the_matching_plan():
    assert DEFAULT_TILE == "T30TVL"
    assert DEFAULT_CLOUD_THRESHOLD_PCT == 20.0
    assert DEFAULT_MIN_SCENES_IN_COMPOSITE == 3
    assert DEFAULT_COMPOSITE_METHOD == "median"
    assert DEFAULT_MAX_OFFSET_DAYS_PRIMARY == 15
    assert DEFAULT_MAX_OFFSET_DAYS_MAX == 30
    assert DEFAULT_VALID_PIXEL_MIN_PCT == 70.0
    assert DEFAULT_VALID_PIXEL_FLAG_PCT == 90.0


def test_scl_asymmetry_class_5_retained_at_plot_excluded_at_baseline():
    # The matching plan's deliberate asymmetry: bare/rock (SCL 5) biases the
    # scene-level "healthy" baseline if included, but is real degradation
    # signal at a trail plot, so it must NOT be excluded there.
    assert 5 in SCL_EXCLUDE_BASELINE
    assert 5 not in SCL_EXCLUDE_PLOT_EXTRACTION
    # Every other masked class stays symmetric.
    assert set(SCL_EXCLUDE_BASELINE) - {5} == set(SCL_EXCLUDE_PLOT_EXTRACTION)


# ── new_planned_manifest ────────────────────────────────────────────────────

def test_new_planned_manifest_has_no_window_or_scenes():
    m = new_planned_manifest()
    assert m.status is ManifestStatus.PLANNED
    assert m.window_start is None
    assert m.window_end is None
    assert m.scene_ids == ()
    assert m.sensor_mix == ()


def test_new_planned_manifest_is_valid():
    assert validate_manifest(new_planned_manifest()) == []


def test_new_planned_manifest_records_generation_metadata():
    m = new_planned_manifest(notes="pilot draft")
    assert m.generated_at  # non-empty ISO timestamp
    assert m.notes == "pilot draft"
    # commit_hash is best-effort (git may be unavailable in some sandboxes);
    # it must never be a fabricated placeholder, only real or empty.
    assert m.commit_hash == "" or len(m.commit_hash) >= 4


# ── validate_manifest — lifecycle gating ────────────────────────────────────

def _windowed(status: ManifestStatus, **kw) -> AcquisitionManifest:
    base = dict(status=status, window_start="2027-06-15", window_end="2027-07-06")
    base.update(kw)
    return AcquisitionManifest(**base)


def test_window_defined_without_window_is_invalid():
    m = AcquisitionManifest(status=ManifestStatus.WINDOW_DEFINED)
    errors = validate_manifest(m)
    assert any("window_start/window_end" in e for e in errors)


def test_window_defined_with_window_is_valid():
    assert validate_manifest(_windowed(ManifestStatus.WINDOW_DEFINED)) == []


def test_window_start_after_end_is_invalid():
    m = AcquisitionManifest(
        status=ManifestStatus.WINDOW_DEFINED,
        window_start="2027-07-06", window_end="2027-06-15",
    )
    errors = validate_manifest(m)
    assert any("window_start must be before window_end" in e for e in errors)


def test_scenes_identified_requires_scene_ids_and_sensor_mix():
    m = _windowed(ManifestStatus.SCENES_IDENTIFIED)
    errors = validate_manifest(m)
    assert any("scene_ids" in e for e in errors)
    assert any("sensor_mix" in e for e in errors)


def test_scenes_identified_below_min_scenes_is_invalid():
    m = _windowed(
        ManifestStatus.SCENES_IDENTIFIED,
        scene_ids=("S2B_MSIL2A_20270620T110629",),  # only 1, min is 3
        sensor_mix=("S2B",),
    )
    errors = validate_manifest(m)
    assert any("min_scenes_in_composite" in e for e in errors)


def test_scenes_identified_with_enough_scenes_is_valid():
    m = _windowed(
        ManifestStatus.SCENES_IDENTIFIED,
        scene_ids=(
            "S2B_MSIL2A_20270620T110629",
            "S2A_MSIL2A_20270625T110701",
            "S2B_MSIL2A_20270630T110629",
        ),
        sensor_mix=("S2A", "S2B"),
    )
    assert validate_manifest(m) == []


@pytest.mark.parametrize("bad_field,bad_value", [
    ("cloud_threshold_pct", 150.0),
    ("cloud_threshold_pct", -1.0),
    ("valid_pixel_min_pct", 200.0),
])
def test_out_of_range_fields_are_invalid(bad_field, bad_value):
    m = AcquisitionManifest(status=ManifestStatus.PLANNED, **{bad_field: bad_value})
    errors = validate_manifest(m)
    assert any(bad_field in e for e in errors)


def test_valid_pixel_flag_below_min_is_invalid():
    m = AcquisitionManifest(
        status=ManifestStatus.PLANNED,
        valid_pixel_min_pct=90.0, valid_pixel_flag_pct=70.0,
    )
    errors = validate_manifest(m)
    assert any("valid_pixel_flag_pct" in e for e in errors)


def test_max_offset_max_below_primary_is_invalid():
    m = AcquisitionManifest(
        status=ManifestStatus.PLANNED,
        max_offset_days_primary=30, max_offset_days_max=15,
    )
    errors = validate_manifest(m)
    assert any("max_offset_days_max" in e for e in errors)


def test_scl_class_5_misconfiguration_is_caught_even_in_planned_stage():
    # The asymmetry check applies regardless of lifecycle stage — a manifest
    # that gets this wrong must never validate, planned or not.
    m = AcquisitionManifest(
        status=ManifestStatus.PLANNED,
        scl_exclude_plot_extraction=(3, 5, 6, 8, 9, 10, 11),  # wrongly includes 5
    )
    errors = validate_manifest(m)
    assert any("RETAINED at plot extraction" in e for e in errors)

    m2 = AcquisitionManifest(
        status=ManifestStatus.PLANNED,
        scl_exclude_baseline=(3, 6, 8, 9, 10, 11),  # wrongly omits 5
    )
    errors2 = validate_manifest(m2)
    assert any("excluded from the scene-level" in e for e in errors2)


# ── round-trip ───────────────────────────────────────────────────────────

def test_write_then_load_round_trips(tmp_path):
    m = new_planned_manifest(notes="round-trip test")
    path = tmp_path / "manifest.json"
    write_manifest(m, path)
    loaded = load_manifest(path)
    assert loaded == m


def test_written_manifest_is_valid_json_with_status_as_string(tmp_path):
    m = new_planned_manifest()
    path = tmp_path / "manifest.json"
    write_manifest(m, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["status"] == "planned"
    assert isinstance(raw["scene_ids"], list)


def test_write_manifest_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "manifest.json"
    write_manifest(new_planned_manifest(), path)
    assert path.exists()


# ── check_against_extraction ────────────────────────────────────────────

def test_check_against_extraction_exact_match():
    m = _windowed(
        ManifestStatus.SCENES_IDENTIFIED,
        scene_ids=("A", "B", "C"), sensor_mix=("S2A",),
    )
    report = check_against_extraction(m, ["A", "B", "C"])
    assert report.ok is True
    assert report.declared_not_used == ()
    assert report.used_not_declared == ()


def test_check_against_extraction_detects_missing_and_extra():
    m = _windowed(
        ManifestStatus.SCENES_IDENTIFIED,
        scene_ids=("A", "B", "C"), sensor_mix=("S2A",),
    )
    report = check_against_extraction(m, ["A", "B", "D"])
    assert report.ok is False
    assert report.declared_not_used == ("C",)
    assert report.used_not_declared == ("D",)
    assert "MISMATCH" in report.summary


def test_check_against_extraction_order_independent():
    m = _windowed(
        ManifestStatus.SCENES_IDENTIFIED,
        scene_ids=("A", "B", "C"), sensor_mix=("S2A",),
    )
    assert check_against_extraction(m, ["C", "A", "B"]).ok is True


# ── the committed draft manifest itself ─────────────────────────────────

def test_committed_manifest_exists_and_is_valid():
    from pathlib import Path
    path = (Path(__file__).resolve().parents[2]
            / "clean_assets" / "paper1" / "acquisition_manifest.json")
    assert path.exists(), "run scripts/paper1/generate_acquisition_manifest.py --init"
    m = load_manifest(path)
    assert validate_manifest(m) == []


def test_committed_manifest_is_honestly_planned_not_populated():
    from pathlib import Path
    path = (Path(__file__).resolve().parents[2]
            / "clean_assets" / "paper1" / "acquisition_manifest.json")
    m = load_manifest(path)
    # No field campaign has run yet (Data Acquisition Triage open item 4) —
    # the committed manifest must not claim otherwise.
    assert m.status is ManifestStatus.PLANNED
    assert m.scene_ids == ()
    assert m.window_start is None
