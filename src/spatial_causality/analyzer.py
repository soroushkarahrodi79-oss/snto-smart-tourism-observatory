from __future__ import annotations

"""
Spatial Causality Module (SCM)
==============================
Determines whether observed environmental change is:

  (A) LOCALIZED_IMPACT   -- human pressure / tourism-related
  (B) LANDSCAPE_DRIVEN   -- climate / regional environmental forcing
  (C) MIXED              -- ambiguous, both drivers present

SCIENTIFIC BASIS
================
The key diagnostic principle is spatial autocorrelation structure.
Climate forcing (drought, temperature anomaly) acts uniformly across the
landscape: all zones (core trail, near surroundings, landscape background)
show similar NDVI signals at the same time.

Localized human impact (trampling, vegetation removal, compaction) produces
a spatial gradient: the immediately disturbed zone (core) is significantly
more degraded than the surrounding undisturbed landscape.

This method is adapted from:
  Marion, J.L. & Leung, Y.F. (2001). Trail resource impacts and assessment.
    Journal of Park and Recreation Administration, 19(3), 17-37.
  Pickering, C.M. et al. (2011). Comparing hiking, mountain biking and
    horse riding impacts on vegetation and soils.
    Journal of Environmental Management, 92, 121-129.
  Sims, N.K. et al. (2014). Multi-scale analysis of vegetation change.
    Remote Sensing, 6, 12271-12294.

SPATIAL ZONES
=============
  Core zone      (0 to CORE_R m):       direct asset footprint
  Near zone      (CORE_R to NEAR_R m):  immediate surroundings
  Landscape zone (NEAR_R to LAND_R m):  regional background

For a LineString trail: each buffer ring is computed around the trail axis.

SPATIAL IMPACT GRADIENT (SIG)
==============================
  SIG = (NDVI_landscape - NDVI_core) / max(NDVI_landscape, 0.01)

  SIG > 0.15 : core significantly worse than landscape (strong localized impact)
  SIG < 0.07 : all zones similar (climate / landscape forcing dominates)
  0.07-0.15  : mixed signal

CROSS-ZONE CORRELATION
======================
Pearson correlation between the core and landscape NDVI time series.

  r > 0.85 : both zones driven by the same temporal forcing (climate)
  r < 0.70 : zones respond differently (localized disturbance in core)

ZONE SIGNAL SIMULATION (when live multi-scale GEE data is unavailable)
=======================================================================
Zone-differentiated NDVI signals are derived from the existing single-zone
observations by applying spatial decay factors calibrated from the human
pressure proxy (HP):

  NDVI_core      = NDVI_landscape x (1 - HP x alpha_core)
  NDVI_near      = NDVI_landscape x (1 - HP x alpha_near)
  NDVI_landscape = NDVI_observed x (1 + gamma)

Where:
  alpha_core = 0.12   (12% maximum NDVI reduction per HP unit in core)
  alpha_near = 0.05   (5% maximum reduction in near zone)
  gamma      = 0.025  (2.5% uplift: landscape is slightly denser than trail buffer)

These coefficients are calibrated from:
  Pickering et al. (2011): 5-20% NDVI reduction in high-pressure corridors.
  Šmída, J. et al. (2018): 3-8% reduction for low-pressure rural trails.
  For HP = 1.0 (maximum): core reduction = 12% (consistent with upper bound).
  For HP = 0.31 (Masatrigo): core reduction ≈ 3.7% (consistent with low-pressure sites).
"""


import math
import statistics
from dataclasses import dataclass

import numpy as np

from src.assets.models import AssetObservation
from src.platform.evidence import EvidenceClass
from src.time_series.mann_kendall import mann_kendall_test
from src.time_series.volatility import compute_deseasonalized_volatility


def evidence_class_for_source(data_source: str) -> EvidenceClass:
    """Evidence tier of an SCM result from its zone data source.

    Observed multi-scale zones (real GEE export) → REAL; the α-decay
    ``simulate_zones`` fallback → SIMULATED. The distinction is the whole point
    of the v2.2 upgrade: attribution backed by observed zones must be
    distinguishable from attribution backed by a simulation.
    """
    s = (data_source or "").lower()
    if "simulat" in s:
        return EvidenceClass.SIMULATED
    if any(tag in s for tag in ("gee", "sentinel", "s2", "stac", "scm_real")):
        return EvidenceClass.REAL
    return EvidenceClass.SIMULATED

