"""
Spatial Causality Module (SCM).

Classifies NDVI change as human-localized vs landscape/climate-driven from a
multi-scale (core/near/landscape) spatial gradient. v2.2 adds a real-zone path
(:mod:`src.spatial_causality.zone_loader`) so attribution can be backed by
observed Sentinel-2 zones (``EvidenceClass.REAL``) instead of the α-decay
simulation (``EvidenceClass.SIMULATED``); :func:`analyse_asset` prefers the real
zones when the GEE export exists and falls back to the labelled simulation
otherwise.
"""
from __future__ import annotations

from src.assets.models import AssetObservation
from src.spatial_causality.analyzer import (
    SpatialCausalityAnalyzer,
    SpatialCausalityResult,
    evidence_class_for_source,
)
from src.spatial_causality.zone_loader import load_real_zones, real_zones_exist

__all__ = [
    "AssetObservation",
    "SpatialCausalityAnalyzer",
    "SpatialCausalityResult",
    "analyse_asset",
    "evidence_class_for_source",
    "load_real_zones",
    "real_zones_exist",
]


def analyse_asset(
    asset_id: str,
    observations: list[AssetObservation],
    *,
    human_pressure: float = 0.0,
) -> SpatialCausalityResult:
    """Run the SCM for one asset, preferring observed multi-scale zones.

    If a real GEE zone export exists for ``asset_id`` the analysis runs on the
    observed core/near/landscape series (result classed ``REAL``); otherwise it
    falls back to ``simulate_zones`` from the single-buffer ``observations``
    using ``human_pressure`` (result classed ``SIMULATED``). Real and simulated
    are never blurred — the result's ``evidence_class`` states which was used.
    """
    analyzer = SpatialCausalityAnalyzer(human_pressure=human_pressure)
    real = load_real_zones(asset_id)
    zones = real if real is not None else analyzer.simulate_zones(observations)
    return analyzer.analyse(asset_id, zones)
