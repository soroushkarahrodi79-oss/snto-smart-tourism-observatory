"""
SNTO — Static PNG thumbnail rendering via Earth Engine ``getThumbURL`` (ADR-015)
================================================================================

The *only* rendering primitive in this phase: turn an analytical EE image into a
signed static PNG thumbnail **URL**. No ``getMapId``, no XYZ tiles, no GIF /
``getVideoThumbURL``, no download, no caching (all deferred / higher-layer).

Alignment contract (critical for the future before/after swipe)
---------------------------------------------------------------
Before and after thumbnails MUST be spatially and visually comparable. This
module guarantees that by making the thumbnail parameters a **pure function of
the alignment inputs** (region, dimensions, visualisation, format) and
independent of the image: render the two panels with the *same* ``region``, the
*same* ``dimensions`` and the *same* ``Visualization`` and they share an
identical projection footprint and value stretch. Because each product's
``Visualization`` carries fixed ``min``/``max`` (see :mod:`.palettes`), before
and after are **never** auto-stretched independently.

Security: signed thumbnail URLs are treated as secrets — they are **never**
logged. EE failures are mapped through the foundation's typed errors.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

from src.integrations.earth_engine.errors import map_ee_exception

logger = logging.getLogger(__name__)

# Conservative hard bounds for a thumbnail's longer side (pixels). Small enough
# to stay a cheap preview, large enough to be legible; the swipe MVP renders
# well within this range.
MIN_THUMBNAIL_DIMENSION = 16
MAX_THUMBNAIL_DIMENSION = 2048

# Only PNG is supported in the MVP (lossless; masked pixels stay transparent).
SUPPORTED_IMAGE_FORMATS: tuple[str, ...] = ("png",)


def _validate_dimensions(dimensions: int) -> None:
    if isinstance(dimensions, bool) or not isinstance(dimensions, int):
        raise ValueError("dimensions must be an int (square thumbnail size).")
    if not (MIN_THUMBNAIL_DIMENSION <= dimensions <= MAX_THUMBNAIL_DIMENSION):
        raise ValueError(
            f"dimensions {dimensions} out of bounds "
            f"[{MIN_THUMBNAIL_DIMENSION}, {MAX_THUMBNAIL_DIMENSION}]."
        )


def _validate_format(image_format: str) -> None:
    if image_format not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(
            f"unsupported image format {image_format!r}; "
            f"supported: {SUPPORTED_IMAGE_FORMATS}."
        )


def build_thumbnail_params(
    *,
    region: Any,
    visualization: Mapping[str, Any],
    dimensions: int,
    image_format: str = "png",
) -> dict[str, Any]:
    """Build the ``getThumbURL`` parameter dict — pure, image-independent.

    Validates dimensions and format, then merges the visualisation with the
    explicit ``region``, ``dimensions`` and ``format``. Two calls with identical
    alignment inputs return **equal** dicts — the basis of the before/after
    alignment guarantee.
    """
    _validate_dimensions(dimensions)
    _validate_format(image_format)
    params: dict[str, Any] = dict(visualization)
    params["region"] = region
    params["dimensions"] = dimensions
    params["format"] = image_format
    return params


def get_thumbnail_url(
    *,
    image: Any,
    region: Any,
    visualization: Mapping[str, Any],
    dimensions: int,
    image_format: str = "png",
) -> str:
    """Return a signed static PNG thumbnail URL for *image* over *region*.

    Does not download the image and does not cache. EE failures are re-raised as
    the foundation's typed errors; the returned URL (a secret) is never logged.
    """
    params = build_thumbnail_params(
        region=region,
        visualization=visualization,
        dimensions=dimensions,
        image_format=image_format,
    )
    try:
        url: str = image.getThumbURL(params)
    except Exception as exc:  # noqa: BLE001 - re-raised as typed, cause chained
        logger.warning("Earth Engine thumbnail generation failed.")
        raise map_ee_exception(exc) from exc
    return url
