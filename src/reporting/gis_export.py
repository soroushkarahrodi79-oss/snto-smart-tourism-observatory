"""
GIS export of SNTO assets + trends + evidence level (issue #25).

WHY
===
SNTO is a decision-intelligence layer, not a GIS. A park's technical staff
already live in QGIS/ArcGIS, so the most useful integration is to hand them the
observatory's conclusions as a standard geospatial layer they can drop straight
into their own project — assets with their real Sentinel-2 trend, the v1.3.0
confidence signal and, crucially, an explicit **evidence level** so nobody
mistakes a calibrated reconstruction for a direct observation.

This module joins the asset geometry (official OAPN cartography) with the real
trend record (``src/platform/satellite_trends``) and emits:

  * **GeoJSON** — universal, dependency-free, always available;
  * **GeoPackage** — the OGC standard QGIS/ArcGIS prefer, when ``geopandas`` is
    installed (it is, per requirements).

Every exported feature carries an ``evidence_level`` property
(``real``/``calibrated``/``synthetic``/``missing`` — the project's existing
vocabulary, ``src/temporal/manifest.DataStatus``) so the trust tier travels
with the data into the external tool. Assets without a matching trend keep
their geometry, get null trend fields and ``has_trend=false`` — never a
fabricated value (non-negotiable: do not blur evidence).

Multi-park by design: the assembler resolves geometry + trends per ``park``
slug (default ``pnsg``), mirroring the v1.2.0 pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from src._version import __version__
from src.temporal.manifest import DataStatus

if TYPE_CHECKING:
    from src.platform.satellite_trends import AssetTrend

_DEFAULT_PROVENANCE = (
    "SNTO — geometría cartografía oficial OAPN; tendencia Sentinel-2 real "
    "(Mann-Kendall desestacionalizado + IC 95% de Sen, v1.3.0)."
)


def _trend_properties(trend: AssetTrend | None) -> dict:
    """Flat, GeoJSON-safe (scalar-only) properties for one asset's trend."""
    if trend is None:
        return {
            "has_trend": False,
            "trend": None,
            "tau": None,
            "p_value": None,
            "trend_significant": None,
            "is_degrading": None,
            "sens_slope": None,
            "sens_slope_ci_low": None,
            "sens_slope_ci_high": None,
            "n_observations": None,
        }
    ci = trend.sens_slope_ci
    return {
        "has_trend": True,
        "trend": trend.trend,
        "tau": round(trend.tau, 4),
        "p_value": round(trend.p_value, 4),
        "trend_significant": trend.significant,
        "is_degrading": trend.is_alert,
        "sens_slope": trend.sens_slope,
        "sens_slope_ci_low": ci[0] if ci else None,
        "sens_slope_ci_high": ci[1] if ci else None,
        "n_observations": trend.n_observations,
    }


def build_feature_collection(
    assets: dict,
    trends: list[AssetTrend] | None = None,
    *,
    ehs_by_id: dict[str, float] | None = None,
    evidence_level: DataStatus = DataStatus.REAL,
    provenance: str = _DEFAULT_PROVENANCE,
    park: str = "pnsg",
) -> dict:
    """Join an assets FeatureCollection with trend/EHS data + evidence label.

    ``assets`` is a GeoJSON FeatureCollection dict; each feature must expose an
    ``asset_id`` property. Geometry is preserved verbatim. Missing trend/EHS
    degrade to explicit nulls, never fabricated values.
    """
    trends_by_id = {t.asset_id: t for t in (trends or [])}
    ehs_by_id = ehs_by_id or {}

    out_features = []
    for feat in assets.get("features", []):
        props = dict(feat.get("properties", {}))
        asset_id = props.get("asset_id")
        trend = trends_by_id.get(asset_id)

        props.update(_trend_properties(trend))
        props["ehs"] = ehs_by_id.get(asset_id)
        props["evidence_level"] = evidence_level.value
        props["provenance"] = provenance
        props["park"] = park

        out_features.append({
            "type": "Feature",
            "geometry": feat.get("geometry"),
            "properties": props,
        })

    return {
        "type": "FeatureCollection",
        "metadata": {
            "system": "Smart Natural Tourism Observatory (SNTO)",
            "version": __version__,
            "park": park,
            "evidence_level": evidence_level.value,
            "feature_count": len(out_features),
            "features_with_trend": sum(
                1 for f in out_features if f["properties"]["has_trend"]
            ),
        },
        "features": out_features,
    }


def export_geojson(fc: dict, path: str | Path) -> Path:
    """Write the FeatureCollection to a .geojson file. Always available."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    return path


def export_geopackage(
    fc: dict, path: str | Path, *, layer: str = "snto_assets"
) -> Path:
    """Write the FeatureCollection to an OGC GeoPackage (.gpkg).

    Requires ``geopandas``. Raises ``RuntimeError`` with an actionable message
    if it is unavailable, so callers can fall back to GeoJSON. GeoPackage
    columns must be scalar, which ``build_feature_collection`` already
    guarantees; the top-level ``metadata`` block is dropped (GPKG has no place
    for it — it lives in the GeoJSON sibling).
    """
    try:
        import geopandas as gpd  # noqa: PLC0415 — optional heavy dep, import on use
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "GeoPackage export requires geopandas. Install it or use "
            "export_geojson() instead."
        ) from exc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf = gpd.GeoDataFrame.from_features(fc["features"], crs="EPSG:4326")
    gdf.to_file(path, layer=layer, driver="GPKG")
    return path
