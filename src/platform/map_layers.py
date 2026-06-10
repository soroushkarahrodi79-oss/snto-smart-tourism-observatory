"""
SNTO — PyDeck map layer builder for the territorial dashboard.

Replaces the Folium/Leaflet approach with Deck.gl / WebGL rendering.
All rendering happens client-side (GPU), so server RAM stays constant
regardless of how many assets are displayed — enabling scale to hundreds
of assets without Streamlit OOM errors.

Design
------
* `assets_to_geojson()` converts TerritorialAsset objects to a GeoJSON
  FeatureCollection. Geometry is approximate (municipality centroid +
  deterministic per-asset jitter) because real trail coordinates live in
  PostGIS / hiking_trails.geojson, not in the platform layer.

  For production: replace the centroid-based geometry with real coordinates
  read from geopandas::

      gdf = gpd.read_file("data/raw_assets/vector_data/hiking_trails.geojson")
      # merge with assets by name/id, then use gdf.geometry directly

* `build_pydeck_deck()` returns a pydeck.Deck with a single GeoJsonLayer
  so the browser receives one WebGL draw call per frame regardless of
  asset count (vs one Leaflet GeoJSON layer per asset in Folium).

* Tier colour encoding (matches sidebar legend):
    Tier 1 — Red     (Atención Inmediata)
    Tier 2 — Orange  (Acción Preventiva)
    Tier 3 — Blue    (Monitorización)
    Tier 4 — Green   (Promoción Activa)

Dependencies: pydeck>=0.9  (pip install pydeck)
"""
from __future__ import annotations

import math
from typing import Any

try:
    import pydeck as pdk
    _PYDECK_AVAILABLE = True
except ImportError:  # pragma: no cover
    pdk = None  # type: ignore[assignment]
    _PYDECK_AVAILABLE = False

# ── Geography: approximate centroids (WGS-84) per municipality ────────────────
# Source: IGN Nomenclátor Geográfico (municipios de la sierra norte, Madrid)
# Format: (latitude, longitude) — note GeoJSON uses [lon, lat]
_REGION_CENTROIDS: dict[str, tuple[float, float]] = {
    "Montejo de la Sierra":    (41.1700, -3.4830),
    "La Hiruela":              (41.1200, -3.4730),
    "Horcajuelo de la Sierra": (41.1630, -3.4330),
    "Puebla de la Sierra":     (41.0830, -3.4520),
    "Prádena del Rincón":      (41.1130, -3.4970),
    "Robregordo":              (41.1750, -3.5640),
}

# Fallback centroid for unknown regions (geographic centre of the reserve)
_DEFAULT_CENTROID = (41.130, -3.490)

# Map centre and initial zoom
_MAP_LATITUDE  = 41.130
_MAP_LONGITUDE = -3.490
_MAP_ZOOM      = 11

# ── Colour palette by tier (RGBA lists for Deck.gl / PyDeck) ─────────────────
TIER_COLORS: dict[int, list[int]] = {
    1: [220,  50,  50, 220],   # Red    — Atención Inmediata
    2: [230, 130,  20, 220],   # Orange — Acción Preventiva
    3: [ 50, 120, 200, 220],   # Blue   — Monitorización Rutinaria
    4: [ 40, 170,  80, 220],   # Green  — Promoción Activa
}
_TIER_COLOR_FALLBACK = [150, 150, 150, 180]

# Line colour is a slightly darker, fully-opaque variant of the fill
_TIER_LINE_COLORS: dict[int, list[int]] = {
    1: [160,  30,  30, 255],
    2: [180,  90,  10, 255],
    3: [ 20,  80, 160, 255],
    4: [ 20, 130,  50, 255],
}

# Human-readable labels for the legend widget
LEGEND_ITEMS: list[dict[str, Any]] = [
    {"tier": 1, "label": "Tier 1 — Atención Inmediata", "hex": "#dc3232"},
    {"tier": 2, "label": "Tier 2 — Acción Preventiva",  "hex": "#e68214"},
    {"tier": 3, "label": "Tier 3 — Monitorización",     "hex": "#3278c8"},
    {"tier": 4, "label": "Tier 4 — Promoción Activa",   "hex": "#28aa50"},
]

# Asset-type emoji for tooltips
_ASSET_EMOJI: dict[str, str] = {
    "TRAIL":             "🥾",
    "VIEWPOINT":         "🔭",
    "RECREATIONAL_AREA": "🌿",
    "NATURAL_PARK":      "🌲",
    "CYCLING_ROUTE":     "🚴",
}

