"""Cache-behaviour tests for the temporal GIF service (ADR-015).

Exercises the application-facing cached wrapper. st.cache_data works outside a
Streamlit runtime (in-memory), so hit/miss and no-cache-on-exception are testable
without a runtime. Each test starts from a cleared cache for isolation. The 8 MiB
cap lives in ``run_change_animation`` (not exercised here — this file only checks
caching identity).
"""
from __future__ import annotations

from datetime import date

import pytest

import src.services.change_animation_service as svc
from src.analysis.change_detection.models import CompositeKind
from src.integrations.earth_engine.errors import EarthEngineQuotaError
from src.services.change_animation_service import (
    ChangeAnimationRequest,
    cached_run_change_animation,
    clear_change_animation_cache,
)


def _req(product=CompositeKind.NDVI, start=date(2023, 7, 1), end=date(2024, 8, 31),
         dims=256, frames=8, fps=2):
    # A real registered territory so bbox resolution in the cache key works.
    return ChangeAnimationRequest(
        territory_id="pnsg", product=product, start=start, end=end,
        max_cloud_pct=20.0, dimensions=dims, max_frame_count=frames,
        frames_per_second=fps,
    )


@pytest.fixture(autouse=True)
def _isolate_cache():
    clear_change_animation_cache()
    yield
    clear_change_animation_cache()


def test_identical_requests_reuse_cached_result(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_animation", lambda req: calls.append(req) or "GIF"
    )
    assert cached_run_change_animation(_req()) == "GIF"
    assert cached_run_change_animation(_req()) == "GIF"  # equal request -> hit
    assert len(calls) == 1


def test_changed_dates_invalidate_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_animation", lambda req: calls.append(req) or "G"
    )
    cached_run_change_animation(_req())
    cached_run_change_animation(_req(end=date(2024, 6, 30)))
    assert len(calls) == 2


def test_changed_frames_invalidate_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_animation", lambda req: calls.append(req) or "G"
    )
    cached_run_change_animation(_req(frames=8))
    cached_run_change_animation(_req(frames=6))
    assert len(calls) == 2


def test_changed_dimensions_invalidate_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_animation", lambda req: calls.append(req) or "G"
    )
    cached_run_change_animation(_req(dims=256))
    cached_run_change_animation(_req(dims=384))
    assert len(calls) == 2


def test_changed_fps_invalidates_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_animation", lambda req: calls.append(req) or "G"
    )
    cached_run_change_animation(_req(fps=2))
    cached_run_change_animation(_req(fps=3))
    assert len(calls) == 2


def test_changed_product_invalidates_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_animation", lambda req: calls.append(req) or "G"
    )
    cached_run_change_animation(_req(product=CompositeKind.NDVI))
    cached_run_change_animation(_req(product=CompositeKind.TRUE_COLOUR))
    assert len(calls) == 2


def test_exception_is_not_cached_as_success(monkeypatch):
    calls = []

    def _raiser(req):
        calls.append(req)
        raise EarthEngineQuotaError("quota exceeded")

    monkeypatch.setattr(svc, "run_change_animation", _raiser)
    with pytest.raises(EarthEngineQuotaError):
        cached_run_change_animation(_req())
    with pytest.raises(EarthEngineQuotaError):
        cached_run_change_animation(_req())
    assert len(calls) == 2  # re-invoked; failure never cached as a success


def test_cache_reset_forces_recompute(monkeypatch):
    calls = []
    monkeypatch.setattr(
        svc, "run_change_animation", lambda req: calls.append(req) or "G"
    )
    cached_run_change_animation(_req())
    clear_change_animation_cache()
    cached_run_change_animation(_req())
    assert len(calls) == 2


def test_ttl_is_900_seconds():
    assert svc.CHANGE_ANIMATION_CACHE_TTL_SECONDS == 900
