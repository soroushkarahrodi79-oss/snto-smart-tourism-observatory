"""Unit tests for composite and difference builders (ADR-015). Offline / mocked ee."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.analysis.change_detection.composites import (
    ndvi_composite,
    true_colour_composite,
)
from src.analysis.change_detection.difference import ndvi_difference


class TestTrueColour:
    def test_band_order_and_median(self):
        collection = MagicMock()
        out = true_colour_composite(collection)
        collection.select.assert_called_once_with(["B4", "B3", "B2"])
        collection.select.return_value.median.assert_called_once_with()
        assert out is collection.select.return_value.median.return_value

    def test_returns_analytical_image_not_visualised(self):
        # The builder must not apply visualize()/uint8() — display scaling is a
        # rendering concern, kept out of the analytical source.
        collection = MagicMock()
        true_colour_composite(collection)
        chain = repr(collection.select.return_value.mock_calls)
        assert "visualize" not in chain
        assert "uint8" not in chain


class TestNdviComposite:
    def test_operation_order_median_of_per_scene_ndvi(self):
        collection = MagicMock()
        out = ndvi_composite(collection)
        # map per-scene NDVI, THEN median (not NDVI of median reflectance).
        collection.map.assert_called_once()
        mapped = collection.map.return_value
        mapped.median.assert_called_once_with()
        mapped.median.return_value.rename.assert_called_once_with("NDVI")
        assert out is mapped.median.return_value.rename.return_value

    def test_per_scene_callback_computes_then_selects_ndvi(self):
        collection = MagicMock()
        ndvi_composite(collection)
        per_scene = collection.map.call_args.args[0]

        img = MagicMock()
        per_scene(img)
        img.normalizedDifference.assert_called_once_with(["B8", "B4"])
        # add_ndvi appends the band, then the callback selects just NDVI.
        img.addBands.return_value.select.assert_called_once_with("NDVI")


class TestNdviDifference:
    def test_after_minus_before(self):
        before = MagicMock()
        after = MagicMock()
        out = ndvi_difference(before_ndvi=before, after_ndvi=after)
        after.subtract.assert_called_once_with(before)
        after.subtract.return_value.rename.assert_called_once_with("dNDVI")
        assert out is after.subtract.return_value.rename.return_value

    def test_sign_convention_documented(self):
        # The module documents: negative = decrease, positive = increase.
        from src.analysis.change_detection import difference

        doc = difference.__doc__ or ""
        assert "negative" in doc.lower() and "decrease" in doc.lower()
        assert "positive" in doc.lower() and "increase" in doc.lower()