# ── Zone radius definitions (metres) ─────────────────────────────────────

CORE_OUTER_M: int = 50
NEAR_OUTER_M: int = 200
LANDSCAPE_OUTER_M: int = 1_000

# ── Simulation parameters ─────────────────────────────────────────────────

_ALPHA_CORE: float = 0.12    # max NDVI reduction per HP unit in core zone
_ALPHA_NEAR: float = 0.05    # max NDVI reduction per HP unit in near zone
_LANDSCAPE_UPLIFT: float = 0.025  # landscape is ~2.5% denser than trail buffer

# ── Classification thresholds ─────────────────────────────────────────────

_SIG_LOCALIZED: float = 0.15    # SIG above this → localized impact signal
_SIG_LANDSCAPE: float = 0.07    # SIG below this → landscape signal
_CORR_LANDSCAPE: float = 0.85   # cross-zone r above this → landscape forcing
_CORR_LOCALIZED: float = 0.70   # cross-zone r below this → localized disturbance


# ── Dataclasses ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ZoneSignal:
    """Environmental statistics for one spatial zone."""

    zone: str                  # "core" | "near" | "landscape"
    inner_radius_m: int
    outer_radius_m: int
    mean_ndvi: float
    mean_ndmi: float
    ndvi_sens_slope: float     # Sen's slope (NDVI/month)
    ndvi_volatility: float     # deseasonalized residual std
    ndmi_sens_slope: float
    anomaly_frequency: float   # fraction of months with |z| > 1.5


@dataclass(frozen=True)
class SpatialGradient:
    """Differential metrics across spatial zones."""

    core_near_delta: float      # core NDVI - near NDVI (negative = core worse)
    near_landscape_delta: float
    core_landscape_delta: float
    spatial_impact_gradient: float   # SIG
    cross_zone_correlation: float    # Pearson r (core series vs landscape series)


@dataclass(frozen=True)
class SpatialCausalityResult:
    """Full output of a Spatial Causality Module analysis."""

    asset_id: str
    classification: str        # LOCALIZED_IMPACT | LANDSCAPE_DRIVEN | MIXED
    confidence: str            # HIGH | MODERATE | LOW

    zones: dict[str, ZoneSignal]
    gradient: SpatialGradient

    # Human-readable outputs
    technical_rationale: str
    plain_language: str
    management_implication: str

    # Metadata
    n_observations: int
    data_source: str
    # Provenance tier: REAL when zones are observed (multi-scale GEE), SIMULATED
    # when derived by the α-decay fallback. Defaulted for back-compat with any
    # caller that builds the result directly.
    evidence_class: EvidenceClass = EvidenceClass.SIMULATED


# ── Main analyser ─────────────────────────────────────────────────────────

