"""
SNTO Phase 7 -- Executive Decision Translation Engine
======================================================
TASK 2: Rule-based translation of technical scores into plain-language
management decisions.

DESIGN PRINCIPLE
================
Every technical output from SNTO Phases 1-6 must have an institutional
equivalent. The translation is deterministic and auditable -- no AI, no
black box. A manager should be able to trace any plain-language statement
back to the specific rule and score that produced it.

TRANSLATION FRAMEWORK
=====================
Six technical dimensions are translated:

  1. EHS  -> Environmental Condition Statement
             What is the state of this site?

  2. DCS  -> Decision Confidence Statement
             How much should we trust this recommendation?

  3. Tier -> Management Action Statement
             What category of response is needed?

  4. TIS  -> Investment Efficiency Statement
             What return does this investment deliver?

  5. SCM  -> Root Cause Statement
             What is causing the environmental change?

  6. Alert -> Urgency Statement
              How quickly must we act?

Each translation produces:
  - A SHORT LABEL   (e.g. "GOOD CONDITION")     for dashboards
  - A SENTENCE      (e.g. "This site...")        for tables and summaries
  - A PARAGRAPH     (e.g. "This site is in...")  for reports
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TranslatedAsset:
    """Full institutional-language representation of one territorial asset."""
    asset_id: str
    asset_name: str

    # Condition
    condition_label: str       # EXCELLENT | GOOD | MODERATE | POOR | CRITICAL
    condition_sentence: str
    condition_paragraph: str

    # Confidence
    confidence_label: str      # VERY HIGH | HIGH | MODERATE | LOW | VERY LOW
    confidence_sentence: str
    confidence_paragraph: str

    # Root cause
    cause_label: str           # VISITOR PRESSURE | CLIMATE | MIXED | UNCLEAR
    cause_sentence: str

    # Urgency
    urgency_label: str         # IMMEDIATE | URGENT | CAUTION | STABLE
    urgency_sentence: str

    # Tier action
    action_label: str          # RESTORE | PREVENT | MONITOR | PROMOTE
    action_sentence: str

    # Investment
    investment_label: str      # HIGH EFFICIENCY | MODERATE | LOW
    investment_sentence: str

    # One-line board summary (maximum simplicity)
    board_one_liner: str

    # Three-sentence director summary
    director_summary: str


# ── EHS translation ────────────────────────────────────────────────────────

def translate_ehs(ehs: float) -> tuple[str, str, str]:
    """Returns (label, sentence, paragraph)."""
    if ehs >= 85:
        label = "EXCELLENT CONDITION"
        sent  = "This site is in excellent environmental condition and actively supports quality tourism."
        para  = (
            f"With an environmental health score of {ehs:.0f}/100, this site is thriving. "
            "Vegetation cover, habitat integrity, and ecosystem stability all indicate a "
            "healthy, resilient asset. This is a strong candidate for active promotion: "
            "it can sustainably accommodate increased visitor numbers without environmental risk."
        )
    elif ehs >= 70:
        label = "GOOD CONDITION"
        sent  = "This site is in good environmental condition and can support standard tourism activities."
        para  = (
            f"Environmental health ({ehs:.0f}/100) is good. The site shows no significant "
            "signs of degradation. Standard monitoring and routine maintenance are sufficient "
            "to maintain current condition. If visitor numbers increase significantly, "
            "preventive monitoring should be intensified."
        )
    elif ehs >= 55:
        label = "MODERATE STRESS"
        sent  = "This site shows signs of moderate environmental stress that require attention within 12 months."
        para  = (
            f"Environmental health ({ehs:.0f}/100) indicates moderate stress. The site "
            "is not yet in critical condition, but early warning signals are present. "
            "Preventive maintenance within the next 12 months will avoid escalation to "
            "a more expensive intervention. Monitoring frequency should be increased."
        )
    elif ehs >= 40:
        label = "DETERIORATING"
        sent  = "This site is in deteriorating condition and requires a management intervention within 6 months."
        para  = (
            f"Environmental health ({ehs:.0f}/100) has declined to a level that threatens "
            "the long-term viability of this site as a tourism asset. Visitor experience "
            "is already compromised. Without intervention within 6 months, the site is "
            "at risk of escalating to critical status, increasing restoration costs significantly."
        )
    elif ehs >= 25:
        label = "POOR CONDITION"
        sent  = "This site is in poor environmental condition and requires urgent restoration investment."
        para  = (
            f"Environmental health ({ehs:.0f}/100) is poor. The site shows active "
            "degradation that will accelerate without immediate action. Emergency "
            "restoration funding should be allocated in the next budget cycle. "
            "The site may need to be partially or fully closed to visitors during restoration."
        )
    else:
        label = "CRITICAL"
        sent  = "This site is in critical condition and requires emergency intervention."
        para  = (
            f"Environmental health ({ehs:.0f}/100) has reached a critical threshold. "
            "Irreversible ecological damage is possible without immediate professional "
            "restoration. The site should be closed to visitors. Emergency budget "
            "allocation is required as a matter of urgency."
        )
    return label, sent, para


# ── DCS translation ────────────────────────────────────────────────────────

def translate_dcs(dcs: float) -> tuple[str, str, str]:
    """Returns (label, sentence, paragraph)."""
    if dcs >= 80:
        label = "VERY HIGH CONFIDENCE"
        sent  = "Evidence is strong. Management decisions can be made with full confidence."
        para  = (
            f"The decision confidence score ({dcs:.0f}/100) is very high, based on a "
            "strong multi-year satellite monitoring record, validated by field data. "
            "Recommendations for this site are reliable and can be approved without "
            "requesting additional evidence. Budget allocations are fully justified."
        )
    elif dcs >= 65:
        label = "HIGH CONFIDENCE"
        sent  = "Evidence is good. Management decisions are well-supported."
        para  = (
            f"Decision confidence ({dcs:.0f}/100) is high. The monitoring record is "
            "solid. Recommendations should be implemented with standard documentation "
            "of assumptions. Minor evidence gaps exist but do not change the "
            "overall management direction."
        )
    elif dcs >= 50:
        label = "MODERATE CONFIDENCE"
        sent  = "Evidence is sufficient for cautious action. Document assumptions carefully."
        para  = (
            f"Decision confidence ({dcs:.0f}/100) is moderate. The evidence base "
            "supports the recommended action but with notable uncertainty. "
            "Decisions should be documented with explicit assumptions. "
            "A monitoring upgrade (EUR 4,500) would significantly improve future "
            "decision reliability for this site."
        )
    elif dcs >= 35:
        label = "LOW CONFIDENCE"
        sent  = "Evidence is insufficient for major investment decisions. Gather data first."
        para  = (
            f"Decision confidence ({dcs:.0f}/100) is low. The satellite record is "
            "short, incomplete, or not field-validated for this site. Major restoration "
            "investment (EUR 35,000+) cannot be confidently justified. The priority "
            "action is a monitoring upgrade (EUR 4,500) to improve the evidence base "
            "before committing capital funds."
        )
    else:
        label = "VERY LOW CONFIDENCE"
        sent  = "Evidence is critically insufficient. No capital investment should be approved without data collection first."
        para  = (
            f"Decision confidence ({dcs:.0f}/100) is critically low. The data available "
            "for this site does not meet the minimum standard for evidence-based "
            "management. Any capital allocation would be speculative. A dedicated "
            "data collection campaign is required before any other management decision."
        )
    return label, sent, para


# ── SCM (root cause) translation ───────────────────────────────────────────

def translate_scm(classification: str, confidence: str) -> tuple[str, str]:
    """Returns (cause_label, cause_sentence)."""
    key = (classification, confidence)

    if classification == "LOCALIZED_IMPACT":
        if confidence in ("HIGH", "MODERATE"):
            label = "VISITOR PRESSURE CONFIRMED"
            sent  = (
                "Visitor activity is confirmed as the primary driver of environmental change. "
                "Managing visitor numbers, routes, and behaviour will restore and protect this site."
            )
        else:
            label = "VISITOR PRESSURE LIKELY"
            sent  = (
                "Visitor pressure appears to be the main cause, but evidence is not yet "
                "conclusive. Visitor management measures are recommended while monitoring is improved."
            )
    elif classification == "LANDSCAPE_DRIVEN":
        if confidence in ("HIGH", "MODERATE"):
            label = "CLIMATE VARIABILITY CONFIRMED"
            sent  = (
                "Climate variability (drought, temperature shifts) is confirmed as the "
                "primary environmental driver. Local restoration is limited in effectiveness; "
                "focus should be on climate-resilient habitat management."
            )
        else:
            label = "CLIMATE INFLUENCE LIKELY"
            sent  = (
                "Climate factors appear to be influencing environmental change but the "
                "relationship is not fully confirmed. Climate resilience measures are "
                "advisable, with continued monitoring to strengthen the evidence."
            )
    else:  # MIXED
        label = "CAUSE UNCLEAR"
        sent  = (
            "Both visitor pressure and climate variability are contributing to "
            "environmental change, but their relative importance cannot yet be determined. "
            "A field investigation is recommended to distinguish the causes before "
            "committing to a specific management approach."
        )

    return label, sent


# ── Alert translation ──────────────────────────────────────────────────────

def translate_alert(alert_level: str, trend: str) -> tuple[str, str]:
    """Returns (urgency_label, urgency_sentence)."""
    if alert_level == "CRITICAL_INTERVENTION":
        return (
            "EMERGENCY",
            "EMERGENCY status: environmental conditions require immediate intervention. "
            "Closure to visitors and emergency restoration funding should be initiated without delay.",
        )
    if alert_level == "URGENT_MONITORING":
        return (
            "URGENT",
            "URGENT status: environmental conditions are declining rapidly. "
            "Intensive field monitoring and an intervention decision are required within 3 months.",
        )
    if alert_level == "PREVENTIVE_ACTION":
        if trend == "decreasing":
            return (
                "CAUTION -- DECLINING",
                "CAUTION: conditions are below optimal and are trending downward. "
                "Preventive measures should be implemented within 6-12 months to avoid escalation.",
            )
        return (
            "CAUTION",
            "CAUTION: conditions are below the desirable threshold. "
            "Preventive maintenance is recommended within the next 12 months.",
        )
    # NORMAL
    if trend == "increasing":
        return (
            "RECOVERING",
            "Site is recovering and on an improving trajectory. Maintain current management approach.",
        )
    return (
        "STABLE",
        "Site is stable. Standard annual monitoring is sufficient.",
    )


# ── Tier / Action translation ──────────────────────────────────────────────

def translate_tier(tier: int, scm_classification: str) -> tuple[str, str]:
    """Returns (action_label, action_sentence)."""
    if tier == 1:
        if scm_classification == "LOCALIZED_IMPACT":
            return (
                "RESTORE IMMEDIATELY",
                "Fund physical restoration immediately. The cause (visitor pressure) is known "
                "and restoration will directly address it. Delay increases costs and risk.",
            )
        elif scm_classification == "LANDSCAPE_DRIVEN":
            return (
                "INVEST IN CLIMATE RESILIENCE",
                "Fund climate resilience measures. Standard restoration is limited; "
                "invest in native species replanting and habitat buffering.",
            )
        return (
            "URGENT INVESTIGATION + RESTORE",
            "Cause unclear -- begin with field investigation to determine the driver, "
            "then commit to restoration. Do not delay field inspection.",
        )
    if tier == 2:
        return (
            "PREVENTIVE MAINTENANCE",
            "Schedule preventive maintenance within 12 months. "
            "Early intervention at this stage costs 3-5x less than emergency restoration.",
        )
    if tier == 3:
        return (
            "CONTINUE MONITORING",
            "Standard monitoring is the appropriate response. "
            "No capital investment needed. Review quarterly.",
        )
    # Tier 4
    return (
        "LAUNCH PROMOTION",
        "This site qualifies for active promotion. Launch a marketing campaign "
        "to increase visitor numbers. Ensure monitoring continues during growth phase.",
    )


# ── TIS translation ────────────────────────────────────────────────────────

def translate_tis(tis: float) -> tuple[str, str]:
    """Returns (investment_label, investment_sentence)."""
    if tis >= 15:
        return (
            "EXCELLENT ROI",
            f"Investment efficiency is excellent (TIS={tis:.1f}/100). "
            "This intervention delivers outstanding territorial benefit per euro invested. "
            "Prioritise for immediate funding.",
        )
    if tis >= 8:
        return (
            "GOOD ROI",
            f"Investment efficiency is good (TIS={tis:.1f}/100). "
            "Funding this intervention is well justified. "
            "Prioritise when budget allows after higher-TIS items.",
        )
    if tis >= 3:
        return (
            "MODERATE ROI",
            f"Investment efficiency is moderate (TIS={tis:.1f}/100). "
            "The intervention delivers value but less efficiently than higher-priority items. "
            "Consider if budget remains after urgent interventions are funded.",
        )
    return (
        "LOW ROI",
        f"Investment efficiency is low (TIS={tis:.1f}/100). "
        "This intervention delivers limited territorial benefit per euro. "
        "Defer until budget and conditions improve.",
    )


# ── Board one-liner ────────────────────────────────────────────────────────

def build_board_one_liner(
    name: str,
    ehs_label: str,
    urgency_label: str,
    action_label: str,
    cost_eur: Optional[int],
) -> str:
    """Maximum simplicity: one sentence for a political decision-maker."""
    cost_str = f" (EUR {cost_eur:,} investment required)" if cost_eur and cost_eur > 0 else ""
    if urgency_label in ("EMERGENCY", "URGENT"):
        return (
            f"{name} is in {ehs_label.lower()} and requires {action_label.lower()}"
            f"{cost_str}."
        )
    if action_label == "LAUNCH PROMOTION":
        return (
            f"{name} is healthy and ready for active tourism promotion{cost_str}."
        )
    return (
        f"{name} is {ehs_label.lower()}. Recommended action: {action_label.lower()}{cost_str}."
    )


# ── Director three-sentence summary ───────────────────────────────────────

def build_director_summary(
    ehs_sentence: str,
    confidence_sentence: str,
    action_sentence: str,
) -> str:
    """Three-sentence strategic summary for the Destination Director."""
    return f"{ehs_sentence} {confidence_sentence} {action_sentence}"


# ── Full asset translation ─────────────────────────────────────────────────

def translate_asset(
    asset,                          # TerritorialAsset (Phase 5 output)
    tis: float = 0.0,
    action_cost_eur: Optional[int] = None,
) -> TranslatedAsset:
    """
    Produce a full institutional-language description of one territorial asset.

    Combines translations of EHS, DCS, SCM, Alert, Tier, and TIS into
    a coherent set of stakeholder-appropriate communications.
    """
    cond_label, cond_sent, cond_para = translate_ehs(asset.ehs)
    conf_label, conf_sent, conf_para = translate_dcs(asset.dcs)
    cause_label, cause_sent         = translate_scm(asset.scm_classification, asset.scm_confidence)
    urgency_label, urgency_sent     = translate_alert(asset.alert_level, asset.trend_direction)
    action_label, action_sent       = translate_tier(asset.tier or 3, asset.scm_classification)
    invest_label, invest_sent       = translate_tis(tis)

    board_liner = build_board_one_liner(
        asset.name, cond_label, urgency_label, action_label, action_cost_eur
    )
    director_summ = build_director_summary(cond_sent, conf_sent, action_sent)

    return TranslatedAsset(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        condition_label=cond_label,
        condition_sentence=cond_sent,
        condition_paragraph=cond_para,
        confidence_label=conf_label,
        confidence_sentence=conf_sent,
        confidence_paragraph=conf_para,
        cause_label=cause_label,
        cause_sentence=cause_sent,
        urgency_label=urgency_label,
        urgency_sentence=urgency_sent,
        action_label=action_label,
        action_sentence=action_sent,
        investment_label=invest_label,
        investment_sentence=invest_sent,
        board_one_liner=board_liner,
        director_summary=director_summ,
    )


# ── Territory-level narrative ──────────────────────────────────────────────

def translate_territory(
    territory_name: str,
    territory_health: float,
    territory_trend: str,
    n_assets: int,
    n_tier1: int,
    n_tier4: int,
    visitor_at_risk: int,
    promotion_visitors: int,
    total_investment_eur: int,
) -> str:
    """
    Produce an institutional territory-level narrative paragraph.
    Used as the opening statement in executive reports.
    """
    if territory_health >= 80:
        health_desc = "in excellent overall condition"
    elif territory_health >= 65:
        health_desc = "in good overall condition with moderate stress in some areas"
    elif territory_health >= 50:
        health_desc = "under moderate environmental stress requiring active management"
    else:
        health_desc = "under significant environmental pressure requiring urgent action"

    trend_desc = {
        "IMPROVING": "The territorial trend is positive and conditions are improving.",
        "STABLE":    "The territorial trend is stable.",
        "DECLINING": "The territorial trend is negative and conditions are worsening.",
    }.get(territory_trend, "The territorial trend is uncertain.")

    urgent_stmt = (
        f"{n_tier1} asset(s) require immediate intervention"
        if n_tier1 > 0 else "No assets currently require emergency intervention"
    )
    promo_stmt = (
        f"{n_tier4} asset(s) are ready for active promotion, "
        f"offering a combined visitor reach of {promotion_visitors:,} visitors per year"
        if n_tier4 > 0 else "No assets currently qualify for active promotion"
    )

    return (
        f"{territory_name} is {health_desc}, monitoring {n_assets} natural assets "
        f"across its territory. {trend_desc} {urgent_stmt}, "
        f"with {visitor_at_risk:,} annual visitor experiences at risk from environmental "
        f"deterioration. Addressing these requires an investment of EUR "
        f"{total_investment_eur:,}. At the same time, {promo_stmt}."
    )
