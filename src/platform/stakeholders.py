"""
SNTO Phase 7 -- Stakeholder Intelligence Model
===============================================
TASK 1: User profiles defining what each audience needs to see.

DESIGN PRINCIPLE
================
Different stakeholders make different decisions. Showing the wrong
information to the wrong audience creates noise, not intelligence.

A Political Decision Maker does not need DCS values.
An Environmental Technician does not need EUR budget totals.
A Tourism Manager does not need Mann-Kendall statistics.

The platform applies a signal filter: for each stakeholder type,
it selects, translates, and formats only the intelligence that enables
their specific decisions.

FIVE STAKEHOLDER PROFILES
==========================
1. Environmental Technician
   Makes: field inspection decisions, data quality calls, anomaly flags.
   Needs: EHS trend, DCS components, SCM classification, anomaly events.
   The most technical audience. Can handle statistical language.

2. Tourism Manager
   Makes: visitor flow decisions, product development, seasonal scheduling.
   Needs: EHS condition, visitor capacity at risk, TIS recommendation.
   Needs tourism-oriented language, not ecology jargon.

3. Destination Director
   Makes: budget allocation, intervention prioritization, strategic planning.
   Needs: TPI ranking, TIS budget, territory health, portfolio view.
   Needs financial and strategic framing.

4. Provincial Government
   Makes: multi-annual investment decisions, policy alignment, reporting to EU.
   Needs: territory health score, investment case, value delivered, risks.
   Needs institutional/policy language.

5. Political Decision Maker
   Makes: budget approval, public announcement, political positioning.
   Needs: simple status, key risk, key opportunity, investment ask.
   Maximum 1-page, no numbers beyond EUR and %. Absolute plain language.
"""
from __future__ import annotations

from dataclasses import dataclass


# ── Stakeholder type constants ─────────────────────────────────────────────

TECHNICIAN          = "ENVIRONMENTAL_TECHNICIAN"
TOURISM_MANAGER     = "TOURISM_MANAGER"
DIRECTOR            = "DESTINATION_DIRECTOR"
GOVERNMENT          = "PROVINCIAL_GOVERNMENT"
POLITICAL           = "POLITICAL_DECISION_MAKER"

STAKEHOLDER_TYPES = [TECHNICIAN, TOURISM_MANAGER, DIRECTOR, GOVERNMENT, POLITICAL]


@dataclass(frozen=True)
class StakeholderProfile:
    """
    Full profile for one stakeholder type.

    The `sees` list contains the technical fields this audience should see.
    The `not_sees` list contains fields explicitly hidden from this audience.
    Decision language is the framing vocabulary for this audience's outputs.
    """
    stakeholder_type: str
    title: str
    primary_role: str
    objectives: list
    decisions: list
    sees: list
    not_sees: list
    language_register: str      # TECHNICAL | OPERATIONAL | STRATEGIC | INSTITUTIONAL | EXECUTIVE
    report_depth: str           # FULL | SUMMARY | BRIEF | ONE_PAGE


# ── Profile definitions ────────────────────────────────────────────────────

