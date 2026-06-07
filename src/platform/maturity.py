"""
SNTO Phase 7 -- Destination Management Maturity Framework
==========================================================
TASK 7: A 5-level maturity model for territorial intelligence capability.

PURPOSE
=======
The maturity framework allows a destination management organisation (DMO)
to understand WHERE IT CURRENTLY STANDS in its journey towards data-driven
governance, and WHAT IT NEEDS TO DO to advance to the next level.

This is not a scoring exercise. It is a diagnostic tool to guide
strategic investment in institutional intelligence capability.

FIVE MATURITY LEVELS
====================
Level 1: REACTIVE MANAGEMENT
  "We respond to problems when they become visible."
  No systematic environmental data. Decisions based on field reports
  and political pressure. No proactive planning.

Level 2: MONITORING-BASED MANAGEMENT
  "We collect data but struggle to use it for decisions."
  Some environmental monitoring exists (visitor counts, basic surveys).
  Data is collected but not systematically translated into management action.
  Reports are produced but rarely drive budget decisions.

Level 3: EVIDENCE-BASED MANAGEMENT
  "We make decisions based on quantitative evidence."
  Multi-year environmental data (satellite + field). Quantified EHS.
  Priority rankings exist. Budget allocations are evidence-linked.
  DCS awareness -- uncertainty is acknowledged.
  Still largely reactive at the territorial level.

Level 4: STRATEGIC TERRITORIAL INTELLIGENCE
  "We plan proactively across the whole destination portfolio."
  Territory-level analysis (TPI, TIS). Scenario planning (A-E).
  Counterfactual reasoning. Stakeholder-adapted communications.
  Investment is justified with clear expected outcomes.
  Evidence gates prevent wasteful capital deployment.

Level 5: PROACTIVE DESTINATION GOVERNANCE
  "We continuously optimise the destination for sustainability."
  Real-time or near-real-time monitoring. Dynamic resource allocation.
  Cross-territorial benchmarking. Predictive risk modelling.
  Integrated into budget planning cycles. EU/SISMOTUR-ready reporting.
  Institutional memory of intervention outcomes. Feedback loops.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaturityLevel:
    """Definition of one maturity level."""
    level: int
    name: str
    description: str
    capabilities: list    # what this level can do
    limitations: list     # what it cannot do
    advancement_path: str # how to reach the next level


MATURITY_LEVELS: dict[int, MaturityLevel] = {

    1: MaturityLevel(
        level=1, name="REACTIVE MANAGEMENT",
        description=(
            "The destination responds to environmental problems only when they become "
            "visually obvious or generate public complaints. Management is event-driven, "
            "not evidence-driven. No systematic data collection or analysis exists."
        ),
        capabilities=[
            "Field observation by ranger or management staff.",
            "Response to visitor complaints or media coverage.",
            "Ad hoc restoration when damage becomes extreme.",
        ],
        limitations=[
            "Cannot detect gradual degradation before it becomes critical.",
            "Cannot prioritise between multiple assets needing attention.",
            "Cannot justify investment decisions to governing authorities.",
            "Cannot communicate environmental value to tourism stakeholders.",
        ],
        advancement_path=(
            "Establish basic environmental monitoring: annual satellite analysis "
            "or standardised field surveys for each asset. Begin recording data "
            "systematically. First step toward Level 2."
        ),
    ),

    2: MaturityLevel(
        level=2, name="MONITORING-BASED MANAGEMENT",
        description=(
            "The destination collects environmental data but has not yet developed "
            "the capacity to translate it into systematic management decisions. "
            "Reports exist but they describe conditions rather than drive action."
        ),
        capabilities=[
            "Annual satellite or field-based environmental assessment.",
            "Environmental condition reports per asset.",
            "Basic trend identification (improving / deteriorating / stable).",
            "Visitor count data at some sites.",
        ],
        limitations=[
            "No standardised scoring to compare assets across the portfolio.",
            "Cannot quantify decision confidence (may act on unreliable data).",
            "Cannot attribute cause of change (climate vs. visitor pressure).",
            "Budget allocation remains political rather than evidence-based.",
        ],
        advancement_path=(
            "Adopt a standardised Environmental Health Score (EHS) framework. "
            "Implement multi-year time-series analysis. Add spatial causality "
            "classification (SCM) to separate climate from human pressure. "
            "This is the foundation of Level 3."
        ),
    ),

    3: MaturityLevel(
        level=3, name="EVIDENCE-BASED MANAGEMENT",
        description=(
            "The destination uses quantified environmental data to make and "
            "justify management decisions. Assets are scored, compared, and "
            "prioritised. Budget decisions are evidence-linked. "
            "Uncertainty is acknowledged through confidence metrics."
        ),
        capabilities=[
            "Environmental Health Score (EHS) per asset.",
            "Multi-year trend analysis with statistical confidence.",
            "Spatial causality classification (SCM): visitor vs. climate driver.",
            "Decision Confidence Score (DCS): evidence quality quantified.",
            "Priority ranking (TPI) for resource allocation.",
            "Budget allocation justified with evidence base.",
            "Alert system with defined response thresholds.",
        ],
        limitations=[
            "Portfolio-level analysis is limited -- still largely asset-by-asset.",
            "Scenario comparison (what happens if we intervene vs. not?) missing.",
            "Investment efficiency (TIS) not yet calculated.",
            "Communication to different stakeholders uses a single format.",
            "No cross-territorial benchmarking.",
        ],
        advancement_path=(
            "Add Phase 5-6 capabilities: Territorial Priority Index (TPI), "
            "Intervention Impact & Scenario Planning (TIS), Counterfactual Reasoning. "
            "Then add Phase 7 stakeholder intelligence. This unlocks Level 4."
        ),
    ),

    4: MaturityLevel(
        level=4, name="STRATEGIC TERRITORIAL INTELLIGENCE",
        description=(
            "The destination uses a fully integrated territorial intelligence "
            "platform that translates environmental data into strategic decisions "
            "for multiple stakeholder audiences. Investment is optimised for "
            "maximum territorial benefit per euro. Inaction costs are quantified."
        ),
        capabilities=[
            "Territory-level health score and portfolio view.",
            "Territorial Priority Index (TPI): rank all assets on one scale.",
            "Intervention scenario comparison (A-E) per asset.",
            "Territorial Impact Score (TIS): investment efficiency ranking.",
            "TIS-optimised budget allocation with transparent rules.",
            "Counterfactual reasoning: 3-year no-intervention trajectories.",
            "Stakeholder-adapted communications (5 audience profiles).",
            "Decision playbooks for standard management situations.",
            "Executive briefings at 1-page, 3-minute, 5-minute levels.",
            "Quarterly institutional reporting for governing authorities.",
        ],
        limitations=[
            "No real-time data integration (relies on periodic satellite analysis).",
            "No cross-territorial benchmarking (single territory at a time).",
            "No intervention outcome tracking (cannot yet validate predictions).",
            "No automated alert escalation -- requires human review cycle.",
        ],
        advancement_path=(
            "Integrate real-time visitor data (mobile signals, visitor counters). "
            "Build multi-territory benchmarking. Track intervention outcomes and "
            "update impact functions with observed results. Automate reporting and "
            "alert escalation pipelines. This completes the Level 5 transition."
        ),
    ),

    5: MaturityLevel(
        level=5, name="PROACTIVE DESTINATION GOVERNANCE",
        description=(
            "The destination operates as a continuously learning environmental "
            "intelligence system. Real-time data, automated alerts, dynamic resource "
            "allocation, and validated impact models create a closed feedback loop. "
            "The destination can demonstrate measurable sustainability outcomes to "
            "European frameworks (SISMOTUR, EUROPARC, Green Deal)."
        ),
        capabilities=[
            "All Level 4 capabilities, plus:",
            "Near-real-time satellite analysis (10-day Sentinel-2 cycle).",
            "Real-time visitor data integration (counters, mobile analytics).",
            "Dynamic visitor management (automatic capacity alerts).",
            "Automated quarterly reporting to SISMOTUR / EUROPARC.",
            "Cross-territorial benchmarking across multiple destinations.",
            "Validated impact models (predicted vs. observed restoration outcomes).",
            "Multi-year investment planning aligned with EU funding cycles.",
            "Institutional memory: intervention outcomes inform future decisions.",
        ],
        limitations=[
            "Requires significant IT infrastructure and data governance.",
            "Requires dedicated intelligence team for maintenance.",
            "Data sovereignty and privacy considerations for real-time visitor data.",
        ],
        advancement_path=(
            "Level 5 is the operational target. Maintenance at this level requires "
            "annual technology review, continuous staff development, and integration "
            "with national and European smart destination frameworks."
        ),
    ),
}


@dataclass(frozen=True)
class MaturityAssessment:
    """Result of assessing a territory's current maturity level."""
    territory_name: str
    current_level: int
    current_level_name: str
    current_level_description: str
    evidence_for_current_level: list    # what the territory already has
    gaps_vs_next_level: list           # what is missing for Level +1
    advancement_investment: str        # what is needed to advance
    strategic_recommendation: str


