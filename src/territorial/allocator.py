"""
SNTO Phase 5 — Resource Allocation Engine
==========================================
Translates tier classification and DCS confidence gates into concrete,
management-ready action recommendations for each territorial asset.

MANAGEMENT CONFIDENCE LAYER
============================
The DCS (Decision Confidence Score) gates every recommendation:

  DCS >= 70  (HIGH)     : act now — evidence is sufficient
  DCS 55-69  (MODERATE) : act, but document residual uncertainty
  DCS < 55   (LOW)      : gather more evidence before committing resources

This creates a 3 x 4 decision matrix (confidence level x tier):

  TIER 1 + DCS HIGH    → Immediate intervention (field inspection + restoration plan)
  TIER 1 + DCS MOD     → Field inspection + prepare intervention (document uncertainty)
  TIER 1 + DCS LOW     → Emergency evidence collection (satellite upgrade + field visit)
  TIER 2 + DCS HIGH    → Preventive maintenance (schedule and execute)
  TIER 2 + DCS MOD     → Targeted monitoring upgrade (confirm signals, then maintain)
  TIER 2 + DCS LOW     → Extended monitoring (DCS improvement before spending capital)
  TIER 3 + DCS HIGH    → Routine annual review (no action needed)
  TIER 3 + DCS LOW     → Data collection upgrade (improve evidence base)
  TIER 4 + DCS HIGH    → Active promotion campaign (high confidence endorsement)
  TIER 4 + DCS MOD     → Promotion feasibility study (confirm before campaign)

UNIT COST ESTIMATES (EUR)
=========================
These are planning estimates. Actual costs depend on asset type, size, and region.

  IMMEDIATE_FIELD_INSPECTION    :  2,500
  RESTORATION_PLANNING_STUDY    :  8,000
  PREVENTIVE_MAINTENANCE        :  8,000 – 15,000 (mid: 11,000)
  VISITOR_MANAGEMENT_PLAN       :  5,000
  MONITORING_UPGRADE            :  4,000
  DATA_COLLECTION_UPGRADE       :  3,500
  VISITOR_COUNTING_STATION      :  2,500
  PROMOTION_CAMPAIGN_FULL       : 12,000
  PROMOTION_FEASIBILITY         :  1,500
  ROUTINE_MONITORING            :      0 (standard operations)

ACTION CODES
============
  IMMEDIATE_RESTORATION       : Tier 1 + DCS HIGH + LOCALIZED cause
  EMERGENCY_INSPECTION        : Tier 1 + DCS HIGH + cause unclear
  URGENT_EVIDENCE_COLLECTION  : Tier 1 + DCS LOW
  PREVENTIVE_MAINTENANCE      : Tier 2 + DCS HIGH/MOD + LOCALIZED cause
  VISITOR_MANAGEMENT          : Tier 2 + DCS HIGH + LOCALIZED
  MONITORING_UPGRADE          : Tier 2 + DCS LOW  OR  Tier 3 + DCS LOW
  DATA_COLLECTION_UPGRADE     : any tier + DCS < 50
  PROMOTION_CAMPAIGN          : Tier 4 + DCS >= 70
  PROMOTION_FEASIBILITY       : Tier 4 + DCS 55-69
  ROUTINE_MONITORING          : Tier 3 + DCS >= 55
"""

from __future__ import annotations

from .models import TerritorialAsset, RecommendedAction


# ── Unit cost lookup ──────────────────────────────────────────────────────

_COSTS: dict[str, int] = {
    "IMMEDIATE_RESTORATION":       35_000,
    "EMERGENCY_INSPECTION":         2_500,
    "URGENT_EVIDENCE_COLLECTION":   3_500,
    "PREVENTIVE_MAINTENANCE":      11_000,
    "VISITOR_MANAGEMENT":           5_000,
    "MONITORING_UPGRADE":           4_000,
    "DATA_COLLECTION_UPGRADE":      3_500,
    "VISITOR_COUNTING_STATION":     2_500,
    "PROMOTION_CAMPAIGN":          12_000,
    "PROMOTION_FEASIBILITY":        1_500,
    "ROUTINE_MONITORING":               0,
}

