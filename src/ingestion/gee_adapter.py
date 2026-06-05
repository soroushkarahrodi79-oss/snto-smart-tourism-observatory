from __future__ import annotations

import logging
from typing import Any

from src.assets.models import AssetObservation, GeometryType, SpatialStats, TourismAsset
from src.ingestion.base import DataIngestionAdapter

logger = logging.getLogger(__name__)

# ── Sentinel-2 SR constants ────────────────────────────────────────────────

# Use the harmonized collection: radiometrically consistent across processing
# baselines (PB < 4.00 and >= 4.00 are normalized to a common range).
_S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

# Surface reflectance scaling factor for all optical bands in this collection.
# Raw integer values must be divided by 10000 to obtain unitless [0, 1] reflectance.
_SR_SCALE = 10_000.0

# Sentinel-2 band names used in this collection
_BAND_RED = "B4"    # Red        665 nm   10 m
_BAND_NIR = "B8"    # NIR broad  842 nm   10 m
_BAND_SWIR = "B11"  # SWIR1     1610 nm   20 m  (resampled to 10 m by GEE at runtime)
_BAND_SCL = "SCL"   # Scene Classification Layer  20 m

# SCL pixel classes to EXCLUDE from analysis (cloud / shadow / snow / saturated)
# 0=no_data, 1=saturated, 3=cloud_shadow, 8=cloud_med_prob,
# 9=cloud_high_prob, 10=thin_cirrus, 11=snow_ice
_SCL_BAD_VALUES = [0, 1, 3, 8, 9, 10, 11]

# Geometry buffer distances in metres
_TRAIL_BUFFER_M = 30    # 3× Sentinel-2 pixel, captures immediate trail corridor
_POINT_BUFFER_M = 50    # 5× pixel, minimal aggregation area for point assets

# Minimum fraction of valid (cloud-free) pixels required to accept a monthly composite
_MIN_VALID_PIX_PCT = 0.30

# Aggregation scale in metres — match NIR/Red 10 m native resolution
_AGGREGATE_SCALE_M = 10

# GEE maximum pixel count guard for reduceRegion
_MAX_PIXELS = int(1e8)


