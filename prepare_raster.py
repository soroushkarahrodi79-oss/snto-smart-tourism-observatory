"""
SNTO -- Sentinel-2 Raster Preparation (Production)
===================================================
Pilot Territory: Sierra del Rincón Biosphere Reserve, Madrid, Spain

Reads Band 4 (Red, 10 m), Band 8 (NIR, 10 m) and Band 11 (SWIR, 20 m) from a
Sentinel-2 L2A .SAFE directory, reprojects all three to EPSG:25830, resamples
B11 to the 10 m reference grid, computes NDVI and NDMI, and writes a 2-band
GeoTIFF (Band 1: NDVI, Band 2: NDMI) to data/clean_assets/.

Usage
-----
    python prepare_raster.py --input /path/to/scene.SAFE --output spring_raster.tif
    python prepare_raster.py --input /path/to/scene.SAFE --output summer_raster.tif

Dependencies
------------
    pip install rasterio numpy
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform
from rasterio.warp import reproject as warp_reproject

# ── Project constants ─────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLEAN_DIR   = os.path.join(_SCRIPT_DIR, "data", "clean_assets")
TARGET_CRS  = CRS.from_epsg(25830)
EPSILON     = 1e-8
NODATA      = np.float32(-9999.0)

SEP = "=" * 72
DIV = "-" * 72


# ── Path resolution ───────────────────────────────────────────────────────────

def _find_img_data(safe_dir: str) -> str:
    """
    Locate the IMG_DATA directory inside a .SAFE bundle.

    Sentinel-2 .SAFE bundles nest IMG_DATA under a GRANULE sub-folder whose
    name varies by product version, e.g.:
        <SAFE>/GRANULE/L2A_T30TVL_A012345_20250810T110701/IMG_DATA/

    Uses glob so the script works regardless of the exact granule name.
    Raises FileNotFoundError with a diagnostic if the directory is absent.
    """
    pattern = os.path.join(safe_dir, "GRANULE", "*", "IMG_DATA")
    matches = glob.glob(pattern)
    if not matches:
        # Fall back: search anywhere inside the SAFE for IMG_DATA
        pattern_deep = os.path.join(safe_dir, "**", "IMG_DATA")
        matches = glob.glob(pattern_deep, recursive=True)
    if not matches:
        raise FileNotFoundError(
            f"IMG_DATA directory not found inside: {safe_dir}\n"
            f"Expected structure: <SAFE>/GRANULE/<granule_name>/IMG_DATA/"
        )
    if len(matches) > 1:
        print(f"  [WARN] Multiple IMG_DATA directories found — using: {matches[0]}")
    return matches[0]


def _find_band(img_data_dir: str, suffix: str) -> str:
    """
    Find a JP2 band file whose name ends with `suffix` anywhere under img_data_dir.

    Sentinel-2 L2A places 10 m bands under IMG_DATA/R10m/ and 20 m under R20m/.
    The search is recursive so resolution sub-folders are handled automatically.

    Raises FileNotFoundError with a full listing of available .jp2 files if the
    band cannot be found.
    """
    pattern = os.path.join(img_data_dir, "**", f"*{suffix}")
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        available = glob.glob(
            os.path.join(img_data_dir, "**", "*.jp2"), recursive=True
        )
        listing = "\n".join(f"  {os.path.basename(p)}" for p in sorted(available))
        raise FileNotFoundError(
            f"Band file matching '*{suffix}' not found under: {img_data_dir}\n"
            f"Available .jp2 files ({len(available)} total):\n{listing}"
        )
    if len(matches) > 1:
        print(f"  [WARN] Multiple matches for *{suffix} — using: {matches[0]}")
    return matches[0]


# ── Reprojection ──────────────────────────────────────────────────────────────

def _reproject_to_epsg25830(
    data: np.ndarray,
    src_profile: dict,
    resampling: Resampling = Resampling.bilinear,
) -> tuple[np.ndarray, dict]:
    """
    Reproject a single-band float32 array to TARGET_CRS (EPSG:25830).

    Returns (reprojected_array, updated_profile).
    No-op (returns originals unchanged) when the source is already EPSG:25830.
    """
    if src_profile["crs"] == TARGET_CRS:
        return data, src_profile

    h, w = data.shape
    src_transform = src_profile["transform"]

    dst_transform, dst_w, dst_h = calculate_default_transform(
        src_profile["crs"],
        TARGET_CRS,
        w,
        h,
        *rasterio.transform.array_bounds(h, w, src_transform),
    )

    dst_data = np.full((dst_h, dst_w), NODATA, dtype=np.float32)
    warp_reproject(
        source=data,
        destination=dst_data,
        src_transform=src_transform,
        src_crs=src_profile["crs"],
        src_nodata=float(NODATA),
        dst_transform=dst_transform,
        dst_crs=TARGET_CRS,
        dst_nodata=float(NODATA),
        resampling=resampling,
    )

    updated_profile = src_profile.copy()
    updated_profile.update(
        crs=TARGET_CRS,
        transform=dst_transform,
        width=dst_w,
        height=dst_h,
        nodata=float(NODATA),
    )
    return dst_data, updated_profile


def _align_to_reference(
    data: np.ndarray,
    src_profile: dict,
    ref_profile: dict,
) -> np.ndarray:
    """
    Resample `data` so its grid (shape, transform, CRS) matches ref_profile.

    Called when B08 and B04 end up on slightly different grids after
    independent reprojections (can happen when source transforms differ).
    """
    dst = np.full(
        (ref_profile["height"], ref_profile["width"]),
        NODATA,
        dtype=np.float32,
    )
    warp_reproject(
        source=data,
        destination=dst,
        src_transform=src_profile["transform"],
        src_crs=src_profile["crs"],
        src_nodata=float(NODATA),
        dst_transform=ref_profile["transform"],
        dst_crs=ref_profile["crs"],
        dst_nodata=float(NODATA),
        resampling=Resampling.bilinear,
    )
    return dst


def _grids_match(profile_a: dict, profile_b: dict) -> bool:
    """Return True when two profiles share the same shape, transform, and CRS."""
    return (
        profile_a["width"]     == profile_b["width"]
        and profile_a["height"]    == profile_b["height"]
        and profile_a["transform"] == profile_b["transform"]
        and profile_a["crs"]       == profile_b["crs"]
    )


# ── Band I/O ──────────────────────────────────────────────────────────────────

def _read_band(path: str) -> tuple[np.ndarray, dict]:
    """
    Open a single-band raster file and return (float32 array, profile dict).

    The profile is normalised: driver is set to GTiff, count to 1, dtype to
    float32, and nodata to NODATA so downstream code can rely on these values.
    """
    with rasterio.open(path) as src:
        data    = src.read(1).astype(np.float32)
        profile = src.profile.copy()

    profile.update(
        driver="GTiff",
        count=1,
        dtype="float32",
        nodata=float(NODATA),
    )
    return data, profile


# ── Index maths ───────────────────────────────────────────────────────────────

def _compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """
    NDVI = (NIR - Red) / (NIR + Red + epsilon).

    epsilon avoids division by zero in dark / no-signal areas.
    Pixels where either input is NODATA are preserved as NODATA.
    """
    nodata_mask = (nir == NODATA) | (red == NODATA)
    with np.errstate(invalid="ignore"):
        ndvi = (nir - red) / (nir + red + EPSILON)
    ndvi[nodata_mask] = NODATA
    return ndvi.astype(np.float32)


def _compute_ndmi(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """
    NDMI = (NIR - SWIR) / (NIR + SWIR + epsilon).

    Normalised Difference Moisture Index using B08 (NIR, 10 m) and B11 (SWIR,
    20 m resampled to 10 m). epsilon avoids division by zero; pixels where
    either input is NODATA are preserved as NODATA.
    """
    nodata_mask = (nir == NODATA) | (swir == NODATA)
    with np.errstate(invalid="ignore"):
        ndmi = (nir - swir) / (nir + swir + EPSILON)
    ndmi[nodata_mask] = NODATA
    return ndmi.astype(np.float32)


# ── Argument parsing ──────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare a Sentinel-2 L2A .SAFE scene → 2-band NDVI/NDMI GeoTIFF "
            "in EPSG:25830 for the SNTO EHS pipeline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python prepare_raster.py "
            "--input scene.SAFE --output spring_raster.tif\n"
            "  python prepare_raster.py "
            "--input scene.SAFE --output summer_raster.tif\n"
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="SAFE_DIR",
        help="Path to the Sentinel-2 L2A .SAFE directory (e.g. S2A_MSIL2A_*.SAFE).",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="FILENAME",
        help=(
            "Output filename, e.g. spring_raster.tif. "
            "Written to data/clean_assets/<FILENAME>."
        ),
    )
    return parser.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    safe_dir    = os.path.abspath(args.input)
    output_name = args.output
    if not output_name.lower().endswith(".tif"):
        output_name += ".tif"

    print(SEP)
    print("  SNTO -- Sentinel-2 Raster Preparation")
    print("  Pilot: Sierra del Rincón Biosphere Reserve, Madrid, Spain")
    print(SEP)
    print()
    print(f"  Input  : {safe_dir}")
    print(f"  Output : data/clean_assets/{output_name}")
    print()

    # ── [1/6] Validate .SAFE directory ───────────────────────────────────────
    print("  [1/6] Validating .SAFE input directory ...")
    if not os.path.isdir(safe_dir):
        print(f"  ERROR: Input path does not exist or is not a directory:\n"
              f"         {safe_dir}")
        sys.exit(1)
    if not safe_dir.endswith(".SAFE"):
        print("  [WARN] Input directory does not end with '.SAFE'. "
              "Proceeding anyway.")
    print(f"    OK: {os.path.basename(safe_dir)}")
    print()

    # ── [2/6] Locate IMG_DATA and band files ─────────────────────────────────
    print("  [2/6] Locating IMG_DATA and band files ...")
    try:
        img_data_dir = _find_img_data(safe_dir)
        print(f"    IMG_DATA  : {img_data_dir}")

        b04_path = _find_band(img_data_dir, "_B04_10m.jp2")
        print(f"    B04 (Red) : {os.path.basename(b04_path)}")

        b08_path = _find_band(img_data_dir, "_B08_10m.jp2")
        print(f"    B08 (NIR) : {os.path.basename(b08_path)}")

        b11_path = _find_band(img_data_dir, "_B11_20m.jp2")
        print(f"    B11 (SWIR): {os.path.basename(b11_path)}")

    except FileNotFoundError as exc:
        print(f"\n  ERROR: Band discovery failed.\n  {exc}")
        sys.exit(1)
    print()

    # ── [3/6] Read bands ─────────────────────────────────────────────────────
    print("  [3/6] Reading bands ...")
    try:
        b04_data, b04_profile = _read_band(b04_path)
        print(f"    B04 shape : {b04_data.shape}  "
              f"CRS: {b04_profile['crs']}  "
              f"dtype: {b04_data.dtype}")

        b08_data, b08_profile = _read_band(b08_path)
        print(f"    B08 shape : {b08_data.shape}  "
              f"CRS: {b08_profile['crs']}  "
              f"dtype: {b08_data.dtype}")

        b11_data, b11_profile = _read_band(b11_path)
        print(f"    B11 shape : {b11_data.shape}  "
              f"CRS: {b11_profile['crs']}  "
              f"dtype: {b11_data.dtype}  (native 20 m)")

    except rasterio.errors.RasterioIOError as exc:
        print(f"\n  ERROR: Failed to read band file.\n  {exc}")
        sys.exit(1)
    print()

    # ── [4/6] Reproject to EPSG:25830 ────────────────────────────────────────
    print("  [4/6] Projecting to EPSG:25830 ...")
    try:
        if b04_profile["crs"] == TARGET_CRS:
            print(f"    B04: already in EPSG:25830 — no reprojection needed.")
        else:
            print(f"    B04: {b04_profile['crs']} → EPSG:25830 ...")
        b04_data, b04_profile = _reproject_to_epsg25830(b04_data, b04_profile)
        print(f"    B04 final shape : {b04_data.shape}")

        if b08_profile["crs"] == TARGET_CRS:
            print(f"    B08: already in EPSG:25830 — no reprojection needed.")
        else:
            print(f"    B08: {b08_profile['crs']} → EPSG:25830 ...")
        b08_data, b08_profile = _reproject_to_epsg25830(b08_data, b08_profile)
        print(f"    B08 final shape : {b08_data.shape}")

        if b11_profile["crs"] == TARGET_CRS:
            print(f"    B11: already in EPSG:25830 — no reprojection needed.")
        else:
            print(f"    B11: {b11_profile['crs']} → EPSG:25830 ...")
        b11_data, b11_profile = _reproject_to_epsg25830(b11_data, b11_profile)
        print(f"    B11 final shape : {b11_data.shape}  (still 20 m grid)")

    except Exception as exc:
        print(f"\n  ERROR: Reprojection to EPSG:25830 failed.\n  {exc}")
        sys.exit(1)

    # Align NIR to the Red grid if they differ (e.g. due to floating-point
    # rounding in independent transform calculations).
    if not _grids_match(b08_profile, b04_profile):
        print()
        print(f"    Grid mismatch detected — aligning B08 to B04 reference grid ...")
        try:
            b08_data = _align_to_reference(b08_data, b08_profile, b04_profile)
            print(f"    B08 aligned : {b08_data.shape}")
        except Exception as exc:
            print(f"\n  ERROR: Grid alignment of B08 to B04 failed.\n  {exc}")
            sys.exit(1)
    else:
        print("    Grid check  : B04 and B08 grids match — no alignment needed.")

    # B11 is natively 20 m: resample to the 10 m B04 reference grid so NDMI
    # aligns pixel-for-pixel with NDVI. Bilinear resampling (20 m → 10 m).
    print()
    print(f"    Resampling B11 (20 m) → B04 reference grid (10 m) ...")
    try:
        b11_data = _align_to_reference(b11_data, b11_profile, b04_profile)
        print(f"    B11 resampled : {b11_data.shape}")
    except Exception as exc:
        print(f"\n  ERROR: Resampling of B11 to B04 grid failed.\n  {exc}")
        sys.exit(1)
    print()

    # ── [5/6] Compute NDVI and NDMI ──────────────────────────────────────────
    print("  [5/6] Computing spectral indices ...")
    ndvi = _compute_ndvi(b08_data, b04_data)
    ndmi = _compute_ndmi(b08_data, b11_data)
    del b04_data, b08_data, b11_data  # free memory before writing

    valid_ndvi = ndvi[ndvi != NODATA]
    print(f"    NDVI  — valid pixels : {len(valid_ndvi):>12,}")
    if len(valid_ndvi):
        print(f"            range        : [{valid_ndvi.min():.4f},  "
              f"{valid_ndvi.max():.4f}]")
        print(f"            mean         :  {valid_ndvi.mean():.4f}")

    valid_ndmi = ndmi[ndmi != NODATA]
    print(f"    NDMI  — valid pixels : {len(valid_ndmi):>12,}")
    if len(valid_ndmi):
        print(f"            range        : [{valid_ndmi.min():.4f},  "
              f"{valid_ndmi.max():.4f}]")
        print(f"            mean         :  {valid_ndmi.mean():.4f}")
    print()

    # ── [6/6] Write 2-band GeoTIFF ───────────────────────────────────────────
    os.makedirs(CLEAN_DIR, exist_ok=True)
    out_path = os.path.join(CLEAN_DIR, output_name)

    print(f"  [6/6] Writing 2-band GeoTIFF → {out_path} ...")
    try:
        out_profile = b04_profile.copy()
        out_profile.update(
            driver="GTiff",
            count=2,
            dtype="float32",
            nodata=float(NODATA),
            compress="lzw",
            tiled=True,
            blockxsize=512,
            blockysize=512,
        )

        with rasterio.open(out_path, "w", **out_profile) as dst:
            dst.write(ndvi,  1)
            dst.write(ndmi,  2)
            dst.update_tags(
                BAND_1="NDVI = (B08 - B04) / (B08 + B04 + 1e-8)",
                BAND_2="NDMI = (B08 - B11) / (B08 + B11 + 1e-8)  [B11 resampled 20m->10m]",
                SOURCE=os.path.basename(safe_dir),
                CRS="EPSG:25830",
                NODATA=str(NODATA),
            )

    except rasterio.errors.RasterioIOError as exc:
        print(f"\n  ERROR: Failed to write output GeoTIFF.\n  {exc}")
        sys.exit(1)

    size_mb = os.path.getsize(out_path) / (1024 ** 2)
    print(f"    File size  : {size_mb:.2f} MB")
    print(f"    Dimensions : {ndvi.shape[1]} cols × {ndvi.shape[0]} rows × 2 bands")
    print(f"    CRS        : EPSG:25830")
    print(f"    Nodata     : {NODATA}")
    print()

    print(SEP)
    print(f"  Done. Output ready for EHS pipeline:")
    print(f"  {out_path}")
    print(SEP)
    print()


if __name__ == "__main__":
    main()
