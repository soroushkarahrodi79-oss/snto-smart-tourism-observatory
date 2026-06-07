"""
SNTO Phase 5 — Territorial Priority Index (TPI)
================================================
Transforms per-asset SNTO outputs into a single intervention-priority score
that public administrations can use to rank assets and allocate resources.

DESIGN PRINCIPLE
================
The TPI measures WHERE TO ALLOCATE ATTENTION FIRST, not how sick an asset is.

A very degraded site with poor evidence (DCS = 30) should NOT top the priority
list — there is not enough information to justify a large intervention. Instead
it triggers "gather evidence urgently."

A moderately stressed asset with very high strategic value, high DCS, and a
clearly identified human pressure cause sits at the top: we know what is wrong,
we know where, we have strong evidence, and many visitors are affected.

Healthy high-EHS assets also reach high TPI via the promotion pathway: they
represent confirmed investment opportunities that deserve active allocation of
marketing resources.

FORMULA
=======
TPI = ConditionUrgency  [0-40]
    + EvidenceStrength   [0-25]
    + StrategicValue     [0-20]
    + CausalityClarity   [0-15]

Maximum: 100

COMPONENT DEFINITIONS
=====================

1. CONDITION URGENCY (0-40)
   Maps EHS and alert level to intervention urgency.

   CRITICAL_INTERVENTION alert:  40.0  (maximum)
   URGENT_MONITORING alert:      26-36  (scaled by EHS and declining trend)
   PREVENTIVE_ACTION alert:      14-24  (scaled by EHS severity)
   NORMAL alert:
     EHS >= 80: promotion urgency = 10-20 (higher EHS = more urgency to promote)
     EHS 60-79: low urgency        = 8-14
     EHS < 60:  concern urgency    = 9-18 (higher EHS deficit = more concern)

   Declining trend adds +12% to urgency for non-CRITICAL alerts.

2. EVIDENCE STRENGTH (0-25)
   25 * (DCS / 100)
   Direct pass-through of the Decision Confidence Score.
   DCS = 100 → full 25 pts.  DCS = 50 → 12.5 pts.

3. STRATEGIC VALUE (0-20)
   Captures the territorial importance of the asset:
   20 * (0.40 * visitor_score + 0.35 * economic_importance + 0.25 * accessibility)

   visitor_score is normalised within the territory against the asset with
   the highest annual visitor volume (territorial_max_visitors).

4. CAUSALITY CLARITY (0-15)
   How unambiguously the Spatial Causality Module identified the driver:
   LOCALIZED_IMPACT + HIGH     : 15  (human cause, clear intervention target)
   LANDSCAPE_DRIVEN + HIGH     : 12  (climate cause, resilience action clear)
   LOCALIZED_IMPACT + MODERATE : 10
   LANDSCAPE_DRIVEN + MODERATE :  8
   MIXED + any                 :  5
   any + LOW                   :  3

   Localized causes score higher than landscape because the intervention is
   directly actionable (manage visitors, rehabilitate trail) rather than
   requiring landscape-scale climate adaptation.

TIER CLASSIFICATION
===================
Tier 4 (PROMOTION OPPORTUNITY):
  EHS >= 75 AND risk_score <= 0.35 AND DCS >= 55 AND trend != "decreasing"

Tier 1 (IMMEDIATE ATTENTION):
  (alert = CRITICAL or URGENT) OR (EHS < 45)
  AND (TPI >= 50 OR EHS < 38)

Tier 2 (PREVENTIVE ACTION):
  TPI >= 38 AND EHS < 75 AND not already Tier 1

Tier 3 (ROUTINE MONITORING):
  Everything else.

NOTE: A Tier 1 asset with DCS < 50 is flagged evidence_gap = True.
The recommended action becomes "urgent evidence collection" rather than
direct intervention — but it still occupies the Tier 1 position because
the condition signal, even if uncertain, is too alarming to ignore.
"""

from __future__ import annotations

from .models import (
    TerritorialAsset,
    TPIComponents,
    TPIResult,
    TIER_LABELS,
    TIER_DESCRIPTIONS,
)


# ── Public entry point ────────────────────────────────────────────────────

