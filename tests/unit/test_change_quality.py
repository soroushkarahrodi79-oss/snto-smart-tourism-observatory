"""Unit tests for change-detection quality metadata (ADR-015). Offline / mocked ee."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from src.analysis.change_detection.models import DateWindow
from src.analysis.change_detection.quality import (
    TOTAL_PIXELS_KEY,
    VALID_PIXELS_KEY,
    evaluate_quality,
    mean_scene_cloud_expr,
    pixel_counts_expr,
    scene_count_expr,
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

    def test_pixel_counts_single_reduce_region_over_mask(self):
        ee = MagicMock()
        img = MagicMock()
        region = MagicMock()
        out = pixel_counts_expr(ee_module=ee, ndvi_image=img, region=region)

        # valid + total are counted from the SAME reduceRegion over the NDVI mask
        # (sum = valid, count = total) — one reduction, same pixel grid.
        img.select.assert_called_once_with("NDVI")
        mask = img.select.return_value.mask.return_value
        reduce = mask.rename.return_value.reduceRegion
        reduce.assert_called_once()  # exactly one reduceRegion
        kwargs = reduce.call_args.kwargs
        # combined sum + count reducer
        ee.Reducer.sum.assert_called_once_with()
        ee.Reducer.sum.return_value.combine.assert_called_once()
        assert kwargs["geometry"] is region
        assert kwargs["scale"] == 10
        assert kwargs["maxPixels"] == int(1e8)
        assert kwargs["bestEffort"] is False
        assert kwargs["tileScale"] == 1
        assert out is reduce.return_value

    def test_pixel_count_keys_are_sum_and_count(self):
        # The service reads these exact keys out of the reduced dictionary.
        assert VALID_PIXELS_KEY == "valid_sum"
        assert TOTAL_PIXELS_KEY == "valid_count"

    def test_no_area_based_denominator_remains(self):
        # Regression guard for the 1/cos(lat) bug: the old area-based builders are
        # gone; the module must not call region.area(maxError=…) anywhere.
        import inspect

        from src.analysis.change_detection import quality

        assert not hasattr(quality, "aoi_pixel_count_expr")
        assert not hasattr(quality, "valid_pixel_count_expr")
        assert hasattr(quality, "pixel_counts_expr")
        assert ".area(maxError" not in inspect.getsource(quality)


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

    def test_full_coverage_fraction_is_one_not_above(self):
        # valid == total (same-grid counts) -> exactly 1.0, never > 1 (the bug).
        q = self._q(valid_pixel_count=1000, aoi_pixel_count=1000)
        assert q.valid_pixel_fraction == 1.0

    def test_fraction_bounded_for_count_consistent_inputs(self):
        # With valid <= total (guaranteed by the shared sum/count reduceRegion),
        # the fraction is always within [0, 1].
        for valid, total in [(0, 1000), (250, 1000), (999, 1000), (1000, 1000)]:
            q = self._q(valid_pixel_count=valid, aoi_pixel_count=total)
            assert 0.0 <= q.valid_pixel_fraction <= 1.0

    def test_no_footprint_gives_none_fraction(self):
        # total == 0 (no composite footprint) -> honest None, not a fake value.
        q = self._q(valid_pixel_count=0, aoi_pixel_count=0)
        assert q.valid_pixel_fraction is None

    def test_min_valid_fraction_is_snto_convention(self):
        assert self._q().min_valid_pixel_fraction == 0.30

    def test_serialisable(self):
        import json

        json.dumps(self._q().to_dict())
