"""Unit tests for the Change Explorer service (ADR-015). Offline / mocked ee."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

import src.services.change_explorer_service as svc
from src.analysis.change_detection.models import CompositeKind, DateWindow, WindowRole
from src.analysis.change_detection.quality import evaluate_quality
from src.config.territories import TerritoryConfig
from src.integrations.earth_engine.errors import EarthEngineQuotaError
from src.services.change_explorer_service import (
    ChangeExplorerRequest,
    ResultStatus,
    run_change_explorer,
)

_BBOX = (-4.21, 40.65, -3.58, 41.08)
_CFG = TerritoryConfig(
    key="tst",
    display_name="Test Park",
    bbox_wgs84=_BBOX,
    s2_tile="T30TVL",
    raw_raster_folder="TST",
    protection_category="National Park",
)
_BEFORE = DateWindow(date(2023, 7, 1), date(2023, 8, 31))
_AFTER = DateWindow(date(2024, 7, 1), date(2024, 8, 31))


def _request(product=CompositeKind.NDVI, dims=512) -> ChangeExplorerRequest:
    return ChangeExplorerRequest(
        territory_id="tst", product=product, before=_BEFORE, after=_AFTER,
        max_cloud_pct=20.0, dimensions=dims,
    )


def _quality(scene_count: int, valid: int, aoi: int = 1000):
    return evaluate_quality(
        window=_BEFORE, requested_max_cloud_pct=20.0, scene_count=scene_count,
        valid_pixel_count=valid, aoi_pixel_count=aoi, mean_scene_cloud_pct=5.0,
    )


@pytest.fixture
def wired(monkeypatch):
    """Patch the service's EE collaborators with spies; return the spy bundle."""
    ee = MagicMock()
    client = MagicMock()
    client.module.return_value = ee
    monkeypatch.setattr(svc, "get_change_explorer_client", lambda *a, **k: client)

    base_before = MagicMock(name="base_before")
    base_after = MagicMock(name="base_after")
    ndvi_before = MagicMock(name="ndvi_before")
    ndvi_after = MagicMock(name="ndvi_after")
    tc_before, tc_after = MagicMock(name="tc_before"), MagicMock(name="tc_after")
    dndvi = MagicMock(name="dndvi")

    build = MagicMock(side_effect=[base_before, base_after])
    ndvi = MagicMock(side_effect=[ndvi_before, ndvi_after])
    tc = MagicMock(side_effect=[tc_before, tc_after])
    diff = MagicMock(return_value=dndvi)
    thumb = MagicMock(side_effect=lambda **kw: f"url::{kw['image']._mock_name}")
    monkeypatch.setattr(svc, "build_sentinel2_collection", build)
    monkeypatch.setattr(svc, "ndvi_composite", ndvi)
    monkeypatch.setattr(svc, "true_colour_composite", tc)
    monkeypatch.setattr(svc, "ndvi_difference", diff)
    monkeypatch.setattr(svc, "get_thumbnail_url", thumb)

    quality = MagicMock(side_effect=lambda ee, **kw: _quality(8, 800))
    monkeypatch.setattr(svc, "_evaluate_window_quality", quality)

    return dict(
        ee=ee, build=build, ndvi=ndvi, tc=tc, diff=diff, thumb=thumb,
        quality=quality, ndvi_before=ndvi_before, ndvi_after=ndvi_after,
        base_before=base_before, base_after=base_after, dndvi=dndvi,
    )


def _run(product=CompositeKind.NDVI):
    return run_change_explorer(_request(product), territory_resolver=lambda _t: _CFG)


# ── Orchestration ─────────────────────────────────────────────────────────────