def compute_tpi(
    asset: TerritorialAsset,
    territorial_max_visitors: int,
) -> TPIResult:
    """
    Compute the Territorial Priority Index for one asset.

    Args:
        asset: TerritorialAsset with all SNTO outputs populated.
        territorial_max_visitors: highest annual visitor count in the
            territory, used to normalise visitor_capacity_annual.

    Returns:
        TPIResult with full component breakdown, tier, and rationale.
    """
    cu, cu_detail = _condition_urgency(asset)
    es = round(25.0 * (asset.dcs / 100.0), 3)
    sv, sv_detail = _strategic_value(asset, territorial_max_visitors)
    cc, cc_detail = _causality_clarity(asset)

    total = _clamp(cu + es + sv + cc, 0.0, 100.0)
    total = round(total, 1)

    components = TPIComponents(
        condition_urgency=round(cu, 2),
        evidence_strength=round(es, 2),
        strategic_value=round(sv, 2),
        causality_clarity=round(cc, 2),
        total=total,
        detail={
            "condition_urgency": cu_detail,
            "evidence_strength": {"dcs": asset.dcs, "score": round(es, 3)},
            "strategic_value": sv_detail,
            "causality_clarity": cc_detail,
        },
    )

    tier, rationale = _classify_tier(asset, total)
    tier_label = TIER_LABELS[tier]
    evidence_gap = (tier in (1, 2)) and (asset.dcs < 55)
    promotion_ready = (tier == 4)

    return TPIResult(
        asset_id=asset.asset_id,
        tpi=total,
        components=components,
        tier=tier,
        tier_label=tier_label,
        tier_rationale=rationale,
        promotion_ready=promotion_ready,
        evidence_gap=evidence_gap,
    )


def rank_assets(
    assets: list[TerritorialAsset],
) -> list[TerritorialAsset]:
    """
    Compute TPI for all assets, assign priority ranks, and write results
    back into the TerritorialAsset objects.

    Priority rank 1 = highest TPI = most urgent territorial attention.
    Within the same TPI (ties), lower EHS breaks the tie for intervention
    assets; higher EHS breaks the tie for promotion assets.

    Returns the same list, sorted by TPI descending.
    """
    if not assets:
        return assets

    max_visitors = max(a.visitor_capacity_annual for a in assets)

    results: list[tuple[TerritorialAsset, TPIResult]] = []
    for asset in assets:
        r = compute_tpi(asset, max_visitors)
        results.append((asset, r))

    # Sort: TPI descending, then EHS (descending for Tier 4, ascending others)
    results.sort(key=lambda x: (
        -x[1].tpi,
        x[0].ehs if x[1].tier != 4 else -x[0].ehs,
    ))

    for rank, (asset, result) in enumerate(results, start=1):
        asset.tpi = result.tpi
        asset.tier = result.tier
        asset.tier_label = result.tier_label
        asset.priority_rank = rank

    return [a for a, _ in results]


# ── Sub-score functions ───────────────────────────────────────────────────

def _condition_urgency(asset: TerritorialAsset) -> tuple[float, dict]:
    """
    Map EHS, alert level, and trend to a 0-40 condition urgency score.

    Logic:
      - CRITICAL alert       → always 40 (maximum urgency)
      - URGENT alert         → 28-36, amplified by declining trend
      - PREVENTIVE alert     → 14-24, scaled by EHS severity
      - NORMAL alert:
          EHS >= 80          → 10-20 (promotion urgency, grows with EHS)
          EHS 60-79          → 8-14  (low concern zone)
          EHS < 60           → 9-20  (mild concern despite no alert)
    """
    al = asset.alert_level
    ehs = asset.ehs
    trend = asset.trend_direction

    if al == "CRITICAL_INTERVENTION":
        factor = 1.000
        label = "CRITICAL alert"

    elif al == "URGENT_MONITORING":
        # Base 0.70 + EHS penalty up to +0.20
        factor = 0.70 + 0.20 * _clamp((1.0 - ehs / 100.0) / 0.6, 0.0, 1.0)
        label = f"URGENT alert, EHS={ehs:.0f}"
        if trend == "decreasing":
            factor = min(1.0, factor * 1.12)
            label += " + declining trend"

    elif al == "PREVENTIVE_ACTION":
        # Preventive assets: factor 0.35-0.60 based on EHS severity
        if ehs < 50:
            factor = 0.60
        elif ehs < 65:
            factor = 0.50
        else:
            factor = 0.38
        label = f"PREVENTIVE alert, EHS={ehs:.0f}"
        if trend == "decreasing":
            factor = min(1.0, factor * 1.10)
            label += " + declining trend"

    else:  # NORMAL
        if ehs >= 80:
            # Promotion urgency: more urgent to capitalise on great condition
            factor = 0.25 + 0.25 * _clamp((ehs - 80) / 20.0, 0.0, 1.0)
            label = f"NORMAL alert, EHS={ehs:.0f} (promotion urgency)"
        elif ehs >= 60:
            factor = 0.20 + 0.10 * _clamp((ehs - 60) / 20.0, 0.0, 1.0)
            label = f"NORMAL alert, EHS={ehs:.0f} (stable zone)"
        else:
            # EHS below 60 but no alert fired — mild concern
            factor = 0.22 + 0.28 * _clamp((60.0 - ehs) / 60.0, 0.0, 1.0)
            label = f"NORMAL alert but EHS={ehs:.0f} (latent concern)"

    score = round(40.0 * factor, 3)
    return score, {"alert_level": al, "factor": round(factor, 4), "label": label}


