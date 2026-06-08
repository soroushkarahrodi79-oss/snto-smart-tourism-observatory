"""
Unit tests for the causal budget logic in tis_engine.py.

These tests exercise _causal_factor() in isolation, then verify the full
_compute_tis + _causal_factor pipeline for the three classification branches.
"""
from __future__ import annotations

import pytest

from tis_engine import _causal_factor, _compute_tis


# ── _causal_factor ────────────────────────────────────────────────────────────

def test_localized_factor_is_one():
    assert _causal_factor("LOCALIZED_IMPACT") == 1.0


def test_landscape_factor_is_zero():
    assert _causal_factor("LANDSCAPE_DRIVEN") == 0.0


def test_mixed_factor_is_half():
    assert _causal_factor("MIXED") == 0.5


def test_none_treated_as_mixed():
    assert _causal_factor(None) == 0.5


# ── Pipeline: causal budget = tis_budget_eur × _causal_factor ────────────────

def _causal_budget(priority: float, length_m: float, scm_cls: str | None) -> float:
    _, gross = _compute_tis(priority, length_m)
    return round(gross * _causal_factor(scm_cls), 2)


def test_localized_impact_causal_equals_gross():
    """LOCALIZED_IMPACT → causal budget equals the full gross budget."""
    _, gross = _compute_tis(75.0, 1000.0)
    causal   = _causal_budget(75.0, 1000.0, "LOCALIZED_IMPACT")
    assert gross > 0
    assert causal == gross


def test_landscape_driven_causal_is_zero():
    """LANDSCAPE_DRIVEN → causal budget is 0 regardless of gross budget."""
    _, gross = _compute_tis(80.0, 2000.0)
    causal   = _causal_budget(80.0, 2000.0, "LANDSCAPE_DRIVEN")
    assert gross > 0
    assert causal == 0.0


def test_mixed_causal_is_half_of_gross():
    """MIXED → causal budget is exactly half of gross budget."""
    _, gross = _compute_tis(70.0, 500.0)
    causal   = _causal_budget(70.0, 500.0, "MIXED")
    assert causal == round(gross * 0.5, 2)


def test_null_classification_causal_is_half_of_gross():
    """NULL scm_classification is treated identically to MIXED."""
    _, gross = _compute_tis(70.0, 500.0)
    causal   = _causal_budget(70.0, 500.0, None)
    assert causal == round(gross * 0.5, 2)


def test_non_critical_trail_causal_budget_is_zero():
    """Trails below the priority threshold have gross=0, so causal=0 for any SCM class."""
    for scm_cls in ("LOCALIZED_IMPACT", "MIXED", "LANDSCAPE_DRIVEN", None):
        assert _causal_budget(50.0, 1000.0, scm_cls) == 0.0
