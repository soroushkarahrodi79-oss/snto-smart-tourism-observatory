from __future__ import annotations

import math

import numpy as np
import pytest

from src.geospatial.aggregation import (
    POINT_BUFFER_M,
    TRAIL_BUFFER_M,
    buffer_asset_geometry,
    compute_pixel_stats,
)


def test_trail_buffer_returns_polygon(masatrigo_asset):
    geom = buffer_asset_geometry(masatrigo_asset)
    assert geom.geom_type == "Polygon"


def test_point_buffer_returns_polygon(viewpoint_asset):
    geom = buffer_asset_geometry(viewpoint_asset)
    assert geom.geom_type == "Polygon"


def test_polygon_asset_returned_as_is(recreational_area_asset):
    geom = buffer_asset_geometry(recreational_area_asset)
    assert geom.geom_type == "Polygon"


def test_trail_buffer_has_area(masatrigo_asset):
    geom = buffer_asset_geometry(masatrigo_asset)
    assert geom.area > 0


def test_custom_buffer_distance(masatrigo_asset):
    small = buffer_asset_geometry(masatrigo_asset, buffer_m=15)
    large = buffer_asset_geometry(masatrigo_asset, buffer_m=60)
    assert large.area > small.area


def test_pixel_stats_basic():
    arr = np.array([0.2, 0.3, 0.4, 0.5, 0.6, 0.35, 0.45])
    stats = compute_pixel_stats(arr, total_pixel_count=len(arr))
    assert stats is not None
    assert abs(stats.mean - float(np.mean(arr))) < 1e-6
    assert stats.p75 > stats.p25
    assert stats.pixel_count == len(arr)


def test_pixel_stats_filters_nan():
    arr = np.array([0.3, float("nan"), 0.5, 0.4, float("nan"), 0.35, 0.45])
    stats = compute_pixel_stats(arr, total_pixel_count=len(arr))
    assert stats is not None
    assert stats.pixel_count == 5  # only non-NaN values


def test_pixel_stats_returns_none_too_few_valid():
    arr = np.array([0.3, float("nan"), float("nan"), float("nan")])
    stats = compute_pixel_stats(arr, total_pixel_count=len(arr))
    assert stats is None


def test_pixel_stats_valid_pct():
    # 7 valid pixels out of 10 total
    arr = np.array([0.3, 0.4, 0.5, 0.35, 0.45, 0.38, 0.42,
                    float("nan"), float("nan"), float("nan")])
    stats = compute_pixel_stats(arr, total_pixel_count=10)
    assert stats is not None
    assert abs(stats.valid_pixel_pct - 0.7) < 0.01


def test_pixel_stats_out_of_range_filtered():
    arr = np.array([0.3, 0.4, 99.0, -99.0, 0.5, 0.35, 0.45])
    stats = compute_pixel_stats(arr, total_pixel_count=len(arr))
    assert stats is not None
    assert stats.pixel_count == 5  # 99.0 and -99.0 filtered out
