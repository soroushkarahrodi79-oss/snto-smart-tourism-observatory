from __future__ import annotations

import math
from typing import Optional

from shapely.geometry import shape

from src.assets.models import GeometryType, TourismAsset

_M_PER_DEG_LAT = 111_320.0  # metres per degree of latitude (near-constant globally)


def _to_shapely(asset: TourismAsset):
    geojson = {"type": asset.geometry.type.value, "coordinates": asset.geometry.coordinates}
    return shape(geojson)


def _centroid_lat_rad(asset: TourismAsset) -> float:
    """Latitude of the asset centroid in radians — used for lon→metre conversion."""
    geom = _to_shapely(asset)
    return math.radians(geom.centroid.y)


def get_centroid(asset: TourismAsset) -> tuple[float, float]:
    """Return (longitude, latitude) of asset centroid."""
    geom = _to_shapely(asset)
    c = geom.centroid
    return (c.x, c.y)


def get_area_ha(asset: TourismAsset) -> Optional[float]:
    """
    Return area in hectares for polygon assets using the asset's own centroid
    latitude for the degree-to-metre conversion. Accurate to < 1% for sites
    up to ~100 km². For production, reproject to a metric CRS (UTM).
    Returns None for non-polygon assets.
    """
    if asset.geometry.type != GeometryType.POLYGON:
        return None
    geom = _to_shapely(asset)
    lat_rad = _centroid_lat_rad(asset)
    m_per_deg_lon = _M_PER_DEG_LAT * math.cos(lat_rad)
    area_m2 = abs(geom.area) * _M_PER_DEG_LAT * m_per_deg_lon
    return area_m2 / 10_000.0  # m² → ha


def get_length_km(asset: TourismAsset) -> Optional[float]:
    """
    Return approximate length in km for linear (trail) assets.
    Uses the asset's centroid latitude for degree-to-metre conversion.
    Returns None for non-LineString assets.
    """
    if asset.geometry.type != GeometryType.LINESTRING:
        return None
    geom = _to_shapely(asset)
    lat_rad = _centroid_lat_rad(asset)
    m_per_deg_lon = _M_PER_DEG_LAT * math.cos(lat_rad)
    coords = list(geom.coords)
    total = 0.0
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        dx = (x2 - x1) * m_per_deg_lon
        dy = (y2 - y1) * _M_PER_DEG_LAT
        total += math.sqrt(dx**2 + dy**2)
    return total / 1_000.0


def enrich_asset_geometry(asset: TourismAsset) -> TourismAsset:
    """
    Return a copy of the asset with area_ha and metadata enriched.
    Does not mutate the original.
    """
    centroid = get_centroid(asset)
    area_ha = get_area_ha(asset)
    length_km = get_length_km(asset)

    extra: dict = {
        "centroid_lon": centroid[0],
        "centroid_lat": centroid[1],
    }
    if area_ha is not None:
        extra["area_ha"] = area_ha
    if length_km is not None:
        extra["length_km"] = length_km

    updated_metadata = {**asset.metadata, **extra}
    return asset.model_copy(update={"area_ha": area_ha, "metadata": updated_metadata})
