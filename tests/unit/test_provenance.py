"""F3 — Data provenance & confidence surfacing.

Phase 0.5C (audited PR 0.5.2) — provenance must degrade *honestly*, keeping four
orthogonal facts separate: derived-output availability, raw-source availability,
provenance completeness and local reproducibility. The state tests below are
deterministic (monkeypatched), so a fresh clone and CI exercise the same cases
regardless of whether this developer machine happens to have the raw ``.SAFE``
scenes on disk.
"""
from __future__ import annotations

import re

import pytest

from src.platform import provenance as prov_mod
from src.platform.provenance import (
    SceneReference,
    data_status_badge,
    detect_scene_dates,
    detect_scene_references,
    load_timeseries_coverage,
    snapshot_provenance,
    snapshot_status_badge,
)
from src.temporal import DataStatus, TrendReadiness

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STATUS_GREEN = "#0F6E56"  # the full-REAL badge colour (State A)

# Two real PNSG scenes (spring + summer), one from each Sentinel-2 unit.
_TWO_REFS = [
    SceneReference("S2A", "2025-08-10"),
    SceneReference("S2B", "2026-04-10"),
]


def _force_state(monkeypatch, *, refs, derived: bool) -> None:
    """Pin ``snapshot_provenance`` into a specific (raw, derived) world."""
    monkeypatch.setattr(prov_mod, "detect_scene_references", lambda _t: list(refs))
    monkeypatch.setattr(prov_mod, "_derived_output_available", lambda _k: derived)


# ── Badge legend (unchanged generic semantics) ───────────────────────────────

def test_badge_exists_for_every_status():
    for status in DataStatus:
        b = data_status_badge(status)
        assert b.emoji and b.label and b.color and b.caveat


def test_real_and_synthetic_badges_differ_in_caveat():
    real = data_status_badge(DataStatus.REAL)
    synth = data_status_badge(DataStatus.SYNTHETIC)
    assert "directa" in real.caveat.lower()
    assert "no usar" in synth.caveat.lower()


# ── Scene reference parsing (sensor ↔ date pairing preserved) ─────────────────

def test_detect_scene_references_pairs_sensor_and_date(tmp_path, monkeypatch):
    """The regex must capture both the sensor id and the acquisition date, paired."""
    folder = tmp_path / "PNSG"  # pnsg territory's raw_raster_folder
    folder.mkdir()
    for name in (
        "S2A_MSIL2A_20250810T110701_N0511_R137_T30TVL_20250810T151608.SAFE",
        "S2B_MSIL2A_20260410T110619_N0512_R137_T30TVL_20260410T133943.SAFE",
        "Datos complementarios",  # non-scene entry must be ignored
    ):
        (folder / name).mkdir()
    monkeypatch.setattr(prov_mod, "_RAW_RASTER_DIR", tmp_path)

    refs = detect_scene_references("pnsg")
    assert refs == [
        SceneReference("S2A", "2025-08-10"),
        SceneReference("S2B", "2026-04-10"),
    ]
    # Each sensor stays bound to its own date — no cross-pairing possible.
    assert {(r.sensor_id, r.acquisition_date) for r in refs} == {
        ("S2A", "2025-08-10"),
        ("S2B", "2026-04-10"),
    }
    # Compatibility wrapper still yields sorted ISO dates only.
    dates = detect_scene_dates("pnsg")
    assert dates == ["2025-08-10", "2026-04-10"]
    assert all(_ISO.match(d) for d in dates)


def test_detect_scene_references_empty_when_folder_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(prov_mod, "_RAW_RASTER_DIR", tmp_path)  # no PNSG subfolder
    assert detect_scene_references("pnsg") == []
    assert detect_scene_dates("pnsg") == []


# ── Three-state provenance regression (the core of PR 0.5.2) ─────────────────

