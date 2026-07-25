"""Contracts for the /api/v2 GeoJSON centroid helper (mobile Fase 2 map data).

Non-negotiable under test: malformed or absent geometry returns None, never a
fabricated coordinate.
"""
from __future__ import annotations

import json

from src.api.v2.geometry import centroid_of_geojson


def test_point_returns_its_own_coordinate() -> None:
    gj = json.dumps({"type": "Point", "coordinates": [-3.96, 40.82]})
    assert centroid_of_geojson(gj) == (40.82, -3.96)


def test_linestring_averages_vertices() -> None:
    gj = json.dumps(
        {"type": "LineString", "coordinates": [[0.0, 0.0], [2.0, 2.0]]}
    )
    assert centroid_of_geojson(gj) == (1.0, 1.0)


def test_polygon_averages_ring_vertices() -> None:
    gj = json.dumps(
        {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 2.0], [2.0, 2.0], [2.0, 0.0]]],
        }
    )
    lat, lon = centroid_of_geojson(gj)
    assert lat == 1.0
    assert lon == 1.0


def test_feature_wrapper_is_unwrapped() -> None:
    gj = json.dumps(
        {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Point", "coordinates": [1.5, 2.5]},
        }
    )
    assert centroid_of_geojson(gj) == (2.5, 1.5)


def test_empty_geometry_returns_none() -> None:
    assert centroid_of_geojson(json.dumps({"type": "Point", "coordinates": []})) is None


def test_malformed_json_returns_none_not_raise() -> None:
    assert centroid_of_geojson("{not json") is None


def test_missing_coordinates_key_returns_none() -> None:
    assert centroid_of_geojson(json.dumps({"type": "Point"})) is None


def test_non_dict_json_returns_none() -> None:
    assert centroid_of_geojson(json.dumps([1, 2, 3])) is None


def test_placeholder_point_geometry_used_in_tests_still_centroids() -> None:
    # the repo's existing test seed geometry: '{"type": "Point", "coordinates": [0, 0]}'
    assert centroid_of_geojson('{"type": "Point", "coordinates": [0, 0]}') == (0.0, 0.0)
