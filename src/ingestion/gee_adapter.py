from __future__ import annotations

import logging
import time
from typing import Any

from src.assets.models import AssetObservation, GeometryType, SpatialStats, TourismAsset
from src.ingestion.base import DataIngestionAdapter

logger = logging.getLogger(__name__)

# ── Sentinel-2 SR collection ───────────────────────────────────────────────────
# Harmonized collection is radiometrically consistent across processing baselines
# (PB < 4.00 and >= 4.00 are normalised to a common reflectance range).
_S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

# Surface reflectance scaling factor: raw DN / 10 000 → unitless [0, 1]
_SR_SCALE = 10_000.0

# Band names in this GEE collection
_BAND_BLUE = "B2"   # Blue       490 nm   10 m — needed for EVI aerosol correction
_BAND_RED  = "B4"   # Red        665 nm   10 m
_BAND_NIR  = "B8"   # NIR broad  842 nm   10 m
_BAND_SWIR = "B11"  # SWIR1     1610 nm   20 m  (GEE resamples to 10 m at runtime)
_BAND_SCL  = "SCL"  # Scene Classification Layer  20 m

# SCL classes to EXCLUDE from analysis (cloud / shadow / snow / saturated)
# 0=no_data, 1=saturated, 3=cloud_shadow, 8=cloud_med_prob,
# 9=cloud_high_prob, 10=thin_cirrus, 11=snow_ice
_SCL_BAD_VALUES: list[int] = [0, 1, 3, 8, 9, 10, 11]

# EVI coefficients (standard MODIS/Liu & Huete 1995)
_EVI_G  = 2.5
_EVI_C1 = 6.0
_EVI_C2 = 7.5
_EVI_L  = 1.0

# Buffer distances in metres
_TRAIL_BUFFER_M = 30    # 3× Sentinel-2 pixel, captures immediate trail corridor
_POINT_BUFFER_M = 50    # 5× pixel, minimal aggregation area for point assets

# Minimum fraction of valid (cloud-free) pixels to accept a monthly composite
_MIN_VALID_PIX_PCT = 0.30

# Aggregation scale in metres — match NIR/Red native 10 m resolution
_AGGREGATE_SCALE_M = 10

# GEE max-pixel guard for reduceRegion
_MAX_PIXELS = int(1e8)

# Retry settings for transient GEE API failures
_MAX_GEE_RETRIES = 3
_GEE_RETRY_BASE_DELAY_S = 2.0   # doubles on each subsequent attempt


