from __future__ import annotations

# Risk model weights (must sum to 1.0)
WEIGHT_ECOLOGICAL: float = 0.4
WEIGHT_HUMAN_PRESSURE: float = 0.3
WEIGHT_VULNERABILITY: float = 0.3

# Alert score thresholds
ALERT_CRITICAL: float = 0.85
ALERT_URGENT: float = 0.70
ALERT_PREVENTIVE: float = 0.50

# NDVI rising trend threshold (units/month)
TREND_RISING_SLOPE: float = 0.002

# NDVI baselines for Iberian Mediterranean scrubland
NDVI_HEALTHY_BASELINE: float = 0.55
NDVI_DEGRADED_THRESHOLD: float = 0.30

# NDMI healthy baseline
NDMI_HEALTHY_BASELINE: float = 0.20

# Anomaly detection
ANOMALY_Z_THRESHOLD: float = 2.0

# Mock data parameters
MOCK_MONTHS: int = 12
MOCK_SPRING_PEAK_MONTH: int = 4  # April — Mediterranean phenology peak

# Human pressure proxy — geo-based thresholds
HP_ROAD_DECAY: float = 1.5          # α for road accessibility exponential decay
HP_SETTLEMENT_DECAY: float = 0.4    # α for settlement proximity decay
HP_POI_SATURATION: int = 15         # POI count that saturates poi_density factor
HP_TRAIL_SATURATION_KM: float = 8.0 # trail network km that saturates connectivity
HP_SLOPE_MAX_DEG: float = 30.0      # slope (degrees) above which access is zero

# Spectral fallback disturbance threshold (deseasonalized NDVI std)
HP_MAX_DISTURBANCE_STD: float = 0.05

# ── Operational EHS — per-scene percentile anchoring ─────────────────────────
# Governs calculate_delta_ehs.py. All five values are intentionally exposed
# here (not hardcoded in the logic) so they can be calibrated and defended.
#
# P_BASE / P_FLOOR are computed from the actual pixel distribution of each
# Sentinel-2 scene, per season, after excluding SCL-masked and trail-buffer
# pixels.  Adjust to match the ecological dynamics of the target territory.
#
# EHS_SEASON_FOR_BUDGET must be "summer" or "spring"; it selects which
# seasonal EHS column tis_engine.py reads for priority and budget.
EHS_P_BASE: int = 90              # percentile → baseline_sano (healthy reference)
EHS_P_FLOOR: int = 10             # percentile → suelo (degraded floor)
EHS_W_NDVI: float = 0.5           # weight of NDVI deficit in composite EHS
EHS_W_NDMI: float = 0.5           # weight of NDMI deficit in composite EHS
EHS_SEASON_FOR_BUDGET: str = "summer"  # season driving priority_score & tis_budget

# ── Operational SCM — raster-based SIG thresholds & causal factors ────────────
# Governs run_scm_operational.py and tis_engine.py.
#
# SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)
# Thresholds match src/spatial_causality/analyzer.py for cross-module consistency.
#
# Causal factors apply the polluter-pays principle to the restoration budget:
# investment should be proportional to the fraction of degradation attributable
# to human pressure rather than to climate forcing beyond local control.
# These are starting values; adjust after field validation.
SCM_SIG_LOCALIZED_THRESHOLD: float = 0.15  # SIG above this → LOCALIZED_IMPACT
SCM_SIG_LANDSCAPE_THRESHOLD: float = 0.07  # SIG below this → LANDSCAPE_DRIVEN

SCM_LOCALIZED_FACTOR: float = 1.0   # trail use is the driver — full budget
SCM_MIXED_FACTOR: float = 0.5       # ambiguous cause — half budget
SCM_LANDSCAPE_FACTOR: float = 0.0   # climate is the driver — no local budget

# ── Decision Confidence Score — minimum quality gates for can_act ─────────────
# Prevents issuing an actionable recommendation when foundational data quality
# or time-series robustness falls below minimum thresholds, even if the total
# DCS score reaches the HIGH band through strong spatial or signal scores.
# These are starting values; adjust after operational calibration.
DCS_MIN_DQ_FOR_ACTION: int = 10   # minimum DQ score (out of 25) to enable can_act
DCS_MIN_TR_FOR_ACTION: int = 12   # minimum TR score (out of 25) to enable can_act
