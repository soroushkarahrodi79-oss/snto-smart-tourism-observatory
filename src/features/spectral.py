from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.assets.models import AssetObservation


@dataclass(frozen=True)
class SpectralFeatures:
    asset_id: str
    mean_ndvi: float
    mean_ndmi: float
    mean_nbr: Optional[float]
    ndvi_series: list[float]  # ordered by observation month
    ndmi_series: list[float]


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

    return SpectralFeatures(
        asset_id=asset_id,
        mean_ndvi=mean_ndvi,
        mean_ndmi=mean_ndmi,
        mean_nbr=mean_nbr,
        ndvi_series=ndvi_series,
        ndmi_series=ndmi_series,
    )


# ------------------------------------------------------------------
# Index formulas (for use when raw band reflectances are available)
# ------------------------------------------------------------------


def compute_ndvi(nir: float, red: float) -> float:
    """(NIR - RED) / (NIR + RED). Returns 0.0 when denominator is zero."""
    denom = nir + red
    return (nir - red) / denom if denom != 0.0 else 0.0


def compute_ndmi(nir: float, swir: float) -> float:
    """(NIR - SWIR) / (NIR + SWIR). Returns 0.0 when denominator is zero."""
    denom = nir + swir
    return (nir - swir) / denom if denom != 0.0 else 0.0


def compute_nbr(nir: float, swir2: float) -> float:
    """(NIR - SWIR2) / (NIR + SWIR2). Returns 0.0 when denominator is zero."""
    denom = nir + swir2
    return (nir - swir2) / denom if denom != 0.0 else 0.0
