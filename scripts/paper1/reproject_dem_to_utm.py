"""
scripts/paper1/reproject_dem_to_utm.py
=======================================
Reproject a geographic-CRS DEM (e.g. Copernicus GLO-30 from OpenTopography,
which ships in EPSG:4326) to EPSG:25830 (UTM 30N) — the CRS every other
spatial component in this pipeline uses.

Why this matters (not just a convention): ``src/geospatial/geometry.py``'s
``compute_slope_aspect()`` derives aspect from the ratio of east-west to
north-south elevation gradients, assuming both pixel axes are in the same real
distance unit. At PNSG's latitude (~40.8°N) one degree of longitude is only
~84 300 m while one degree of latitude is ~111 100 m — computing aspect
directly on a geographic-CRS DEM skews every angle by roughly that ratio,
silently mis-assigning ``build_ecological_strata.py``'s S1 (north-facing) /
S2 (south-facing) split. Reprojecting to a metric CRS first removes that
anisotropy.

Nodata handling: reprojecting a geographic rectangle into UTM rotates its
footprint, leaving triangular gaps at the corners with no source coverage.
These are written as explicit ``NaN`` — never silently ``0`` — so downstream
``isfinite()`` checks treat them as missing rather than as a spurious
sea-level reading.

Usage:
    python scripts/paper1/reproject_dem_to_utm.py \\
        --src pnsg_dem_wgs84.tif --dst pnsg_dem.tif [--resolution 30] [--dst-crs EPSG:25830]

The reprojected file is not committed to this repository (see
clean_assets/field_validation/reference/README.md — every raster in this
project is git-ignored by policy); this script exists so the transformation
is reproducible from documented, versioned code rather than an ad-hoc shell
session.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def reproject_dem(src_path: Path, dst_path: Path, *, dst_crs: str = "EPSG:25830",
                  resolution: float = 30.0) -> dict:
    import rasterio
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds,
            resolution=resolution)
        kwargs = src.meta.copy()
        kwargs.update({
            "crs": dst_crs, "transform": transform, "width": width,
            "height": height, "compress": "deflate", "nodata": float("nan"),
        })
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(dst_path, "w", **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=transform, dst_crs=dst_crs,
                dst_nodata=float("nan"),
                resampling=Resampling.bilinear,
            )
    return {"width": width, "height": height, "crs": dst_crs, "resolution": resolution}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, required=True, help="Source DEM (any CRS rasterio reads).")
    p.add_argument("--dst", type=Path, required=True, help="Output path for the reprojected DEM.")
    p.add_argument("--dst-crs", default="EPSG:25830")
    p.add_argument("--resolution", type=float, default=30.0)
    args = p.parse_args()

    info = reproject_dem(args.src, args.dst, dst_crs=args.dst_crs, resolution=args.resolution)
    print(f"Reprojected {args.src} -> {args.dst} "
          f"({info['width']}x{info['height']} px, {info['resolution']} m, {info['crs']})")


if __name__ == "__main__":
    main()