PROFILES: dict[str, StakeholderProfile] = {

    TECHNICIAN: StakeholderProfile(
        stakeholder_type=TECHNICIAN,
        title="Environmental Technician / Monitoring Officer",
        primary_role=(
            "Operates the monitoring infrastructure, validates satellite data, "
            "conducts field inspections, and maintains the evidence base."
        ),
        objectives=[
            "Maintain continuous, high-quality environmental data.",
            "Detect anomalies and escalate to alert status when thresholds are crossed.",
            "Improve DCS by closing evidence gaps with field validation.",
            "Document the cause of environmental change (SCM classification).",
        ],
        decisions=[
            "Trigger a field inspection for an anomaly event.",
            "Upgrade monitoring coverage for low-DCS assets.",
            "Flag data quality issues that affect DCS computation.",
            "Adjust anomaly detection thresholds seasonally.",
        ],
        sees=[
            "EHS per asset (full time series)",
            "DCS component breakdown (data quality, temporal robustness, spatial consistency)",
            "SCM classification + confidence level",
            "Mann-Kendall trend test results",
            "Anomaly event log (z-scores, dates, directions)",
            "NDVI / NDMI seasonal patterns",
            "Satellite observation coverage statistics",
        ],
        not_sees=[
            "EUR budget totals or investment recommendations",
            "Tourism visitor revenue projections",
            "Political priority framing",
            "TIS or TPI rankings (not their responsibility to act on)",
        ],
        language_register="TECHNICAL",
        report_depth="FULL",
    ),

    TOURISM_MANAGER: StakeholderProfile(
        stakeholder_type=TOURISM_MANAGER,
        title="Tourism Product Manager / Destination Experience Officer",
        primary_role=(
            "Manages the visitor experience, develops tourism products, "
            "and ensures environmental health supports sustained tourism demand."
        ),
        objectives=[
            "Protect visitor experience quality at key sites.",
            "Identify assets ready for promotion campaigns.",
            "Anticipate environmental deterioration before it affects tourism.",
            "Align marketing investment with environmental carrying capacity.",
        ],
        decisions=[
            "Restrict or redirect visitors from environmentally stressed sites.",
            "Launch promotion campaigns for healthy, evidence-backed assets.",
            "Develop seasonal visitor management plans.",
            "De-market or close degraded routes until restored.",
        ],
        sees=[
            "Asset environmental condition (plain-language, no technical scores)",
            "Visitor capacity at risk (how many visitors affected)",
            "Promotion-ready assets (which sites qualify for active marketing)",
            "Tourism impact of inaction (revenue at risk from deterioration)",
            "Recommended action per asset (plain language)",
        ],
        not_sees=[
            "Mann-Kendall statistics, z-scores, NDVI values",
            "DCS component breakdown",
            "SCM technical classification codes",
            "Raw EHS numerical scores (unless simplified as condition bands)",
        ],
        language_register="OPERATIONAL",
        report_depth="SUMMARY",
    ),

    DIRECTOR: StakeholderProfile(
        stakeholder_type=DIRECTOR,
        title="Destination Director / Protected Area Manager",
        primary_role=(
            "Oversees the destination portfolio, allocates operational and investment "
            "budgets, and translates environmental intelligence into management priorities."
        ),
        objectives=[
            "Maximize territory environmental health with available resources.",
            "Build an evidence-based investment case for the governing authority.",
            "Balance conservation needs with tourism promotion opportunities.",
            "Track intervention outcomes and adjust strategy quarterly.",
        ],
        decisions=[
            "Approve EUR budget allocation for Tier 1-2 restoration interventions.",
            "Commission DCS-upgrading monitoring for evidence-weak assets.",
            "Launch or suspend promotion campaigns based on TIS and EHS.",
            "Set asset-level management targets for the coming season.",
        ],
        sees=[
            "Territory Health Score (overall portfolio condition)",
            "TPI ranking (priority order for action)",
            "TIS budget allocation (where EUR goes for maximum impact)",
            "DCS confidence level (which recommendations are reliable)",
            "Scenario comparison (why this intervention was chosen)",
            "Counterfactual cost of inaction (what happens if nothing is done)",
            "EUR cost per action (for budget planning)",
        ],
        not_sees=[
            "Raw NDVI / NDMI data",
            "Statistical test results",
            "Per-pixel satellite analysis",
        ],
        language_register="STRATEGIC",
        report_depth="SUMMARY",
    ),

    GOVERNMENT: StakeholderProfile(
        stakeholder_type=GOVERNMENT,
        title="Provincial Government / Regional Competent Authority",
        primary_role=(
            "Allocates multi-annual capital budgets, sets policy for protected areas "
            "and tourism development, and ensures European compliance reporting."
        ),
        objectives=[
            "Protect natural heritage assets as public goods.",
            "Demonstrate evidence-based stewardship to the European Commission.",
            "Achieve long-term tourism sustainability aligned with Green Deal goals.",
            "Justify public investment through measurable outcomes.",
        ],
        decisions=[
            "Multi-annual capital investment in priority conservation assets.",
            "Policy alignment: visitor management by-laws, access restrictions.",
            "Reporting to Natura 2000 / EUROPARC / SISMOTUR frameworks.",
            "Territorial planning decisions (new infrastructure vs conservation buffer).",
        ],
        sees=[
            "Territory Health Score + trend",
            "Assets at risk summary (count, visitor impact, EUR exposure)",
            "Investment case (EUR required, EUR benefit, payback logic)",
            "Evidence confidence rate (% assets with reliable data)",
            "Comparison to benchmark or previous period",
            "Alignment with Green Deal / Agenda 2030 indicators",
        ],
        not_sees=[
            "Technical monitoring specifications",
            "Per-asset scenario comparison tables",
            "Internal operational budgets",
            "Day-to-day management decisions",
        ],
        language_register="INSTITUTIONAL",
        report_depth="BRIEF",
    ),

    POLITICAL: StakeholderProfile(
        stakeholder_type=POLITICAL,
        title="Mayor / Regional Minister / Elected Official",
        primary_role=(
            "Approves major budgets, takes political responsibility for territorial "
            "governance, and communicates environmental and tourism policy to citizens."
        ),
        objectives=[
            "Protect the municipality's natural heritage for current and future generations.",
            "Sustain tourism as a pillar of regional economic development.",
            "Demonstrate responsible public stewardship of conservation resources.",
            "Respond to citizen and media concerns about environmental quality.",
        ],
        decisions=[
            "Approve the annual conservation and tourism investment budget.",
            "Announce restoration projects and promotion campaigns publicly.",
            "Endorse or block new tourism development in sensitive areas.",
        ],
        sees=[
            "Status: territory healthy / at risk / in crisis",
            "Headline: how many sites need action",
            "Investment ask: single EUR figure",
            "Key risk: what happens if we do not act",
            "Key opportunity: what tourism growth is possible with investment",
            "Plain-language recommendation: one clear sentence per decision",
        ],
        not_sees=[
            "Any technical score, index, or statistical result",
            "Asset-level detail beyond the top 1-2 critical cases",
            "Operational budget breakdowns",
            "Methodological descriptions",
        ],
        language_register="EXECUTIVE",
        report_depth="ONE_PAGE",
    ),
}