@pytest.mark.parametrize(
    "refs, derived, exp_status, exp_derived, exp_raw, exp_complete, exp_repro, exp_n",
    [
        (_TWO_REFS, True, DataStatus.REAL, True, True, True, True, 2),
        ([], True, DataStatus.REAL, True, False, False, False, None),
        ([], False, DataStatus.MISSING, False, False, False, False, None),
        # Raw scenes present but the derived output absent is NOT reproducible:
        # local reproducibility narrowly requires the derived artifact too.
        (_TWO_REFS, False, DataStatus.MISSING, False, True, False, False, None),
    ],
    ids=["A_raw+derived", "B_derived_only", "C_neither", "C_raw_only_no_derived"],
)
def test_snapshot_three_states(
    monkeypatch, refs, derived, exp_status, exp_derived, exp_raw,
    exp_complete, exp_repro, exp_n,
):
    _force_state(monkeypatch, refs=refs, derived=derived)
    p = snapshot_provenance("pnsg")
    assert p.status is exp_status
    assert p.derived_output_available is exp_derived
    assert p.raw_scenes_available is exp_raw
    assert p.provenance_complete is exp_complete
    assert p.locally_reproducible is exp_repro
    assert p.n_scenes == exp_n  # None compares equal to None; 2 to 2


def test_state_a_is_fully_traceable(monkeypatch):
    """Raw + derived present: real scenes, real dates/sensors, honest depth."""
    _force_state(monkeypatch, refs=_TWO_REFS, derived=True)
    p = snapshot_provenance("pnsg")
    assert p.scene_dates == ["2025-08-10", "2026-04-10"]
    assert {r.sensor_id for r in p.scene_refs} == {"S2A", "S2B"}
    # 2 scenes → seasonal ΔEHS valid, Mann-Kendall not claimed.
    assert p.readiness is TrendReadiness.SEASONAL_ONLY
    assert p.mann_kendall_justified is False
    assert p.seasonal_delta_valid is True
    # State A may use the direct-observation wording.
    badge = snapshot_status_badge(p)
    assert badge.color == "#0F6E56"
    assert "directa" in badge.caveat.lower()


def test_state_b_degrades_honestly(monkeypatch):
    """Derived-only: REAL-derived, but provenance explicitly incomplete."""
    _force_state(monkeypatch, refs=[], derived=True)
    p = snapshot_provenance("pnsg")
    # No fabricated scene metadata.
    assert p.n_scenes is None
    assert p.scene_dates == []
    assert p.scene_refs == []
    # Trend readiness is NOT recomputed from an invented count.
    assert p.readiness is None
    assert p.mann_kendall_justified is False
    # The degraded statement is surfaced verbatim.
    assert "no es reproducible localmente" in p.caveat
    assert "no están disponibles en este entorno" in p.caveat
    # The old fabricated "2 escenas estacionales" wording is gone.
    assert "escenas estacionales" not in p.inference_label


def test_state_c_is_missing_without_fabrication(monkeypatch):
    _force_state(monkeypatch, refs=[], derived=False)
    p = snapshot_provenance("pnsg")
    assert p.n_scenes is None
    assert p.scene_dates == []
    assert p.scene_refs == []
    assert p.readiness is None
    badge = snapshot_status_badge(p)
    assert badge.emoji == "—"  # the "Sin dato" badge


# ── Regression guards against the original defect ────────────────────────────

def test_state_b_never_fabricates_two_scenes(monkeypatch):
    """The removed ``n_scenes = ... else 2`` fallback must not creep back."""
    _force_state(monkeypatch, refs=[], derived=True)
    p = snapshot_provenance("pnsg")
    assert p.n_scenes is None
    assert p.n_scenes != 2


def test_state_b_badge_carries_no_unqualified_direct_observation(monkeypatch):
    """State B must not present the raw provenance as locally inspectable."""
    _force_state(monkeypatch, refs=[], derived=True)
    p = snapshot_provenance("pnsg")
    badge = snapshot_status_badge(p)
    # Must not reuse the full REAL badge's "Observación directa Sentinel-2 L2A".
    assert "Observación directa Sentinel-2 L2A" not in badge.caveat
    assert "directa" not in badge.caveat.lower()
    # Must instead say provenance is incomplete / not reproducible.
    assert "no es reproducible localmente" in badge.caveat
    # Distinct colour from the full-REAL green.
    assert badge.color != _STATUS_GREEN


# ── Time-series coverage (unchanged) ─────────────────────────────────────────

def test_timeseries_coverage_is_none_when_no_manifest():
    # snr has no multi-year manifest → None.
    assert load_timeseries_coverage("snr") is None


def test_timeseries_coverage_shape_when_present():
    cov = load_timeseries_coverage("pnsg")
    if cov is not None:  # present only after run_pipeline_a_timeseries has run
        assert {"n_expected", "n_present", "fraction", "dominant_status"} <= set(cov)
