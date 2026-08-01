"""ManagedAssetRepository — CRUD + lifecycle/territory lookups (Fase 5, 5.2).

The spatial lookups (``list_within_distance`` / ``list_intersecting``, v3.0)
run in-DB against the PostGIS ``geom`` column and therefore only work on a
PostgreSQL/PostGIS backend; on SQLite (dev/tests) they raise
``PostGISUnavailable`` rather than silently returning wrong answers.
"""
from __future__ import annotations

import json
import math
from typing import Any, cast

from geoalchemy2 import Geography
from sqlalchemy import cast as sql_cast
from sqlalchemy import func, select

from src.persistence.enums import ManagedAssetStatus
from src.persistence.models.managed_asset import ManagedAsset
from src.persistence.repositories.base import Repository


class PostGISUnavailable(RuntimeError):
    """Raised when a spatial query is attempted on a non-PostGIS backend."""


class SpatialQueryValidationError(ValueError):
    """Raised before SQL execution when spatial-query input is invalid."""


def _validate_territory_id(territory_id: int) -> int:
    if isinstance(territory_id, bool) or not isinstance(territory_id, int):
        raise SpatialQueryValidationError("territory_id must be an integer")
    if territory_id <= 0:
        raise SpatialQueryValidationError("territory_id must be greater than zero")
    return territory_id


def _finite_number(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpatialQueryValidationError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise SpatialQueryValidationError(f"{name} must be a finite number")
    return number


def _position(value: object, *, label: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) < 2:
        raise SpatialQueryValidationError(
            f"{label} must contain longitude and latitude"
        )
    lon = _finite_number(value[0], name=f"{label} longitude")
    lat = _finite_number(value[1], name=f"{label} latitude")
    if not -180.0 <= lon <= 180.0:
        raise SpatialQueryValidationError(
            f"{label} longitude must be between -180 and 180"
        )
    if not -90.0 <= lat <= 90.0:
        raise SpatialQueryValidationError(
            f"{label} latitude must be between -90 and 90"
        )
    return lon, lat


def _position_sequence(
    value: object, *, label: str, minimum: int
) -> list[tuple[float, float]]:
    if not isinstance(value, list) or len(value) < minimum:
        raise SpatialQueryValidationError(
            f"{label} must contain at least {minimum} coordinate positions"
        )
    return [
        _position(item, label=f"{label}[{index}]")
        for index, item in enumerate(value)
    ]


def _polygon(value: object, *, label: str) -> None:
    if not isinstance(value, list) or not value:
        raise SpatialQueryValidationError(f"{label} must contain at least one ring")
    for index, ring in enumerate(value):
        positions = _position_sequence(
            ring, label=f"{label}[{index}]", minimum=4
        )
        if positions[0] != positions[-1]:
            raise SpatialQueryValidationError(
                f"{label}[{index}] must be a closed linear ring"
            )


def _validate_geometry(geometry: dict[str, Any], *, label: str = "GeoJSON") -> None:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        _position(coordinates, label=f"{label} Point")
    elif geometry_type == "MultiPoint":
        _position_sequence(coordinates, label=f"{label} MultiPoint", minimum=1)
    elif geometry_type == "LineString":
        _position_sequence(coordinates, label=f"{label} LineString", minimum=2)
    elif geometry_type == "MultiLineString":
        if not isinstance(coordinates, list) or not coordinates:
            raise SpatialQueryValidationError(
                f"{label} MultiLineString must contain at least one line"
            )
        for index, line in enumerate(coordinates):
            _position_sequence(
                line,
                label=f"{label} MultiLineString[{index}]",
                minimum=2,
            )
    elif geometry_type == "Polygon":
        _polygon(coordinates, label=f"{label} Polygon")
    elif geometry_type == "MultiPolygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise SpatialQueryValidationError(
                f"{label} MultiPolygon must contain at least one polygon"
            )
        for index, polygon in enumerate(coordinates):
            _polygon(polygon, label=f"{label} MultiPolygon[{index}]")
    elif geometry_type == "GeometryCollection":
        geometries = geometry.get("geometries")
        if not isinstance(geometries, list) or not geometries:
            raise SpatialQueryValidationError(
                f"{label} GeometryCollection must contain at least one geometry"
            )
        for index, item in enumerate(geometries):
            if not isinstance(item, dict):
                raise SpatialQueryValidationError(
                    f"{label} GeometryCollection[{index}] must be an object"
                )
            _validate_geometry(
                cast(dict[str, Any], item),
                label=f"{label} GeometryCollection[{index}]",
            )
    else:
        raise SpatialQueryValidationError(
            "GeoJSON must be a geometry fragment or a Feature containing one"
        )


