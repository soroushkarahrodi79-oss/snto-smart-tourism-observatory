"""
SNTO — Change-detection quality metadata (ADR-015)
==================================================

Two layers, kept apart on purpose:

1. **EE expression builders** (``scene_count_expr``, ``mean_scene_cloud_expr``,
   ``valid_pixel_count_expr``, ``aoi_pixel_count_expr``) — construct lazy EE
   objects only. They never call ``getInfo``; the future service evaluates them.
   Emptiness is therefore never probed inside a pure builder.
2. **A pure assembler** (:func:`evaluate_quality`) — takes the *already-evaluated*
   scalars and returns a fully JSON-serialisable :class:`QualityMetadata`,
   applying the no-scenes / insufficient-coverage warning logic offline.

Cloud metrics are not conflated: ``CLOUDY_PIXEL_PERCENTAGE`` is scene metadata
(pre-filter + ``mean_scene_cloud``), whereas valid-pixel coverage is an
SCL-derived AOI/composite measure.

reduceRegion knobs are explicit and justified:
* ``scale = DEFAULT_SCALE_M`` (10 m) — the native NIR/Red resolution, matching the
  ingestion adapter; finer would oversample, coarser would blur the AOI count.
* ``max_pixels = DEFAULT_MAX_PIXELS`` (1e8) — the adapter's historical guard.
* ``best_effort = False`` — we want a faithful count, not a silently downsampled
  one; the service can raise this deliberately for very large AOIs.
* ``tile_scale = 1`` — default; raise only to relieve memory pressure.

The valid-pixel adequacy bar reuses the established SNTO convention
``MIN_VALID_PIXEL_FRACTION`` (0.30) rather than inventing a new threshold.
"""
from __future__ import annotations

from typing import Any

from src.analysis.change_detection.models import DateWindow, QualityMetadata
from src.integrations.earth_engine.collections import (
    DEFAULT_MAX_PIXELS,
    DEFAULT_SCALE_M,
    MIN_VALID_PIXEL_FRACTION,
    NDVI_BAND,
    S2_COLLECTION_ID,
)

CLOUDY_PIXEL_PERCENTAGE = "CLOUDY_PIXEL_PERCENTAGE"
COMPOSITE_METHOD = "median"


# ── EE expression builders (lazy; no getInfo) ─────────────────────────────────

def scene_count_expr(collection: Any) -> Any:
    """``ee.Number`` of scenes remaining after scene-level filtering."""
    return collection.size()


def mean_scene_cloud_expr(collection: Any) -> Any:
    """``ee.Number``: mean ``CLOUDY_PIXEL_PERCENTAGE`` over the filtered scenes.

    Scene metadata — the aggregate whole-granule cloudiness, *not* AOI pixel
    validity.
    """
    return collection.aggregate_mean(CLOUDY_PIXEL_PERCENTAGE)


def valid_pixel_count_expr(
    *,
    ee_module: Any,
    ndvi_image: Any,
    region: Any,
    scale: int = DEFAULT_SCALE_M,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    best_effort: bool = False,
    tile_scale: int = 1,
) -> Any:
    """``ee.Number`` of valid (unmasked) NDVI pixels within *region*.

    A single ``reduceRegion(ee.Reducer.count())`` over the NDVI band — one
    reduction, no redundancy. ``count`` ignores masked pixels, so this is the
    valid-pixel count for the composite inside the AOI.
    """
    ee = ee_module
    reduced = ndvi_image.select(NDVI_BAND).reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=region,
        scale=scale,
        maxPixels=max_pixels,
        bestEffort=best_effort,
        tileScale=tile_scale,
    )
    return reduced.get(NDVI_BAND)


def aoi_pixel_count_expr(*, region: Any, scale: int = DEFAULT_SCALE_M) -> Any:
    """``ee.Number`` of pixels the AOI covers at *scale* (area ÷ scale²).

    Uses ``region.area`` (geometry measure), *not* a second ``reduceRegion``, so
    the fraction denominator costs no extra pixel reduction.
    """
    return region.area(maxError=1).divide(scale * scale)


# ── Pure assembler (offline; no EE) ───────────────────────────────────────────

def evaluate_quality(
    *,
    window: DateWindow,
    requested_max_cloud_pct: float,
    scene_count: int | None,
    valid_pixel_count: int | None,
    aoi_pixel_count: int | None,
    mean_scene_cloud_pct: float | None,
    dataset_id: str = S2_COLLECTION_ID,
    composite_method: str = COMPOSITE_METHOD,
    min_valid_pixel_fraction: float = MIN_VALID_PIXEL_FRACTION,
) -> QualityMetadata:
    """Assemble :class:`QualityMetadata` from evaluated scalars (pure, offline).

    Computes ``valid_pixel_fraction = valid / aoi`` and emits warnings for the
    two degraded states the service must surface understandably:

    * **no scenes** — the filtered collection is empty (nothing to composite);
    * **insufficient coverage** — valid-pixel fraction below the SNTO minimum.
    """
    valid_fraction: float | None = None
    if valid_pixel_count is not None and aoi_pixel_count:
        valid_fraction = valid_pixel_count / aoi_pixel_count

    warnings: list[str] = []
    if not scene_count:
        warnings.append(
            "no_scenes: no Sentinel-2 scenes matched the window and cloud "
            "threshold; no composite can be formed."
        )
    elif valid_fraction is not None and valid_fraction < min_valid_pixel_fraction:
        warnings.append(
            "insufficient_valid_pixels: valid-pixel coverage "
            f"{valid_fraction:.2%} is below the {min_valid_pixel_fraction:.0%} "
            "SNTO minimum; the composite may be unreliable."
        )

    return QualityMetadata(
        dataset_id=dataset_id,
        composite_method=composite_method,
        window=window,
        requested_max_cloud_pct=requested_max_cloud_pct,
        scene_count=scene_count,
        valid_pixel_count=valid_pixel_count,
        aoi_pixel_count=aoi_pixel_count,
        valid_pixel_fraction=valid_fraction,
        mean_scene_cloud_pct=mean_scene_cloud_pct,
        min_valid_pixel_fraction=min_valid_pixel_fraction,
        warnings=tuple(warnings),
    )
