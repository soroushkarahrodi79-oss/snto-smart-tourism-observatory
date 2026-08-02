"""
SNTO — Shared Sentinel-2 collection construction & masking (ADR-015)
====================================================================

Single source of truth for the Sentinel-2 SR pieces that both the offline
ingestion adapter (``src/ingestion/gee_adapter.py``) and the in-process Visual
Change Explorer need: the collection id, band names, the SCL bad-class pixel
mask, the NDVI definition, the minimum-valid-pixel convention, and the
scene-level collection builder.

Design
------
* **No Earth Engine import.** The masking / index helpers use only *methods on
  the EE objects handed to them* (``image.select``, ``image.normalizedDifference``,
  …), and :func:`build_sentinel2_collection` takes the ``ee`` module explicitly
  (``ee_module=``). So this module stays importable and unit-testable without the
  SDK, consistent with the rest of the foundation.
* **No network.** Nothing here calls ``getInfo`` / ``getThumbURL`` / ``getDownloadURL``.
  Builders return lazy EE objects; evaluation is the caller's concern
  (quality evaluation / the future service), never a constructor side effect.
* **Masking vs. scene filtering are two different things** (kept distinct on
  purpose, see the Visual Change Explorer docs):
  - ``CLOUDY_PIXEL_PERCENTAGE`` is *scene metadata* used as a cheap **scene-level**
    pre-filter (drop whole granules cloudier than the user threshold).
  - The **SCL bad-class mask** is a **pixel-level** mask (cloud / shadow / cirrus /
    snow / saturated / no-data) applied to every retained scene.
"""
from __future__ import annotations

from typing import Any

# ── Collection & bands ────────────────────────────────────────────────────────
# Harmonized SR collection: radiometrically consistent across processing
# baselines (PB < 4.00 and >= 4.00 normalised to a common reflectance range).
S2_COLLECTION_ID = "COPERNICUS/S2_SR_HARMONIZED"

# Surface-reflectance scaling factor: raw DN / 10 000 → unitless [0, 1].
SR_SCALE = 10_000.0

BAND_BLUE = "B2"   # 490 nm  10 m
BAND_GREEN = "B3"  # 560 nm  10 m
BAND_RED = "B4"    # 665 nm  10 m
BAND_NIR = "B8"    # 842 nm  10 m
BAND_SWIR1 = "B11"  # 1610 nm 20 m (GEE resamples to 10 m at reduce time)
BAND_SCL = "SCL"   # Scene Classification Layer 20 m

# True-colour band order (R, G, B) for visualisation composites.
TRUE_COLOUR_BANDS: tuple[str, str, str] = (BAND_RED, BAND_GREEN, BAND_BLUE)

# Canonical index band names.
NDVI_BAND = "NDVI"
DNDVI_BAND = "dNDVI"

# SCL classes to EXCLUDE (cloud / shadow / snow / saturated / no-data):
# 0=no_data, 1=saturated, 3=cloud_shadow, 8=cloud_med_prob,
# 9=cloud_high_prob, 10=thin_cirrus, 11=snow_ice.
SCL_BAD_VALUES: tuple[int, ...] = (0, 1, 3, 8, 9, 10, 11)

# Minimum fraction of valid (cloud-free) pixels for a composite to be trusted.
# This is the established SNTO convention (was ``_MIN_VALID_PIX_PCT`` in the
# ingestion adapter); reused verbatim so the two paths agree.
MIN_VALID_PIXEL_FRACTION = 0.30

# Aggregation scale (m) — matches the 10 m NIR/Red native resolution.
DEFAULT_SCALE_M = 10

# reduceRegion pixel guard (matches the ingestion adapter's historical value).
DEFAULT_MAX_PIXELS = int(1e8)


# ── Pixel-level mask & indices (EE-object-in / EE-object-out, no ee module) ────

def mask_scl(image: Any) -> Any:
    """Return *image* with SCL bad-class pixels masked out.

    Uses only methods on the passed EE image (``select``/``neq``/``And``/
    ``updateMask``) so it works both server-side (inside ``.map``) and under a
    mocked ``ee`` in tests. All original bands are preserved (``updateMask`` only
    changes the mask, not the band set).
    """
    scl = image.select(BAND_SCL)
    mask = scl.neq(SCL_BAD_VALUES[0])
    for bad_val in SCL_BAD_VALUES[1:]:
        mask = mask.And(scl.neq(bad_val))
    return image.updateMask(mask)


def add_ndvi(image: Any) -> Any:
    """Return *image* with an ``NDVI`` band appended.

    NDVI = (NIR − RED) / (NIR + RED) via ``normalizedDifference``. This is the
    **single** NDVI definition in the codebase; the ingestion adapter delegates
    here. NDVI is invariant to the common SR scale factor, so applying it to raw
    or ``/SR_SCALE`` reflectance yields identical values.
    """
    ndvi = image.normalizedDifference([BAND_NIR, BAND_RED]).rename(NDVI_BAND)
    return image.addBands(ndvi)


# ── Scene-level collection builder ────────────────────────────────────────────

def build_sentinel2_collection(
    *,
    ee_module: Any,
    geometry: Any,
    start_date: str,
    end_date: str,
    max_cloud_percentage: float,
) -> Any:
    """Build a masked Sentinel-2 SR ImageCollection for a date window.

    Pipeline (all lazy — **no** ``getInfo``):

    1. ``ee.ImageCollection(S2_COLLECTION_ID)``
    2. ``.filterBounds(geometry)``
    3. ``.filterDate(start_date, end_date)`` — **end-exclusive**, the Earth Engine
       convention: the window is ``[start_date, end_date)``. Callers that work in
       inclusive user dates must convert to the EE-exclusive end **once**, at the
       :class:`~src.analysis.change_detection.models.DateWindow` boundary — this
       function does no date arithmetic and never reads the current date.
    4. ``.filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percentage))``
       — the **scene-level** cloud pre-filter (whole-granule metadata).
    5. ``.map(mask_scl)`` — the **pixel-level** SCL bad-class mask.

    All native bands are retained (no ``select``), so both true colour
    (B4/B3/B2) and NDVI (B8/B4) can be derived downstream. Emptiness / all-cloud
    is **not** probed here; it is surfaced later via quality evaluation.
    """
    ee = ee_module
    return (
        ee.ImageCollection(S2_COLLECTION_ID)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percentage))
        .map(mask_scl)
    )
