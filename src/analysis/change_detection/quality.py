"""
SNTO — Change-detection quality metadata (ADR-015)
==================================================

Two layers, kept apart on purpose:

1. **EE expression builders** (``scene_count_expr``, ``mean_scene_cloud_expr``,
   ``pixel_counts_expr``) — construct lazy EE objects only. They never call
   ``getInfo``; the service evaluates them. Emptiness is therefore never probed
   inside a pure builder.
2. **A pure assembler** (:func:`evaluate_quality`) — takes the *already-evaluated*
   scalars and returns a fully JSON-serialisable :class:`QualityMetadata`,
   applying the no-scenes / insufficient-coverage warning logic offline.

Cloud metrics are not conflated: ``CLOUDY_PIXEL_PERCENTAGE`` is scene metadata
(pre-filter + ``mean_scene_cloud``), whereas valid-pixel coverage is an
SCL-derived AOI/composite measure.

Valid-pixel fraction — **bounded by construction** (fixes a confirmed live bug
where ``valid_pixel_fraction`` came out as 1.325 ≈ 1/cos(latitude)). The previous
denominator mixed two incompatible bases: the numerator was a ``reduceRegion``
pixel *count* on the Sentinel-2 UTM 10 m grid, while the denominator was
``geometry.area()/scale²`` — a geodesic m² area that, for a lat/lon rectangle,
differs from the UTM pixel count by roughly the latitude-cosine factor. Both the
valid count **and** the total count are now taken from the **same**
``reduceRegion`` over the NDVI mask (``sum`` of the 0/1 mask = valid pixels;
``count`` of the mask = total footprint pixels), on one identical pixel grid — so
``valid ≤ total`` always and ``fraction = valid/total ∈ [0, 1]``. When there is no
composite footprint the counts are ``0``/``None`` and the fraction is honestly
``None``.

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


_VALID_BAND = "valid"


def pixel_counts_expr(
    *,
    ee_module: Any,
    ndvi_image: Any,
    region: Any,
    scale: int = DEFAULT_SCALE_M,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    best_effort: bool = False,
    tile_scale: int = 1,
) -> Any:
    """``ee.Dictionary`` with the valid and total pixel counts on ONE grid.

    Both counts come from a **single** ``reduceRegion`` over the NDVI mask
    (``ndvi.mask()`` — a 0/1 image that is itself unmasked across the composite
    footprint), so they share the exact same projection, scale and region:

    * ``valid_sum``   = ``Reducer.sum``   of the mask → number of **valid** pixels;
    * ``valid_count`` = ``Reducer.count`` of the mask → number of **total**
      footprint pixels (valid + invalid).

    Because ``sum ≤ count`` on the same grid, ``valid/total ∈ [0, 1]`` — this is
    the numerically defensible denominator that replaces the old, incompatible
    ``geometry.area()/scale²``. No ``getInfo`` here.
    """
    ee = ee_module
    mask_band = ndvi_image.select(NDVI_BAND).mask().rename(_VALID_BAND)
    reducer = ee.Reducer.sum().combine(ee.Reducer.count(), sharedInputs=True)
    return mask_band.reduceRegion(
        reducer=reducer,
        geometry=region,
        scale=scale,
        maxPixels=max_pixels,
        bestEffort=best_effort,
        tileScale=tile_scale,
    )


# Keys produced by ``pixel_counts_expr`` (``<band>_<reducer>``).
VALID_PIXELS_KEY = f"{_VALID_BAND}_sum"
TOTAL_PIXELS_KEY = f"{_VALID_BAND}_count"


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

    ``valid_pixel_count`` and ``aoi_pixel_count`` are now the ``sum`` and ``count``
    of the NDVI mask from the **same** ``reduceRegion`` (see
    :func:`pixel_counts_expr`), so ``valid ≤ aoi`` and ``valid_pixel_fraction =
    valid / aoi ∈ [0, 1]`` by construction. When ``aoi`` is ``0``/``None`` (no
    composite footprint) the fraction is honestly ``None``. Emits warnings for the
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
