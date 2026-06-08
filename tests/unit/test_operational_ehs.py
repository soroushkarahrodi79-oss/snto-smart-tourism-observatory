"""
Unit tests for the operational EHS formula in calculate_delta_ehs.py.

These tests verify the two mathematical primitives — _deficit and _trail_ehs —
independently of any raster I/O, database, or real Sentinel-2 data.

The formula under test:
  D = clamp((baseline_sano − observed) / (baseline_sano − suelo), 0, 1)
  EHS = 100 × (W_NDVI × D_ndvi + W_NDMI × D_ndmi)

Both baseline_sano and suelo are derived from the real pixel distribution of
each Sentinel-2 scene (see _compute_scene_baselines in calculate_delta_ehs.py).
"""
from __future__ import annotations

import pytest

from calculate_delta_ehs import _deficit, _trail_ehs


# ── _deficit boundary conditions ──────────────────────────────────────────────

def test_deficit_at_baseline_is_zero():
    """Observation equal to baseline_sano → D = 0 (no stress)."""
    assert _deficit(0.70, baseline=0.70, floor=0.20) == 0.0


def test_deficit_at_floor_is_one():
    """Observation equal to suelo → D = 1 (maximum stress)."""
    assert _deficit(0.20, baseline=0.70, floor=0.20) == 1.0


def test_deficit_above_baseline_clamped_to_zero():
    """Observation above baseline (healthier than reference) → D = 0, not negative."""
    assert _deficit(0.85, baseline=0.70, floor=0.20) == 0.0


def test_deficit_below_floor_clamped_to_one():
    """Observation below suelo → D = 1, not > 1."""
    assert _deficit(0.05, baseline=0.70, floor=0.20) == 1.0


def test_deficit_midpoint():
    """Observation halfway between baseline and floor → D = 0.5."""
    mid = (0.70 + 0.20) / 2  # 0.45
    result = _deficit(mid, baseline=0.70, floor=0.20)
    assert abs(result - 0.5) < 1e-9


def test_deficit_degenerate_distribution_returns_zero():
    """When baseline ≤ floor (flat or inverted distribution), return 0 gracefully."""
    assert _deficit(0.40, baseline=0.40, floor=0.40) == 0.0
    assert _deficit(0.40, baseline=0.30, floor=0.40) == 0.0


# ── _trail_ehs boundary conditions ────────────────────────────────────────────

# Scenario setup:
#   NDVI range: baseline_sano=0.70, suelo=0.20  (healthy Mediterranean scrubland)
#   NDMI range: baseline_sano=0.10, suelo=−0.30 (moisture saturation → deficit)
_NDVI_BASE  = 0.70
_NDVI_FLOOR = 0.20
_NDMI_BASE  = 0.10
_NDMI_FLOOR = -0.30


def test_ehs_at_baseline_is_zero():
    """
    Trail with both indices at baseline_sano → EHS = 0.
    D_ndvi = 0, D_ndmi = 0 → EHS = 100 × (0.5 × 0 + 0.5 × 0) = 0.
    """
    ehs = _trail_ehs(
        ndvi_obs=_NDVI_BASE, ndmi_obs=_NDMI_BASE,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
        w_ndvi=0.5, w_ndmi=0.5,
    )
    assert ehs == 0.0


def test_ehs_at_suelo_is_hundred():
    """
    Trail with both indices at suelo → EHS = 100.
    D_ndvi = 1, D_ndmi = 1 → EHS = 100 × (0.5 × 1 + 0.5 × 1) = 100.
    """
    ehs = _trail_ehs(
        ndvi_obs=_NDVI_FLOOR, ndmi_obs=_NDMI_FLOOR,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
        w_ndvi=0.5, w_ndmi=0.5,
    )
    assert ehs == 100.0


def test_ehs_midpoint_is_fifty():
    """Halfway between baseline and floor on both indices → EHS ≈ 50."""
    mid_ndvi = (_NDVI_BASE + _NDVI_FLOOR) / 2   # 0.45
    mid_ndmi = (_NDMI_BASE + _NDMI_FLOOR) / 2   # -0.10
    ehs = _trail_ehs(
        ndvi_obs=mid_ndvi, ndmi_obs=mid_ndmi,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
        w_ndvi=0.5, w_ndmi=0.5,
    )
    assert ehs is not None
    assert abs(ehs - 50.0) < 1e-3


def test_ehs_above_baseline_clamped_to_zero():
    """Observations healthier than baseline_sano still give EHS = 0."""
    ehs = _trail_ehs(
        ndvi_obs=0.90, ndmi_obs=0.30,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
        w_ndvi=0.5, w_ndmi=0.5,
    )
    assert ehs == 0.0


def test_ehs_range_is_zero_to_hundred():
    """EHS must remain in [0, 100] for any valid observation."""
    cases = [
        (_NDVI_BASE, _NDMI_BASE),         # no stress
        (_NDVI_FLOOR, _NDMI_FLOOR),        # full stress
        (0.50, -0.05),                     # intermediate
        (0.99, 0.50),                      # well above baseline
        (0.01, -0.99),                     # well below floor
    ]
    for ndvi, ndmi in cases:
        ehs = _trail_ehs(
            ndvi_obs=ndvi, ndmi_obs=ndmi,
            ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
            ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
            w_ndvi=0.5, w_ndmi=0.5,
        )
        assert ehs is not None
        assert 0.0 <= ehs <= 100.0, f"EHS out of range for NDVI={ndvi}, NDMI={ndmi}: {ehs}"


# ── Missing data handling ──────────────────────────────────────────────────────

def test_ehs_both_none_returns_none():
    """No spectral data at all → None (trail outside raster extent)."""
    ehs = _trail_ehs(
        ndvi_obs=None, ndmi_obs=None,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
    )
    assert ehs is None


def test_ehs_single_ndvi_spans_full_range():
    """When only NDVI is available, EHS still spans [0, 100]."""
    ehs_min = _trail_ehs(
        ndvi_obs=_NDVI_BASE, ndmi_obs=None,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
    )
    ehs_max = _trail_ehs(
        ndvi_obs=_NDVI_FLOOR, ndmi_obs=None,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
    )
    assert ehs_min == 0.0
    assert ehs_max == 100.0


def test_ehs_single_ndmi_spans_full_range():
    """When only NDMI is available, EHS still spans [0, 100]."""
    ehs_min = _trail_ehs(
        ndvi_obs=None, ndmi_obs=_NDMI_BASE,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
    )
    ehs_max = _trail_ehs(
        ndvi_obs=None, ndmi_obs=_NDMI_FLOOR,
        ndvi_baseline=_NDVI_BASE, ndvi_floor=_NDVI_FLOOR,
        ndmi_baseline=_NDMI_BASE, ndmi_floor=_NDMI_FLOOR,
    )
    assert ehs_min == 0.0
    assert ehs_max == 100.0
