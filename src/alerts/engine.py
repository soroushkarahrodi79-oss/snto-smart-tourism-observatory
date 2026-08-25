from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config.constants import (
    ALERT_CRITICAL,
    ALERT_PREVENTIVE,
    ALERT_URGENT,
)
from src.risk_engine.scorer import RiskScore
from src.time_series.trend import TrendResult, is_declining


class AlertLevel(str, Enum):
    CRITICAL_INTERVENTION = "CRITICAL_INTERVENTION"
    URGENT_MONITORING = "URGENT_MONITORING"
    PREVENTIVE_ACTION = "PREVENTIVE_ACTION"
    NORMAL = "NORMAL"


# Canonical alert-severity ordering (lower index = more severe). The single
# source for any consumer that must rank or escalate alerts (e.g.
# ``src/platform/enrichment.py``), so the ordering is defined exactly once (K-23).
ALERT_SEVERITY: dict[AlertLevel, int] = {
    AlertLevel.CRITICAL_INTERVENTION: 0,
    AlertLevel.URGENT_MONITORING: 1,
    AlertLevel.PREVENTIVE_ACTION: 2,
    AlertLevel.NORMAL: 3,
}


def classify_alert_level(score: float, is_declining_trend: bool) -> AlertLevel:
    """Map a risk score (0-1) and a declining-trend flag to an alert level.

    The **single source** of the alert threshold ladder (K-23): both
    :class:`AlertEngine` and ``src/platform/enrichment.py`` classify through this,
    so the cut-points live once in ``src/config/constants.py`` and the ladder is
    written once. Callers supply the declining-trend condition in whatever form
    they hold it (a ``TrendResult`` via ``is_declining``, or a gated
    ``trend_direction == "decreasing"`` string).
    """
    if score > ALERT_CRITICAL:
        return AlertLevel.CRITICAL_INTERVENTION
    if score >= ALERT_URGENT and is_declining_trend:
        return AlertLevel.URGENT_MONITORING
    if score >= ALERT_PREVENTIVE:
        return AlertLevel.PREVENTIVE_ACTION
    return AlertLevel.NORMAL


OPERATIONAL_ACTIONS: dict[AlertLevel, list[str]] = {
    AlertLevel.CRITICAL_INTERVENTION: [
        "immediate_site_inspection",
        "access_restriction",
        "emergency_restoration",
    ],
    AlertLevel.URGENT_MONITORING: [
        "bi_weekly_monitoring",
        "preventive_maintenance",
        "visitor_limit_review",
    ],
    AlertLevel.PREVENTIVE_ACTION: [
        "quarterly_inspection",
        "maintenance_schedule",
        "visitor_education",
    ],
    AlertLevel.NORMAL: [
        "annual_monitoring",
        "routine_promotion",
    ],
}


@dataclass(frozen=True)
class Alert:
    asset_id: str
    level: AlertLevel
    score: float
    triggered_rules: list[str]
    recommended_actions: list[str]


class AlertEngine:
    def evaluate_asset(
        self,
        risk_score: RiskScore,
        trend: TrendResult,
    ) -> Alert:
        """Apply rule set in priority order; return the most severe matching Alert."""
        level, rules = self._classify_level(risk_score.score, trend)
        return Alert(
            asset_id=risk_score.asset_id,
            level=level,
            score=risk_score.score,
            triggered_rules=rules,
            recommended_actions=OPERATIONAL_ACTIONS[level],
        )

    def _classify_level(
        self,
        score: float,
        trend: TrendResult,
    ) -> tuple[AlertLevel, list[str]]:
        # Level from the single-source ladder; the human-readable rules (which
        # cite the exact thresholds and, for URGENT, the trend statistics) are
        # built here because only the engine has the full TrendResult.
        level = classify_alert_level(score, is_declining(trend))
        if level is AlertLevel.CRITICAL_INTERVENTION:
            rules = [f"score={score:.3f} > critical_threshold={ALERT_CRITICAL}"]
        elif level is AlertLevel.URGENT_MONITORING:
            # Worsening = NDVI actively declining (statistically credible negative
            # slope) while score is already high; is_declining requires R² >= 0.30.
            rules = [
                f"score={score:.3f} >= urgent_threshold={ALERT_URGENT}",
                f"trend_slope={trend.slope:.4f} (R²={trend.r_squared:.2f}) — declining vegetation confirmed",
            ]
        elif level is AlertLevel.PREVENTIVE_ACTION:
            rules = [f"score={score:.3f} >= preventive_threshold={ALERT_PREVENTIVE}"]
        else:
            rules = [f"score={score:.3f} < preventive_threshold={ALERT_PREVENTIVE}"]
        return level, rules
