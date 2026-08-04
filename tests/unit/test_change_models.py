"""Unit tests for change-detection typed models (ADR-015). Pure, offline."""
from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from src.analysis.change_detection.models import (
    CompositeKind,
    CompositeProduct,
    DateWindow,
    WindowRole,
)

# ── DateWindow ────────────────────────────────────────────────────────────────

class TestDateWindow:
    def test_valid_window(self):
        w = DateWindow(date(2024, 6, 1), date(2024, 6, 30))
        assert w.ee_start_date() == "2024-06-01"
        assert w.ee_end_date() == "2024-07-01"  # inclusive end + 1 day
        assert w.duration_days == 30

    def test_same_day_window_is_valid(self):
        w = DateWindow(date(2024, 6, 15), date(2024, 6, 15))
        assert w.ee_end_date() == "2024-06-16"
        assert w.duration_days == 1

    def test_reversed_dates_rejected(self):
        with pytest.raises(ValueError):
            DateWindow(date(2024, 6, 30), date(2024, 6, 1))

    def test_month_and_year_boundary(self):
        w = DateWindow(date(2023, 12, 31), date(2024, 1, 1))
        assert w.ee_start_date() == "2023-12-31"
        assert w.ee_end_date() == "2024-01-02"
        assert w.duration_days == 2

    def test_leap_day(self):
        w = DateWindow(date(2024, 2, 29), date(2024, 2, 29))
        assert w.ee_end_date() == "2024-03-01"
        assert w.duration_days == 1

    def test_ee_exclusive_end_conversion(self):
        incl = DateWindow(date(2024, 6, 1), date(2024, 6, 10), end_inclusive=True)
        excl = DateWindow(date(2024, 6, 1), date(2024, 6, 11), end_inclusive=False)
        # Inclusive [1..10] and exclusive [1..11) cover the same 10 days.
        assert incl.ee_end_date() == excl.ee_end_date() == "2024-06-11"
        assert incl.duration_days == excl.duration_days == 10

    def test_exclusive_same_day_is_empty_and_rejected(self):
        with pytest.raises(ValueError):
            DateWindow(date(2024, 6, 1), date(2024, 6, 1), end_inclusive=False)

    def test_non_date_type_rejected(self):
        with pytest.raises(TypeError):
            DateWindow("2024-06-01", date(2024, 6, 30))  # type: ignore[arg-type]

    def test_datetime_rejected(self):
        with pytest.raises(TypeError):
            DateWindow(datetime(2024, 6, 1, 12), date(2024, 6, 30))  # type: ignore[arg-type]

    def test_models_module_does_not_import_ee(self):
        # No network/EE coupling: the models module never binds an ``ee`` symbol,
        # so constructing a model cannot trigger EE work.
        import src.analysis.change_detection.models as m

        assert not hasattr(m, "ee")
        DateWindow(date(2024, 6, 1), date(2024, 6, 30))  # constructs cleanly

    def test_serialisable(self):
        json.dumps(DateWindow(date(2024, 6, 1), date(2024, 6, 30)).to_dict())


# ── CompositeProduct ──────────────────────────────────────────────────────────

class TestCompositeProduct:
    def _product(self):
        return CompositeProduct(
            kind=CompositeKind.NDVI,
            role=WindowRole.BEFORE,
            band_names=("NDVI",),
            image=MagicMock(),
        )

    def test_identity_equality_avoids_ee_eq(self):
        img = MagicMock()
        a = CompositeProduct(CompositeKind.NDVI, WindowRole.BEFORE, ("NDVI",), img)
        b = CompositeProduct(CompositeKind.NDVI, WindowRole.BEFORE, ("NDVI",), img)
        # eq=False -> identity semantics, so no EE __eq__ is ever triggered.
        assert a == a
        assert a != b

    def test_image_excluded_from_repr(self):
        p = self._product()
        assert "image=" not in repr(p)

    def test_to_dict_is_metadata_only_and_serialisable(self):
        p = self._product()
        d = p.to_dict()
        assert "image" not in d
        assert d == {"kind": "ndvi", "role": "before", "band_names": ["NDVI"]}
        json.dumps(d)
