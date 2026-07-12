"""Unit tests for the GIS export (issue #25)."""

from __future__ import annotations

import json

from src.platform.satellite_trends import AssetTrend
from src.reporting.gis_export import (
    build_feature_collection,
    export_geojson,
)
from src.temporal.manifest import DataStatus


def _assets_fc() -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-3.8, 41.0]},
                "properties": {
                    "asset_id": "a1", "name": "Uno", "category": "senderismo",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-3.7, 40.9]},
                "properties": {"asset_id": "a2", "name": "Dos", "category": "ciclismo"},
            },
        ],
    }


def _trend(asset_id: str) -> AssetTrend:
    return AssetTrend(
        asset_id=asset_id,
        category="senderismo",
        n_observations=60,
        tau=-0.31,
        p_value=0.012,
        trend="decreasing",
        annual_mean_ndvi={"2021": 0.4},
        partial_years=[],
        worst_year="2022",
        best_year="2024",
        ndvi_min=0.2,
        ndvi_max=0.5,
        sens_slope=-0.001,
        sens_slope_ci=(-0.003, -0.0005),
    )


def test_geometry_and_base_props_preserved():
    fc = build_feature_collection(_assets_fc(), [_trend("a1")])
    assert fc["type"] == "FeatureCollection"
    f0 = fc["features"][0]
    assert f0["geometry"] == {"type": "Point", "coordinates": [-3.8, 41.0]}
    assert f0["properties"]["name"] == "Uno"
    assert f0["properties"]["category"] == "senderismo"


def test_trend_joined_and_flattened_to_scalars():
    fc = build_feature_collection(_assets_fc(), [_trend("a1")])
    p = fc["features"][0]["properties"]
    assert p["has_trend"] is True
    assert p["trend"] == "decreasing"
    assert p["trend_significant"] is True
    assert p["is_degrading"] is True
    # CI tuple split into two scalar columns (GeoJSON/GPKG safe)
    assert p["sens_slope_ci_low"] == -0.003
    assert p["sens_slope_ci_high"] == -0.0005
    assert "sens_slope_ci" not in p


def test_asset_without_trend_degrades_to_nulls():
    fc = build_feature_collection(_assets_fc(), [_trend("a1")])
    p2 = fc["features"][1]["properties"]  # a2 has no trend
    assert p2["has_trend"] is False
    assert p2["trend"] is None
    assert p2["sens_slope_ci_low"] is None


def test_evidence_level_and_ehs_travel_with_features():
    fc = build_feature_collection(
        _assets_fc(), [_trend("a1")],
        ehs_by_id={"a1": 7.3},
        evidence_level=DataStatus.CALIBRATED,
    )
    p = fc["features"][0]["properties"]
    assert p["evidence_level"] == "calibrated"
    assert p["ehs"] == 7.3
    assert fc["metadata"]["evidence_level"] == "calibrated"
    # missing EHS is explicit null, not fabricated
    assert fc["features"][1]["properties"]["ehs"] is None


def test_metadata_counts():
    fc = build_feature_collection(_assets_fc(), [_trend("a1")], park="pn_monfrague")
    assert fc["metadata"]["feature_count"] == 2
    assert fc["metadata"]["features_with_trend"] == 1
    assert fc["metadata"]["park"] == "pn_monfrague"


def test_export_geojson_roundtrip(tmp_path):
    fc = build_feature_collection(_assets_fc(), [_trend("a1")])
    out = export_geojson(fc, tmp_path / "sub" / "export.geojson")
    assert out.exists()
    reloaded = json.loads(out.read_text(encoding="utf-8"))
    assert reloaded["type"] == "FeatureCollection"
    assert len(reloaded["features"]) == 2
    assert reloaded["features"][0]["properties"]["asset_id"] == "a1"