def _strategic_value(
    asset: TerritorialAsset,
    territorial_max_visitors: int,
) -> tuple[float, dict]:
    """
    Compute strategic importance score (0-20).

    visitor_score is normalised against the territorial maximum so that
    a flagship park does not automatically dominate every asset type.
    """
    visitor_score = _clamp(
        asset.visitor_capacity_annual / max(1, territorial_max_visitors)
    )
    sv_composite = (
        0.40 * visitor_score
        + 0.35 * _clamp(asset.economic_importance, 0.0, 1.0)
        + 0.25 * _clamp(asset.accessibility_score, 0.0, 1.0)
    )
    score = round(20.0 * sv_composite, 3)
    return score, {
        "visitor_score": round(visitor_score, 4),
        "economic_importance": asset.economic_importance,
        "accessibility_score": asset.accessibility_score,
        "sv_composite": round(sv_composite, 4),
    }


def _causality_clarity(asset: TerritorialAsset) -> tuple[float, dict]:
    """
    Translate SCM classification + confidence into a 0-15 clarity score.
    """
    key = (asset.scm_classification, asset.scm_confidence)
    lookup = {
        ("LOCALIZED_IMPACT", "HIGH"):     15,
        ("LANDSCAPE_DRIVEN", "HIGH"):     12,
        ("LOCALIZED_IMPACT", "MODERATE"): 10,
        ("LANDSCAPE_DRIVEN", "MODERATE"):  8,
        ("MIXED",            "HIGH"):      6,
        ("MIXED",            "MODERATE"):  5,
        ("LOCALIZED_IMPACT", "LOW"):       4,
        ("LANDSCAPE_DRIVEN", "LOW"):       4,
        ("MIXED",            "LOW"):       3,
    }
    score = float(lookup.get(key, 3))
    return score, {
        "scm_classification": asset.scm_classification,
        "scm_confidence": asset.scm_confidence,
        "clarity_score": score,
    }


def _classify_tier(asset: TerritorialAsset, tpi: float) -> tuple[int, str]:
    """
    Assign one of four intervention priority tiers.

    Decision order (top wins):
    1. Tier 4 PROMOTION OPPORTUNITY — healthy, confident, stable
    2. Tier 1 IMMEDIATE ATTENTION  — critical/urgent alert or very low EHS
    3. Tier 2 PREVENTIVE ACTION    — TPI >= 38 and EHS < 75
    4. Tier 3 ROUTINE MONITORING   — everything else
    """
    ehs = asset.ehs
    risk = asset.risk_score
    dcs = asset.dcs
    alert = asset.alert_level
    trend = asset.trend_direction

    # ── Tier 4: Promotion Opportunity ─────────────────────────────────────
    if (ehs >= 75
            and risk <= 0.35
            and dcs >= 55
            and trend != "decreasing"):
        rationale = (
            f"EHS = {ehs:.0f}/100 (good), risk = {risk:.2f} (low), "
            f"DCS = {dcs:.0f}/100 (evidence sufficient), trend stable or improving. "
            "Asset is environmentally healthy and evidence-backed. "
            "Allocate promotional resources."
        )
        return 4, rationale

    # ── Tier 1: Immediate Attention ────────────────────────────────────────
    is_critical_alert = alert in ("CRITICAL_INTERVENTION", "URGENT_MONITORING")
    is_very_low_ehs = ehs < 45
    if is_critical_alert or is_very_low_ehs:
        if tpi >= 50 or ehs < 38:
            dcs_note = (
                " DCS is LOW -- urgent evidence collection required before full intervention."
                if dcs < 55 else
                " Evidence supports immediate action."
            )
            rationale = (
                f"Alert = {alert}, EHS = {ehs:.0f}/100, TPI = {tpi:.0f}."
                f"{dcs_note}"
            )
            return 1, rationale

    # ── Tier 2: Preventive Action ─────────────────────────────────────────
    if tpi >= 38 and ehs < 75:
        rationale = (
            f"TPI = {tpi:.0f} >= 38 and EHS = {ehs:.0f} < 75. "
            "Warning signals present. Preventive maintenance avoids deterioration."
        )
        return 2, rationale

    # ── Tier 3: Routine Monitoring ────────────────────────────────────────
    rationale = (
        f"TPI = {tpi:.0f}, EHS = {ehs:.0f}. "
        "No urgent signals. Annual monitoring is sufficient."
    )
    return 3, rationale


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))
