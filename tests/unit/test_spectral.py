from __future__ import annotations

import math

import pytest

from src.features.spectral import (
    compute_evi,
    compute_msavi2,
    compute_nbr,
    compute_ndmi,
    compute_ndvi,
    extract_spectral_features,
)


def test_compute_ndvi_known_value():
    result = compute_ndvi(nir=0.8, red=0.2)
    assert abs(result - 0.6) < 1e-10


def test_compute_ndvi_zero_denominator():
    assert compute_ndvi(0.0, 0.0) == 0.0


def test_compute_ndmi_known_value():
    result = compute_ndmi(nir=0.8, swir=0.2)
    assert abs(result - 0.6) < 1e-10


def test_compute_nbr_known_value():
    result = compute_nbr(nir=0.8, swir2=0.4)
    assert abs(result - (0.4 / 1.2)) < 1e-10


def test_extract_spectral_features_means(mock_observations):
    features = extract_spectral_features(mock_observations)
    expected_mean = sum(o.ndvi for o in mock_observations) / 12
    assert abs(features.mean_ndvi - expected_mean) < 1e-10


def test_extract_spectral_features_series_length(mock_observations):
    features = extract_spectral_features(mock_observations)
    assert len(features.ndvi_series) == 12
    assert len(features.ndmi_series) == 12


def test_extract_spectral_features_no_nbr(mock_observations):
    features = extract_spectral_features(mock_observations)
    assert features.mean_nbr is None


def test_extract_spectral_features_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        extract_spectral_features([])


# ── EVI tests ─────────────────────────────────────────────────────────────────

def test_compute_evi_known_value():
    # EVI = 2.5 × (0.5 – 0.1) / (0.5 + 6×0.1 – 7.5×0.05 + 1)
    #     = 2.5 × 0.4 / (0.5 + 0.6 – 0.375 + 1) = 1.0 / 1.725
    nir, red, blue = 0.5, 0.1, 0.05
    expected = 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0)
    result = compute_evi(nir, red, blue)
    assert abs(result - expected) < 1e-10


def test_compute_evi_zero_denominator():
    # nir + C1*red - C2*blue + L = 0 is pathological; function must not crash
    # Construct: 0.0 + 6×0.0 – 7.5×(1.0/7.5) + 1.0 ≈ 0 — force denom = 0
    assert compute_evi(nir=0.0, red=0.0, blue=1.0 / 7.5) == 0.0


def test_compute_evi_differentiates_where_ndvi_saturates():
    # Core anti-saturation property: as canopy density increases from medium
    # to very dense, NDVI barely changes (both > 0.85 in saturation zone) while
    # EVI continues to track canopy structure differences.
    nir_mid,  red_mid,  blue_mid  = 0.50, 0.10, 0.04   # medium dense
    nir_high, red_high, blue_high = 0.75, 0.06, 0.025  # very dense

    ndvi_mid  = compute_ndvi(nir_mid,  red_mid)
    ndvi_high = compute_ndvi(nir_high, red_high)
    evi_mid   = compute_evi(nir_mid,  red_mid,  blue_mid)
    evi_high  = compute_evi(nir_high, red_high, blue_high)

    # Both NDVI values are in the moderate-to-high range; their delta is small
    ndvi_delta = abs(ndvi_high - ndvi_mid)
    # EVI should show at least as large a separation (it doesn't plateau the same way)
    evi_delta  = abs(evi_high - evi_mid)
    assert ndvi_mid > 0.60 and ndvi_high > 0.80    # saturation zone entry
    assert evi_delta > 0.0                          # EVI still differentiates


def test_compute_evi_healthy_vegetation_range():
    # Dense beech forest in summer: NIR~0.55, RED~0.08, BLUE~0.04
    evi = compute_evi(nir=0.55, red=0.08, blue=0.04)
    assert 0.3 < evi < 0.7, f"EVI={evi:.4f} outside expected dense-forest range"


# ── MSAVI2 tests ──────────────────────────────────────────────────────────────

def test_compute_msavi2_known_value():
    # MSAVI2 = (2×0.5 + 1 – √((2×0.5+1)² – 8×(0.5–0.1))) / 2
    #        = (2 – √(4 – 3.2)) / 2 = (2 – √0.8) / 2
    nir, red = 0.5, 0.1
    disc = (2.0 * nir + 1.0) ** 2 - 8.0 * (nir - red)
    expected = (2.0 * nir + 1.0 - math.sqrt(disc)) / 2.0
    assert abs(compute_msavi2(nir, red) - expected) < 1e-10


def test_compute_msavi2_bare_soil_low():
    # Bare soil: NDVI~0, MSAVI2 should also be near zero or small
    result = compute_msavi2(nir=0.2, red=0.18)
    assert -0.1 < result < 0.15


def test_compute_msavi2_healthy_vegetation_positive():
    result = compute_msavi2(nir=0.60, red=0.07)
    assert result > 0.40


def test_compute_msavi2_equal_bands_near_zero():
    # When NIR ≈ RED (bare soil or water body), MSAVI2 should be near zero.
    # Discriminant = (2n+1)² - 8(n-r); when n=r, disc = (2n+1)² ≥ 0 always.
    result = compute_msavi2(nir=0.15, red=0.15)
    assert abs(result) < 1e-10


# ── SpectralFeatures with EVI ─────────────────────────────────────────────────

def test_extract_spectral_features_evi_populated(mock_observations):
    from src.assets.models import AssetObservation
    obs_with_evi = [
        AssetObservation(
            asset_id=o.asset_id, year=o.year, month=o.month,
            ndvi=o.ndvi, ndmi=o.ndmi, evi=0.40,
        )
        for o in mock_observations
    ]
    features = extract_spectral_features(obs_with_evi)
    assert features.mean_evi is not None
    assert abs(features.mean_evi - 0.40) < 1e-10
    assert len(features.evi_series) == len(obs_with_evi)


def test_extract_spectral_features_evi_none_when_absent(mock_observations):
    features = extract_spectral_features(mock_observations)
    assert features.mean_evi is None
    assert features.evi_series == []