def assess_territory_maturity(
    territory_name: str,
    phases_implemented: list,          # list of phase numbers (e.g. [1,2,3,4,5,6,7])
    n_assets: int,
    pct_assets_with_dcs: float,        # % assets with meaningful DCS
    has_scenario_planning: bool,
    has_stakeholder_comms: bool,
    has_real_time_data: bool,
    has_multi_territory: bool,
) -> MaturityAssessment:
    """
    Determine the territory's maturity level based on implemented capabilities.
    """
    # Level determination logic
    if all(p in phases_implemented for p in [1, 2, 3, 4, 5, 6, 7]):
        if has_real_time_data and has_multi_territory:
            level = 5
        else:
            level = 4
    elif all(p in phases_implemented for p in [1, 2, 3, 4]):
        level = 3
    elif any(p in phases_implemented for p in [1, 2]):
        level = 2
    else:
        level = 1

    ml     = MATURITY_LEVELS[level]
    ml_up  = MATURITY_LEVELS.get(level + 1)

    # Evidence for current level
    evidence = []
    if 1 in phases_implemented:
        evidence.append("Multi-year Environmental Health Score (EHS) computed for all assets.")
    if 2 in phases_implemented:
        evidence.append("Temporal trend analysis (Mann-Kendall) with statistical confidence.")
    if 3 in phases_implemented:
        evidence.append("Risk Engine with 5-component risk assessment.")
    if 4 in phases_implemented:
        evidence.append("Spatial Causality Module (SCM) separating visitor from climate drivers.")
    if 5 in phases_implemented:
        evidence.append("Decision Confidence Score (DCS) quantifying evidence reliability.")
    if "TPI" in phases_implemented or 5 in phases_implemented:
        evidence.append("Territorial Priority Index (TPI) ranking all assets on one scale.")
    if 6 in phases_implemented:
        evidence.append("Intervention Scenario Planning (TIS) with 5-scenario comparison.")
        evidence.append("Counterfactual reasoning: 3-year no-intervention projections.")
    if 7 in phases_implemented:
        evidence.append("Stakeholder-adapted intelligence for 5 audience profiles.")
        evidence.append("Decision playbooks for standard management situations.")
        evidence.append("Executive briefings at 1-page, 3-minute, and 5-minute levels.")
    if has_real_time_data:
        evidence.append("Real-time visitor data integration.")
    if has_multi_territory:
        evidence.append("Cross-territorial benchmarking capability.")

    # Gaps vs. next level
    gaps = []
    if ml_up:
        if level == 3 and not has_scenario_planning:
            gaps.append("Intervention scenario comparison (TIS) not yet implemented.")
        if level == 3 and not has_stakeholder_comms:
            gaps.append("Stakeholder-adapted communications not yet implemented.")
        if level == 4 and not has_real_time_data:
            gaps.append("No real-time visitor data integration.")
        if level == 4 and not has_multi_territory:
            gaps.append("No cross-territorial benchmarking capability.")
        if level < 4:
            gaps.append("Territory-level portfolio analysis (TPI, TIS) not yet operational.")
        if level < 4:
            gaps.append("Investment efficiency optimisation (TIS budget) not yet in use.")

    # Advancement investment estimate
    if level == 3:
        adv_invest = (
            "EUR 15,000-25,000 for Phase 5-6 implementation + Phase 7 stakeholder "
            "communications layer. 3-month implementation timeline."
        )
    elif level == 4:
        adv_invest = (
            "EUR 40,000-80,000 for real-time data infrastructure (visitor counters, "
            "API integration). 6-12 months for multi-territory expansion."
        )
    else:
        adv_invest = (
            "EUR 50,000-120,000 annual platform maintenance and continuous improvement."
        )

    strategic = _strategic_recommendation(level, territory_name, n_assets)

    return MaturityAssessment(
        territory_name=territory_name,
        current_level=level,
        current_level_name=ml.name,
        current_level_description=ml.description,
        evidence_for_current_level=evidence,
        gaps_vs_next_level=gaps,
        advancement_investment=adv_invest,
        strategic_recommendation=strategic,
    )


