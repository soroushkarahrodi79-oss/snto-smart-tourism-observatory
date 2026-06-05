from __future__ import annotations

import pytest

from src.assets.models import AssetType, GeoJSONGeometry, TourismAsset


def test_trail_requires_linestring():
    with pytest.raises(ValueError, match="LineString"):
        TourismAsset(
            asset_id="bad",
            name="Bad Trail",
            asset_type=AssetType.TRAIL,
            geometry=GeoJSONGeometry(type="Point", coordinates=[-7.0, 38.9]),
            region="Test",
        )


def test_viewpoint_requires_point():
    with pytest.raises(ValueError, match="Point"):
        TourismAsset(
            asset_id="bad",
            name="Bad Viewpoint",
            asset_type=AssetType.VIEWPOINT,
            geometry=GeoJSONGeometry(
                type="LineString", coordinates=[[-7.0, 38.9], [-6.9, 38.9]]
            ),
            region="Test",
        )


def test_recreational_area_requires_polygon():
    with pytest.raises(ValueError, match="Polygon"):
        TourismAsset(
            asset_id="bad",
            name="Bad Area",
            asset_type=AssetType.RECREATIONAL_AREA,
            geometry=GeoJSONGeometry(type="Point", coordinates=[-7.0, 38.9]),
            region="Test",
        )


def test_valid_trail(masatrigo_asset):
    assert masatrigo_asset.asset_type == AssetType.TRAIL
    assert masatrigo_asset.geometry.type.value == "LineString"
    assert masatrigo_asset.elevation_m == 420.0


def test_asset_default_country(masatrigo_asset):
    assert masatrigo_asset.country == "Spain"


def test_asset_metadata_defaults_empty(masatrigo_asset):
    assert masatrigo_asset.metadata == {}
