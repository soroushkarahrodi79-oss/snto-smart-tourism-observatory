"""Unit tests for the temporal GIF orchestration service (ADR-015). Offline.

Every Earth Engine collaborator is mocked; the GIF download is patched (no
network). Verifies: one grouped scene-count getInfo, empty-frame removal, the
≥2-usable-frame guard, URL-to-bytes with cap/timeout/magic validation, that the
signed URL is never stored or logged, request validation and the cache key.
"""
from __future__ import annotations

import socket
import urllib.error
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

import src.services.change_animation_service as svc
from src.analysis.change_detection.models import CompositeKind
from src.config.territories import TerritoryConfig
from src.integrations.earth_engine.errors import EarthEngineQuotaError
from src.services.change_animation_service import (
    ChangeAnimationRequest,
    GifInvalidError,
    GifTimeoutError,
    GifTooLargeError,
    InsufficientUsableFramesError,
    run_change_animation,
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
_GIF = b"GIF89a" + b"\x00" * 128


def _request(product=CompositeKind.NDVI, start=date(2023, 7, 1),
             end=date(2024, 8, 31), dims=256, frames=8,
             fps=2) -> ChangeAnimationRequest:
    return ChangeAnimationRequest(
        territory_id="tst", product=product, start=start, end=end,
        max_cloud_pct=20.0, dimensions=dims, max_frame_count=frames,
        frames_per_second=fps,
    )


@pytest.fixture
def wired(monkeypatch):
    """Patch the service's EE + download collaborators with spies."""
    ee = MagicMock()
    client = MagicMock()
    client.module.return_value = ee
    monkeypatch.setattr(svc, "get_change_explorer_client", lambda *a, **k: client)
    monkeypatch.setattr(svc, "bbox_to_ee_rectangle", lambda ee, bbox: "GEOM")

    # build_frame returns (image, collection); index-tagged mocks.
    def _build_frame(*, ee_module, geometry, window, product, max_cloud_pct,
                     frame_index):
        return (MagicMock(name=f"img{frame_index}"),
                MagicMock(name=f"col{frame_index}"))

    monkeypatch.setattr(svc, "build_frame", MagicMock(side_effect=_build_frame))

    # One grouped scene-count getInfo. Default: every frame has scenes.
    counts_expr = MagicMock()
    monkeypatch.setattr(
        svc, "scene_counts_expr", MagicMock(return_value=counts_expr)
    )
    monkeypatch.setattr(svc, "build_video_collection", MagicMock(return_value="VID"))
    monkeypatch.setattr(
        svc, "get_video_thumbnail_url",
        MagicMock(return_value="https://ee.example/video/SECRET-TOKEN"),
    )
    monkeypatch.setattr(svc, "_fetch_gif_bytes", MagicMock(return_value=_GIF))

    return dict(ee=ee, counts_expr=counts_expr)


def _set_counts(wired, counts):
    wired["counts_expr"].getInfo.return_value = counts


def _run(**kw):
    return run_change_animation(_request(**kw), territory_resolver=lambda _t: _CFG)


# ── Orchestration ─────────────────────────────────────────────────────────────

class TestOrchestration:
    def test_returns_artifact_with_gif_bytes(self, wired):
        _set_counts(wired, [5, 6, 7, 8])  # 4 planned frames, all usable
        art = _run(start=date(2023, 7, 1), end=date(2023, 10, 31), frames=8)
        assert art.gif_bytes == _GIF
        assert art.byte_size == len(_GIF)
        assert art.territory_name == "Test Park"
        assert art.frame_count == 4
        assert art.planned_frame_count == 4

    def test_single_grouped_getinfo(self, wired):
        _set_counts(wired, [5, 6])
        _run(start=date(2023, 7, 1), end=date(2023, 8, 31))
        wired["counts_expr"].getInfo.assert_called_once()  # never one call/frame

    def test_empty_frames_dropped_with_warning(self, wired):
        _set_counts(wired, [5, 0, 7, 8])  # second frame has no scenes
        art = _run(start=date(2023, 7, 1), end=date(2023, 10, 31))
        assert art.frame_count == 3
        assert art.planned_frame_count == 4
        assert any("omitted" in w for w in art.warnings)
        # Metadata still records all planned frames, marking the omitted one.
        assert len(art.frames) == 4
        omitted = [f for f in art.frames if f.scene_count == 0]
        assert len(omitted) == 1 and omitted[0].warning is not None

    def test_fewer_than_two_usable_raises(self, wired):
        _set_counts(wired, [5, 0, 0, 0])
        with pytest.raises(InsufficientUsableFramesError):
            _run(start=date(2023, 7, 1), end=date(2023, 10, 31))

    def test_getinfo_error_mapped_to_typed(self, wired):
        wired["counts_expr"].getInfo.side_effect = RuntimeError("Quota exceeded")
        with pytest.raises(EarthEngineQuotaError):
            _run(start=date(2023, 7, 1), end=date(2023, 8, 31))

    def test_video_url_never_stored_on_artifact(self, wired):
        _set_counts(wired, [5, 6])
        art = _run(start=date(2023, 7, 1), end=date(2023, 8, 31))
        # No attribute holds the signed URL; repr and to_dict exclude bytes/URL.
        blob = repr(art) + str(art.to_dict())
        assert "SECRET-TOKEN" not in blob
        assert "gif_bytes" not in art.to_dict()

    def test_to_dict_is_metadata_only(self, wired):
        _set_counts(wired, [5, 6])
        art = _run(start=date(2023, 7, 1), end=date(2023, 8, 31))
        d = art.to_dict()
        assert d["frame_count"] == 2
        assert d["byte_size"] == len(_GIF)
        assert "gif_bytes" not in d and "url" not in d

    def test_unknown_territory_raises_valueerror(self, wired):
        def _boom(_t):
            raise KeyError(_t)

        with pytest.raises(ValueError, match="unknown territory"):
            run_change_animation(_request(), territory_resolver=_boom)

    def test_disclaimer_attached(self, wired):
        _set_counts(wired, [5, 6])
        art = _run(start=date(2023, 7, 1), end=date(2023, 8, 31))
        assert "exploratoria" in art.evidence_label
        assert "validación de campo" in art.evidence_label


# ── Request validation ────────────────────────────────────────────────────────

class TestRequestValidation:
    def test_rejects_dndvi_product(self):
        with pytest.raises(ValueError, match="unsupported animation product"):
            _request(product=CompositeKind.DNDVI)

    def test_rejects_datetime(self):
        with pytest.raises(TypeError):
            ChangeAnimationRequest(
                territory_id="tst", product=CompositeKind.NDVI,
                start=datetime(2023, 7, 1), end=date(2024, 8, 31),
                max_cloud_pct=20.0, dimensions=256, max_frame_count=8,
                frames_per_second=2,
            )

    def test_rejects_reversed(self):
        with pytest.raises(ValueError, match="before end"):
            _request(start=date(2024, 8, 31), end=date(2023, 7, 1))

    def test_rejects_span_over_24_months(self):
        with pytest.raises(ValueError, match="exceeds"):
            _request(start=date(2021, 1, 1), end=date(2023, 12, 31))

    def test_rejects_span_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            _request(start=date(2023, 7, 5), end=date(2023, 7, 20))

    def test_rejects_bad_cloud(self):
        with pytest.raises(ValueError, match="max_cloud_pct"):
            _request().__class__(
                territory_id="tst", product=CompositeKind.NDVI,
                start=date(2023, 7, 1), end=date(2023, 8, 31),
                max_cloud_pct=150.0, dimensions=256, max_frame_count=8,
                frames_per_second=2,
            )

    def test_rejects_bad_dimensions(self):
        with pytest.raises(ValueError, match="dimensions"):
            _request(dims=512)

    def test_rejects_bad_fps(self):
        with pytest.raises(ValueError, match="frames_per_second"):
            _request(fps=5)

    def test_rejects_bad_frame_count(self):
        with pytest.raises(ValueError, match="max_frame_count"):
            _request(frames=20)

    def test_rejects_bool_frame_count(self):
        with pytest.raises(ValueError, match="max_frame_count"):
            _request(frames=True)


# ── Cache key ─────────────────────────────────────────────────────────────────

class TestCacheKey:
    def test_deterministic(self):
        assert _request().cache_key(_BBOX) == _request().cache_key(_BBOX)

    def test_includes_versions_and_bbox_not_secrets(self):
        key = _request().cache_key(_BBOX)
        assert svc.DATASET_ID in key
        assert svc.COMPOSITE_METHOD_VERSION in key
        assert svc.VISUALISATION_VERSION in key
        assert svc.ANIMATION_PLANNER_VERSION in key
        assert _BBOX in key
        assert all(not hasattr(part, "getVideoThumbURL") for part in key)

    def test_changes_with_frames_dims_fps_product(self):
        base = _request().cache_key(_BBOX)
        assert base != _request(frames=6).cache_key(_BBOX)
        assert base != _request(dims=384).cache_key(_BBOX)
        assert base != _request(fps=3).cache_key(_BBOX)
        assert base != _request(product=CompositeKind.TRUE_COLOUR).cache_key(_BBOX)

    def test_changes_with_dates(self):
        base = _request().cache_key(_BBOX)
        other = _request(end=date(2024, 6, 30)).cache_key(_BBOX)
        assert base != other


# ── _fetch_gif_bytes (patched urlopen; no network) ────────────────────────────

class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._pos = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n: int) -> bytes:
        chunk = self._payload[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk


class TestFetchGifBytes:
    def test_valid_gif_returned(self, monkeypatch):
        monkeypatch.setattr(
            svc.urllib.request, "urlopen",
            lambda req, timeout=None: _FakeResponse(_GIF),
        )
        assert svc._fetch_gif_bytes("https://ee.example/video/T") == _GIF

    def test_oversize_aborts(self, monkeypatch):
        big = b"GIF89a" + b"\x00" * (svc.MAX_GIF_BYTES + 10)
        monkeypatch.setattr(
            svc.urllib.request, "urlopen",
            lambda req, timeout=None: _FakeResponse(big),
        )
        with pytest.raises(GifTooLargeError):
            svc._fetch_gif_bytes("https://ee.example/video/T")

    def test_invalid_magic_rejected(self, monkeypatch):
        monkeypatch.setattr(
            svc.urllib.request, "urlopen",
            lambda req, timeout=None: _FakeResponse(b"<html>nope</html>"),
        )
        with pytest.raises(GifInvalidError):
            svc._fetch_gif_bytes("https://ee.example/video/T")

    def test_socket_timeout_mapped(self, monkeypatch):
        def _boom(req, timeout=None):
            raise socket.timeout("timed out")

        monkeypatch.setattr(svc.urllib.request, "urlopen", _boom)
        with pytest.raises(GifTimeoutError):
            svc._fetch_gif_bytes("https://ee.example/video/T")

    def test_urlerror_timeout_reason_mapped(self, monkeypatch):
        def _boom(req, timeout=None):
            raise urllib.error.URLError(socket.timeout("timed out"))

        monkeypatch.setattr(svc.urllib.request, "urlopen", _boom)
        with pytest.raises(GifTimeoutError):
            svc._fetch_gif_bytes("https://ee.example/video/T")

    def test_url_not_logged_on_failure(self, monkeypatch, caplog):
        def _boom(req, timeout=None):
            raise urllib.error.URLError("boom")

        monkeypatch.setattr(svc.urllib.request, "urlopen", _boom)
        with caplog.at_level("DEBUG"), pytest.raises(svc.GifDownloadError):
            svc._fetch_gif_bytes("https://ee.example/video/SECRET-TOKEN")
        assert not any("SECRET-TOKEN" in r.getMessage() for r in caplog.records)


# ── Scope guard ───────────────────────────────────────────────────────────────

def test_service_makes_no_tile_or_download_calls():
    import inspect

    source = inspect.getsource(svc)
    for forbidden in (".getMapId(", ".getDownloadURL("):
        assert forbidden not in source