_LABELS: dict[str, str] = {
    "IMMEDIATE_RESTORATION":      "Immediate ecological restoration",
    "EMERGENCY_INSPECTION":       "Emergency field inspection",
    "URGENT_EVIDENCE_COLLECTION": "Urgent evidence collection (satellite + field)",
    "PREVENTIVE_MAINTENANCE":     "Preventive maintenance programme",
    "VISITOR_MANAGEMENT":         "Visitor management plan and signage",
    "MONITORING_UPGRADE":         "Monitoring equipment upgrade",
    "DATA_COLLECTION_UPGRADE":    "Satellite data collection upgrade",
    "VISITOR_COUNTING_STATION":   "Visitor counting station installation",
    "PROMOTION_CAMPAIGN":         "Tourism promotion campaign",
    "PROMOTION_FEASIBILITY":      "Promotion feasibility assessment",
    "ROUTINE_MONITORING":         "Routine annual monitoring (standard operations)",
}

_EXPECTED_VALUE: dict[str, str] = {
    "IMMEDIATE_RESTORATION":
        "Halt active degradation; begin vegetation recovery within 1-2 seasons.",
    "EMERGENCY_INSPECTION":
        "Characterise on-ground condition; enable evidence-based intervention within 90 days.",
    "URGENT_EVIDENCE_COLLECTION":
        "Improve DCS to >=60 within 12 months; unlock evidence-gated intervention.",
    "PREVENTIVE_MAINTENANCE":
        "Prevent moderate stress from progressing to urgent degradation.",
    "VISITOR_MANAGEMENT":
        "Reduce human pressure at core zone; improve EHS trajectory within 2-3 years.",
    "MONITORING_UPGRADE":
        "Improve spatial resolution of signal; confirm or rule out localised impact.",
    "DATA_COLLECTION_UPGRADE":
        "Close evidence gap; build DCS to actionable threshold (>=55) in 1-2 seasons.",
    "VISITOR_COUNTING_STATION":
        "Replace geo-proxy with direct visitor data; reduce human pressure model uncertainty.",
    "PROMOTION_CAMPAIGN":
        "Drive qualified visitor traffic to high-quality asset; boost regional tourism revenue.",
    "PROMOTION_FEASIBILITY":
        "Confirm carrying capacity and visitor experience quality before full campaign launch.",
    "ROUTINE_MONITORING":
        "Maintain situational awareness; detect early deterioration before it escalates.",
}


# ── Main entry point ──────────────────────────────────────────────────────

def allocate(
    assets: list[TerritorialAsset],
    priority_ranks: dict[str, int] | None = None,
) -> dict[str, RecommendedAction]:
    """
    Assign a RecommendedAction to every asset based on tier + DCS gate.

    Args:
        assets: list of TerritorialAsset objects with tier already set.
        priority_ranks: optional dict mapping asset_id → priority_rank.
            If None, ranks are taken from asset.priority_rank.

    Returns:
        dict mapping asset_id → RecommendedAction
    """
    results: dict[str, RecommendedAction] = {}
    for asset in assets:
        rank = (
            priority_ranks.get(asset.asset_id, 999)
            if priority_ranks
            else (asset.priority_rank or 999)
        )
        action = _decide_action(asset, rank)
        results[asset.asset_id] = action
        # Write back to asset for convenience
        asset.recommended_action_code = action.action_code
        asset.recommended_action_label = action.action_label
        asset.budget_estimate_eur = action.estimated_cost_eur
    return results


# ── Decision logic ────────────────────────────────────────────────────────

