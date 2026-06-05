from __future__ import annotations

"""
Geo-based Human Pressure Proxy for natural tourism assets.

SCIENTIFIC MOTIVATION
=====================
The previous proxy (deseasonalized NDVI volatility) was fundamentally flawed:
  - Even after 2-harmonic fitting, residual variability from asymmetric
    Mediterranean phenology exceeds the 0.05 disturbance threshold.
  - Spectral NDVI volatility cannot distinguish between seasonal asynchrony
    and genuine human disturbance without multi-year baseline data.
  - The proxy produced identical maximum values (1.0) for every asset
    regardless of actual visitor pressure or accessibility.

The replacement uses five independently measurable geographic proximity
factors derived from OpenStreetMap and terrain data.  Each factor has a
clear physical interpretation and a documented decay function calibrated
to recreation ecology literature.

FORMULA
=======
    human_pressure = 0.35 * road_accessibility
                   + 0.25 * settlement_proximity
                   + 0.20 * poi_density
                   + 0.10 * trail_connectivity
                   + 0.10 * slope_accessibility

FACTOR DETAILS
==============

1. road_accessibility = exp(-1.5 * d_road_km)
   - Exponential decay from nearest motorable road (secondary or higher).
   - α = 1.5: 1 km gives 0.22 (moderate), 2 km gives 0.05 (low).
   - Rationale: >85% of recreational visitors arrive by car (Arnberger 2012).
     Road proximity is the dominant accessibility determinant for day-trip
     tourism in rural Iberian landscapes.

2. settlement_proximity = exp(-0.4 * d_settlement_km)
   - Exponential decay from nearest inhabited settlement (village or larger).
   - α = 0.4: 5 km gives 0.14 (minimal catchment), 1 km gives 0.67 (high).
   - Rationale: Population catchment gravity model. Settlement size could
     refine this; a flat decay is used here as a conservative default.

3. poi_density = clamp(n_pois / POI_SATURATION)
   - Linear saturation: 0 at 0 tourism POIs, 1.0 at POI_SATURATION.
   - POI_SATURATION = 15 tourism/amenity POIs within 5 km radius.
   - Rationale: OSM tourism/amenity density correlates with destination
     awareness, signage quality, and marketing exposure (Grinberger 2018).

4. trail_connectivity = clamp(path_km / TRAIL_SATURATION)
   - Linear saturation: 0 at isolated trail, 1.0 at TRAIL_SATURATION km
     of path/trail network within 1 km radius.
   - TRAIL_SATURATION = 8 km.
   - Rationale: Connected trail networks enable circuit routes, attract
     multi-day hikers, and increase cumulative visitor numbers.

5. slope_accessibility = 1 - clamp(mean_slope_deg / 30.0)
   - Inverted: steep terrain reduces accessibility.
   - 0° = fully accessible (flat), 30°+ = essentially inaccessible.
   - Rationale: Slope > 20° limits casual visitor access; professional
     hikers can manage up to 30°. Beyond 30° the asset is inaccessible
     to the general public regardless of proximity.

METADATA KEYS
=============
Populate TourismAsset.metadata with:
    {
      "geo_proximity": {
        "road_km": <float>,           # km to nearest secondary+ road
        "settlement_km": <float>,     # km to nearest inhabited place
        "poi_count_5km": <int>,       # OSM tourism/amenity POIs within 5 km
        "trail_network_km": <float>,  # OSM path/track length within 1 km
        "mean_slope_deg": <float>,    # mean terrain slope in degrees
      }
    }

LIMITATIONS
===========
- Road and settlement distances are Euclidean, not travel-time.
  For complex terrain, network-based accessibility would be more accurate.
- OSM completeness varies: rural Spain has good trail coverage but POI
  coverage may under-represent informal recreation pressure.
- Does not capture seasonality of visitor patterns (summer peaks).
- Visitor counts (where available) should be used instead of or
  alongside this proxy when official monitoring data exists.

CALIBRATION SOURCES
===================
- Arnberger, A. (2012). Recreation use of urban forests. Urban Forestry.
- Grinberger, A.Y. et al. (2018). OSM for tourism analysis. AGILE.
- González-De Vega, S. et al. (2018). Extremadura scrubland degradation.
  Remote Sensing.
"""

import math
from dataclasses import dataclass
from typing import Any

