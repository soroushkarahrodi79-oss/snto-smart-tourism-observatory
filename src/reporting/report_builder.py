from __future__ import annotations

from datetime import date
from typing import Any

from src.alerts.engine import Alert, AlertLevel
from src.ranking.ranker import RankedAsset
from src.risk_engine.scorer import RiskScore


def build_report(
    scores: list[RiskScore],
    alerts: list[Alert],
    ranked: list[RankedAsset],
    report_date: str | None = None,
) -> dict[str, Any]:
    """
    Build a structured JSON report suitable for:
      - Direct JSON serialisation
      - PDF template rendering (WeasyPrint / ReportLab)

    Returns a dict with sections: metadata, executive_summary, kpi_section,
    critical_assets, recommended_actions, risk_trends.
    """
    if report_date is None:
        report_date = date.today().isoformat()

    total = len(scores)
    critical = [a for a in alerts if a.level == AlertLevel.CRITICAL_INTERVENTION]
    urgent = [a for a in alerts if a.level == AlertLevel.URGENT_MONITORING]
    preventive = [a for a in alerts if a.level == AlertLevel.PREVENTIVE_ACTION]
    normal = [a for a in alerts if a.level == AlertLevel.NORMAL]

    avg_score = sum(s.score for s in scores) / total if total else 0.0
    max_score = max((s.score for s in scores), default=0.0)
    min_score = min((s.score for s in scores), default=0.0)

    return {
        "metadata": {
            "report_date": report_date,
            "system": "Smart Natural Tourism Observatory (SNTO)",
            "version": "1.0.0",
            "total_assets_evaluated": total,
        },
        "executive_summary": {
            "overview": (
                f"{total} natural tourism asset(s) evaluated. "
                f"{len(critical)} require critical intervention, "
                f"{len(urgent)} require urgent monitoring, "
                f"{len(preventive)} preventive action recommended, "
                f"{len(normal)} in normal status."
            ),
            "average_risk_score": round(avg_score, 4),
            "highest_risk_score": round(max_score, 4),
            "lowest_risk_score": round(min_score, 4),
        },
        "kpi_section": {
            "critical_intervention_count": len(critical),
            "urgent_monitoring_count": len(urgent),
            "preventive_action_count": len(preventive),
            "normal_count": len(normal),
            "average_risk_score": round(avg_score, 4),
            "assets_above_threshold_0_5": sum(1 for s in scores if s.score >= 0.5),
            "assets_above_threshold_0_7": sum(1 for s in scores if s.score >= 0.7),
        },
        "critical_assets": [
            {
                "rank": r.rank,
                "asset_id": r.asset_id,
                "risk_score": round(r.risk_score, 4),
                "percentile": r.percentile,
            }
            for r in ranked
            if r.risk_score >= 0.5
        ],
        "recommended_actions": _aggregate_actions(alerts),
        "risk_trends": [
            {
                "asset_id": s.asset_id,
                "score": round(s.score, 4),
                "ecological_degradation": round(s.components.ecological_degradation, 4),
                "human_pressure_proxy": round(s.components.human_pressure_proxy, 4),
                "vulnerability_index": round(s.components.vulnerability_index, 4),
            }
            for s in sorted(scores, key=lambda x: x.score, reverse=True)
        ],
    }


def _aggregate_actions(alerts: list[Alert]) -> list[dict[str, Any]]:
    """Collect unique actions per alert level, sorted by severity."""
    level_order = [
        AlertLevel.CRITICAL_INTERVENTION,
        AlertLevel.URGENT_MONITORING,
        AlertLevel.PREVENTIVE_ACTION,
        AlertLevel.NORMAL,
    ]
    result = []
    for level in level_order:
        level_alerts = [a for a in alerts if a.level == level]
        if not level_alerts:
            continue
        actions: list[str] = []
        for a in level_alerts:
            for action in a.recommended_actions:
                if action not in actions:
                    actions.append(action)
        result.append(
            {
                "alert_level": level.value,
                "asset_count": len(level_alerts),
                "asset_ids": [a.asset_id for a in level_alerts],
                "actions": actions,
            }
        )
    return result
