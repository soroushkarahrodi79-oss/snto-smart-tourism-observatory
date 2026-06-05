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