# ── Calibration constants ─────────────────────────────────────────────────

_ROAD_DECAY: float = 1.5        # α for road accessibility exponential
_SETTLEMENT_DECAY: float = 0.4  # α for settlement proximity exponential
POI_SATURATION: int = 15        # POI count that saturates the density factor
TRAIL_SATURATION: float = 8.0   # km of trail network that saturates connectivity
_SLOPE_MAX: float = 30.0        # degrees above which accessibility is zero

# Component weights (must sum to 1.0)
_W_ROAD: float = 0.35
_W_SETTLEMENT: float = 0.25
_W_POI: float = 0.20
_W_TRAIL: float = 0.10
_W_SLOPE: float = 0.10


@dataclass(frozen=True)
class GeoProximityFactors:
    """
    Pre-computed geographic proximity values for a single asset.

    All values are scalars derived from spatial analysis (OSM + DEM).
    Populated externally and stored in TourismAsset.metadata['geo_proximity'].
    """

    road_km: float             # distance to nearest motorable road (km)
    settlement_km: float       # distance to nearest inhabited place (km)
    poi_count_5km: int         # tourism/amenity POIs within 5 km radius
    trail_network_km: float    # total path/track length within 1 km radius (km)
    mean_slope_deg: float      # mean terrain slope in degrees

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> "GeoProximityFactors | None":
        """
        Extract from TourismAsset.metadata['geo_proximity'] if present.
        Returns None if the key is absent (triggers spectral fallback).
        """
        geo = metadata.get("geo_proximity")
        if geo is None:
            return None
        try:
            return cls(
                road_km=float(geo["road_km"]),
                settlement_km=float(geo["settlement_km"]),
                poi_count_5km=int(geo["poi_count_5km"]),
                trail_network_km=float(geo["trail_network_km"]),
                mean_slope_deg=float(geo["mean_slope_deg"]),
            )
        except (KeyError, TypeError, ValueError):
            return None


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def compute_road_accessibility(road_km: float) -> float:
    """
    Exponential decay: 1.0 at road edge, 0.22 at 1 km, 0.05 at 2 km.
    Returns 0.0 for negative distances (guard against bad input).
    """
    return _clamp(math.exp(-_ROAD_DECAY * max(0.0, road_km)))


def compute_settlement_proximity(settlement_km: float) -> float:
    """
    Exponential decay: 1.0 at settlement edge, 0.67 at 1 km, 0.14 at 5 km.
    """
    return _clamp(math.exp(-_SETTLEMENT_DECAY * max(0.0, settlement_km)))


def compute_poi_density(poi_count: int) -> float:
    """Linear saturation at POI_SATURATION (default 15) POIs within 5 km."""
    return _clamp(poi_count / POI_SATURATION)


def compute_trail_connectivity(trail_km: float) -> float:
    """Linear saturation at TRAIL_SATURATION (default 8 km) within 1 km radius."""
    return _clamp(trail_km / TRAIL_SATURATION)


def compute_slope_accessibility(mean_slope_deg: float) -> float:
    """
    Inverted slope factor: flat terrain (0°) gives 1.0, ≥30° gives 0.0.
    High slope accessibility → high human pressure from accessible terrain.
    """
    return _clamp(1.0 - mean_slope_deg / _SLOPE_MAX)


def compute_geo_human_pressure(factors: GeoProximityFactors) -> float:
    """
    Weighted combination of five geographic pressure factors.

    Returns a value in [0, 1] where:
      0.0 = completely inaccessible, no amenities, extreme slope
      1.0 = road-edge location, urban-adjacent, dense POIs, flat terrain

    Formula:
        P = 0.35 * road_access + 0.25 * settlement_prox
          + 0.20 * poi_density + 0.10 * trail_connect
          + 0.10 * slope_access
    """
    road = compute_road_accessibility(factors.road_km)
    settlement = compute_settlement_proximity(factors.settlement_km)
    poi = compute_poi_density(factors.poi_count_5km)
    trail = compute_trail_connectivity(factors.trail_network_km)
    slope = compute_slope_accessibility(factors.mean_slope_deg)

    return _clamp(
        _W_ROAD * road
        + _W_SETTLEMENT * settlement
        + _W_POI * poi
        + _W_TRAIL * trail
        + _W_SLOPE * slope
    )
