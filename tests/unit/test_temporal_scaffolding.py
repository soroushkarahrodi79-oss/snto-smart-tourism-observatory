"""F2 — Temporal series scaffolding: spec, validity gate, provenance manifest."""
from __future__ import annotations

import json

import pytest

from src.temporal import (
    MK_MIN_N,
    MK_ROBUST_N,
    PNSG_5Y,
    Cadence,
    DataStatus,
    SeriesSpec,
    TrendReadiness,
    assess_trend_readiness,
    build_manifest_from_observations,
    classify_source,
    spec_for_territory,
)


class _Stats:
    def __init__(self, pixel_count, valid_pixel_pct):
        self.pixel_count = pixel_count
        self.valid_pixel_pct = valid_pixel_pct


class _Obs:
    def __init__(self, year, month, cloud=10.0, source="GEE:S2_SR_HARMONIZED",
                 pixel_count=400, valid_pct=0.9):
        self.year = year
        self.month = month
        self.cloud_cover_pct = cloud
        self.data_source = source
        self.ndvi_stats = _Stats(pixel_count, valid_pct)


# ── SeriesSpec ──────────────────────────────────────────────────────────────

def test_pnsg_5y_is_72_monthly_periods():
    assert PNSG_5Y.cadence is Cadence.MONTHLY
    assert PNSG_5Y.years() == [2021, 2022, 2023, 2024, 2025, 2026]
    assert PNSG_5Y.n_expected() == 72
    assert len(PNSG_5Y.periods()) == 72
    assert PNSG_5Y.label() == "2021–2026"


def test_monthly_period_keys_are_zero_padded():
    spec = SeriesSpec("pnsg", 2021, 2021, Cadence.MONTHLY)
    assert spec.period_keys()[0] == "2021-01"
    assert spec.period_keys()[-1] == "2021-12"


def test_seasonal_cadence_has_four_periods_per_year():
    spec = SeriesSpec("pnsg", 2021, 2022, Cadence.SEASONAL)
    assert spec.n_expected() == 8
    assert spec.periods()[0].key == "2021-winter"


def test_spec_rejects_reversed_year_span():
    with pytest.raises(ValueError):
        SeriesSpec("pnsg", 2026, 2021)


def test_spec_for_territory_resolves_tile_from_registry():
    spec = spec_for_territory("pnsg", 2021, 2026)
    assert spec.s2_tile == "T30TVL"
    assert spec.territory_key == "pnsg"


# ── Trend validity gate ─────────────────────────────────────────────────────

def test_gate_insufficient_below_two():
    r = assess_trend_readiness(1)
    assert r.readiness is TrendReadiness.INSUFFICIENT
    assert not r.seasonal_delta_valid and not r.mann_kendall_justified


def test_gate_two_scenes_is_seasonal_only_not_trend():
    """The current real PNSG state: 2 scenes ⇒ ΔEHS valid, Mann-Kendall not."""
    r = assess_trend_readiness(2)
    assert r.readiness is TrendReadiness.SEASONAL_ONLY
    assert r.seasonal_delta_valid is True
    assert r.mann_kendall_justified is False


def test_gate_mk_computable_but_underpowered_between_4_and_10():
    r = assess_trend_readiness(MK_MIN_N)
    assert r.readiness is TrendReadiness.TREND_EMERGING
    assert r.mann_kendall_justified is True


def test_gate_robust_at_or_above_threshold():
    r = assess_trend_readiness(MK_ROBUST_N)
    assert r.readiness is TrendReadiness.TREND_ROBUST
    assert r.mann_kendall_justified is True


# ── Provenance manifest ─────────────────────────────────────────────────────

def test_classify_source_tiers():
    assert classify_source("GEE:S2_SR_HARMONIZED") is DataStatus.REAL
    assert classify_source("mock:dry-run") is DataStatus.SYNTHETIC
    assert classify_source("calibrated:AEMET") is DataStatus.CALIBRATED
    assert classify_source(None) is DataStatus.MISSING


def test_manifest_marks_missing_periods_as_gaps():
    spec = SeriesSpec("pnsg", 2021, 2021, Cadence.MONTHLY)  # 12 expected
    obs = [_Obs(2021, m) for m in (4, 5, 6)]                # only 3 present
    man = build_manifest_from_observations(spec, obs)
    assert man.n_expected() == 12
    assert man.n_present() == 3
    assert man.coverage() == round(3 / 12, 4)
    assert "2021-01" in man.gaps()
    assert "2021-04" not in man.gaps()
    assert man.dominant_status() is DataStatus.REAL


def test_manifest_keeps_best_observation_per_period():
    spec = SeriesSpec("pnsg", 2021, 2021, Cadence.MONTHLY)
    worse = _Obs(2021, 7, valid_pct=0.4, pixel_count=100)
    better = _Obs(2021, 7, valid_pct=0.95, pixel_count=500)
    man = build_manifest_from_observations(spec, [worse, better])
    july = next(r for r in man.records if r.period_key == "2021-07")
    assert july.present and july.n_valid_pixels == 500


def test_manifest_round_trips_to_json(tmp_path):
    spec = SeriesSpec("pnsg", 2021, 2021, Cadence.MONTHLY)
    man = build_manifest_from_observations(spec, [_Obs(2021, 6)])
    path = man.write_json(tmp_path / "m.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["coverage"]["n_expected"] == 12
    assert payload["coverage"]["n_present"] == 1
    assert payload["spec"]["s2_tile"] == "T30TVL"
    assert len(payload["records"]) == 12