# Metres per degree of latitude (near-constant globally)
_M_PER_DEG_LAT = 111_320.0


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _region_centroid(region: str) -> tuple[float, float]:
    """Return (lat, lon) for a region name, falling back to reserve centre."""
    return _REGION_CENTROIDS.get(region, _DEFAULT_CENTROID)


def _jitter(asset_id: str, lat: float, lon: float, spread: float = 0.007) -> tuple[float, float]:
    """Apply a deterministic, asset-specific offset within a region.

    Uses the asset_id hash so the same asset always appears at the same
    location across page reloads, while different assets in the same
    municipality are spread out (spread ≈ 700 m at 41 °N).
    """
    h = hash(asset_id) & 0xFFFF
    dlat = (((h >> 8) & 0xFF) / 255.0 - 0.5) * spread
    dlon = (((h      ) & 0xFF) / 255.0 - 0.5) * spread
    return lat + dlat, lon + dlon


def _trail_endpoints(
    lat: float, lon: float, length_km: float, heading_deg: float
) -> tuple[list[float], list[float]]:
    """Compute start and end [lon, lat] for a trail line.

    Positions the trail symmetrically around (lat, lon) with the given
    heading (0° = North, 90° = East) and total length *length_km*.
    """
    half_km = length_km / 2.0
    lat_rad = math.radians(lat)

    # Metres per degree of longitude at this latitude
    m_per_deg_lon = _M_PER_DEG_LAT * math.cos(lat_rad)

    heading_rad = math.radians(heading_deg)
    dlat_km =  math.cos(heading_rad) * half_km
    dlon_km =  math.sin(heading_rad) * half_km

    dlat_deg = dlat_km * 1000.0 / _M_PER_DEG_LAT
    dlon_deg = dlon_km * 1000.0 / m_per_deg_lon

    start = [lon - dlon_deg, lat - dlat_deg]   # [lon, lat] — GeoJSON order
    end   = [lon + dlon_deg, lat + dlat_deg]
    return start, end


def _heading_from_id(asset_id: str) -> float:
    """Return a deterministic compass heading (0-360°) for a trail."""
    h = (hash(asset_id) >> 16) & 0xFFFF
    return (h / 65535.0) * 360.0


def _point_radius_m(asset) -> float:
    """Return a display radius in metres appropriate for a point asset."""
    # Defaults by type — sized for zoom ~11 (≈ 1 px ≈ 30 m)
    defaults = {
        "VIEWPOINT":         60.0,
        "RECREATIONAL_AREA": 80.0,
        "NATURAL_PARK":      90.0,
    }
    return defaults.get(asset.asset_type, 70.0)


# ── GeoJSON feature builders ──────────────────────────────────────────────────

def _build_properties(asset) -> dict[str, Any]:
    """Shared GeoJSON property payload for all asset types."""
    tier     = asset.tier or 0
    color    = TIER_COLORS.get(tier, _TIER_COLOR_FALLBACK)
    lcolor   = _TIER_LINE_COLORS.get(tier, _TIER_COLOR_FALLBACK)
    emoji    = _ASSET_EMOJI.get(asset.asset_type, "📍")
    tier_lbl = (asset.tier_label or "Sin clasificar").replace("_", " ").title()
    desc     = (asset.description or "")[:120] + ("…" if len(asset.description or "") > 120 else "")

    return {
        "asset_id":    asset.asset_id,
        "name":        asset.name,
        "asset_type":  f"{emoji} {asset.asset_type.replace('_',' ').title()}",
        "region":      asset.region,
        "ehs":         round(asset.ehs, 1),
        "tier":        tier,
        "tier_label":  tier_lbl,
        "tpi":         round(asset.tpi, 1) if asset.tpi is not None else "—",
        "alert":       (asset.alert_level or "").replace("_", " "),
        "description": desc,
        # Deck.gl / GeoJsonLayer colour accessors
        "fill_color":  color,
        "line_color":  lcolor,
    }


def _trail_feature(asset) -> dict[str, Any]:
    """GeoJSON Feature (LineString) for a TRAIL asset."""
    lat, lon = _region_centroid(asset.region)
    lat, lon = _jitter(asset.asset_id, lat, lon, spread=0.006)
    length_km = asset.length_km or 2.0
    heading   = _heading_from_id(asset.asset_id)
    start, end = _trail_endpoints(lat, lon, length_km, heading)

    props = _build_properties(asset)
    props["length_km"] = asset.length_km or "—"
    props["elevation"] = f"{asset.elevation_m:.0f} m" if asset.elevation_m else "—"

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [start, end],
        },
        "properties": props,
    }


