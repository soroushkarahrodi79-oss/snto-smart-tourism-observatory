from __future__ import annotations

from src.ingestion.mock_generator import MockDataGenerator


def test_determinism(masatrigo_asset):
    gen = MockDataGenerator()
    obs1 = gen.fetch_time_series(masatrigo_asset, year=2024)
    obs2 = gen.fetch_time_series(masatrigo_asset, year=2024)
    assert [o.ndvi for o in obs1] == [o.ndvi for o in obs2]
    assert [o.ndmi for o in obs1] == [o.ndmi for o in obs2]


def test_returns_12_observations(masatrigo_asset):
    obs = MockDataGenerator().fetch_time_series(masatrigo_asset, year=2024)
    assert len(obs) == 12


def test_ndvi_in_valid_range(masatrigo_asset):
    obs = MockDataGenerator().fetch_time_series(masatrigo_asset, year=2024)
    for o in obs:
        assert 0.0 <= o.ndvi <= 1.0, f"NDVI {o.ndvi} out of range at month {o.month}"


def test_ndmi_in_valid_range(masatrigo_asset):
    obs = MockDataGenerator().fetch_time_series(masatrigo_asset, year=2024)
    for o in obs:
        assert -1.0 <= o.ndmi <= 1.0, f"NDMI {o.ndmi} out of range at month {o.month}"


def test_months_are_1_to_12(masatrigo_asset):
    obs = MockDataGenerator().fetch_time_series(masatrigo_asset, year=2024)
    months = [o.month for o in obs]
    assert months == list(range(1, 13))


def test_different_assets_produce_different_series(masatrigo_asset, viewpoint_asset):
    gen = MockDataGenerator()
    obs_a = gen.fetch_time_series(masatrigo_asset, year=2024)
    obs_b = gen.fetch_time_series(viewpoint_asset, year=2024)
    ndvi_a = [o.ndvi for o in obs_a]
    ndvi_b = [o.ndvi for o in obs_b]
    assert ndvi_a != ndvi_b


def test_data_source_is_mock(masatrigo_asset):
    obs = MockDataGenerator().fetch_time_series(masatrigo_asset, year=2024)
    assert all(o.data_source == "mock" for o in obs)
