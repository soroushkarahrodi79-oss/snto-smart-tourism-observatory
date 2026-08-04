"""
SNTO — Earth Engine animated-GIF integration via ``getVideoThumbURL`` (ADR-015)
===============================================================================

The single low-level primitive for turning a **pre-visualised** (RGB)
``ee.ImageCollection`` into a signed animated-**GIF** URL. GIF only; no
``getMapId``, no tiles, no exports, no download, no caching (all higher-layer).

Verified against the real Earth Engine 1.7.37 contract:
``ImageCollection.getVideoThumbURL(params: dict) -> str``. Its params mirror
``getMapId`` plus ``dimensions``, ``region`` (E,S,W,N **or** GeoJSON — we always
pass an ``ee.Geometry`` to avoid coordinate-order ambiguity), ``format`` (only
``'gif'`` is supported) and ``framesPerSecond``. Because the frames are already
visualised, no per-frame visualisation params are passed here — that is what
guarantees one identical stretch/palette across the whole animation.

Security: the signed URL is returned but **never logged**. SDK failures are
mapped to the foundation's typed error hierarchy.
"""
from __future__ import annotations

import logging
from typing import Any

from src.integrations.earth_engine.errors import map_ee_exception

logger = logging.getLogger(__name__)

# Hard limits for the video (the analysis layer owns frame/span limits).
ALLOWED_VIDEO_DIMENSIONS: tuple[int, ...] = (256, 384)
DEFAULT_VIDEO_DIMENSIONS = 256
ALLOWED_FPS: tuple[int, ...] = (1, 2, 3)
DEFAULT_FPS = 2
SUPPORTED_VIDEO_FORMATS: tuple[str, ...] = ("gif",)


def _validate_dimensions(dimensions: int) -> None:
    if isinstance(dimensions, bool) or not isinstance(dimensions, int):
        raise ValueError("dimensions must be an int.")
    if dimensions not in ALLOWED_VIDEO_DIMENSIONS:
        raise ValueError(
            f"dimensions {dimensions} not allowed; use one of "
            f"{ALLOWED_VIDEO_DIMENSIONS}."
        )


def _validate_fps(frames_per_second: int) -> None:
    if isinstance(frames_per_second, bool) or not isinstance(frames_per_second, int):
        raise ValueError("frames_per_second must be an int.")
    if frames_per_second not in ALLOWED_FPS:
        raise ValueError(
            f"frames_per_second {frames_per_second} not allowed; use one of "
            f"{ALLOWED_FPS}."
        )


def _validate_format(image_format: str) -> None:
    if image_format not in SUPPORTED_VIDEO_FORMATS:
        raise ValueError(
            f"unsupported video format {image_format!r}; "
            f"supported: {SUPPORTED_VIDEO_FORMATS}."
        )


def build_video_params(
    *,
    region: Any,
    dimensions: int,
    frames_per_second: int,
    image_format: str = "gif",
) -> dict[str, Any]:
    """Build the ``getVideoThumbURL`` parameter dict (pure; validates bounds)."""
    _validate_dimensions(dimensions)
    _validate_fps(frames_per_second)
    _validate_format(image_format)
    return {
        "region": region,
        "dimensions": dimensions,
        "framesPerSecond": frames_per_second,
        "format": image_format,
    }


def get_video_thumbnail_url(
    *,
    image_collection: Any,
    region: Any,
    dimensions: int,
    frames_per_second: int,
    image_format: str = "gif",
) -> str:
    """Return a signed animated-GIF URL for a pre-visualised RGB collection.

    Uses only ``getVideoThumbURL``. Does not download or cache. EE failures are
    re-raised as typed foundation errors; the signed URL is never logged.
    """
    params = build_video_params(
        region=region,
        dimensions=dimensions,
        frames_per_second=frames_per_second,
        image_format=image_format,
    )
    try:
        url: str = image_collection.getVideoThumbURL(params)
    except Exception as exc:  # noqa: BLE001 - re-raised as typed, cause chained
        logger.warning("Earth Engine video (GIF) generation failed.")
        raise map_ee_exception(exc) from exc
    return url