def _point_feature(asset) -> dict[str, Any]:
    """GeoJSON Feature (Point) for non-trail assets."""
    lat, lon = _region_centroid(asset.region)
    lat, lon = _jitter(asset.asset_id, lat, lon, spread=0.010)

    props = _build_properties(asset)
    props["point_radius"] = _point_radius_m(asset)
    props["area_ha"]  = f"{asset.area_ha:.1f} ha" if asset.area_ha else "—"
    props["elevation"] = f"{asset.elevation_m:.0f} m" if asset.elevation_m else "—"

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat],   # GeoJSON: [longitude, latitude]
        },
        "properties": props,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def assets_to_geojson(assets: list) -> dict[str, Any]:
    """Convert a list of TerritorialAsset objects to a GeoJSON FeatureCollection.

    Trail assets become LineString features; all other types become Point
    features. Properties include tier-coded colours ready for Deck.gl
    accessor expressions (``"properties.fill_color"``).

    Args:
        assets: Ranked TerritorialAsset objects (tier and tpi must be set).

    Returns:
        GeoJSON FeatureCollection dict — pass directly to
        ``pydeck.Layer("GeoJsonLayer", data=...)``.
    """
    features = []
    for asset in assets:
        if asset.asset_type in ("TRAIL", "CYCLING_ROUTE"):
            features.append(_trail_feature(asset))
        else:
            features.append(_point_feature(asset))
    return {"type": "FeatureCollection", "features": features}


def build_pydeck_deck(assets: list) -> "pdk.Deck":
    """Build a Deck.gl / PyDeck deck for the territorial asset portfolio.

    Uses a single ``GeoJsonLayer`` so the browser issues one WebGL draw
    call per frame regardless of asset count — O(1) GPU cost vs O(N)
    with one Folium layer per asset.

    Args:
        assets: Ranked TerritorialAsset objects (tier set by rank_assets()).

    Returns:
        pydeck.Deck ready for ``st.pydeck_chart()``.

    Raises:
        ImportError: if pydeck is not installed.
    """
    if not _PYDECK_AVAILABLE:
        raise ImportError(
            "pydeck is required for map rendering. "
            "Install it with: pip install pydeck"
        )

    geojson = assets_to_geojson(assets)

    tooltip = {
        "html": (
            "<div style='"
            "font-family:system-ui,sans-serif;"
            "padding:10px 12px;"
            "max-width:270px;"
            "line-height:1.5;"
            "'>"
            "<b style='font-size:13px'>{name}</b><br/>"
            "<span style='color:#a0b0c0;font-size:11px'>{asset_type} · {region}</span>"
            "<hr style='border:none;border-top:1px solid #2e4560;margin:6px 0'/>"
            "<b>EHS</b> {ehs}/100 &nbsp;·&nbsp; "
            "<b>Tier</b> {tier} — {tier_label}<br/>"
            "<span style='font-size:11px;color:#c8d6e5'>{alert}</span><br/>"
            "<span style='font-size:11px;color:#a0b0c0;margin-top:4px;display:block'>"
            "{description}</span>"
            "</div>"
        ),
        "style": {
            "background": "#1b2d42",
            "color": "white",
            "border-radius": "6px",
            "padding": "0",
            "box-shadow": "0 4px 12px rgba(0,0,0,.4)",
        },
    }

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
        # Point colour (fills circles, colours line rings)
        get_fill_color="properties.fill_color",
        get_line_color="properties.line_color",
        # Point-specific: radius in metres
        get_point_radius="properties.point_radius",
        point_radius_units="meters",
        point_radius_min_pixels=5,
        point_radius_max_pixels=18,
        # Line-specific: width in metres (trails)
        get_line_width=35,
        line_width_units="meters",
        line_width_min_pixels=2,
        line_width_max_pixels=8,
        # Polygon fill opacity is handled via fill_color alpha channel
        opacity=1.0,
    )

    view_state = pdk.ViewState(
        latitude=_MAP_LATITUDE,
        longitude=_MAP_LONGITUDE,
        zoom=_MAP_ZOOM,
        pitch=0,
        bearing=0,
    )

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    )


# ── Spectral diagnostic view ──────────────────────────────────────────────────

# RdYlGn colour ramp anchored at EHS breakpoints (ColorBrewer 5-class diverging).
# Each entry: (ehs_threshold, [R, G, B]).  Values between stops are interpolated.
_SPECTRAL_RAMP: list[tuple[float, list[int]]] = [
    (0.0,   [165,   0,  38]),   # deep red    — critical degradation
    (30.0,  [215,  48,  39]),   # red
    (45.0,  [253, 174,  97]),   # orange
    (60.0,  [255, 255, 191]),   # pale yellow — transitional
    (75.0,  [166, 217, 106]),   # yellow-green
    (100.0, [ 26, 152,  80]),   # deep green  — excellent health
]