def _gee_retry(fn, description: str = "GEE call"):
    """Call *fn()*, retrying up to _MAX_GEE_RETRIES times on any exception.

    Uses exponential backoff (2 s, 4 s, 8 s) to handle transient quota errors,
    network hiccups, and GEE backend timeouts that are common on free accounts.
    Raises the original exception if all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_GEE_RETRIES):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_GEE_RETRIES - 1:
                wait = _GEE_RETRY_BASE_DELAY_S * (2 ** attempt)
                logger.warning(
                    "%s failed (attempt %d/%d): %s — retrying in %.0f s",
                    description, attempt + 1, _MAX_GEE_RETRIES, exc, wait,
                )
                time.sleep(wait)
    raise last_exc  # type: ignore[misc]


class GEEAdapter(DataIngestionAdapter):
    """
    Google Earth Engine Sentinel-2 SR adapter.

    Pipeline per monthly observation:
      1. Filter COPERNICUS/S2_SR_HARMONIZED by date and asset geometry
      2. Apply SCL cloud / shadow / snow mask
      3. Compute per-pixel NDVI, NDMI, EVI with SR scaling
         (EVI uses B2 Blue to correct atmospheric aerosol scattering)
      4. Create monthly median composite (robust to residual cloud artifacts)
      5. Reduce over asset geometry: mean, median, p25, p75, stdDev, pixelCount
      6. Return AssetObservation with scalar means + full SpatialStats

    Multi-year:
      Use fetch_multiyear_time_series() to obtain 2021–2025 monthly records
      suitable for Mann-Kendall trend analysis and EHS computation.

    Authentication options:
      (a) Service account — pass project_id + path to JSON key file
      (b) Personal auth  — pass project_id only; run `earthengine authenticate`
          once on the machine before calling any method

    Installation:
        pip install earthengine-api
    """

    def __init__(
        self,
        project_id: str,
        key_file: str = "",
        trail_buffer_m: int = _TRAIL_BUFFER_M,
        point_buffer_m: int = _POINT_BUFFER_M,
    ) -> None:
        self.project_id = project_id
        self.key_file = key_file
        self.trail_buffer_m = trail_buffer_m
        self.point_buffer_m = point_buffer_m
        self._initialized = False

    # ── Public interface ───────────────────────────────────────────────────────

    def fetch_time_series(
        self,
        asset: TourismAsset,
        year: int,
        months: int = 12,
    ) -> list[AssetObservation]:
        """Fetch monthly observations for a single calendar year (base interface)."""
        self._initialize()
        import ee  # noqa: F401 — deferred; only needed at call time

        ee_geom = self._to_ee_geometry(asset)
        collection = self._build_masked_collection(ee_geom, year, year + 1)

        observations: list[AssetObservation] = []
        for month_idx in range(months):
            month = (month_idx % 12) + 1
            obs = self._fetch_monthly_observation(
                asset=asset,
                collection=collection,
                ee_geom=ee_geom,
                year=year,
                month=month,
            )
            if obs is not None:
                observations.append(obs)
            else:
                logger.warning(
                    "No valid composite for %s %d/%02d (cloud coverage too high).",
                    asset.asset_id, year, month,
                )
        return observations

    def fetch_multiyear_time_series(
        self,
        asset: TourismAsset,
        years: list[int],
    ) -> list[AssetObservation]:
        """Fetch monthly NDVI / NDMI / EVI observations across multiple years.

        Builds a SINGLE GEE ImageCollection spanning the full date range
        (cheaper than one collection per year) then iterates month-by-month.
        Observations are sorted chronologically; months with insufficient
        cloud-free coverage are silently skipped (logged at WARNING level).

        Typical call for a 2021–2025 Mann-Kendall analysis::

            obs = adapter.fetch_multiyear_time_series(asset, list(range(2021, 2026)))
            mk  = mann_kendall_test([o.ndvi for o in obs])

        Args:
            asset: The tourism asset whose geometry defines the aggregation zone.
            years: List of calendar years, e.g. [2021, 2022, 2023, 2024, 2025].
                   Must be sorted; gaps are allowed (GEE handles them gracefully).

        Returns:
            Chronologically ordered list of AssetObservation.  May be shorter
            than len(years) × 12 when cloud cover is high.
        """
        if not years:
            return []

        self._initialize()

        ee_geom = self._to_ee_geometry(asset)
        start_year = min(years)
        end_year   = max(years) + 1  # exclusive
        collection = self._build_masked_collection(ee_geom, start_year, end_year)

        observations: list[AssetObservation] = []
        total = len(years) * 12
        fetched = 0

        for year in sorted(years):
            for month in range(1, 13):
                obs = self._fetch_monthly_observation(
                    asset=asset,
                    collection=collection,
                    ee_geom=ee_geom,
                    year=year,
                    month=month,
                )
                fetched += 1
                if obs is not None:
                    observations.append(obs)
                    logger.debug(
                        "[%s] %d/%02d → NDVI=%.3f NDMI=%.3f EVI=%s",
                        asset.asset_id, year, month, obs.ndvi, obs.ndmi,
                        f"{obs.evi:.3f}" if obs.evi is not None else "n/a",
                    )
                else:
                    logger.warning(
                        "[%s] %d/%02d skipped — insufficient cloud-free pixels.",
                        asset.asset_id, year, month,
                    )

        logger.info(
            "[%s] Multi-year fetch complete: %d/%d months with valid data.",
            asset.asset_id, len(observations), total,
        )
        return observations

    # ── Geometry helpers ───────────────────────────────────────────────────────

    def _to_ee_geometry(self, asset: TourismAsset):
        """Convert a TourismAsset geometry to a buffered ee.Geometry for aggregation."""
        import ee

        coords = asset.geometry.coordinates
        gtype  = asset.geometry.type

        if gtype == GeometryType.LINESTRING:
            return ee.Geometry.LineString(coords).buffer(self.trail_buffer_m)
        elif gtype == GeometryType.POINT:
            return ee.Geometry.Point(coords).buffer(self.point_buffer_m)
        else:
            return ee.Geometry.Polygon(coords)

    # ── Collection pipeline ────────────────────────────────────────────────────

    def _build_masked_collection(self, ee_geom, start_year: int, end_year: int):
        """Filter S2 SR to geometry + date range, apply SCL mask, compute indices."""
        import ee

        return (
            ee.ImageCollection(_S2_COLLECTION)
            .filterBounds(ee_geom)
            .filterDate(f"{start_year}-01-01", f"{end_year}-01-01")
            .map(self._cloud_mask_scl)
            .map(self._compute_scaled_indices)
        )

    @staticmethod
    def _cloud_mask_scl(image):
        """Mask cloud, shadow, cirrus, snow pixels using the SCL band.

        SCL is the recommended masking approach for Sentinel-2 L2A.
        It supersedes the older QA60 bitmask which only covered high-confidence clouds.
        """
        import ee

        scl = image.select(_BAND_SCL)
        mask = scl.neq(_SCL_BAD_VALUES[0])
        for bad_val in _SCL_BAD_VALUES[1:]:
            mask = mask.And(scl.neq(bad_val))
        return image.updateMask(mask)

    @staticmethod
    def _compute_scaled_indices(image):
        """Compute NDVI, NDMI, and EVI from SR-scaled reflectance, adding them as bands.

        B11 (SWIR1, 20 m) is automatically resampled by GEE to the output
        resolution set in reduceRegion (scale=10 m) using bilinear interpolation.

        EVI uses the blue band (B2) to correct for atmospheric aerosol scattering.
        It avoids NDVI saturation in dense forest canopies (NDVI > 0.80).
        """
        b2  = image.select(_BAND_BLUE).divide(_SR_SCALE)
        b4  = image.select(_BAND_RED).divide(_SR_SCALE)
        b8  = image.select(_BAND_NIR).divide(_SR_SCALE)
        b11 = image.select(_BAND_SWIR).divide(_SR_SCALE)

        ndvi = b8.subtract(b4).divide(b8.add(b4)).rename("NDVI")
        ndmi = b8.subtract(b11).divide(b8.add(b11)).rename("NDMI")

        # EVI = G × (NIR – RED) / (NIR + C1×RED – C2×BLUE + L)
        evi_num   = b8.subtract(b4).multiply(_EVI_G)
        evi_denom = b8.add(b4.multiply(_EVI_C1)).subtract(b2.multiply(_EVI_C2)).add(_EVI_L)
        # Guard against zero/negative denominator before division
        evi = evi_num.divide(evi_denom.where(evi_denom.lte(0), 1e-6)).rename("EVI")

        return image.addBands([ndvi, ndmi, evi])

    # ── Monthly aggregation ────────────────────────────────────────────────────

    def _fetch_monthly_observation(
        self,
        asset: TourismAsset,
        collection,
        ee_geom,
        year: int,
        month: int,
    ) -> AssetObservation | None:
        """Build a monthly median composite and reduce to scalar statistics.

        Monthly median compositing is more robust to residual cloud / haze
        artifacts than mean compositing.  5–10 valid scenes/month are typical
        for Sierra del Rincón given the 5-day revisit of Sentinel-2 A+B.

        Returns None when the valid-pixel fraction is below _MIN_VALID_PIX_PCT,
        signalling a cloud-dominated month that should be gap-filled rather
        than used as-is.
        """
        import ee

        start = ee.Date.fromYMD(year, month, 1)
        end   = start.advance(1, "month")
        monthly = collection.filterDate(start, end)

        # Avoid a getInfo() roundtrip if the collection is trivially empty
        image_count = _gee_retry(
            lambda: monthly.size().getInfo(),
            description=f"size() {year}/{month:02d}",
        )
        if image_count == 0:
            return None

        composite = monthly.median()

        reducer = (
            ee.Reducer.mean()
            .combine(ee.Reducer.median(),            sharedInputs=True)
            .combine(ee.Reducer.percentile([25, 75]), sharedInputs=True)
            .combine(ee.Reducer.stdDev(),             sharedInputs=True)
            .combine(ee.Reducer.count(),              sharedInputs=True)
        )

        raw: dict[str, Any] = _gee_retry(
            lambda: composite.select(["NDVI", "NDMI", "EVI"]).reduceRegion(
                reducer=reducer,
                geometry=ee_geom,
                scale=_AGGREGATE_SCALE_M,
                maxPixels=_MAX_PIXELS,
            ).getInfo(),
            description=f"reduceRegion {asset.asset_id} {year}/{month:02d}",
        )

        ndvi_mean = raw.get("NDVI_mean")
        ndmi_mean = raw.get("NDMI_mean")
        evi_mean  = raw.get("EVI_mean")

        if ndvi_mean is None or ndmi_mean is None:
            return None

        area_m2      = _gee_retry(lambda: ee_geom.area(maxError=1).getInfo())
        total_pixels = max(1, area_m2 / (_AGGREGATE_SCALE_M ** 2))
        valid_pixels = int(raw.get("NDVI_count", 0))
        valid_pct    = valid_pixels / total_pixels

        if valid_pct < _MIN_VALID_PIX_PCT:
            return None

        cloud_pct = round((1.0 - valid_pct) * 100.0, 1)

        ndvi_stats = SpatialStats(
            mean=float(ndvi_mean),
            median=float(raw.get("NDVI_median", ndvi_mean)),
            p25=float(raw.get("NDVI_p25", ndvi_mean)),
            p75=float(raw.get("NDVI_p75", ndvi_mean)),
            std=float(raw.get("NDVI_stdDev", 0.0)),
            pixel_count=valid_pixels,
            valid_pixel_pct=round(valid_pct, 3),
        )
        ndmi_stats = SpatialStats(
            mean=float(ndmi_mean),
            median=float(raw.get("NDMI_median", ndmi_mean)),
            p25=float(raw.get("NDMI_p25", ndmi_mean)),
            p75=float(raw.get("NDMI_p75", ndmi_mean)),
            std=float(raw.get("NDMI_stdDev", 0.0)),
            pixel_count=valid_pixels,
            valid_pixel_pct=round(valid_pct, 3),
        )

        return AssetObservation(
            asset_id=asset.asset_id,
            year=year,
            month=month,
            ndvi=float(ndvi_mean),
            ndmi=float(ndmi_mean),
            evi=float(evi_mean) if evi_mean is not None else None,
            cloud_cover_pct=cloud_pct,
            data_source="GEE:S2_SR_HARMONIZED",
            ndvi_stats=ndvi_stats,
            ndmi_stats=ndmi_stats,
        )

    # ── Initialisation ─────────────────────────────────────────────────────────

    def _initialize(self) -> None:
        if self._initialized:
            return
        try:
            import ee
        except ImportError as exc:
            raise RuntimeError(
                "earthengine-api is not installed. "
                "Run: pip install earthengine-api"
            ) from exc

        if self.key_file:
            credentials = ee.ServiceAccountCredentials(
                email="",
                key_file=self.key_file,
            )
            ee.Initialize(credentials=credentials, project=self.project_id)
        else:
            # Personal auth — requires prior `earthengine authenticate` call
            ee.Initialize(project=self.project_id)

        self._initialized = True
        logger.info("GEE initialized. Project: %s", self.project_id)
