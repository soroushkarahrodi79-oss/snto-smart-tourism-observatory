"""F3 — Data provenance & confidence surfacing."""
from __future__ import annotations

import re

from src.platform.provenance import (
    data_status_badge,
    detect_scene_dates,
    load_timeseries_coverage,
    snapshot_provenance,
)
from src.temporal import DataStatus, TrendReadiness

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def test_badge_exists_for_every_status():
    for status in DataStatus:
        b = data_status_badge(status)
        assert b.emoji and b.label and b.color and b.caveat


def test_real_and_synthetic_badges_differ_in_caveat():
    real = data_status_badge(DataStatus.REAL)
    synth = data_status_badge(DataStatus.SYNTHETIC)
    assert "directa" in real.caveat.lower()
    assert "no usar" in synth.caveat.lower()


def test_detect_scene_dates_returns_iso_dates():
    """Dates parsed from real .SAFE products must be well-formed and sorted."""
    dates = detect_scene_dates("pnsg")
    assert all(_ISO.match(d) for d in dates)
    assert dates == sorted(dates)


def test_snapshot_provenance_is_real_and_honest_about_depth():
    prov = snapshot_provenance("pnsg")
    assert prov.status is DataStatus.REAL
    assert prov.inference_label  # non-empty
    # With a seasonal snapshot (< 4 scenes) Mann-Kendall must NOT be claimed.
    if prov.n_scenes < 4:
        assert prov.readiness is TrendReadiness.SEASONAL_ONLY
        assert prov.mann_kendall_justified is False
        assert prov.seasonal_delta_valid is True
        assert "alerta temprana" in prov.caveat.lower()


def test_timeseries_coverage_is_none_when_no_manifest():
    # snr has filemode outputs but no multi-year manifest → None.
    assert load_timeseries_coverage("snr") is None


def test_timeseries_coverage_shape_when_present():
    cov = load_timeseries_coverage("pnsg")
    if cov is not None:  # present only after run_pipeline_a_timeseries has run
        assert {"n_expected", "n_present", "fraction", "dominant_status"} <= set(cov)
