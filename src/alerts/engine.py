from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config.constants import (
    ALERT_CRITICAL,
    ALERT_PREVENTIVE,
    ALERT_URGENT,
)
from src.risk_engine.scorer import RiskScore
from src.time_series.trend import TrendResult, is_declining, is_rising


class AlertLevel(str, Enum):
    CRITICAL_INTERVENTION = "CRITICAL_INTERVENTION"
    URGENT_MONITORING = "URGENT_MONITORING"
    PREVENTIVE_ACTION = "PREVENTIVE_ACTION"
    NORMAL = "NORMAL"


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
        if score > ALERT_CRITICAL:
            return AlertLevel.CRITICAL_INTERVENTION, [
                f"score={score:.3f} > critical_threshold={ALERT_CRITICAL}"
            ]

        # Worsening = NDVI actively declining (statistically credible negative slope)
        # while score is already high. Requires R² >= 0.30 to avoid noise artefacts.
        if score >= ALERT_URGENT and is_declining(trend):
            return AlertLevel.URGENT_MONITORING, [
                f"score={score:.3f} >= urgent_threshold={ALERT_URGENT}",
                f"trend_slope={trend.slope:.4f} (R²={trend.r_squared:.2f}) — declining vegetation confirmed",
            ]

        if score >= ALERT_PREVENTIVE:
            return AlertLevel.PREVENTIVE_ACTION, [
                f"score={score:.3f} >= preventive_threshold={ALERT_PREVENTIVE}"
            ]

        return AlertLevel.NORMAL, [f"score={score:.3f} < preventive_threshold={ALERT_PREVENTIVE}"]
