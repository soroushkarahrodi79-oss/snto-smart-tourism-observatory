"""
SNTO — Median composite builders (ADR-015)
==========================================

Pure EE-object-in / EE-object-out builders. Each takes a *masked* Sentinel-2
collection (from
:func:`src.integrations.earth_engine.collections.build_sentinel2_collection`,
which already applies the SCL pixel mask per scene) and returns a lazy EE image.
No ``getInfo``; emptiness / all-cloud is surfaced later by quality evaluation,
never by fabricating blank imagery here.
"""
from __future__ import annotations

from typing import Any

from src.integrations.earth_engine.collections import (
    NDVI_BAND,
    TRUE_COLOUR_BANDS,
    add_ndvi,
)


def true_colour_composite(collection: Any) -> Any:
    """Median **true-colour reflectance** composite (bands B4, B3, B2).

    Returns the analytical median-reflectance image with the true-colour bands in
    R, G, B order. It is intentionally **not** stretched to 8-bit here — display
    scaling is a rendering concern (``earth_engine.palettes`` +
    ``earth_engine.render``), kept separate from the analytical source image.
    """
    return collection.select(list(TRUE_COLOUR_BANDS)).median()


def _per_scene_ndvi(image: Any) -> Any:
    """Per-scene NDVI (single band) — the map callback for :func:`ndvi_composite`."""
    return add_ndvi(image).select(NDVI_BAND)


def ndvi_composite(collection: Any) -> Any:
    """Median **NDVI** composite, computed as *median of per-scene NDVI*.

    Methodology (deliberate, documented): NDVI is computed on each already-masked
    scene, then the per-scene NDVI ImageCollection is reduced with ``median``.
    This is **not** ``NDVI(median reflectance)`` — reducing NDVI directly avoids
    band-wise reflectance medians producing a ratio that no single acquisition
    actually observed, and it is robust to residual haze. The output band keeps
    the canonical name ``NDVI``.
    """
    ndvi_collection = collection.map(_per_scene_ndvi)
    return ndvi_collection.median().rename(NDVI_BAND)