class TestOrchestration:
    def test_valid_request_returns_ok_result(self, wired):
        r = _run()
        assert r.status is ResultStatus.OK
        assert r.has_swipe is True
        assert r.territory_name == "Test Park"
        assert r.dndvi_artifact is not None

    def test_one_collection_build_per_window(self, wired):
        _run()
        assert wired["build"].call_count == 2
        c0 = wired["build"].call_args_list[0].kwargs
        c1 = wired["build"].call_args_list[1].kwargs
        assert c0["start_date"] == "2023-07-01" and c0["end_date"] == "2023-09-01"
        assert c1["start_date"] == "2024-07-01" and c1["end_date"] == "2024-09-01"
        assert c0["max_cloud_percentage"] == 20.0

    def test_bbox_coordinate_order_wsen(self, wired):
        _run()
        wired["ee"].Geometry.Rectangle.assert_called_once_with(
            [-4.21, 40.65, -3.58, 41.08], proj=None, geodesic=False
        )

    def test_unknown_territory_raises_valueerror(self):
        def _boom(_t):
            raise KeyError(_t)

        with pytest.raises(ValueError, match="unknown territory"):
            run_change_explorer(_request(), territory_resolver=_boom)

    def test_ndvi_product_does_not_build_true_colour(self, wired):
        _run(product=CompositeKind.NDVI)
        wired["tc"].assert_not_called()

    def test_true_colour_product_builds_true_colour(self, wired):
        _run(product=CompositeKind.TRUE_COLOUR)
        assert wired["tc"].call_count == 2

    def test_dndvi_reuses_ndvi_composites_no_extra_build(self, wired):
        _run()
        wired["diff"].assert_called_once_with(
            before_ndvi=wired["ndvi_before"], after_ndvi=wired["ndvi_after"]
        )
        assert wired["build"].call_count == 2  # no extra collection for dNDVI

    def test_quality_evaluated_once_per_window(self, wired):
        _run()
        assert wired["quality"].call_count == 2

    def test_three_aligned_render_calls(self, wired):
        _run()
        assert wired["thumb"].call_count == 3
        calls = wired["thumb"].call_args_list
        regions = {c.kwargs["region"] for c in calls}
        dims = {c.kwargs["dimensions"] for c in calls}
        assert len(regions) == 1  # identical region
        assert dims == {512}      # identical dimensions

    def test_before_after_share_visualisation(self, wired):
        _run(product=CompositeKind.NDVI)
        calls = wired["thumb"].call_args_list
        # before + after use the same NDVI visualisation (no independent stretch).
        assert calls[0].kwargs["visualization"] == calls[1].kwargs["visualization"]

    def test_render_roles(self, wired):
        r = _run()
        assert r.before_artifact.role is WindowRole.BEFORE
        assert r.after_artifact.role is WindowRole.AFTER
        assert r.dndvi_artifact.role is WindowRole.DIFFERENCE


# ── Degraded / no-data short-circuits ─────────────────────────────────────────

class TestDegradedStates:
    def test_no_scenes_short_circuits_before_render(self, wired):
        wired["quality"].side_effect = lambda ee, **kw: _quality(0, 0)
        r = _run()
        assert r.status is ResultStatus.NO_DATA
        assert r.before_artifact is None and r.dndvi_artifact is None
        wired["thumb"].assert_not_called()  # no fabricated URLs

    def test_all_cloud_no_valid_pixels_short_circuits(self, wired):
        wired["quality"].side_effect = lambda ee, **kw: _quality(6, 0)
        r = _run()
        assert r.status is ResultStatus.NO_DATA
        wired["thumb"].assert_not_called()

    def test_insufficient_coverage_still_renders_with_warning(self, wired):
        wired["quality"].side_effect = lambda ee, **kw: _quality(6, 100)  # 10% < 30%
        r = _run()
        assert r.status is ResultStatus.DEGRADED_COVERAGE
        assert r.has_swipe is True
        assert any("insufficient_valid_pixels" in w for w in r.warnings)


# ── Quality evaluation boundary (real _evaluate_window_quality, mock ee) ──────

