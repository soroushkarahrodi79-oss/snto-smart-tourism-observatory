from __future__ import annotations

import pytest

from src.features.spectral import (
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
