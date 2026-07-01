"""Tests de validación cruzada inter-sensor (Sentinel-2 vs referencia).

Cubren ``src/validation/cross_sensor.py``.
"""
from __future__ import annotations

import pytest

from src.validation.cross_sensor import (
    cross_sensor_agreement,
    willmott_index,
)


def test_identical_series_perfect_agreement():
    s = [0.4, 0.42, 0.38, 0.5, 0.47, 0.41]
    rep = cross_sensor_agreement(s, s)
    assert rep.pearson_r == 1.0
    assert rep.rmse == 0.0
    assert rep.mae == 0.0
    assert rep.bias == 0.0
    assert rep.willmott_d == 1.0
    assert rep.ba_lower_loa == 0.0 and rep.ba_upper_loa == 0.0
    assert "fuerte" in rep.verdict


def test_constant_offset_is_biased_but_correlated():
    ref = [0.40, 0.42, 0.38, 0.50, 0.47, 0.41]
    primary = [v + 0.05 for v in ref]      # sesgo sistemático +0.05
    rep = cross_sensor_agreement(primary, ref)
    assert rep.pearson_r == pytest.approx(1.0, abs=1e-6)
    assert rep.bias == pytest.approx(0.05, abs=1e-6)
    assert rep.rmse == pytest.approx(0.05, abs=1e-6)
    assert "sesgo" in rep.verdict           # buena covariación, sesgada


def test_bland_altman_limits_bracket_mean():
    ref = [0.40, 0.42, 0.38, 0.50, 0.47, 0.41, 0.44, 0.39]
    primary = [0.41, 0.44, 0.36, 0.52, 0.46, 0.43, 0.45, 0.40]
    rep = cross_sensor_agreement(primary, ref)
    assert rep.ba_lower_loa <= rep.ba_mean_diff <= rep.ba_upper_loa


def test_anticorrelated_series_no_agreement():
    ref = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    primary = list(reversed(ref))
    rep = cross_sensor_agreement(primary, ref)
    assert rep.pearson_r < 0
    assert "sin concordancia" in rep.verdict


def test_willmott_bounds():
    ref = [0.3, 0.5, 0.4, 0.6, 0.35, 0.55]
    primary = [0.32, 0.48, 0.42, 0.58, 0.36, 0.5]
    d = willmott_index(primary, ref)
    assert 0.0 <= d <= 1.0


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        cross_sensor_agreement([0.1, 0.2, 0.3], [0.1, 0.2])


def test_too_few_pairs_raises():
    with pytest.raises(ValueError):
        cross_sensor_agreement([0.1, 0.2], [0.1, 0.2])


def test_moderate_correlation_verdict():
    ref = [0.30, 0.42, 0.35, 0.50, 0.38, 0.46, 0.33, 0.48, 0.36, 0.44, 0.31, 0.49]
    # Ruido moderado sobre la referencia (co-varía, pero no de forma fuerte).
    primary = [0.405, 0.39, 0.368, 0.507, 0.418, 0.397,
               0.311, 0.446, 0.312, 0.402, 0.287, 0.477]
    rep = cross_sensor_agreement(primary, ref)
    assert 0.6 <= rep.pearson_r < 0.8
    assert "moderada" in rep.verdict
