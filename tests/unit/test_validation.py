"""F5 — Field-validation schema and satellite↔terrain agreement metrics."""
from __future__ import annotations

import pytest

from src.validation import (
    ErosionClass,
    FieldObservation,
    cliffs_delta,
    control_impact_contrast,
    spearman_correlation,
    split_impact_control,
    validate_satellite_vs_field,
)
from src.validation.io import FIELDNAMES, load_field_observations, write_template


def _obs(plot_id, is_control, **kw):
    base = dict(plot_id=plot_id, lat=40.8, lon=-3.9, distance_to_trail_m=0.0,
                is_control=is_control)
    base.update(kw)
    return FieldObservation(**base)


# ── B-02: strict degradation index + additive schema ────────────────────────

def test_permissive_index_is_unchanged_by_b02():
    # Before/after guard: the permissive method's outputs are pinned so a future
    # edit that alters it (it feeds every product path) fails here.
    assert _obs("a", False, soil_compaction_mpa=3.0, veg_cover_pct=0.0,
                erosion_class=ErosionClass.SEVERE).degradation_index() == 100.0
    assert _obs("b", True, soil_compaction_mpa=0.0, veg_cover_pct=100.0,
                erosion_class=ErosionClass.NONE).degradation_index() == 0.0
    assert _obs("c", False, veg_cover_pct=40.0).degradation_index() == 60.0
    assert _obs("d", False, soil_compaction_mpa=1.5,
                erosion_class=2).degradation_index() == 58.33
    assert _obs("e", False).degradation_index() is None


@pytest.mark.parametrize("kw", [
    dict(veg_cover_pct=40.0, erosion_class=1),          # missing compaction
    dict(soil_compaction_mpa=2.0, erosion_class=1),     # missing cover
    dict(soil_compaction_mpa=2.0, veg_cover_pct=40.0),  # missing erosion
    dict(veg_cover_pct=40.0),                           # 1 of 3
    dict(),                                             # none
])
def test_strict_index_none_on_any_missing_core_component(kw):
    assert _obs("p", False, **kw).degradation_index_strict() is None


def test_strict_index_equals_permissive_when_all_three_present():
    o = _obs("p", False, soil_compaction_mpa=1.5, veg_cover_pct=40.0,
             erosion_class=2)
    # (50 compaction + 60 cover-deficit + 66.67 erosion) / 3 = 58.89
    assert o.degradation_index_strict() == o.degradation_index() == 58.89
    # bare_soil_pct is recorded but is NOT a component (Contract §H).
    o2 = _obs("p", False, soil_compaction_mpa=1.5, veg_cover_pct=40.0,
              erosion_class=2, bare_soil_pct=80.0)
    assert o2.degradation_index_strict() == 58.89


def test_new_columns_round_trip_and_blanks_stay_none(tmp_path):
    path = write_template(tmp_path / "o.csv", [
        {"plot_id": "x1", "lat": 40.8, "lon": -3.9, "distance_to_trail_m": 0,
         "is_control": "false", "gps_accuracy_m": 3.2, "subplot_id": "A",
         "bare_soil_pct": 15, "observer_id": "obs1", "notes": "ok"},
        {"plot_id": "x2", "lat": 40.8, "lon": -3.9, "distance_to_trail_m": 50,
         "is_control": "true"},
    ])
    o1, o2 = load_field_observations(path)
    assert (o1.gps_accuracy_m, o1.subplot_id, o1.bare_soil_pct,
            o1.observer_id, o1.notes) == (3.2, "A", 15.0, "obs1", "ok")
    assert o2.gps_accuracy_m is None and o2.bare_soil_pct is None
    assert o2.subplot_id is None and o2.observer_id is None and o2.notes is None


def test_old_csv_without_new_columns_still_loads(tmp_path):
    old = tmp_path / "old.csv"
    old.write_text(
        "plot_id,lat,lon,distance_to_trail_m,is_control,soil_compaction_mpa,"
        "veg_cover_pct,erosion_class\ny1,40.8,-3.9,0,false,2.0,30,1\n",
        encoding="utf-8")
    (o,) = load_field_observations(old)
    assert o.gps_accuracy_m is None
    assert o.degradation_index() is not None  # existing columns unaffected


def test_fieldnames_are_additive_not_reordered():
    # The original 14 columns keep their positions; the 5 new ones are appended.
    assert FIELDNAMES[:14] == [
        "plot_id", "asset_id", "lat", "lon", "distance_to_trail_m", "is_control",
        "soil_compaction_mpa", "veg_cover_pct", "erosion_class", "trail_width_m",
        "visitor_count", "photo_ref", "stratum", "observed_at",
    ]
    assert FIELDNAMES[14:] == [
        "gps_accuracy_m", "subplot_id", "bare_soil_pct", "observer_id", "notes"]


# ── Field schema ────────────────────────────────────────────────────────────

def test_degradation_index_combines_available_components():
    o = _obs("p1", False, soil_compaction_mpa=3.0, veg_cover_pct=0.0,
             erosion_class=ErosionClass.SEVERE)
    assert o.degradation_index() == 100.0   # all components maxed
    pristine = _obs("p2", True, soil_compaction_mpa=0.0, veg_cover_pct=100.0,
                    erosion_class=ErosionClass.NONE)
    assert pristine.degradation_index() == 0.0


def test_degradation_index_none_when_no_components():
    assert _obs("p3", False).degradation_index() is None


def test_split_impact_control():
    obs = [_obs("a", False), _obs("b", True), _obs("c", False)]
    impact, control = split_impact_control(obs)
    assert [o.plot_id for o in impact] == ["a", "c"]
    assert [o.plot_id for o in control] == ["b"]


# ── Correlation ───────────────────────────────────────────────────────────────

def test_spearman_perfect_monotonic():
    assert spearman_correlation([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert spearman_correlation([1, 2, 3, 4], [40, 30, 20, 10]) == -1.0


def test_spearman_guards_small_or_constant():
    assert spearman_correlation([1, 2], [3, 4]) == 0.0
    assert spearman_correlation([5, 5, 5], [1, 2, 3]) == 0.0
    with pytest.raises(ValueError):
        spearman_correlation([1, 2, 3], [1, 2])


def test_validate_satellite_vs_field_strong_positive():
    pairs = [(10, 12), (30, 28), (55, 60), (80, 75), (95, 90)]
    rep = validate_satellite_vs_field(pairs)
    assert rep.n == 5
    assert rep.spearman >= 0.6 and rep.direction_ok
    assert "fuerte" in rep.verdict


def test_validate_flags_insufficient_sample():
    rep = validate_satellite_vs_field([(10, 12), (20, 25)])
    assert "insuficiente" in rep.verdict


# ── Control–Impact contrast (BACI) ────────────────────────────────────────────

def test_cliffs_delta_direction():
    assert cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0    # a wholly above b
    assert cliffs_delta([1, 2, 3], [5, 6, 7]) == -1.0


def test_control_impact_contrast_detects_large_effect():
    impact = [70, 75, 80, 65]    # degraded trail corridor
    control = [20, 25, 15, 30]   # pristine control plots
    res = control_impact_contrast(impact, control)
    assert res.impact_more_degraded is True
    assert res.delta > 0 and res.cliffs_delta == 1.0
    assert "efecto grande" in res.verdict


def test_control_impact_contrast_no_gradient():
    res = control_impact_contrast([30, 32, 28], [31, 29, 33])
    assert "sin gradiente" in res.verdict or res.impact_more_degraded is False


def test_control_impact_requires_both_groups():
    with pytest.raises(ValueError):
        control_impact_contrast([1, 2], [])