class GEEAdapter(DataIngestionAdapter):
    """
    Google Earth Engine Sentinel-2 SR adapter.

    Pipeline per monthly observation:
      1. Filter COPERNICUS/S2_SR_HARMONIZED by date and asset geometry
      2. Apply SCL cloud / shadow / snow mask
      3. Compute per-pixel NDVI = (B8 - B4) / (B8 + B4) with SR scaling
      4. Compute per-pixel NDMI = (B8 - B11) / (B8 + B11) with SR scaling
         (B11 at 20 m is automatically resampled by GEE when scale=10 is set)
      5. Create monthly median composite (robust to residual cloud artifacts)
      6. Reduce over asset geometry: mean, median, p25, p75, stdDev, pixelCount
      7. Return AssetObservation with scalar means + full SpatialStats

    Authentication options:
      (a) Service account — pass project_id + path to JSON key file
      (b) Personal auth  — pass project_id only; run `earthengine authenticate`
          once on the machine before using the system

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

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def fetch_time_series(
        self,
        asset: TourismAsset,
        year: int,
        months: int = 12,
    ) -> list[AssetObservation]:
        self._initialize()
        import ee  # deferred; only needed at call time

        ee_geom = self._to_ee_geometry(asset)
        collection = self._build_masked_collection(ee_geom, year)

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
                    "No valid composite for %s month=%d/%d (cloud coverage too high).",
                    asset.asset_id,
                    year,
                    month,
                )

        return observations

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _to_ee_geometry(self, asset: TourismAsset):
        """
        Convert a TourismAsset geometry to an ee.Geometry suitable for
        pixel aggregation.

        LineString trails are buffered to create a corridor polygon — this is
        essential because Sentinel-2 pixels cover 100 m² each, and a
        zero-width line would intersect no pixels.
        Point viewpoints are buffered to a small circle for the same reason.
        Polygon recreational areas are used directly.
        """
        import ee

        coords = asset.geometry.coordinates
        gtype = asset.geometry.type

        if gtype == GeometryType.LINESTRING:
            return ee.Geometry.LineString(coords).buffer(self.trail_buffer_m)
        elif gtype == GeometryType.POINT:
            return ee.Geometry.Point(coords).buffer(self.point_buffer_m)
        else:
            return ee.Geometry.Polygon(coords)

    # ------------------------------------------------------------------
    # Collection pipeline
    # ------------------------------------------------------------------

    def _build_masked_collection(self, ee_geom, year: int):
        """
        Filter the S2 SR collection to the asset geometry and year,
        then apply the SCL cloud/shadow/snow mask.
        """
        import ee

        start = f"{year}-01-01"
        end = f"{year + 1}-01-01"

        return (
            ee.ImageCollection(_S2_COLLECTION)
            .filterBounds(ee_geom)
            .filterDate(start, end)
            .map(self._cloud_mask_scl)
            .map(self._compute_scaled_indices)
        )

    @staticmethod
    def _cloud_mask_scl(image):
        """
        Mask cloud, shadow, cirrus, snow pixels using the SCL band.

        SCL (Scene Classification Layer) is the recommended masking approach
        for Sentinel-2 L2A (surface reflectance) products.  It supersedes the
        older QA60 bitmask approach which only covered high-confidence clouds.
        """
        import ee

        scl = image.select(_BAND_SCL)
        # Build a mask: 1 = valid pixel, 0 = bad
        mask = scl.neq(_SCL_BAD_VALUES[0])
        for bad_val in _SCL_BAD_VALUES[1:]:
            mask = mask.And(scl.neq(bad_val))
        return image.updateMask(mask)

    @staticmethod
    def _compute_scaled_indices(image):
        """
        Compute NDVI and NDMI from SR-scaled reflectance bands and attach
        them as new image bands named 'NDVI' and 'NDMI'.

        Band scaling: divide raw integer DN by 10 000 to get unitless [0, 1]
        surface reflectance before applying the normalised difference formula.

        B11 (SWIR1, 20 m) is automatically resampled by GEE to the output
        resolution specified in reduceRegion (scale=10 m) using the default
        bilinear interpolation.  This is the correct approach for NDMI; using
        the raw 20 m B11 without resampling would spatially misalign with the
        10 m NIR band.
        """
        b4 = image.select(_BAND_RED).divide(_SR_SCALE)
        b8 = image.select(_BAND_NIR).divide(_SR_SCALE)
        b11 = image.select(_BAND_SWIR).divide(_SR_SCALE)

        ndvi = b8.subtract(b4).divide(b8.add(b4)).rename("NDVI")
        ndmi = b8.subtract(b11).divide(b8.add(b11)).rename("NDMI")

        return image.addBands([ndvi, ndmi])

    # ------------------------------------------------------------------
    # Monthly aggregation
    # ------------------------------------------------------------------

    def _fetch_monthly_observation(
        self,
        asset: TourismAsset,
        collection,
        ee_geom,
        year: int,
        month: int,
    ) -> AssetObservation | None:
        """
        Build a monthly median composite and reduce it to scalar statistics
        over the asset geometry.

        Monthly median compositing:
        - More robust to remaining cloud / haze artifacts than mean compositing
        - Reduces salt-and-pepper noise from partially cloud-masked pixels
        - 5–10 valid scenes per month are sufficient for a stable median in
          Extremadura (typical revisit every 5 days for Sentinel-2 A+B combined)

        Returns None if the valid-pixel fraction is below _MIN_VALID_PIX_PCT,
        which indicates a cloud-dominated month that should be gap-filled
        rather than used as-is.
        """
        import ee

        start = ee.Date.fromYMD(year, month, 1)
        end = start.advance(1, "month")

        monthly = collection.filterDate(start, end)
        image_count = monthly.size().getInfo()

        if image_count == 0:
            return None

        composite = monthly.median()

        # Combined reducer: mean + median + p25/p75 + stdDev + count (valid pixels)
        reducer = (
            ee.Reducer.mean()
            .combine(ee.Reducer.median(), sharedInputs=True)
            .combine(ee.Reducer.percentile([25, 75]), sharedInputs=True)
            .combine(ee.Reducer.stdDev(), sharedInputs=True)
            .combine(ee.Reducer.count(), sharedInputs=True)
        )

        raw = composite.select(["NDVI", "NDMI"]).reduceRegion(
            reducer=reducer,
            geometry=ee_geom,
            scale=_AGGREGATE_SCALE_M,
            maxPixels=_MAX_PIXELS,
        ).getInfo()

        # Parse reducer output key names (GEE appends reducer names to band names)
        ndvi_mean = raw.get("NDVI_mean")
        ndmi_mean = raw.get("NDMI_mean")

        if ndvi_mean is None or ndmi_mean is None:
            return None

        # Compute total pixel count to derive valid fraction
        # Total pixels ≈ geometry_area_m2 / (scale² )
        area_m2 = ee_geom.area(maxError=1).getInfo()
        total_pixels = max(1, area_m2 / (_AGGREGATE_SCALE_M ** 2))
        valid_pixels = int(raw.get("NDVI_count", 0))
        valid_pct = valid_pixels / total_pixels

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
            cloud_cover_pct=cloud_pct,
            data_source="GEE:S2_SR_HARMONIZED",
            ndvi_stats=ndvi_stats,
            ndmi_stats=ndmi_stats,
        )

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        if self._initialized:
            return
        try:
            import ee
        except ImportError as exc:
            raise RuntimeError(
                "earthengine-api is not installed. Run: pip install earthengine-api"
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
