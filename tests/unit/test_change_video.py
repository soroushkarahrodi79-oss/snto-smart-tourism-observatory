"""Unit tests for the Earth Engine video (GIF) integration primitive (ADR-015).

Offline: the ``ee.ImageCollection`` is a mock. Verifies parameter construction,
bound validation, that only ``getVideoThumbURL`` is used, and that SDK failures
map to typed foundation errors — the signed URL is never logged.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.integrations.earth_engine.errors import (
    EarthEngineError,
    EarthEngineQuotaError,
)
from src.integrations.earth_engine.video import (
    ALLOWED_FPS,
    ALLOWED_VIDEO_DIMENSIONS,
    build_video_params,
    get_video_thumbnail_url,
)

# ── build_video_params ────────────────────────────────────────────────────────

class TestBuildVideoParams:
    def test_happy_path(self):
        region = MagicMock(name="geometry")
        params = build_video_params(
            region=region, dimensions=256, frames_per_second=2,
        )
        assert params == {
            "region": region, "dimensions": 256,
            "framesPerSecond": 2, "format": "gif",
        }

    @pytest.mark.parametrize("dims", ALLOWED_VIDEO_DIMENSIONS)
    def test_allowed_dimensions(self, dims):
        build_video_params(region=MagicMock(), dimensions=dims, frames_per_second=2)

    def test_rejects_bad_dimensions(self):
        with pytest.raises(ValueError, match="dimensions"):
            build_video_params(
                region=MagicMock(), dimensions=512, frames_per_second=2
            )

    def test_rejects_bool_dimensions(self):
        with pytest.raises(ValueError, match="dimensions"):
            build_video_params(
                region=MagicMock(), dimensions=True, frames_per_second=2
            )

    @pytest.mark.parametrize("fps", ALLOWED_FPS)
    def test_allowed_fps(self, fps):
        build_video_params(region=MagicMock(), dimensions=256, frames_per_second=fps)

    def test_rejects_bad_fps(self):
        with pytest.raises(ValueError, match="frames_per_second"):
            build_video_params(
                region=MagicMock(), dimensions=256, frames_per_second=10
            )

    def test_rejects_bool_fps(self):
        with pytest.raises(ValueError, match="frames_per_second"):
            build_video_params(
                region=MagicMock(), dimensions=256, frames_per_second=False
            )

    def test_rejects_non_gif_format(self):
        with pytest.raises(ValueError, match="format"):
            build_video_params(
                region=MagicMock(), dimensions=256, frames_per_second=2,
                image_format="mp4",
            )


# ── get_video_thumbnail_url ───────────────────────────────────────────────────

class TestGetVideoUrl:
    def test_uses_get_video_thumb_url_only(self):
        col = MagicMock()
        col.getVideoThumbURL.return_value = "https://ee.example/video/TOKEN"
        region = MagicMock()
        url = get_video_thumbnail_url(
            image_collection=col, region=region, dimensions=256,
            frames_per_second=2,
        )
        assert url == "https://ee.example/video/TOKEN"
        col.getVideoThumbURL.assert_called_once()
        params = col.getVideoThumbURL.call_args.args[0]
        assert params["format"] == "gif"
        assert params["region"] is region
        # No getMapId / tile / download call on the collection.
        col.getMapId.assert_not_called()
        col.getDownloadURL.assert_not_called()

    def test_sdk_failure_mapped_to_typed_error(self):
        col = MagicMock()
        col.getVideoThumbURL.side_effect = RuntimeError("Quota exceeded")
        with pytest.raises(EarthEngineQuotaError):
            get_video_thumbnail_url(
                image_collection=col, region=MagicMock(), dimensions=256,
                frames_per_second=2,
            )

    def test_generic_failure_is_typed_ee_error(self):
        col = MagicMock()
        col.getVideoThumbURL.side_effect = RuntimeError("something odd")
        with pytest.raises(EarthEngineError):
            get_video_thumbnail_url(
                image_collection=col, region=MagicMock(), dimensions=256,
                frames_per_second=2,
            )

    def test_url_not_logged(self, caplog):
        col = MagicMock()
        col.getVideoThumbURL.return_value = "https://ee.example/video/SECRET-TOKEN"
        with caplog.at_level("DEBUG"):
            get_video_thumbnail_url(
                image_collection=col, region=MagicMock(), dimensions=256,
                frames_per_second=2,
            )
        assert not any("SECRET-TOKEN" in r.getMessage() for r in caplog.records)
