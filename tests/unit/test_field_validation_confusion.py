"""Confusion matrix, per-asset field index and CSV I/O tests (#26)."""

from __future__ import annotations

from src.validation import (
    FieldObservation,
    build_pairs,
    confusion_matrix,
    field_degraded,
    field_index_by_asset,
    load_field_observations,
    satellite_alert,
    write_template,
)


class _Trend:
    """Minimal AssetTrend stand-in exposing the fields the classifier reads."""

    def __init__(self, asset_id: str, trend: str, p_value: float):
        self.asset_id = asset_id
        self.trend = trend
        self.p_value = p_value

    @property
    def significant(self) -> bool:
        return self.p_value < 0.05

    @property
    def is_alert(self) -> bool:
        return self.trend == "decreasing" and self.significant


def test_satellite_alert_only_on_significant_decrease():
    assert satellite_alert(_Trend("a", "decreasing", 0.01)) is True
    assert satellite_alert(_Trend("a", "decreasing", 0.20)) is False  # not sig
    assert satellite_alert(_Trend("a", "increasing", 0.01)) is False


def test_field_degraded_threshold_and_null():
    assert field_degraded(None) is None
    assert field_degraded(60.0) is True
    assert field_degraded(49.9) is False
    assert field_degraded(40.0, threshold=30.0) is True


def test_confusion_matrix_counts_and_metrics():
    # tp, fp, fn, tn
    cm = confusion_matrix([(True, True), (True, False), (False, True),
                           (False, False)])
    assert (cm.tp, cm.fp, cm.fn, cm.tn) == (1, 1, 1, 1)
    assert cm.accuracy == 0.5
    assert cm.precision == 0.5
    assert cm.recall == 0.5
    assert cm.cohen_kappa == 0.0  # chance-level agreement


def test_confusion_matrix_perfect_agreement():
    cm = confusion_matrix([(True, True), (True, True), (False, False),
                           (False, False)])
    assert cm.cohen_kappa == 1.0
    assert cm.accuracy == 1.0


def test_confusion_matrix_empty_is_honest_not_fabricated():
    cm = confusion_matrix([])
    assert cm.n == 0
    assert cm.cohen_kappa is None
    assert "pendiente" in cm.verdict or "campaña" in cm.verdict


def test_build_pairs_skips_assets_without_field_index():
    trends = {
        "a1": _Trend("a1", "decreasing", 0.01),
        "a2": _Trend("a2", "increasing", 0.01),
    }
    field_idx = {"a1": 70.0, "a2": None}  # a2 has no field datum
    pairs = build_pairs(trends, field_idx)
    assert pairs == [(True, True)]  # only a1; a2 skipped, never guessed


def test_field_index_by_asset_uses_impact_plots_only():
    obs = [
        FieldObservation("p1", 40.0, -3.9, 0, False, asset_id="a1",
                         veg_cover_pct=20.0),   # degradation 80
        FieldObservation("p2", 40.0, -3.9, 80, True, asset_id="a1",
                         veg_cover_pct=90.0),   # control — excluded
        FieldObservation("p3", 40.1, -3.8, 0, False, asset_id="a2"),  # no data
    ]
    idx = field_index_by_asset(obs)
    assert idx["a1"] == 80.0          # only the impact plot
    assert "a2" not in idx            # no measurable component → not fabricated


def test_csv_template_roundtrip(tmp_path):
    seed = [{
        "plot_id": "porrones_impact_1",
        "asset_id": "pnsg_escalada_maliciosa_porrones",
        "lat": 40.7405, "lon": -3.9251, "distance_to_trail_m": 0,
        "is_control": "false", "stratum": "escalada-roquedo",
    }]
    path = write_template(tmp_path / "obs.csv", seed)
    loaded = load_field_observations(path)
    assert len(loaded) == 1
    o = loaded[0]
    assert o.plot_id == "porrones_impact_1"
    assert o.asset_id == "pnsg_escalada_maliciosa_porrones"
    assert o.is_control is False
    # blank measurement cells load as explicit None, never 0
    assert o.soil_compaction_mpa is None
    assert o.veg_cover_pct is None
    assert o.degradation_index() is None