def _normalise_geojson_geometry(geojson: str) -> str:
    if not isinstance(geojson, str) or not geojson.strip():
        raise SpatialQueryValidationError("geojson must be a non-empty JSON string")
    try:
        parsed = json.loads(geojson)
    except (TypeError, ValueError) as exc:
        raise SpatialQueryValidationError("geojson is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise SpatialQueryValidationError("GeoJSON must be a JSON object")
    payload = cast(dict[str, Any], parsed)
    if "crs" in payload:
        raise SpatialQueryValidationError(
            "GeoJSON CRS must be omitted; coordinates are interpreted as EPSG:4326"
        )
    if payload.get("type") == "Feature":
        candidate = payload.get("geometry")
        if not isinstance(candidate, dict):
            raise SpatialQueryValidationError(
                "GeoJSON Feature must contain a non-null geometry object"
            )
        geometry = cast(dict[str, Any], candidate)
    else:
        geometry = payload
    if "crs" in geometry:
        raise SpatialQueryValidationError(
            "GeoJSON CRS must be omitted; coordinates are interpreted as EPSG:4326"
        )
    _validate_geometry(geometry)
    return json.dumps(geometry, separators=(",", ":"), allow_nan=False)


class ManagedAssetRepository(Repository[ManagedAsset]):
    model = ManagedAsset

    def _require_postgis(self) -> None:
        """Guard: spatial SQL is only valid on PostgreSQL/PostGIS."""
        if self.session.get_bind().dialect.name != "postgresql":
            raise PostGISUnavailable(
                "spatial queries require a PostgreSQL/PostGIS backend; the "
                "active engine is "
                f"{self.session.get_bind().dialect.name!r}"
            )

    def get_by_external_id(self, external_asset_id: str) -> ManagedAsset | None:
        return self.session.scalars(
            select(ManagedAsset).where(
                ManagedAsset.external_asset_id == external_asset_id
            )
        ).first()

    def list_by_territory(self, territory_id: int) -> list[ManagedAsset]:
        return list(
            self.session.scalars(
                select(ManagedAsset).where(ManagedAsset.territory_id == territory_id)
            )
        )

    def list_by_status(self, status: ManagedAssetStatus) -> list[ManagedAsset]:
        return list(
            self.session.scalars(
                select(ManagedAsset).where(ManagedAsset.status == status)
            )
        )

    def list_within_distance(
        self,
        territory_id: int,
        *,
        lon: float,
        lat: float,
        meters: float,
    ) -> list[ManagedAsset]:
        """Territory assets within ``meters`` of an EPSG:4326 point.

        Distance is measured on the spheroid (``geography`` cast), so ``meters``
        is true ground distance regardless of latitude. Rows with ``geom IS
        NULL`` (absent/invalid GeoJSON) are excluded. PostGIS-only.
        """
        territory_id = _validate_territory_id(territory_id)
        lon = _finite_number(lon, name="longitude")
        lat = _finite_number(lat, name="latitude")
        meters = _finite_number(meters, name="meters")
        if not -180.0 <= lon <= 180.0:
            raise SpatialQueryValidationError(
                "longitude must be between -180 and 180"
            )
        if not -90.0 <= lat <= 90.0:
            raise SpatialQueryValidationError("latitude must be between -90 and 90")
        if meters < 0.0:
            raise SpatialQueryValidationError(
                "meters must be greater than or equal to zero"
            )
        self._require_postgis()
        point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        stmt = select(ManagedAsset).where(
            ManagedAsset.territory_id == territory_id,
            ManagedAsset.geom.isnot(None),
            func.ST_DWithin(
                sql_cast(ManagedAsset.geom, Geography(srid=4326)),
                sql_cast(point, Geography(srid=4326)),
                meters,
            ),
        )
        return list(self.session.scalars(stmt))

    def list_intersecting(
        self, territory_id: int, *, geojson: str
    ) -> list[ManagedAsset]:
        """Territory assets intersecting an EPSG:4326 GeoJSON geometry.

        A geometry fragment or a Feature is accepted. Invalid, empty,
        out-of-range, or explicitly-CRS-tagged input raises a typed validation
        error before SQL runs. Rows with ``geom IS NULL`` are excluded.
        """
        territory_id = _validate_territory_id(territory_id)
        geometry = _normalise_geojson_geometry(geojson)
        self._require_postgis()
        other = func.ST_SetSRID(func.ST_GeomFromGeoJSON(geometry), 4326)
        stmt = select(ManagedAsset).where(
            ManagedAsset.territory_id == territory_id,
            ManagedAsset.geom.isnot(None),
            func.ST_Intersects(ManagedAsset.geom, other),
        )
        return list(self.session.scalars(stmt))