class TestEvaluationBoundary:
    def test_single_combined_getinfo(self):
        ee = MagicMock()
        ee.Dictionary.return_value.getInfo.return_value = {
            "scene_count": 5, "mean_scene_cloud": 10.0,
            "valid_pixels": 800, "aoi_pixels": 1000,
        }
        q = svc._evaluate_window_quality(
            ee, base_collection=MagicMock(), ndvi_image=MagicMock(),
            geometry=MagicMock(), window=_BEFORE, max_cloud_pct=20.0,
        )
        ee.Dictionary.assert_called_once()
        ee.Dictionary.return_value.getInfo.assert_called_once()  # exactly one call
        assert q.scene_count == 5
        assert q.valid_pixel_count == 800
        assert q.valid_pixel_fraction == 0.8
        assert q.mean_scene_cloud_pct == 10.0

    def test_getinfo_error_mapped_to_typed(self):
        ee = MagicMock()
        ee.Dictionary.return_value.getInfo.side_effect = RuntimeError("Quota exceeded")
        with pytest.raises(EarthEngineQuotaError):
            svc._evaluate_window_quality(
                ee, base_collection=MagicMock(), ndvi_image=MagicMock(),
                geometry=MagicMock(), window=_BEFORE, max_cloud_pct=20.0,
            )


# ── Request validation & cache key ────────────────────────────────────────────

class TestRequestAndCacheKey:
    def test_rejects_dndvi_as_swipe_product(self):
        with pytest.raises(ValueError):
            ChangeExplorerRequest(
                territory_id="tst", product=CompositeKind.DNDVI,
                before=_BEFORE, after=_AFTER, max_cloud_pct=20.0, dimensions=512,
            )

    def test_rejects_out_of_range_cloud(self):
        with pytest.raises(ValueError):
            ChangeExplorerRequest(
                territory_id="tst", product=CompositeKind.NDVI,
                before=_BEFORE, after=_AFTER, max_cloud_pct=150.0, dimensions=512,
            )

    def test_rejects_out_of_range_dimensions(self):
        with pytest.raises(ValueError):
            ChangeExplorerRequest(
                territory_id="tst", product=CompositeKind.NDVI,
                before=_BEFORE, after=_AFTER, max_cloud_pct=20.0, dimensions=9999,
            )

    def test_cache_key_deterministic(self):
        assert _request().cache_key(_BBOX) == _request().cache_key(_BBOX)

    def test_cache_key_includes_versions_not_secrets(self):
        key = _request().cache_key(_BBOX)
        assert svc.DATASET_ID in key
        assert svc.COMPOSITE_METHOD_VERSION in key
        assert svc.VISUALISATION_VERSION in key
        assert _BBOX in key
        # No signed URLs, no Settings, no EE objects in the key.
        assert all(not hasattr(part, "getThumbURL") for part in key)

    def test_cache_key_changes_with_dates(self):
        other = ChangeExplorerRequest(
            territory_id="tst", product=CompositeKind.NDVI, before=_BEFORE,
            after=DateWindow(date(2025, 7, 1), date(2025, 8, 31)),
            max_cloud_pct=20.0, dimensions=512,
        )
        assert other.cache_key(_BBOX) != _request().cache_key(_BBOX)

    def test_cache_key_changes_with_cloud_dims_product(self):
        base = _request().cache_key(_BBOX)
        cloud = ChangeExplorerRequest(
            territory_id="tst", product=CompositeKind.NDVI, before=_BEFORE,
            after=_AFTER, max_cloud_pct=40.0, dimensions=512,
        ).cache_key(_BBOX)
        dims = _request(dims=256).cache_key(_BBOX)
        prod = _request(product=CompositeKind.TRUE_COLOUR).cache_key(_BBOX)
        assert base != cloud and base != dims and base != prod


# ── Scope guard ───────────────────────────────────────────────────────────────

def test_service_makes_no_gif_or_tile_calls():
    import inspect

    source = inspect.getsource(svc)
    # Look for actual call syntax, not prose mentions in the module docstring.
    for forbidden in (".getMapId(", ".getVideoThumbURL(", ".getDownloadURL("):
        assert forbidden not in source
