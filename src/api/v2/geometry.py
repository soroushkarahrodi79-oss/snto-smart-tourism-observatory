"""Lightweight GeoJSON centroid for /api/v2 read responses (v3.0, mobile Fase 2).

``ManagedAsset.geometry_geojson`` already stores real geometry (opaque ``Text``
today — PostGIS is future work per the v3 roadmap), but nothing in `/api/v2`
exposed a coordinate a client could drop a map pin on. This module is a small,
dependency-free centroid — deliberately **not** importing ``shapely``
(``src.geospatial.geometry`` already does real geometric analysis for the
Pipeline A/B analytical core; that is a different, heavier layer with a
different job). This one only answers "roughly where is this asset", for a
read-only map marker, with plain arithmetic over the GeoJSON coordinate
arrays.

Degrades honestly: malformed or unsupported geometry returns ``None`` — never
a fabricated coordinate (ADR-004).
"""
from __future__ import annotations

import json


def _flatten_coordinates(coords) -> list[tuple[float, float]]:  # noqa: ANN001
    """Recursively collect every [lon, lat] pair out of a GeoJSON coordinates tree."""
    if not coords:
        return []
    # A leaf coordinate pair looks like [lon, lat] (both numbers).
    if (
        len(coords) >= 2
        and isinstance(coords[0], (int, float))
        and isinstance(coords[1], (int, float))
    ):
        return [(float(coords[0]), float(coords[1]))]
    points: list[tuple[float, float]] = []
    for item in coords:
        points.extend(_flatten_coordinates(item))
    return points


def centroid_of_geojson(geojson_text: str) -> tuple[float, float] | None:
    """Return (latitude, longitude) — the plain arithmetic mean of every vertex.

    Supports Point/LineString/Polygon/MultiPoint/MultiLineString/MultiPolygon
    (any nesting of a GeoJSON ``coordinates`` array) and a bare Feature. Returns
    ``None`` for empty, malformed, or unparseable input — never a guessed point.
    """
    try:
        geom = json.loads(geojson_text)
    except (TypeError, ValueError):
        return None
    if not isinstance(geom, dict):
        return None
    if geom.get("type") == "Feature":
        geom = geom.get("geometry") or {}
    coords = geom.get("coordinates")
    points = _flatten_coordinates(coords)
    if not points:
        return None
    lat = sum(p[1] for p in points) / len(points)
    lon = sum(p[0] for p in points) / len(points)
    return (lat, lon)
