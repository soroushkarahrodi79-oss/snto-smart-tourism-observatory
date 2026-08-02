"""Unit tests for change-detection quality metadata (ADR-015). Offline / mocked ee."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from src.analysis.change_detection.models import DateWindow
from src.analysis.change_detection.quality import (
    aoi_pixel_count_expr,
    evaluate_quality,
    mean_scene_cloud_expr,
    scene_count_expr,
    valid_pixel_count_expr,
)

_WINDOW = DateWindow(date(2024, 6, 1), date(2024, 6, 30))


# ── EE expression builders ────────────────────────────────────────────────────

class TestExpressionBuilders:
    def test_scene_count_expr(self):
        collection = MagicMock()
        out = scene_count_expr(collection)
        collection.size.assert_called_once_with()
        assert out is collection.size.return_value

    def test_mean_scene_cloud_expr(self):
        collection = MagicMock()
        mean_scene_cloud_expr(collection)
        collection.aggregate_mean.assert_called_once_with("CLOUDY_PIXEL_PERCENTAGE")

    def test_valid_pixel_count_single_reduce_region(self):
        ee = MagicMock()
        img = MagicMock()
        region = MagicMock()
        out = valid_pixel_count_expr(ee_module=ee, ndvi_image=img, region=region)

        img.select.assert_called_once_with("NDVI")
        reduce = img.select.return_value.reduceRegion
        reduce.assert_called_once()  # exactly one reduceRegion
        kwargs = reduce.call_args.kwargs
        assert kwargs["reducer"] is ee.Reducer.count.return_value
        assert kwargs["geometry"] is region
        assert kwargs["scale"] == 10
        assert kwargs["maxPixels"] == int(1e8)
        assert kwargs["bestEffort"] is False
        assert kwargs["tileScale"] == 1
        reduce.return_value.get.assert_called_once_with("NDVI")
        assert out is reduce.return_value.get.return_value

    def test_aoi_pixel_count_uses_area_not_reduce_region(self):
        region = MagicMock()
        aoi_pixel_count_expr(region=region, scale=10)
        region.area.assert_called_once_with(maxError=1)
        region.area.return_value.divide.assert_called_once_with(100)


# ── Pure assembler ────────────────────────────────────────────────────────────

class TestEvaluateQuality:
    def _q(self, **over):
        base = dict(
            window=_WINDOW,
            requested_max_cloud_pct=20.0,
            scene_count=8,
            valid_pixel_count=800,
            aoi_pixel_count=1000,
            mean_scene_cloud_pct=5.0,
        )
        base.update(over)
        return evaluate_quality(**base)

    def test_adequate(self):
        q = self._q()
        assert q.dataset_id == "COPERNICUS/S2_SR_HARMONIZED"
        assert q.composite_method == "median"
        assert q.has_scenes is True
        assert q.valid_pixel_fraction == 0.8
        assert q.adequate_coverage is True
        assert q.warnings == ()

    def test_no_scenes(self):
        q = self._q(scene_count=0, valid_pixel_count=None)
        assert q.has_scenes is False
        assert any("no_scenes" in w for w in q.warnings)

    def test_insufficient_coverage(self):
        q = self._q(valid_pixel_count=100)  # 100/1000 = 0.10 < 0.30
        assert q.valid_pixel_fraction == 0.1
        assert q.adequate_coverage is False
        assert any("insufficient_valid_pixels" in w for w in q.warnings)

    def test_scene_cloud_not_confused_with_pixel_validity(self):
        # High whole-scene cloudiness but good AOI valid-pixel coverage: distinct
        # metrics, and coverage governs adequacy.
        q = self._q(mean_scene_cloud_pct=95.0, valid_pixel_count=800)
        assert q.mean_scene_cloud_pct == 95.0
        assert q.valid_pixel_fraction == 0.8
        assert q.adequate_coverage is True

    def test_min_valid_fraction_is_snto_convention(self):
        assert self._q().min_valid_pixel_fraction == 0.30

    def test_serialisable(self):
        import json

        json.dumps(self._q().to_dict())
