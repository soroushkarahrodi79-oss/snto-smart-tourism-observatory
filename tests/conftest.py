from __future__ import annotations

import pytest

from src.assets.models import AssetObservation, AssetType, GeoJSONGeometry, TourismAsset
from src.ingestion.mock_generator import MockDataGenerator


@pytest.fixture
def masatrigo_asset() -> TourismAsset:
    return TourismAsset(
        asset_id="masatrigo-trail-001",
        name="Masatrigo Trail, Badajoz",
        asset_type=AssetType.TRAIL,
        geometry=GeoJSONGeometry(
            type="LineString",
            coordinates=[[-7.02, 38.88], [-7.00, 38.90]],
        ),
        region="Extremadura",
        country="Spain",
        elevation_m=420.0,
    )


@pytest.fixture
def viewpoint_asset() -> TourismAsset:
    return TourismAsset(
        asset_id="mirador-001",
        name="Mirador del Valle",
        asset_type=AssetType.VIEWPOINT,
        geometry=GeoJSONGeometry(
            type="Point",
            coordinates=[-6.95, 38.85],
        ),
        region="Extremadura",
    )


@pytest.fixture
def recreational_area_asset() -> TourismAsset:
    return TourismAsset(
        asset_id="area-recreativa-001",
        name="Area Recreativa Valdecaballeros",
        asset_type=AssetType.RECREATIONAL_AREA,
        geometry=GeoJSONGeometry(
            type="Polygon",
            coordinates=[[
                [-5.42, 39.22],
                [-5.40, 39.22],
                [-5.40, 39.20],
                [-5.42, 39.20],
                [-5.42, 39.22],
            ]],
        ),
        region="Extremadura",
    )


@pytest.fixture
def mock_observations(masatrigo_asset: TourismAsset) -> list[AssetObservation]:
    return MockDataGenerator().fetch_time_series(masatrigo_asset, year=2024)
