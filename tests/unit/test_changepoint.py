"""Tests de detección de punto de cambio (test de Pettitt, 1979).

Cubren ``src/time_series/changepoint.py``.
"""
from __future__ import annotations

from src.time_series.changepoint import pettitt_test


def test_pettitt_locates_step():
    # Escalón entre el índice 9 y el 10 → el segundo régimen empieza en 10.
    series = [1.0] * 10 + [9.0] * 10
    r = pettitt_test(series)
    assert r.change_index == 10


def test_pettitt_step_is_significant():
    series = [1.0] * 20 + [5.0] * 20
    r = pettitt_test(series)
    assert r.is_significant is True
    assert r.change_index == 20


def test_pettitt_constant_series_not_significant():
    r = pettitt_test([5.0] * 20)
    assert r.is_significant is False
    assert r.k_statistic == 0.0


def test_pettitt_noisy_flat_not_significant():
    series = [(1.0 if t % 2 else -1.0) * 0.1 for t in range(30)]
    r = pettitt_test(series)
    assert r.is_significant is False


def test_pettitt_short_series_returns_none():
    r = pettitt_test([1.0, 2.0, 3.0])
    assert r.change_index is None
    assert r.is_significant is False


def test_pettitt_index_in_valid_range():
    series = [0.4, 0.42, 0.39, 0.20, 0.19, 0.22, 0.41, 0.43, 0.40, 0.44]
    r = pettitt_test(series)
    assert 1 <= r.change_index < len(series)


def test_pettitt_handles_ties():
    # Repeticiones (empates) no deben romper el ranking promedio.
    series = [1.0, 1.0, 1.0, 2.0, 2.0, 9.0, 9.0, 9.0, 9.0, 9.0]
    r = pettitt_test(series)
    assert r.change_index is not None
    assert 1 <= r.change_index < len(series)


def test_pettitt_detects_drop_after_rise():
    # Caída sostenida tras un tramo alto: la ruptura cae en el descenso.
    series = [0.8] * 12 + [0.3] * 12
    r = pettitt_test(series)
    assert r.change_index == 12
    assert r.is_significant is True