class SpatialCausalityAnalyzer:
    """
    Analyses multi-scale spatial structure of NDVI/NDMI signals to infer
    whether observed change is localized (human) or landscape-scale (climate).

    Usage
    -----
    Either provide pre-computed zone observations (when real multi-scale GEE
    data is available) or call simulate_zones() to derive zone signals from
    a single-scale observation series using the human pressure proxy.

    Parameters
    ----------
    human_pressure : float
        Geo-based human pressure proxy [0, 1] from compute_geo_human_pressure().
        Used only when simulating zone signals; ignored when zone observations
        are provided directly.
    """

    def __init__(self, human_pressure: float = 0.0) -> None:
        if not 0.0 <= human_pressure <= 1.0:
            raise ValueError("human_pressure must be in [0, 1].")
        self.human_pressure = human_pressure

    # ------------------------------------------------------------------
    # Zone signal simulation
    # ------------------------------------------------------------------

    def simulate_zones(
        self,
        observations: list[AssetObservation],
    ) -> dict[str, list[AssetObservation]]:
        """
        Derive zone-differentiated observation lists from a single-scale record.

        Applies spatial decay functions calibrated from trampling literature to
        produce plausible core, near, and landscape signals.  The resulting series
        preserve the temporal structure (seasonal cycle, drought events) of the
        original while reflecting the expected spatial gradient driven by HP.

        Returns
        -------
        Dict mapping zone name to a list of zone-specific AssetObservation objects.
        Each observation has modified ndvi / ndmi values representing that zone.
        """
        hp = self.human_pressure
        zones: dict[str, list[AssetObservation]] = {
            "core": [], "near": [], "landscape": []
        }

        for obs in observations:
            # Landscape: slightly above the 30m-buffer mean (undisturbed background)
            ndvi_land = min(0.95, obs.ndvi * (1.0 + _LANDSCAPE_UPLIFT))
            ndmi_land = min(0.60, obs.ndmi * (1.0 + _LANDSCAPE_UPLIFT * 0.8))

            # Core: reduced by human pressure
            ndvi_core = max(0.05, ndvi_land * (1.0 - hp * _ALPHA_CORE))
            ndmi_core = max(-0.20, ndmi_land * (1.0 - hp * _ALPHA_CORE * 0.8))

            # Near: partially reduced
            ndvi_near = max(0.05, ndvi_land * (1.0 - hp * _ALPHA_NEAR))
            ndmi_near = max(-0.20, ndmi_land * (1.0 - hp * _ALPHA_NEAR * 0.8))

            for zone, ndvi, ndmi in [
                ("core", ndvi_core, ndmi_core),
                ("near", ndvi_near, ndmi_near),
                ("landscape", ndvi_land, ndmi_land),
            ]:
                zones[zone].append(
                    AssetObservation(
                        asset_id=obs.asset_id,
                        year=obs.year,
                        month=obs.month,
                        ndvi=round(ndvi, 5),
                        ndmi=round(ndmi, 5),
                        cloud_cover_pct=obs.cloud_cover_pct,
                        data_source=f"scm_simulated:{zone}",
                    )
                )

        return zones

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyse(
        self,
        asset_id: str,
        zone_observations: dict[str, list[AssetObservation]],
    ) -> SpatialCausalityResult:
        """
        Run the full Spatial Causality analysis.

        Parameters
        ----------
        asset_id : str
        zone_observations : dict mapping "core" | "near" | "landscape" to observation lists.
        """
        required = {"core", "near", "landscape"}
        if not required.issubset(zone_observations):
            raise ValueError(f"zone_observations must contain keys: {required}")

        # Compute zone-level signals
        zone_signals: dict[str, ZoneSignal] = {}
        zone_ndvi_series: dict[str, list[float]] = {}
        for zone_name, obs_list in zone_observations.items():
            zs, ndvi_series = self._compute_zone_signal(zone_name, obs_list)
            zone_signals[zone_name] = zs
            zone_ndvi_series[zone_name] = ndvi_series

        # Spatial gradient
        gradient = self._compute_gradient(zone_signals, zone_ndvi_series)

        # Classification
        classification, confidence = self._classify(gradient)

        # Explanation generation
        rationale = self._build_rationale(classification, gradient, zone_signals)
        plain = self._build_plain_language(classification, zone_signals, gradient, asset_id)
        mgmt = self._build_management(classification, confidence)

        n_obs = len(zone_observations["core"])
        source = (
            zone_observations["core"][0].data_source if n_obs > 0 else "unknown"
        )

        return SpatialCausalityResult(
            asset_id=asset_id,
            classification=classification,
            confidence=confidence,
            zones=zone_signals,
            gradient=gradient,
            technical_rationale=rationale,
            plain_language=plain,
            management_implication=mgmt,
            n_observations=n_obs,
            data_source=source,
            evidence_class=evidence_class_for_source(source),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_zone_signal(
        self,
        zone_name: str,
        obs: list[AssetObservation],
    ) -> tuple[ZoneSignal, list[float]]:
        """Compute descriptive statistics for one zone from its observations."""
        if not obs:
            raise ValueError(f"Empty observations for zone '{zone_name}'.")

        ndvi_series = [o.ndvi for o in obs]
        ndmi_series = [o.ndmi for o in obs]

        mean_ndvi = statistics.mean(ndvi_series)
        mean_ndmi = statistics.mean(ndmi_series)

        # Trend via Mann-Kendall Sen slope
        ndvi_mk = mann_kendall_test(ndvi_series)
        ndmi_mk = mann_kendall_test(ndmi_series)

        # Deseasonalized volatility
        ndvi_vol = (
            compute_deseasonalized_volatility(ndvi_series)
            if len(ndvi_series) >= 6
            else _std(ndvi_series)
        )

        # Anomaly frequency (same-zone z-score; simplified for zone signals)
        ndvi_mean = mean_ndvi
        ndvi_std = _std(ndvi_series)
        n_anomalous = sum(
            1 for v in ndvi_series
            if ndvi_std > 0 and abs((v - ndvi_mean) / ndvi_std) > 1.5
        )
        anom_freq = n_anomalous / len(ndvi_series) if ndvi_series else 0.0

        radii = {
            "core": (0, CORE_OUTER_M),
            "near": (CORE_OUTER_M, NEAR_OUTER_M),
            "landscape": (NEAR_OUTER_M, LANDSCAPE_OUTER_M),
        }
        inner, outer = radii[zone_name]

        return (
            ZoneSignal(
                zone=zone_name,
                inner_radius_m=inner,
                outer_radius_m=outer,
                mean_ndvi=round(mean_ndvi, 5),
                mean_ndmi=round(mean_ndmi, 5),
                ndvi_sens_slope=ndvi_mk.sens_slope,
                ndvi_volatility=round(ndvi_vol, 5),
                ndmi_sens_slope=ndmi_mk.sens_slope,
                anomaly_frequency=round(anom_freq, 4),
            ),
            ndvi_series,
        )

    def _compute_gradient(
        self,
        zones: dict[str, ZoneSignal],
        series: dict[str, list[float]],
    ) -> SpatialGradient:
        """Compute all spatial differential metrics."""
        core = zones["core"]
        near = zones["near"]
        land = zones["landscape"]

        core_near_delta = core.mean_ndvi - near.mean_ndvi
        near_land_delta = near.mean_ndvi - land.mean_ndvi
        core_land_delta = core.mean_ndvi - land.mean_ndvi

        denom = max(land.mean_ndvi, 0.01)
        sig = (land.mean_ndvi - core.mean_ndvi) / denom

        # Pearson correlation between core and landscape time series
        corr = _pearson(series["core"], series["landscape"])

        return SpatialGradient(
            core_near_delta=round(core_near_delta, 5),
            near_landscape_delta=round(near_land_delta, 5),
            core_landscape_delta=round(core_land_delta, 5),
            spatial_impact_gradient=round(sig, 5),
            cross_zone_correlation=round(corr, 4),
        )

    def _classify(
        self,
        gradient: SpatialGradient,
    ) -> tuple[str, str]:
        """
        Two-criterion classification using SIG and cross-zone correlation.

        Priority order:
          1. Strong SIG + consistent gradient    → LOCALIZED_IMPACT
          2. Weak SIG + high correlation         → LANDSCAPE_DRIVEN
          3. Everything else                     → MIXED
        """
        sig = gradient.spatial_impact_gradient
        corr = gradient.cross_zone_correlation

        if sig > _SIG_LOCALIZED and corr < _CORR_LOCALIZED:
            # Strong spatial gradient, zones respond differently over time
            confidence = "HIGH" if sig > 0.20 and corr < 0.60 else "MODERATE"
            return "LOCALIZED_IMPACT", confidence

        if sig < _SIG_LANDSCAPE and corr > _CORR_LANDSCAPE:
            # Zones are nearly identical — same forcing acts on all
            confidence = "HIGH" if sig < 0.04 and corr > 0.92 else "MODERATE"
            return "LANDSCAPE_DRIVEN", confidence

        # Intermediate case
        return "MIXED", "LOW"

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------

    def _build_rationale(
        self,
        classification: str,
        gradient: SpatialGradient,
        zones: dict[str, ZoneSignal],
    ) -> str:
        sig = gradient.spatial_impact_gradient
        corr = gradient.cross_zone_correlation
        c = zones["core"]
        l_ = zones["landscape"]

        parts = [
            f"SIG={sig:.4f} (threshold: localized>{_SIG_LOCALIZED}, landscape<{_SIG_LANDSCAPE}).",
            f"Cross-zone correlation r={corr:.4f} (landscape r>{_CORR_LANDSCAPE}, localized r<{_CORR_LOCALIZED}).",
            f"Core NDVI={c.mean_ndvi:.4f}, Landscape NDVI={l_.mean_ndvi:.4f}.",
            f"Core-landscape delta={gradient.core_landscape_delta:+.4f}.",
        ]
        if classification == "LOCALIZED_IMPACT":
            parts.append(
                "Core zone is significantly more degraded than landscape. "
                "Low cross-zone correlation indicates core and landscape are "
                "driven by different processes."
            )
        elif classification == "LANDSCAPE_DRIVEN":
            parts.append(
                "All spatial zones show similar NDVI levels. "
                "High cross-zone correlation confirms that the same temporal "
                "forcing (climate) acts uniformly across all scales."
            )
        else:
            parts.append(
                "SIG and correlation fall in the intermediate range. "
                "Both localized and landscape-scale processes may be operating."
            )
        return " ".join(parts)

    def _build_plain_language(
        self,
        classification: str,
        zones: dict[str, ZoneSignal],
        gradient: SpatialGradient,
        asset_id: str,
    ) -> str:
        c = zones["core"]
        l_ = zones["landscape"]
        pct_diff = abs(gradient.core_landscape_delta) / max(l_.mean_ndvi, 0.01) * 100

        if classification == "LOCALIZED_IMPACT":
            return (
                f"The vegetation directly on the trail ({c.mean_ndvi:.2f} NDVI) "
                f"is noticeably poorer than the surrounding landscape "
                f"({l_.mean_ndvi:.2f} NDVI), a difference of {pct_diff:.1f}%. "
                "This pattern suggests that trail use and human activity "
                "are causing vegetation stress that does not extend far beyond "
                "the trail itself. The surrounding area is in better condition, "
                "indicating that the cause is local rather than climate-wide."
            )
        elif classification == "LANDSCAPE_DRIVEN":
            return (
                f"Vegetation health is similar across the trail ({c.mean_ndvi:.2f} NDVI), "
                f"its surroundings, and the wider landscape ({l_.mean_ndvi:.2f} NDVI). "
                f"The difference is only {pct_diff:.1f}%, well within natural variation. "
                "This means that any stress visible at the trail is part of a broader "
                "regional pattern -- most likely related to rainfall, drought, or "
                "seasonal climate. The trail itself is not the cause."
            )
        else:
            return (
                f"The trail area ({c.mean_ndvi:.2f} NDVI) shows moderate differences "
                f"from the wider landscape ({l_.mean_ndvi:.2f} NDVI), "
                f"with a {pct_diff:.1f}% divergence. "
                "This intermediate pattern makes it difficult to definitively "
                "attribute the change to either trail use or climate alone. "
                "Both may be contributing."
            )

    def _build_management(self, classification: str, confidence: str) -> str:
        if classification == "LOCALIZED_IMPACT":
            if confidence == "HIGH":
                return (
                    "INVESTIGATE HUMAN PRESSURE. The spatial pattern strongly "
                    "suggests trail use is degrading vegetation. Recommended actions: "
                    "visitor count deployment, trail surface assessment, and "
                    "consideration of access regulation or trail hardening."
                )
            return (
                "PREVENTIVE MONITORING. A spatial impact signal is present but "
                "not yet conclusive. Deploy visitor counter; reassess after "
                "next annual satellite composite."
            )
        elif classification == "LANDSCAPE_DRIVEN":
            if confidence == "HIGH":
                return (
                    "MONITOR ONLY. The environmental stress is climate-driven "
                    "and affects the entire landscape equally. No trail-specific "
                    "intervention is required. Link monitoring to regional drought "
                    "bulletins (AEMET SPI). Reassess annually."
                )
            return (
                "MONITOR ONLY. Moderate evidence of landscape-scale forcing. "
                "No immediate management action required."
            )
        return (
            "INVESTIGATE FURTHER. The signal is mixed. Collect visitor count "
            "data and cross-reference with next season's satellite composite "
            "before deciding on intervention."
        )


# ── Utility functions ─────────────────────────────────────────────────────

def _std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((x - mean) ** 2 for x in values) / n)


def _pearson(x: list[float], y: list[float]) -> float:
    """Pearson correlation coefficient. Returns 0.0 for constant series."""
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    xa = np.array(x[:n], dtype=float)
    ya = np.array(y[:n], dtype=float)
    if np.std(xa) == 0.0 or np.std(ya) == 0.0:
        return 0.0
    return float(np.corrcoef(xa, ya)[0, 1])
