"""
SNTO ETL Phase 0 -- Sentinel-2 Raster Processor
=================================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Locates the Sentinel-2A L2A ZIP in data/raw_assets/raster_data/, selectively
extracts only the three required bands (B04 Red 10m, B08 NIR 10m, B11 SWIR
20m), clips them to the Sierra del Rincón bounding box, resamples B11 to 10m
via bilinear interpolation, computes NDVI and NDMI, and writes 5 production-
ready GeoTIFFs to data/clean_assets/.

Inputs  : data/raw_assets/raster_data/S2A_MSIL2A_*.zip
Outputs : data/clean_assets/clean_S2_B04_red.tif
          data/clean_assets/clean_S2_B08_nir.tif
          data/clean_assets/clean_S2_B11_swir.tif
          data/clean_assets/clean_S2_NDVI.tif
          data/clean_assets/clean_S2_NDMI.tif
"""
from __future__ import annotations

import io
import shutil
import sys
import zipfile
from pathlib import Path

# Ensure UTF-8 output regardless of terminal code page
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.mask import mask as rio_mask
from rasterio.transform import array_bounds, from_bounds
from rasterio.warp import reproject as rio_reproject
from shapely.geometry import box, mapping

SEP = "=" * 72
DIV = "-" * 72

PROJECT_ROOT = Path(__file__).parent
RASTER_DIR   = PROJECT_ROOT / "data" / "raw_assets" / "raster_data"
CLEAN_DIR    = PROJECT_ROOT / "data" / "clean_assets"
TMP_DIR      = RASTER_DIR / "tmp_sentinel"

# Sierra del Rincón study bounding box (EPSG:4326)
BBOX_4326 = (-3.65, 41.05, -3.30, 41.20)   # minx, miny, maxx, maxy

# Sentinel-2 tile T30TVL → WGS84 / UTM Zone 30N
BAND_CRS_EPSG = 32630


def _locate_zip() -> Path:
    """Find the single Sentinel-2A L2A ZIP file in RASTER_DIR."""
    zips = list(RASTER_DIR.glob("S2A_MSIL2A*.zip"))
    if len(zips) != 1:
        raise FileNotFoundError(
            f"Expected exactly 1 Sentinel-2A ZIP in {RASTER_DIR}, found {len(zips)}"
        )
    return zips[0]


