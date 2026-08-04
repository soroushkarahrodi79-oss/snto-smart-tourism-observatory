"""
SNTO — Temporal animation planning + frame construction (ADR-015)
=================================================================

Two concerns, kept pure and framework-thin:

1. **Local frame planner** (`plan_frame_windows`) — no Earth Engine, no network,
   no current-date use: turns an inclusive ``[start, end]`` interval + a frame
   cap into contiguous, non-overlapping, chronological calendar-month
   :class:`DateWindow` frames. The step grows in whole months so the frame count
   stays within the hard limits.
2. **EE frame construction** — one masked Sentinel-2 collection per frame (shared
   helper), the selected product composite (True-Colour median / median-of-
   per-scene NDVI), **pre-visualised** with the centralised fixed visualisation so
   every frame shares one stretch/palette (no per-frame auto-stretch), tagged with
   ``system:time_start`` + frame index. All lazy — **no** ``getInfo`` here.

The GIF is exploratory: **scene count is checked per frame** (cheaply, one grouped
call in the service), but the full per-pixel valid-pixel coverage is **not**
recomputed for every frame (that would add repeated expensive ``reduceRegion``
work). See the service for the single grouped scene-count evaluation.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from datetime import datetime as _datetime
from typing import Any

from src.analysis.change_detection.composites import (
    ndvi_composite,
    true_colour_composite,
)
from src.analysis.change_detection.models import CompositeKind, DateWindow
from src.integrations.earth_engine.collections import build_sentinel2_collection
from src.integrations.earth_engine.palettes import NDVI, TRUE_COLOUR, Visualization

# Version tag — part of the animation cache key so a planner change invalidates.
ANIMATION_PLANNER_VERSION = "anim-plan-v1"

# Hard limits (frames / span). Dimensions & FPS limits live in
# integrations/earth_engine/video.py (the lowest layer).
MIN_FRAMES = 2
MAX_FRAMES = 12
DEFAULT_MAX_FRAMES = 8
ALLOWED_MAX_FRAMES: tuple[int, ...] = (4, 6, 8, 10, 12)
MAX_SPAN_MONTHS = 24

_PRODUCT_VIS: dict[CompositeKind, Visualization] = {
    CompositeKind.TRUE_COLOUR: TRUE_COLOUR,
    CompositeKind.NDVI: NDVI,
}


# ── Month arithmetic (small safe helpers; no external dependency) ─────────────

def _add_months(anchor_first_of_month: date, n: int) -> date:
    """Return the first day of the month *n* months after *anchor* (a 1st-of-month)."""
    total = (anchor_first_of_month.year * 12 + (anchor_first_of_month.month - 1)) + n
    year, month0 = divmod(total, 12)
    return date(year, month0 + 1, 1)


def calendar_month_span(start: date, end: date) -> int:
    """Number of distinct calendar months touched by inclusive ``[start, end]``."""
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


# ── Frame planner (pure) ──────────────────────────────────────────────────────

def plan_frame_windows(
    start: date, end: date, max_frames: int
) -> list[DateWindow]:
    """Plan contiguous calendar-month frame windows for inclusive ``[start, end]``.

    Rules: prefer whole-month windows; if the span would exceed *max_frames*,
    grow the step to ``ceil(months / max_frames)`` whole months; the first and
    last frame may be partial months; every day belongs to exactly one frame; no
    gaps, no overlaps; the final inclusive date is retained; the frame count stays
    in ``[MIN_FRAMES, MAX_FRAMES]``. Rejects spans too short for two frames or
    longer than :data:`MAX_SPAN_MONTHS`. Never reads the current date.
    """
    if isinstance(start, _datetime) or isinstance(end, _datetime):
        raise TypeError("plan_frame_windows requires datetime.date, not datetime.")
    if not isinstance(start, date) or not isinstance(end, date):
        raise TypeError("start/end must be datetime.date instances.")
    if start > end:
        raise ValueError(f"reversed animation range: {start} > {end}.")

    months = calendar_month_span(start, end)
    if months > MAX_SPAN_MONTHS:
        raise ValueError(
            f"animation span {months} months exceeds the {MAX_SPAN_MONTHS}-month max."
        )
    if months < MIN_FRAMES:
        raise ValueError(
            "animation span is too short to form at least two monthly frames "
            f"(span={months} month)."
        )
    if max_frames < MIN_FRAMES:
        raise ValueError(f"max_frames must be >= {MIN_FRAMES}, got {max_frames}.")

    step = max(1, math.ceil(months / max_frames))
    first_month = date(start.year, start.month, 1)

    frames: list[DateWindow] = []
    k = 0
    while True:
        block_start = _add_months(first_month, k * step)
        if block_start > end:
            break
        block_end_excl = _add_months(first_month, (k + 1) * step)
        frame_start = start if k == 0 else block_start
        if end < block_end_excl:
            frames.append(DateWindow(frame_start, end, end_inclusive=True))
            break
        frame_end = block_end_excl - timedelta(days=1)
        frames.append(DateWindow(frame_start, frame_end, end_inclusive=True))
        k += 1

    if not (MIN_FRAMES <= len(frames) <= MAX_FRAMES):
        raise ValueError(
            f"planner produced {len(frames)} frames, outside "
            f"[{MIN_FRAMES}, {MAX_FRAMES}]."
        )
    return frames


# ── EE frame construction (lazy; no getInfo) ──────────────────────────────────

def build_frame(
    *,
    ee_module: Any,
    geometry: Any,
    window: DateWindow,
    product: CompositeKind,
    max_cloud_pct: float,
    frame_index: int,
) -> tuple[Any, Any]:
    """Build one animation frame.

    Returns ``(visualised_image, masked_collection)``:

    * ``masked_collection`` — the shared masked Sentinel-2 collection for the frame
      window (used by the service for the grouped scene-count check);
    * ``visualised_image`` — the product median composite (True-Colour B4/B3/B2 or
      median-of-per-scene NDVI) **pre-visualised** with the centralised fixed
      visualisation (RGB), tagged with ``system:time_start`` + frame metadata. The
      pre-visualisation guarantees one identical stretch/palette across all frames.
    """
    ee = ee_module
    if product not in _PRODUCT_VIS:
        raise ValueError(f"unsupported animation product {product!r}.")

    collection = build_sentinel2_collection(
        ee_module=ee,
        geometry=geometry,
        start_date=window.ee_start_date(),
        end_date=window.ee_end_date(),
        max_cloud_percentage=max_cloud_pct,
    )
    if product is CompositeKind.NDVI:
        composite = ndvi_composite(collection)
    else:
        composite = true_colour_composite(collection)

    visualised = composite.visualize(**_PRODUCT_VIS[product].to_ee_params())
    visualised = visualised.set(
        {
            "system:time_start": ee.Date(window.ee_start_date()).millis(),
            "frame_index": frame_index,
            "frame_start": window.ee_start_date(),
            "frame_end": window.ee_end_date(),
        }
    )
    return visualised, collection


def scene_counts_expr(*, ee_module: Any, collections: list[Any]) -> Any:
    """One grouped ``ee.List`` of ``collection.size()`` for every planned frame.

    Evaluated with a **single** ``getInfo`` in the service — never one call per
    frame.
    """
    return ee_module.List([col.size() for col in collections])


def build_video_collection(*, ee_module: Any, images: list[Any]) -> Any:
    """Chronological ``ee.ImageCollection`` of the (already visualised) frames."""
    return ee_module.ImageCollection.fromImages(images).sort("system:time_start")