def _decide_action(asset: TerritorialAsset, rank: int) -> RecommendedAction:
    tier = asset.tier or 3
    dcs = asset.dcs
    scm = asset.scm_classification
    ehs = asset.ehs
    alert = asset.alert_level

    # DCS confidence gate
    if dcs >= 70:
        conf = "HIGH"
    elif dcs >= 55:
        conf = "MODERATE"
    else:
        conf = "LOW"

    is_localized = (scm == "LOCALIZED_IMPACT")

    # ── Tier 1: Immediate Attention ───────────────────────────────────────
    if tier == 1:
        if conf == "LOW":
            code = "URGENT_EVIDENCE_COLLECTION"
            just = (
                f"Asset is in critical condition (EHS={ehs:.0f}/100, alert={alert}) "
                f"but DCS={dcs:.0f}/100 is too low to justify large expenditure. "
                "Collect more satellite observations and conduct a field survey "
                "before committing restoration funds."
            )
        elif is_localized and conf in ("HIGH", "MODERATE"):
            code = "IMMEDIATE_RESTORATION"
            just = (
                f"Condition is critical (EHS={ehs:.0f}/100) and cause is confirmed "
                "localised human pressure (LOCALIZED_IMPACT). "
                f"DCS={dcs:.0f}/100 supports immediate action. "
                "Initiate ecological restoration and implement visitor controls."
            )
        else:
            code = "EMERGENCY_INSPECTION"
            just = (
                f"Condition is critical (EHS={ehs:.0f}/100, alert={alert}). "
                "Cause is not fully localised — an immediate field inspection "
                "is required to characterise on-ground damage and determine "
                "whether restoration or climate-resilience investment is needed."
            )

    # ── Tier 2: Preventive Action ─────────────────────────────────────────
    elif tier == 2:
        if conf == "LOW":
            code = "DATA_COLLECTION_UPGRADE"
            just = (
                f"Asset shows preventive-level stress (EHS={ehs:.0f}/100) but "
                f"DCS={dcs:.0f}/100 is below the actionable threshold. "
                "Invest in longer satellite time series and field validation "
                "to unlock confident preventive intervention."
            )
        elif is_localized:
            code = "VISITOR_MANAGEMENT"
            just = (
                f"Spatial analysis confirms localised human pressure (LOCALIZED_IMPACT). "
                f"EHS={ehs:.0f}/100 with preventive signals. "
                "A visitor management plan and improved trailhead signage will "
                "reduce core-zone pressure before it reaches critical levels."
            )
        else:
            code = "PREVENTIVE_MAINTENANCE"
            just = (
                f"EHS={ehs:.0f}/100 — asset is deteriorating but not yet critical. "
                "Cause is landscape-driven or mixed; preventive maintenance "
                "(trail resurfacing, drainage, erosion barriers) will improve "
                "climate resilience and stabilise the EHS trajectory."
            )

    # ── Tier 4: Promotion Opportunity ─────────────────────────────────────
    elif tier == 4:
        if conf in ("HIGH", "MODERATE") and dcs >= 60:
            code = "PROMOTION_CAMPAIGN"
            just = (
                f"EHS={ehs:.0f}/100 — excellent condition confirmed by "
                f"{dcs:.0f}/100 confidence score. Asset is ready for active "
                "promotion. Include in destination marketing campaigns and "
                "regional tourism observatory showcase."
            )
        else:
            code = "PROMOTION_FEASIBILITY"
            just = (
                f"EHS={ehs:.0f}/100 is good but DCS={dcs:.0f}/100 is moderate. "
                "Conduct a promotion feasibility assessment (visitor experience "
                "quality, carrying capacity) before committing campaign budget."
            )

    # ── Tier 3: Routine Monitoring ─────────────────────────────────────────
    else:
        if dcs < 50:
            code = "DATA_COLLECTION_UPGRADE"
            just = (
                f"EHS={ehs:.0f}/100 is acceptable but DCS={dcs:.0f}/100 is low. "
                "Investing in a longer satellite time series will improve "
                "evidence quality before the next planning cycle."
            )
        else:
            code = "ROUTINE_MONITORING"
            just = (
                f"EHS={ehs:.0f}/100 — no urgent signals. Annual monitoring "
                "is sufficient. Review at next quarterly assessment."
            )

    return RecommendedAction(
        action_code=code,
        action_label=_LABELS[code],
        justification=just,
        confidence_level=conf,
        expected_value=_EXPECTED_VALUE[code],
        estimated_cost_eur=_COSTS[code],
        priority_rank=rank,
        dcs_gate_passed=(conf != "LOW"),
    )
