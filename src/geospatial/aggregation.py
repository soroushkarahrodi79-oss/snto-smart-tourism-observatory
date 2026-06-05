from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from src.assets.models import GeometryType, SpatialStats, TourismAsset

# Buffer distances for non-polygon assets — chosen to guarantee ≥ 5 pixels
# at Sentinel-2 10 m resolution even for the shortest trail segments.
TRAIL_BUFFER_M: int = 30
POINT_BUFFER_M: int = 50

# WGS84 degrees-to-metres approximation constants (adequate for < 100 km extent)
_M_PER_DEG_LAT = 111_320.0


def buffer_asset_geometry(asset: TourismAsset, buffer_m: Optional[int] = None) -> "Shapely geometry":
    """
    Return a Shapely geometry representing the aggregation footprint for an asset.

    - LineString trails → buffer to a corridor polygon
    - Point viewpoints → buffer to a circle polygon
    - Polygon recreational areas → returned as-is (no buffer)

    The buffer is performed in approximate metres using a local planar
    approximation at the asset centroid latitude.  For production, reproject
    to ETRS89 / UTM zone 29N (EPSG:25829) before buffering.
    """
    geojson = {
        "type": asset.geometry.type.value,
        "coordinates": asset.geometry.coordinates,
    }
    geom = shape(geojson)
    gtype = asset.geometry.type

    if gtype == GeometryType.POLYGON:
        return geom

    # Local scale factors at centroid latitude
    centroid_lat = geom.centroid.y
    lat_rad = math.radians(centroid_lat)
    m_per_deg_lon = _M_PER_DEG_LAT * math.cos(lat_rad)

    if buffer_m is None:
        buffer_m = TRAIL_BUFFER_M if gtype == GeometryType.LINESTRING else POINT_BUFFER_M

    # Convert metres to degrees for a planar-approximate buffer
    # Use the geometric mean of lon and lat scales for an isotropic buffer
    deg_per_m_lat = 1.0 / _M_PER_DEG_LAT
    deg_per_m_lon = 1.0 / m_per_deg_lon
    buffer_deg = buffer_m * math.sqrt(deg_per_m_lat * deg_per_m_lon)

    return geom.buffer(buffer_deg)


@dataclass(frozen=True)
class PixelStats:
    """Statistics computed from a numpy array of valid pixel values."""
    mean: float
    median: float
    p25: float
    p75: float
    std: float
    pixel_count: int
    valid_pixel_pct: float


def compute_pixel_stats(
    pixel_values: np.ndarray,
    total_pixel_count: int,
    nodata: float = float("nan"),
) -> Optional[PixelStats]:
    """
    Compute distribution statistics from a flat array of pixel values.

    Filters out nodata / NaN values before computing statistics.
    Returns None if fewer than 5 valid pixels remain.

    Args:
        pixel_values: 1D array of raw index values (already scaled to [-1, 1]).
        total_pixel_count: total pixels in the geometry (valid + masked).
        nodata: value to treat as invalid (in addition to NaN).
    """
    arr = pixel_values.astype(float).ravel()
    # Mask nodata and out-of-range values
    valid_mask = ~np.isnan(arr)
    if not math.isnan(nodata):
        valid_mask &= arr != nodata
    # Sentinel-2 SR reflectance indices are in [-1, 1]
    valid_mask &= (arr >= -1.0) & (arr <= 1.0)

    valid = arr[valid_mask]
    if len(valid) < 5:
        return None

    return PixelStats(
        mean=float(np.mean(valid)),
        median=float(np.median(valid)),
        p25=float(np.percentile(valid, 25)),
        p75=float(np.percentile(valid, 75)),
        std=float(np.std(valid)),
        pixel_count=int(len(valid)),
        valid_pixel_pct=round(len(valid) / max(1, total_pixel_count), 3),
    )


def pixel_stats_to_spatial_stats(ps: PixelStats) -> SpatialStats:
    """Convert internal PixelStats dataclass to the Pydantic SpatialStats model."""
    return SpatialStats(
        mean=ps.mean,
        median=ps.median,
        p25=ps.p25,
        p75=ps.p75,
        std=ps.std,
        pixel_count=ps.pixel_count,
        valid_pixel_pct=ps.valid_pixel_pct,
    )