def _strategic_recommendation(level: int, name: str, n_assets: int) -> str:
    if level >= 4:
        return (
            f"{name} has achieved Strategic Territorial Intelligence (Level 4). "
            "The platform is ready for institutional deployment and can support evidence-based "
            "governance at the provincial level. The next strategic investment should focus "
            "on real-time data integration and multi-territory expansion to reach Level 5."
        )
    if level == 3:
        return (
            f"{name} is at Evidence-Based Management (Level 3) -- a solid foundation. "
            "The priority investment to advance to Level 4 is the Territorial Intelligence "
            "and Scenario Planning layer (Phases 5-7): EUR 15,000-25,000 over 3 months. "
            "This will transform the system from an asset-level tool into a destination-level "
            "decision platform, unlocking substantially higher institutional value."
        )
    return (
        f"{name} is at Level {level}. The path to evidence-based governance requires "
        "systematic environmental monitoring investment across all {n_assets} assets. "
        "Begin with EHS computation (Phases 1-4) as the foundational step."
    )


def format_maturity_report(assessment: MaturityAssessment) -> list[str]:
    """Format a maturity assessment as report lines."""
    ml = MATURITY_LEVELS[assessment.current_level]
    next_ml = MATURITY_LEVELS.get(assessment.current_level + 1)

    lines = [
        f"CURRENT MATURITY LEVEL: {assessment.current_level} -- {assessment.current_level_name}",
        "",
        "WHAT THIS MEANS:",
        f"  {assessment.current_level_description}",
        "",
        "EVIDENCE THAT SUPPORTS THIS LEVEL:",
    ]
    for ev in assessment.evidence_for_current_level:
        lines.append(f"  [+] {ev}")

    if next_ml:
        lines += ["", f"GAPS VS. LEVEL {assessment.current_level + 1} ({next_ml.name}):"]
        if assessment.gaps_vs_next_level:
            for g in assessment.gaps_vs_next_level:
                lines.append(f"  [ ] {g}")
        else:
            lines.append("  No gaps identified -- ready to advance to next level.")
        lines += [
            "",
            f"ADVANCEMENT INVESTMENT ESTIMATE:",
            f"  {assessment.advancement_investment}",
        ]

    lines += [
        "",
        "STRATEGIC RECOMMENDATION:",
        f"  {assessment.strategic_recommendation}",
        "",
        "MATURITY SCALE REFERENCE:",
        "  Level 1: Reactive Management     -- respond to crises only",
        "  Level 2: Monitoring-Based        -- data collected but not used",
        "  Level 3: Evidence-Based          -- decisions linked to data",
        f"  Level 4: Strategic Intelligence  -- territorial optimisation",
        "  Level 5: Proactive Governance    -- continuous learning system",
        f"  >> CURRENT: Level {assessment.current_level}",
    ]
    return lines