def _extract_bands(zip_path: Path) -> tuple[Path, Path, Path]:
    """Selectively extract B04, B08, B11 JP2 files from the ZIP.

    Extracts only ~252 MB instead of the full 1+ GB archive.
    Returns (b04_path, b08_path, b11_path).
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = zip_path.stem + ".SAFE"

    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()

        def _find_band(pattern_dir: str, pattern_file: str) -> str:
            matches = [n for n in names if pattern_dir in n and pattern_file in n]
            if not matches:
                raise FileNotFoundError(
                    f"Band file matching '{pattern_file}' in '{pattern_dir}' not found "
                    f"inside {zip_path.name}. Found entries (sample): "
                    f"{[n for n in names if '.jp2' in n][:6]}"
                )
            return matches[0]

        b04_entry = _find_band("IMG_DATA/R10m", "B04_10m.jp2")
        b08_entry = _find_band("IMG_DATA/R10m", "B08_10m.jp2")
        b11_entry = _find_band("IMG_DATA/R20m", "B11_20m.jp2")

        print(f"  Extracting B04: {Path(b04_entry).name}")
        z.extract(b04_entry, TMP_DIR)
        print(f"  Extracting B08: {Path(b08_entry).name}")
        z.extract(b08_entry, TMP_DIR)
        print(f"  Extracting B11: {Path(b11_entry).name}")
        z.extract(b11_entry, TMP_DIR)

    safe_dir = TMP_DIR / safe_name
    b04_path = next(safe_dir.glob("GRANULE/*/IMG_DATA/R10m/*_B04_10m.jp2"))
    b08_path = next(safe_dir.glob("GRANULE/*/IMG_DATA/R10m/*_B08_10m.jp2"))
    b11_path = next(safe_dir.glob("GRANULE/*/IMG_DATA/R20m/*_B11_20m.jp2"))
    return b04_path, b08_path, b11_path


def _bbox_to_utm() -> tuple[float, float, float, float]:
    """Transform Sierra del Rincón bbox from EPSG:4326 to UTM Zone 30N."""
    t = Transformer.from_crs(4326, BAND_CRS_EPSG, always_xy=True)
    xmin, ymin = t.transform(BBOX_4326[0], BBOX_4326[1])
    xmax, ymax = t.transform(BBOX_4326[2], BBOX_4326[3])
    return xmin, ymin, xmax, ymax


def _clip_band(
    band_path: Path,
    clip_geom: dict,
) -> tuple[np.ndarray, object, object]:
    """Open a JP2 band, clip to study area, return (data_uint16[H,W], transform, crs)."""
    with rasterio.open(band_path) as ds:
        out, transform = rio_mask(ds, [clip_geom], crop=True, nodata=0)
        crs = ds.crs
    return out[0], transform, crs


def _resample_to_ref(
    src_arr: np.ndarray,
    src_transform: object,
    src_crs: object,
    ref_transform: object,
    ref_crs: object,
    ref_h: int,
    ref_w: int,
) -> np.ndarray:
    """Bilinear-resample src_arr to the reference grid (ref_h x ref_w).

    rasterio.mask does not support out_shape, so resampling uses warp.reproject.
    """
    dst = np.empty((1, ref_h, ref_w), dtype=np.float32)
    rio_reproject(
        source=src_arr.astype(np.float32)[np.newaxis],
        destination=dst,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=ref_transform,
        dst_crs=ref_crs,
        resampling=Resampling.bilinear,
    )
    return dst[0]


def _compute_index(band_a: np.ndarray, band_b: np.ndarray) -> np.ndarray:
    """Compute normalised difference index (A - B) / (A + B) with zero guard.

    np.where evaluates both branches before masking, so we suppress the
    divide-by-zero RuntimeWarning that would otherwise appear for zero pixels.
    """
    a = band_a.astype(np.float32)
    b = band_b.astype(np.float32)
    denom = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(denom == 0, 0.0, (a - b) / denom)
    return result.astype(np.float32)


def _write_tif(
    out_path: Path,
    data: np.ndarray,
    profile: dict,
) -> None:
    """Write a single-band array to a GeoTIFF."""
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data[np.newaxis])


def main() -> None:
    print(SEP)
    print("  SNTO ETL -- Sentinel-2 Raster Processor")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(f"  Bbox (WGS84): {BBOX_4326}")
    print(f"  Output: {CLEAN_DIR}")
    print(SEP)
    print()

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # -- Step 1: Locate ZIP ------------------------------------------------
    zip_path = _locate_zip()
    print(f"  Source ZIP : {zip_path.name}")
    print()

    # -- Step 2: Extract 3 bands -------------------------------------------
    print("  Selective extraction (B04, B08, B11 only):")
    b04_path, b08_path, b11_path = _extract_bands(zip_path)
    print()
    print(f"  B04 path: ...{b04_path.relative_to(TMP_DIR)}")
    print(f"  B08 path: ...{b08_path.relative_to(TMP_DIR)}")
    print(f"  B11 path: ...{b11_path.relative_to(TMP_DIR)}")
    print()

    try:
        # -- Step 3: Build UTM clip geometry -----------------------------------
        xmin_utm, ymin_utm, xmax_utm, ymax_utm = _bbox_to_utm()
        clip_geom = mapping(box(xmin_utm, ymin_utm, xmax_utm, ymax_utm))
        print(f"  Bbox (UTM {BAND_CRS_EPSG}):")
        print(f"    xmin={xmin_utm:.0f}  ymin={ymin_utm:.0f}")
        print(f"    xmax={xmax_utm:.0f}  ymax={ymax_utm:.0f}")
        print()

        # -- Step 4: Clip B04 (Red, 10m) and B08 (NIR, 10m) -------------------
        print("  Clipping B04 (Red, 10m) ...")
        b04_arr, ref_transform, ref_crs = _clip_band(b04_path, clip_geom)
        ref_h, ref_w = b04_arr.shape

        print("  Clipping B08 (NIR, 10m) ...")
        b08_arr, _, _ = _clip_band(b08_path, clip_geom)

        print(f"  B04/B08 clipped shape: {ref_h} x {ref_w} pixels @ 10m")
        print()

        # -- Step 5: Clip B11 (SWIR, 20m) and resample to 10m -----------------
        print("  Clipping B11 (SWIR, 20m) ...")
        b11_clipped, b11_transform_20m, b11_crs = _clip_band(b11_path, clip_geom)
        print(f"  B11 clipped shape (native 20m): {b11_clipped.shape[0]} x {b11_clipped.shape[1]}")

        # Derive a pixel-perfect 10m transform from the reference B04 bounds
        ref_bounds = array_bounds(ref_h, ref_w, ref_transform)
        ref_transform_10m = from_bounds(*ref_bounds, ref_w, ref_h)

        print("  Resampling B11 to 10m via bilinear interpolation ...")
        b11_arr = _resample_to_ref(
            b11_clipped, b11_transform_20m, b11_crs,
            ref_transform_10m, ref_crs, ref_h, ref_w,
        )
        print(f"  B11 resampled shape: {b11_arr.shape[0]} x {b11_arr.shape[1]}")
        print()

        # -- Step 6: Compute spectral indices ----------------------------------
        print("  Computing NDVI = (B08 - B04) / (B08 + B04) ...")
        ndvi = _compute_index(b08_arr, b04_arr)

        print("  Computing NDMI = (B08 - B11) / (B08 + B11) ...")
        ndmi = _compute_index(b08_arr, b11_arr)
        print()

        # -- Step 7: Write outputs ---------------------------------------------
        band_profile: dict = {
            "driver":    "GTiff",
            "dtype":     "uint16",
            "width":     ref_w,
            "height":    ref_h,
            "count":     1,
            "crs":       ref_crs,
            "transform": ref_transform,
            "compress":  "lzw",
        }
        index_profile: dict = {
            **band_profile,
            "dtype":  "float32",
            "nodata": -9999.0,
        }

        outputs: list[tuple[str, np.ndarray, dict]] = [
            ("clean_S2_B04_red.tif",  b04_arr.astype(np.uint16),                        band_profile),
            ("clean_S2_B08_nir.tif",  b08_arr.astype(np.uint16),                        band_profile),
            # b11_arr is float32 after bilinear resampling; clip before uint16 cast to
            # prevent negative-float wraparound (e.g. -0.001 → 65535 without clip).
            ("clean_S2_B11_swir.tif", np.clip(b11_arr, 0, 65535).astype(np.uint16),     band_profile),
            ("clean_S2_NDVI.tif",     ndvi,                                               index_profile),
            ("clean_S2_NDMI.tif",     ndmi,                                               index_profile),
        ]

        print("  Writing GeoTIFFs:")
        for fname, data, profile in outputs:
            out_path = CLEAN_DIR / fname
            _write_tif(out_path, data, profile)
            size_mb = out_path.stat().st_size / 1_048_576
            print(f"    {fname:<30}  {size_mb:6.1f} MB")
        print()

        # -- Step 9: Summary ---------------------------------------------------
        print(DIV)
        print("  INDEX STATISTICS")
        print(DIV)

        # A pixel is valid when at least one source band has a positive DN value.
        # Using (b04 > 0) | (b08 > 0) is more precise than `ndvi != 0`, which
        # wrongly discards legitimate zero-NDVI pixels (bare soil, water edges).
        valid_mask = (b04_arr > 0) | (b08_arr > 0)
        valid_ndvi = ndvi[valid_mask]
        valid_ndmi = ndmi[valid_mask]

        print(f"  NDVI  min={ndvi.min():.4f}  max={ndvi.max():.4f}"
              f"  mean={valid_ndvi.mean():.4f}  (valid px: {len(valid_ndvi):,})")
        print(f"  NDMI  min={ndmi.min():.4f}  max={ndmi.max():.4f}"
              f"  mean={valid_ndmi.mean():.4f}  (valid px: {len(valid_ndmi):,})")
        print()
        print(f"  Note: NDVI mean ~0.30-0.45 expected for August Mediterranean scrubland.")
        print()
        print(DIV)
        print()
        print(f"  Done. 5 GeoTIFFs written to: {CLEAN_DIR}")
        print()
        print(SEP)

    finally:
        # -- Step 8: Cleanup (always runs, even on error) ----------------------
        if TMP_DIR.exists():
            shutil.rmtree(TMP_DIR)
        print("  Temporary extraction directory removed.")


if __name__ == "__main__":
    main()
