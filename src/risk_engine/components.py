from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config.constants import NDMI_HEALTHY_BASELINE, NDVI_HEALTHY_BASELINE
from src.features.spectral import SpectralFeatures
from src.risk_engine.human_pressure import GeoProximityFactors, compute_geo_human_pressure
from src.time_series.anomaly import AnomalyResult
from src.time_series.trend import TrendResult
from src.time_series.volatility import compute_deseasonalized_volatility


@dataclass(frozen=True)
class RiskComponents:
    ecological_degradation: float   # [0, 1]
    human_pressure_proxy: float     # [0, 1]
    vulnerability_index: float      # [0, 1]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_ecological_degradation(
    features: SpectralFeatures,
    trend: TrendResult,
    ndvi_baseline: float = NDVI_HEALTHY_BASELINE,
) -> float:
    """
    Combines three signals normalised to [0, 1]:
      - NDVI deficit from healthy baseline (40% weight)
      - Negative trend magnitude (40% weight)
      - NDMI deficit from healthy baseline (20% weight)
    """
    # NDVI deficit: how far below baseline (1.0 = completely bare)
    ndvi_deficit = _clamp((ndvi_baseline - features.mean_ndvi) / ndvi_baseline)

    # Negative trend: slope in range [-0.008, 0] mapped to [1, 0].
    # 0.008 NDVI units/month = ~0.10/year, the upper bound of severe degradation
    # in Iberian Mediterranean scrubland (González-De Vega et al. 2018).
    # The previous value (0.05/month = 0.60/year) was physically unreachable.
    max_bad_slope = 0.008
    trend_score = _clamp(-trend.slope / max_bad_slope)

    # NDMI deficit
    ndmi_range = NDMI_HEALTHY_BASELINE + 1.0  # shift so [-1,+baseline] maps to [0,1]
    ndmi_deficit = _clamp((NDMI_HEALTHY_BASELINE - features.mean_ndmi) / ndmi_range)

    return _clamp(0.40 * ndvi_deficit + 0.40 * trend_score + 0.20 * ndmi_deficit)


def compute_human_pressure_proxy(
    features: SpectralFeatures,
    volatility: float,  # reserved for future direct-pass use; not used internally
    asset_metadata: dict[str, Any],
) -> float:
    """
    Human pressure proxy with two routing paths:

    PATH A — Geographic (preferred):
      Used when asset_metadata contains 'geo_proximity' (road distances, POI
      counts, trail network, slope from OSM + DEM).  Returns a physically
      meaningful 0–1 score based on five accessibility and demand factors.
      See src/risk_engine/human_pressure.py for full documentation.

    PATH B — Spectral fallback:
      Used when no geo_proximity data is available.  Applies 2-harmonic
      Fourier deseasonalization to the NDVI series and measures the residual
      standard deviation.  High residuals signal non-seasonal vegetation
      disturbance.  Less reliable than the geo approach; should only be used
      as a temporary fallback until geo context is populated.

      Note: even with 2 harmonics, the spectral fallback is less precise than
      the geo proxy for sites with complex multi-modal phenology (e.g. irrigated
      fields adjacent to natural vegetation).

    Optional modifier:
      If visitor_count_annual is present in metadata, it supplements either
      path as a direct demand signal.
    """
    # PATH A — geo-based proxy
    geo_factors = GeoProximityFactors.from_metadata(asset_metadata)
    if geo_factors is not None:
        pressure = compute_geo_human_pressure(geo_factors)
        # Optional visitor supplement: blend in direct demand data
        visitor_count = asset_metadata.get("visitor_count_annual", 0)
        if visitor_count:
            visitor_score = _clamp(visitor_count / 50_000)
            pressure = _clamp(0.70 * pressure + 0.30 * visitor_score)
        return pressure

    # PATH B — spectral fallback
    deseas_vol = compute_deseasonalized_volatility(features.ndvi_series)
    max_disturbance_std = 0.05
    volatility_score = _clamp(deseas_vol / max_disturbance_std)

    visitor_count = asset_metadata.get("visitor_count_annual", 0)
    if visitor_count:
        visitor_score = _clamp(visitor_count / 50_000)
        return _clamp(0.60 * volatility_score + 0.40 * visitor_score)
    return volatility_score


def compute_vulnerability_index(
    features: SpectralFeatures,
    anomaly: AnomalyResult,
    elevation_m: float | None,
) -> float:
    """
    Combines:
      - Low NDMI (drought / moisture stress exposure)
      - Anomaly magnitude (deviation from historical baseline)
      - Elevation modifier (higher altitude = more exposed, slight uplift)
    """
    # NDMI drought stress: measures how far below the healthy baseline (0.20) the
    # asset sits. The previous formula (-mean_ndmi) only fired for NDMI < 0, leaving
    # Mediterranean semi-arid sites (typical summer NDMI 0.05–0.15) with zero stress
    # contribution. The corrected formula fires as soon as NDMI drops below the
    # healthy baseline, with 1.0 at NDMI = -1.0 (completely dry/bare soil).
    ndmi_stress = _clamp(
        (NDMI_HEALTHY_BASELINE - features.mean_ndmi) / (NDMI_HEALTHY_BASELINE + 1.0)
    )

    # Anomaly contribution: z_score magnitude normalised to threshold of 4
    anomaly_score = _clamp(abs(anomaly.z_score) / 4.0)

    # Elevation modifier: assets above 1500m get up to 0.1 uplift
    elevation_modifier = 0.0
    if elevation_m is not None:
        elevation_modifier = _clamp(elevation_m / 15_000.0)

    return _clamp(0.50 * ndmi_stress + 0.40 * anomaly_score + 0.10 * elevation_modifier)
