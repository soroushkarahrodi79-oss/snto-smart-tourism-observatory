from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from src.assets.models import AssetObservation


@dataclass(frozen=True)
class SpectralFeatures:
    asset_id: str
    mean_ndvi: float
    mean_ndmi: float
    mean_nbr: Optional[float]
    ndvi_series: list[float]   # ordered by observation month
    ndmi_series: list[float]
    mean_evi: Optional[float] = None          # None when no EVI observations present
    evi_series: list[float] = field(default_factory=list)


def extract_spectral_features(observations: list[AssetObservation]) -> SpectralFeatures:
    """Aggregate monthly observations into per-asset spectral statistics."""
    if not observations:
        raise ValueError("Cannot extract features from an empty observation list.")

    asset_id = observations[0].asset_id
    ndvi_series = [o.ndvi for o in observations]
    ndmi_series = [o.ndmi for o in observations]

    mean_ndvi = sum(ndvi_series) / len(ndvi_series)
    mean_ndmi = sum(ndmi_series) / len(ndmi_series)

    nbr_values = [o.nbr for o in observations if o.nbr is not None]
    mean_nbr = sum(nbr_values) / len(nbr_values) if nbr_values else None

    evi_values = [o.evi for o in observations if o.evi is not None]
    if evi_values:
        mean_evi: Optional[float] = sum(evi_values) / len(evi_values)
        evi_series = [o.evi if o.evi is not None else float("nan") for o in observations]
    else:
        mean_evi = None
        evi_series = []

    return SpectralFeatures(
        asset_id=asset_id,
        mean_ndvi=mean_ndvi,
        mean_ndmi=mean_ndmi,
        mean_nbr=mean_nbr,
        ndvi_series=ndvi_series,
        ndmi_series=ndmi_series,
        mean_evi=mean_evi,
        evi_series=evi_series,
    )


# ── Index formulas (for use when raw band reflectances are available) ─────────


def compute_ndvi(nir: float, red: float) -> float:
    """(NIR – RED) / (NIR + RED). Returns 0.0 when denominator is zero."""
    denom = nir + red
    return (nir - red) / denom if denom != 0.0 else 0.0


def compute_ndmi(nir: float, swir: float) -> float:
    """(NIR – SWIR) / (NIR + SWIR). Returns 0.0 when denominator is zero."""
    denom = nir + swir
    return (nir - swir) / denom if denom != 0.0 else 0.0


def compute_nbr(nir: float, swir2: float) -> float:
    """(NIR – SWIR2) / (NIR + SWIR2). Returns 0.0 when denominator is zero."""
    denom = nir + swir2
    return (nir - swir2) / denom if denom != 0.0 else 0.0


def compute_evi(
    nir: float,
    red: float,
    blue: float,
    G: float = 2.5,
    C1: float = 6.0,
    C2: float = 7.5,
    L: float = 1.0,
) -> float:
    """Enhanced Vegetation Index (Liu & Huete 1995).

    EVI = G × (NIR – RED) / (NIR + C1 × RED – C2 × BLUE + L)

    Unlike NDVI, EVI uses the blue band to correct for atmospheric aerosol
    scattering and includes a canopy background adjustment (L).  It does not
    saturate in dense forests (NDVI > ~0.80), making it superior for detecting
    sub-canopy stress in closed-canopy ecosystems such as Hayedos.

    All inputs are surface reflectances in [0, 1].  Returns 0.0 when the
    denominator is zero or negative (pathological geometry).

    Args:
        nir:  NIR reflectance (Sentinel-2 B08, 10 m).
        red:  Red reflectance  (Sentinel-2 B04, 10 m).
        blue: Blue reflectance (Sentinel-2 B02, 10 m).
        G:    Gain factor — 2.5 per MODIS standard.
        C1:   Aerosol resistance coefficient for red band — 6.0.
        C2:   Aerosol resistance coefficient for blue band — 7.5.
        L:    Canopy background adjustment — 1.0.

    Returns:
        EVI value; typically in [-1, 1] for natural surfaces but theoretically
        unbounded; real vegetation EVI is approximately in [0, 0.7].
    """
    denom = nir + C1 * red - C2 * blue + L
    return G * (nir - red) / denom if denom != 0.0 else 0.0


def compute_msavi2(nir: float, red: float) -> float:
    """Modified Soil-Adjusted Vegetation Index 2 (Qi et al. 1994).

    MSAVI2 = (2×NIR + 1 – √((2×NIR + 1)² – 8×(NIR – RED))) / 2

    MSAVI2 does not require the blue band, making it a robust fallback when
    blue-band quality is compromised (e.g. haze, adjacency effects).  Like EVI,
    it avoids NDVI saturation in dense canopies through its self-adjusting
    soil-line correction.

    Args:
        nir: NIR reflectance (Sentinel-2 B08, 10 m).
        red: Red reflectance  (Sentinel-2 B04, 10 m).

    Returns:
        MSAVI2 value in approximately [-1, 1]; healthy dense vegetation ~0.4–0.7.
        Returns 0.0 when the discriminant is negative (non-physical reflectance).
    """
    discriminant = (2.0 * nir + 1.0) ** 2 - 8.0 * (nir - red)
    if discriminant < 0.0:
        return 0.0
    return (2.0 * nir + 1.0 - math.sqrt(discriminant)) / 2.0