def get_profile(stakeholder_type: str) -> StakeholderProfile:
    """Return the profile for a stakeholder type. Raises ValueError if unknown."""
    if stakeholder_type not in PROFILES:
        raise ValueError(
            f"Unknown stakeholder type: {stakeholder_type!r}. "
            f"Valid types: {list(PROFILES)}"
        )
    return PROFILES[stakeholder_type]


def profile_summary(profile: StakeholderProfile) -> list[str]:
    """Return a formatted summary of one profile for reporting."""
    lines = [
        f"PROFILE: {profile.title}",
        f"Role   : {profile.primary_role}",
        "",
        "OBJECTIVES:",
    ]
    for obj in profile.objectives:
        lines.append(f"  - {obj}")
    lines += ["", "DECISIONS THEY MAKE:"]
    for dec in profile.decisions:
        lines.append(f"  - {dec}")
    lines += ["", "INFORMATION THEY SEE:"]
    for s in profile.sees:
        lines.append(f"  + {s}")
    lines += ["", "INFORMATION HIDDEN FROM THEM:"]
    for ns in profile.not_sees:
        lines.append(f"  - {ns}")
    lines += [
        "",
        f"Language level : {profile.language_register}",
        f"Report depth   : {profile.report_depth}",
    ]
    return lines
