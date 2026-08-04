"""Cache-behaviour tests for the Change Explorer service (ADR-015).

Exercises the application-facing cached wrapper. st.cache_data works outside a
Streamlit runtime (in-memory), so hit/miss and no-cache-on-exception are testable
without a runtime. Each test starts from a cleared cache for isolation.
"""
from __future__ import annotations

from datetime import date

import pytest

import src.services.change_explorer_service as svc
from src.analysis.change_detection.models import CompositeKind, DateWindow
from src.integrations.earth_engine.errors import EarthEngineQuotaError
from src.services.change_explorer_service import (
    ChangeExplorerRequest,
    cached_run_change_explorer,
    clear_change_explorer_cache,
)

# Use a real registered territory so bbox resolution in the cache key works.
_BEFORE = DateWindow(date(2023, 7, 1), date(2023, 8, 31))
_AFTER = DateWindow(date(2024, 7, 1), date(2024, 8, 31))


def _req(after=_AFTER, cloud=20.0, dims=512, product=CompositeKind.NDVI):
    return ChangeExplorerRequest(
        territory_id="pnsg", product=product, before=_BEFORE, after=after,
        max_cloud_pct=cloud, dimensions=dims,
    )


@pytest.fixture(autouse=True)
def _isolate_cache():
    clear_change_explorer_cache()
    yield
    clear_change_explorer_cache()


def test_identical_requests_reuse_cached_result(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_explorer", lambda req: calls.append(req) or "RESULT"
    )
    assert cached_run_change_explorer(_req()) == "RESULT"
    assert cached_run_change_explorer(_req()) == "RESULT"  # equal request -> hit
    assert len(calls) == 1


def test_changed_dates_invalidate_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_explorer", lambda req: calls.append(req) or "R"
    )
    cached_run_change_explorer(_req())
    cached_run_change_explorer(
        _req(after=DateWindow(date(2025, 7, 1), date(2025, 8, 31)))
    )
    assert len(calls) == 2


def test_changed_cloud_threshold_invalidates_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_explorer", lambda req: calls.append(req) or "R"
    )
    cached_run_change_explorer(_req(cloud=20.0))
    cached_run_change_explorer(_req(cloud=40.0))
    assert len(calls) == 2


def test_changed_dimensions_invalidate_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_explorer", lambda req: calls.append(req) or "R"
    )
    cached_run_change_explorer(_req(dims=512))
    cached_run_change_explorer(_req(dims=256))
    assert len(calls) == 2


def test_changed_product_invalidates_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_explorer", lambda req: calls.append(req) or "R"
    )
    cached_run_change_explorer(_req(product=CompositeKind.NDVI))
    cached_run_change_explorer(_req(product=CompositeKind.TRUE_COLOUR))
    assert len(calls) == 2


def test_exception_is_not_cached_as_success(monkeypatch):
    calls = []

    def _raiser(req):
        calls.append(req)
        raise EarthEngineQuotaError("quota exceeded")

    monkeypatch.setattr(svc, "run_change_explorer", _raiser)
    with pytest.raises(EarthEngineQuotaError):
        cached_run_change_explorer(_req())
    with pytest.raises(EarthEngineQuotaError):
        cached_run_change_explorer(_req())
    assert len(calls) == 2  # re-invoked; failure never cached as a success


def test_cache_reset_forces_recompute(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_explorer", lambda req: calls.append(req) or "R"
    )
    cached_run_change_explorer(_req())
    clear_change_explorer_cache()
    cached_run_change_explorer(_req())
    assert len(calls) == 2
