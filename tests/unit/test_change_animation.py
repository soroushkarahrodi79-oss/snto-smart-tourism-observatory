"""Unit tests for temporal animation planning + frame construction (ADR-015).

Pure planner tests need no Earth Engine; frame-construction tests use a mocked
``ee`` module and patch the analysis collaborators. No network, no getInfo.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

import src.analysis.change_detection.animation as anim
from src.analysis.change_detection.animation import (
    MAX_FRAMES,
    MAX_SPAN_MONTHS,
    MIN_FRAMES,
    build_frame,
    build_video_collection,
    calendar_month_span,
    plan_frame_windows,
    scene_counts_expr,
)
from src.analysis.change_detection.models import CompositeKind, DateWindow

# ── calendar_month_span ───────────────────────────────────────────────────────

class TestMonthSpan:
    def test_same_month(self):
        assert calendar_month_span(date(2023, 7, 3), date(2023, 7, 28)) == 1

    def test_two_months(self):
        assert calendar_month_span(date(2023, 7, 1), date(2023, 8, 31)) == 2

    def test_across_year_boundary(self):
        assert calendar_month_span(date(2023, 11, 1), date(2024, 2, 1)) == 4


# ── plan_frame_windows ────────────────────────────────────────────────────────

class TestPlanner:
    def test_rejects_datetime(self):
        with pytest.raises(TypeError):
            plan_frame_windows(datetime(2023, 7, 1), date(2023, 8, 31), 8)

    def test_rejects_reversed(self):
        with pytest.raises(ValueError, match="reversed"):
            plan_frame_windows(date(2024, 1, 1), date(2023, 1, 1), 8)

    def test_rejects_span_over_max(self):
        with pytest.raises(ValueError, match="exceeds"):
            plan_frame_windows(date(2020, 1, 1), date(2023, 12, 31), 8)

    def test_rejects_span_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            plan_frame_windows(date(2023, 7, 5), date(2023, 7, 20), 8)

    def test_rejects_max_frames_below_min(self):
        with pytest.raises(ValueError, match="max_frames"):
            plan_frame_windows(date(2023, 1, 1), date(2023, 12, 31), 1)

    def test_two_month_span_two_frames(self):
        w = plan_frame_windows(date(2023, 7, 1), date(2023, 8, 31), 8)
        assert len(w) == 2
        assert w[0].start == date(2023, 7, 1) and w[0].end == date(2023, 7, 31)
        assert w[1].start == date(2023, 8, 1) and w[1].end == date(2023, 8, 31)

    def test_frames_are_contiguous_no_gaps_no_overlaps(self):
        w = plan_frame_windows(date(2023, 1, 1), date(2023, 12, 31), 12)
        assert len(w) == 12
        for prev, nxt in zip(w, w[1:]):
            assert nxt.start == prev.end + timedelta(days=1)

    def test_first_frame_keeps_partial_start(self):
        w = plan_frame_windows(date(2023, 7, 15), date(2023, 9, 30), 8)
        assert w[0].start == date(2023, 7, 15)  # partial first month preserved

    def test_last_frame_keeps_inclusive_end(self):
        w = plan_frame_windows(date(2023, 7, 1), date(2023, 9, 20), 8)
        assert w[-1].end == date(2023, 9, 20)  # partial last month preserved

    def test_every_day_in_exactly_one_frame(self):
        w = plan_frame_windows(date(2023, 3, 10), date(2023, 11, 5), 6)
        # Continuous coverage from the true start to the true end.
        assert w[0].start == date(2023, 3, 10)
        assert w[-1].end == date(2023, 11, 5)
        for prev, nxt in zip(w, w[1:]):
            assert nxt.start == prev.end + timedelta(days=1)

    def test_adaptive_step_bounds_frame_count(self):
        # 24 months with max 8 frames -> step 3 months -> 8 frames.
        w = plan_frame_windows(date(2022, 1, 1), date(2023, 12, 31), 8)
        assert len(w) == 8

    def test_count_always_within_hard_bounds(self):
        for months, cap in ((2, 8), (6, 4), (24, 12), (13, 6)):
            end_year, end_month0 = divmod((2023 * 12) + (months - 1), 12)
            end = date(end_year, end_month0 + 1, 28)
            w = plan_frame_windows(date(2023, 1, 1), end, cap)
            assert MIN_FRAMES <= len(w) <= MAX_FRAMES

    def test_max_span_is_24_months(self):
        assert MAX_SPAN_MONTHS == 24


# ── build_frame ───────────────────────────────────────────────────────────────

@pytest.fixture
def frame_wired(monkeypatch):
    ee = MagicMock()
    collection = MagicMock(name="collection")
    composite = MagicMock(name="composite")
    visualised = MagicMock(name="visualised")
    composite.visualize.return_value = visualised
    visualised.set.return_value = visualised

    build = MagicMock(return_value=collection)
    ndvi = MagicMock(return_value=composite)
    tc = MagicMock(return_value=composite)
    monkeypatch.setattr(anim, "build_sentinel2_collection", build)
    monkeypatch.setattr(anim, "ndvi_composite", ndvi)
    monkeypatch.setattr(anim, "true_colour_composite", tc)
    return dict(
        ee=ee, collection=collection, composite=composite,
        visualised=visualised, build=build, ndvi=ndvi, tc=tc,
    )


def _win():
    return DateWindow(date(2023, 7, 1), date(2023, 7, 31))


class TestBuildFrame:
    def test_ndvi_uses_ndvi_composite_not_true_colour(self, frame_wired):
        build_frame(
            ee_module=frame_wired["ee"], geometry=MagicMock(), window=_win(),
            product=CompositeKind.NDVI, max_cloud_pct=20.0, frame_index=0,
        )
        frame_wired["ndvi"].assert_called_once()
        frame_wired["tc"].assert_not_called()

    def test_true_colour_uses_true_colour_composite(self, frame_wired):
        build_frame(
            ee_module=frame_wired["ee"], geometry=MagicMock(), window=_win(),
            product=CompositeKind.TRUE_COLOUR, max_cloud_pct=20.0, frame_index=0,
        )
        frame_wired["tc"].assert_called_once()
        frame_wired["ndvi"].assert_not_called()

    def test_rejects_unsupported_product(self, frame_wired):
        with pytest.raises(ValueError, match="unsupported animation product"):
            build_frame(
                ee_module=frame_wired["ee"], geometry=MagicMock(), window=_win(),
                product=CompositeKind.DNDVI, max_cloud_pct=20.0, frame_index=0,
            )

    def test_frame_is_previsualised(self, frame_wired):
        img, col = build_frame(
            ee_module=frame_wired["ee"], geometry=MagicMock(), window=_win(),
            product=CompositeKind.NDVI, max_cloud_pct=20.0, frame_index=3,
        )
        # The composite is visualised (fixed stretch) before being returned.
        frame_wired["composite"].visualize.assert_called_once()
        assert img is frame_wired["visualised"]
        assert col is frame_wired["collection"]

    def test_frame_tagged_with_time_and_index(self, frame_wired):
        build_frame(
            ee_module=frame_wired["ee"], geometry=MagicMock(), window=_win(),
            product=CompositeKind.NDVI, max_cloud_pct=20.0, frame_index=5,
        )
        props = frame_wired["visualised"].set.call_args.args[0]
        assert props["frame_index"] == 5
        assert "system:time_start" in props
        assert props["frame_start"] == "2023-07-01"

    def test_collection_built_with_exclusive_end(self, frame_wired):
        build_frame(
            ee_module=frame_wired["ee"], geometry=MagicMock(), window=_win(),
            product=CompositeKind.NDVI, max_cloud_pct=15.0, frame_index=0,
        )
        kw = frame_wired["build"].call_args.kwargs
        assert kw["start_date"] == "2023-07-01"
        assert kw["end_date"] == "2023-08-01"  # inclusive->exclusive
        assert kw["max_cloud_percentage"] == 15.0


# ── scene_counts_expr / build_video_collection ────────────────────────────────

def test_scene_counts_expr_is_one_grouped_list():
    ee = MagicMock()
    c0, c1 = MagicMock(), MagicMock()
    c0.size.return_value = "s0"
    c1.size.return_value = "s1"
    scene_counts_expr(ee_module=ee, collections=[c0, c1])
    ee.List.assert_called_once_with(["s0", "s1"])


def test_build_video_collection_sorts_chronologically():
    ee = MagicMock()
    imgs = [MagicMock(), MagicMock()]
    build_video_collection(ee_module=ee, images=imgs)
    ee.ImageCollection.fromImages.assert_called_once_with(imgs)
    ee.ImageCollection.fromImages.return_value.sort.assert_called_once_with(
        "system:time_start"
    )