def _ehs_to_rgba(ehs: float, alpha: int = 220) -> list[int]:
    """Interpolate an RGBA colour from the RdYlGn spectral ramp for a given EHS.

    Args:
        ehs   : Ecological Health Score 0-100.
        alpha : Opacity byte 0-255 (default 220).

    Returns:
        [R, G, B, A] list ready for Deck.gl colour accessors.
    """
    ehs = max(0.0, min(100.0, ehs))
    # Find the two surrounding stops
    for i in range(len(_SPECTRAL_RAMP) - 1):
        lo_val, lo_rgb = _SPECTRAL_RAMP[i]
        hi_val, hi_rgb = _SPECTRAL_RAMP[i + 1]
        if lo_val <= ehs <= hi_val:
            t = (ehs - lo_val) / (hi_val - lo_val) if hi_val != lo_val else 0.0
            r = int(lo_rgb[0] + t * (hi_rgb[0] - lo_rgb[0]))
            g = int(lo_rgb[1] + t * (hi_rgb[1] - lo_rgb[1]))
            b = int(lo_rgb[2] + t * (hi_rgb[2] - lo_rgb[2]))
            return [r, g, b, alpha]
    # Fallback — should not be reached
    return [128, 128, 128, alpha]


def _assets_to_geojson_spectral(assets: list) -> dict[str, Any]:
    """GeoJSON FeatureCollection with EHS-gradient colours (spectral diagnostic view).

    Identical geometry to assets_to_geojson() but replaces tier-coded colours
    with a continuous RdYlGn gradient derived from each asset's EHS score,
    simulating the NDVI/NDMI spectral signature of corridor degradation.
    """
    features = []
    for asset in assets:
        color  = _ehs_to_rgba(asset.ehs)
        lcolor = _ehs_to_rgba(asset.ehs, alpha=255)

        if asset.asset_type in ("TRAIL", "CYCLING_ROUTE"):
            feat = _trail_feature(asset)
        else:
            feat = _point_feature(asset)

        # Override tier colours with spectral colours
        feat["properties"]["fill_color"] = color
        feat["properties"]["line_color"] = lcolor
        features.append(feat)

    return {"type": "FeatureCollection", "features": features}


def build_pydeck_deck_spectral(assets: list) -> "pdk.Deck":
    """Build a Deck.gl deck using the EHS spectral-gradient colour scheme.

    Identical layer config to build_pydeck_deck() except colours encode
    ecological health (RdYlGn) rather than management tier.  Hover tooltip
    adds NDVI/NDMI context explaining the colour encoding.

    Args:
        assets: Ranked TerritorialAsset objects (ehs must be set).

    Returns:
        pydeck.Deck ready for st.pydeck_chart().

    Raises:
        ImportError: if pydeck is not installed.
    """
    if not _PYDECK_AVAILABLE:
        raise ImportError(
            "pydeck is required for map rendering. "
            "Install it with: pip install pydeck"
        )

    geojson = _assets_to_geojson_spectral(assets)

    tooltip = {
        "html": (
            "<div style='"
            "font-family:system-ui,sans-serif;"
            "padding:10px 12px;"
            "max-width:270px;"
            "line-height:1.5;"
            "'>"
            "<b style='font-size:13px'>{name}</b><br/>"
            "<span style='color:#a0b0c0;font-size:11px'>{asset_type} · {region}</span>"
            "<hr style='border:none;border-top:1px solid #2e4560;margin:6px 0'/>"
            "<b>EHS (Salud Ecológica)</b> {ehs}/100<br/>"
            "<span style='font-size:11px;color:#c8d6e5'>"
            "Color = gradiente espectral NDVI/NDMI · "
            "🟢 verde = saludable · 🔴 rojo = degradado"
            "</span><br/>"
            "<span style='font-size:11px;color:#a0b0c0;margin-top:4px;display:block'>"
            "{description}</span>"
            "</div>"
        ),
        "style": {
            "background": "#1b2d42",
            "color": "white",
            "border-radius": "6px",
            "padding": "0",
            "box-shadow": "0 4px 12px rgba(0,0,0,.4)",
        },
    }

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
        get_fill_color="properties.fill_color",
        get_line_color="properties.line_color",
        get_point_radius="properties.point_radius",
        point_radius_units="meters",
        point_radius_min_pixels=5,
        point_radius_max_pixels=18,
        get_line_width=35,
        line_width_units="meters",
        line_width_min_pixels=2,
        line_width_max_pixels=8,
        opacity=1.0,
    )

    view_state = pdk.ViewState(
        latitude=_MAP_LATITUDE,
        longitude=_MAP_LONGITUDE,
        zoom=_MAP_ZOOM,
        pitch=0,
        bearing=0,
    )

    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    )
