"""
SNTO Phase 7 -- Decision Playbooks
=====================================
TASK 6: Institutional decision playbooks for standard management situations.

A playbook is a pre-agreed response pattern for a recognisable situation.
It reduces decision latency: instead of analysing the situation from scratch
every time, managers match the situation to a playbook and apply the
pre-validated action sequence.

FIVE INSTITUTIONAL PLAYBOOKS
=============================
Case 1: High Risk + High Confidence
  The worst situation -- but the most actionable.
  Evidence is strong, problem is clear, action is justified.
  Decision: RESTORE. Do not delay.

Case 2: High Risk + Low Confidence
  Dangerous but uncertain. Cannot commit capital without more data.
  Decision: COLLECT EVIDENCE first, then RESTORE.

Case 3: Healthy Asset + High Strategic Value
  A low-risk, high-value asset that can drive tourism growth.
  Decision: PROMOTE and MONITOR.

Case 4: Promotion Opportunity
  Asset is ready for promotion investment.
  Decision: LAUNCH CAMPAIGN with evidence gate.

Case 5: Budget Constraint
  Available budget is insufficient for all recommended actions.
  Decision: PRIORITISE BY TIS. Defer what does not fit.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlaybookMatch:
    """Result of matching one asset to a decision playbook."""
    asset_id: str
    asset_name: str
    playbook_code: str
    playbook_title: str
    matched_reason: str
    recommended_action: str
    action_sequence: list       # list[str], ordered steps
    urgency: str                # IMMEDIATE | HIGH | MEDIUM | LOW
    expected_outcome: str
    risk_if_not_acted: str
    cost_note: str              # rough cost guidance


# ── Playbook matching ──────────────────────────────────────────────────────

def match_playbook(asset) -> PlaybookMatch:
    """
    Match one TerritorialAsset (with Phase 5 tier/tpi set and Phase 6 TIS) to
    the most appropriate decision playbook.
    """
    ehs   = asset.ehs
    dcs   = asset.dcs
    tier  = asset.tier or 3
    scm   = asset.scm_classification
    alert = asset.alert_level

    # Case 1: High Risk + High Confidence
    if (tier == 1 and dcs >= 60 and
            alert in ("CRITICAL_INTERVENTION", "URGENT_MONITORING")):
        return _case1_high_risk_high_confidence(asset)

    # Case 2: High Risk + Low Confidence
    if (tier == 1 and dcs < 60) or (tier <= 2 and dcs < 45):
        return _case2_high_risk_low_confidence(asset)

    # Case 3: Healthy + High Strategic Value
    if (ehs >= 75 and asset.economic_importance >= 0.70 and tier == 4):
        return _case3_healthy_high_value(asset)

    # Case 4: Promotion Opportunity
    if tier == 4:
        return _case4_promotion_opportunity(asset)

    # Case 5 (default for Tier 2-3 with budget context) -- handled by reporter
    # Default: Case 5 (budget-constrained preventive)
    return _case5_budget_constrained(asset)


def _case1_high_risk_high_confidence(asset) -> PlaybookMatch:
    return PlaybookMatch(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        playbook_code="CASE-1",
        playbook_title="High Risk + High Confidence -- IMMEDIATE RESTORATION",
        matched_reason=(
            f"Alert level is {asset.alert_level}, EHS={asset.ehs:.0f}/100, "
            f"DCS={asset.dcs:.0f}/100. Strong evidence of active degradation "
            "with sufficient confidence to act immediately."
        ),
        recommended_action=(
            "Fund and initiate physical restoration without delay. "
            "All evidence gates have been passed."
        ),
        action_sequence=[
            "STEP 1: Approve restoration budget (EUR 35,000).",
            "STEP 2: Commission field assessment to confirm scope (1-2 weeks).",
            "STEP 3: Tender to qualified restoration contractor.",
            "STEP 4: Restrict visitor access during restoration works.",
            f"STEP 5: Install post-restoration monitoring (EUR 4,500).",
            "STEP 6: Review environmental health 6 months post-restoration.",
            "STEP 7: Reopen to visitors with carrying capacity limits if EHS > 60.",
        ],
        urgency="IMMEDIATE",
        expected_outcome=(
            f"EHS improvement of 8-14 points within 12-18 months. "
            "Risk reduction of 10-20%. Asset returns to sustainable visitor operations."
        ),
        risk_if_not_acted=(
            "Continued degradation will escalate restoration cost by 40-60% within 2 years. "
            "Visitor experience deteriorates, generating negative destination reputation."
        ),
        cost_note="EUR 35,000-39,500 (restoration + monitoring). Justified by EUR 100K+ inaction cost.",
    )


def _case2_high_risk_low_confidence(asset) -> PlaybookMatch:
    return PlaybookMatch(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        playbook_code="CASE-2",
        playbook_title="High Risk + Low Confidence -- EVIDENCE FIRST",
        matched_reason=(
            f"Asset is in urgent condition (EHS={asset.ehs:.0f}/100, Tier {asset.tier}) "
            f"but DCS={asset.dcs:.0f}/100 is too low to justify EUR 35,000 restoration. "
            "The evidence base must be improved before capital commitment."
        ),
        recommended_action=(
            "Do NOT approve restoration immediately. Commission a monitoring upgrade "
            "and targeted field survey to build the evidence base. "
            "Restoration decision at next budget cycle."
        ),
        action_sequence=[
            "STEP 1: Approve monitoring upgrade (EUR 4,500) for satellite + field data.",
            "STEP 2: Commission a targeted field survey to confirm degradation cause.",
            "STEP 3: Review DCS after 6 months of enhanced monitoring.",
            "STEP 4: If DCS reaches 55+, escalate to Case 1 playbook.",
            "STEP 5: Implement visitor access restrictions as a precautionary measure.",
            "STEP 6: Do not commit restoration budget until DCS threshold is met.",
        ],
        urgency="HIGH",
        expected_outcome=(
            "DCS improves to 55+ within 6-12 months, enabling confident restoration "
            "decision in the next budget cycle. Visitor restrictions limit further damage."
        ),
        risk_if_not_acted=(
            "Committing EUR 35,000 on insufficient evidence risks ineffective or "
            "misdirected restoration. The actual cause may be climate (requiring different "
            "intervention) or the severity may be overstated."
        ),
        cost_note="EUR 4,500 now + EUR 35,000 at next cycle. Lower risk than immediate restoration.",
    )


def _case3_healthy_high_value(asset) -> PlaybookMatch:
    return PlaybookMatch(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        playbook_code="CASE-3",
        playbook_title="Healthy Asset + High Strategic Value -- PROMOTE AND PROTECT",
        matched_reason=(
            f"EHS={asset.ehs:.0f}/100 (excellent), DCS={asset.dcs:.0f}/100, "
            f"economic importance={asset.economic_importance:.0%}. "
            "This is a flagship destination asset ready for active promotion."
        ),
        recommended_action=(
            "Launch a full promotion campaign backed by monitoring to protect "
            "the environmental quality that makes this asset attractive."
        ),
        action_sequence=[
            f"STEP 1: Launch digital promotion campaign (EUR 12,000-15,000).",
            "STEP 2: Set a sustainable visitor capacity target (max 25% growth).",
            "STEP 3: Implement visitor monitoring (visitor counters, seasonal tracking).",
            "STEP 4: Review EHS quarterly during the promotion period.",
            "STEP 5: If EHS drops below 75, suspend campaign and re-evaluate.",
            "STEP 6: Use tourism revenue growth to fund monitoring and preventive maintenance.",
        ],
        urgency="MEDIUM",
        expected_outcome=(
            f"15-25% visitor growth within 12 months. EHS maintained above 75. "
            "Enhanced destination reputation and increased regional tourism revenue."
        ),
        risk_if_not_acted=(
            "The asset's value is not communicated to potential visitors. "
            "Tourism revenue opportunity is lost. Other destinations may capture "
            "the same market with inferior natural assets."
        ),
        cost_note="EUR 12,000-15,000 campaign. High positive ROI from visitor revenue growth.",
    )


def _case4_promotion_opportunity(asset) -> PlaybookMatch:
    return PlaybookMatch(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        playbook_code="CASE-4",
        playbook_title="Promotion Opportunity -- TARGETED CAMPAIGN",
        matched_reason=(
            f"EHS={asset.ehs:.0f}/100 and DCS={asset.dcs:.0f}/100 qualify this asset "
            "for Tier 4 (Promotion Opportunity) classification. "
            "Environmental health supports increased visitor numbers."
        ),
        recommended_action=(
            "Develop a targeted promotion campaign appropriate to the asset's "
            "visitor capacity and strategic position in the destination portfolio."
        ),
        action_sequence=[
            "STEP 1: Define visitor target (current capacity + 15-20%).",
            "STEP 2: Identify primary market segment (day-trippers, nature tourists, families).",
            f"STEP 3: Allocate promotion budget (EUR 8,000-12,000).",
            "STEP 4: Launch campaign through destination marketing channels.",
            "STEP 5: Monitor EHS monthly during first campaign season.",
            "STEP 6: Adjust visitor capacity limits if EHS shows stress signals.",
        ],
        urgency="LOW",
        expected_outcome=(
            "Measurable visitor growth within one tourism season. "
            "Positive contribution to destination economic performance. "
            "Environmental health maintained or improved."
        ),
        risk_if_not_acted=(
            "Tourism opportunity cost: visitor revenue and destination profile growth "
            "foregone while the asset sits underutilised."
        ),
        cost_note="EUR 8,000-12,000 campaign. Positive ROI expected within 1-2 seasons.",
    )


def _case5_budget_constrained(asset) -> PlaybookMatch:
    tier  = asset.tier or 3
    tier_name = {1: "Tier 1 -- Immediate", 2: "Tier 2 -- Preventive",
                 3: "Tier 3 -- Monitoring", 4: "Tier 4 -- Promotion"}.get(tier, "Tier ?")
    return PlaybookMatch(
        asset_id=asset.asset_id,
        asset_name=asset.name,
        playbook_code="CASE-5",
        playbook_title="Budget Constrained -- PRIORITISE BY TERRITORIAL IMPACT",
        matched_reason=(
            f"{tier_name} asset: EHS={asset.ehs:.0f}/100, DCS={asset.dcs:.0f}/100. "
            "Intervention is recommended but must be prioritised against other claims "
            "on the available budget."
        ),
        recommended_action=(
            "Include in TIS-ranked budget queue. Fund when budget becomes available, "
            "prioritising by Territorial Impact Score. Implement monitoring "
            "in the interim to prevent undetected deterioration."
        ),
        action_sequence=[
            "STEP 1: Confirm priority rank in territorial budget queue (TIS-based).",
            "STEP 2: Implement monitoring upgrade if DCS < 65 (EUR 4,500).",
            "STEP 3: Apply for supplementary funding (EU, national grants).",
            "STEP 4: Review at next budget cycle -- fund if resources allow.",
            "STEP 5: If condition deteriorates to Tier 1, escalate to Case 1 or 2.",
        ],
        urgency="MEDIUM",
        expected_outcome=(
            "Asset condition maintained or monitored while awaiting budget allocation. "
            "No further deterioration if monitoring is active."
        ),
        risk_if_not_acted=(
            "Preventive opportunities become more expensive restorations if delayed "
            "too long. Monitoring at minimum prevents surprise deterioration."
        ),
        cost_note="EUR 4,500 monitoring now; EUR 11,000-35,000 when budget allows.",
    )


# ── Playbook summary ───────────────────────────────────────────────────────

def format_playbook(match: PlaybookMatch) -> list[str]:
    """Format one playbook match for report inclusion."""
    lines = [
        f"PLAYBOOK {match.playbook_code}: {match.playbook_title}",
        f"Asset    : {match.asset_name}",
        f"Urgency  : {match.urgency}",
        "",
        f"WHY THIS PLAYBOOK:",
        f"  {match.matched_reason}",
        "",
        f"RECOMMENDED ACTION:",
        f"  {match.recommended_action}",
        "",
        "ACTION SEQUENCE:",
    ]
    for step in match.action_sequence:
        lines.append(f"  {step}")
    lines += [
        "",
        f"EXPECTED OUTCOME:",
        f"  {match.expected_outcome}",
        "",
        f"RISK IF NOT ACTED:",
        f"  {match.risk_if_not_acted}",
        "",
        f"COST GUIDANCE:",
        f"  {match.cost_note}",
    ]
    return lines
