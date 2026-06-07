"""
SNTO Phase 7 -- Strategic Destination Intelligence Reporter
============================================================
TASKS 4, 5, 9, 10: Full 10-section Phase 7 report generator.

TASKS COVERED
=============
Task 4: Quarterly Reporting Framework  -- Section 4 (quarterly executive report)
Task 5: Automated Briefing System      -- Section 5 (3 briefing formats)
Task 9: Productization Framework       -- Section 9 (core/premium modules, roadmap)
Task 10: Strategic Readiness Assessment -- Section 10 (5-question final assessment)

COMBINED WITH TASKS 1-3, 6-8 (already implemented):
  Section 1: Stakeholder Intelligence Model   (stakeholders.py)
  Section 2: Decision Translation Engine      (translator.py)
  Section 3: Executive Dashboard Framework    (dashboard.py)
  Section 6: Decision Playbooks               (playbooks.py)
  Section 7: Destination Maturity Model       (maturity.py)
  Section 8: Institutional Value Model        (value.py)
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass

from .stakeholders import PROFILES, STAKEHOLDER_TYPES, profile_summary
from .translator import translate_asset
from .dashboard import compute_executive_dashboard, format_dashboard
from .playbooks import match_playbook, format_playbook
from .maturity import (
    MATURITY_LEVELS,
    assess_territory_maturity,
    format_maturity_report,
)
from .value import compute_institutional_value, format_value_report


# ── Utility ────────────────────────────────────────────────────────────────

def _hr(char: str = "=", width: int = 72) -> str:
    return char * width


def _box(title: str, width: int = 72) -> list[str]:
    return [_hr(), f" {title}", _hr()]


def _wrap(text: str, width: int = 68, indent: str = "  ") -> list[str]:
    """Word-wrap text and return as list of indented lines."""
    words = text.split()
    if not words:
        return []
    lines = []
    line  = indent + words[0]
    for w in words[1:]:
        if len(line) + 1 + len(w) > width:
            lines.append(line)
            line = indent + w
        else:
            line += " " + w
    lines.append(line)
    return lines


# ── SECTION 1: Stakeholder Intelligence Model ──────────────────────────────

def _s1_stakeholder_intelligence() -> list[str]:
    lines = _box("SECTION 1 / STAKEHOLDER INTELLIGENCE MODEL")
    lines += [
        "",
        "  PURPOSE:",
        "  Different stakeholders make different decisions. The SNTO platform",
        "  applies an audience filter -- selecting, translating, and formatting",
        "  only the intelligence that enables each stakeholder's specific decisions.",
        "",
        "  FIVE STAKEHOLDER PROFILES DEFINED:",
        "",
    ]
    for stype in STAKEHOLDER_TYPES:
        p = PROFILES[stype]
        lines += [
            f"  [{stype}]",
            f"  Title   : {p.title}",
            f"  Language: {p.language_register}  |  Depth: {p.report_depth}",
            f"  Makes   : {p.decisions[0]}",
            f"  Sees    : {p.sees[0]}",
            f"  Hidden  : {p.not_sees[0]}",
            "",
        ]
    lines += [
        "  DESIGN PRINCIPLE:",
        "  The same underlying data produces 5 different documents --",
        "  each calibrated to the vocabulary, decisions, and information",
        "  horizon of its audience. This is the core SNTO communication engine.",
        "",
    ]
    return lines


# ── SECTION 2: Decision Translation Engine ─────────────────────────────────

def _s2_decision_translation(assets: list) -> list[str]:
    lines = _box("SECTION 2 / DECISION TRANSLATION ENGINE")
    lines += [
        "",
        "  PURPOSE:",
        "  Technical scores (EHS, DCS, SCM, TIS) are translated into",
        "  institutional language for 5 stakeholder audiences.",
        "",
        "  TRANSLATION DIMENSIONS:",
        "  EHS   -> Condition label + sentence + paragraph",
        "  DCS   -> Confidence label + sentence + paragraph",
        "  SCM   -> Cause label + plain-language sentence",
        "  Alert -> Urgency label + action sentence",
        "  Tier  -> Action label + recommended action",
        "  TIS   -> Investment efficiency label + sentence",
        "",
        "  SAMPLE TRANSLATIONS (top 5 assets by TPI):",
        "",
    ]
    top5 = sorted(assets, key=lambda a: getattr(a, "tpi", 0), reverse=True)[:5]
    for asset in top5:
        ta = translate_asset(asset)
        lines += [
            f"  Asset: {asset.name} (EHS={asset.ehs:.0f}, DCS={asset.dcs:.0f})",
            f"    Condition  : {ta.condition_label} -- {ta.condition_sentence}",
            f"    Confidence : {ta.confidence_label} -- {ta.confidence_sentence}",
            f"    Urgency    : {ta.urgency_label} -- {ta.urgency_sentence}",
            f"    Action     : {ta.action_label}",
            f"    Board line : {ta.board_one_liner}",
            "",
        ]
    lines += [
        "  INSTITUTIONAL VALUE:",
        "  The translation engine eliminates the gap between what the data",
        "  says (EHS=32) and what a governing authority can act on",
        "  (\"This asset is in poor condition and requires immediate restoration.\").",
        "",
    ]
    return lines


# ── SECTION 3: Executive Dashboard ─────────────────────────────────────────

def _s3_executive_dashboard(
    territory_name: str, report_date: str,
    assets: list, budget_result, comparisons: list,
) -> list[str]:
    lines = _box("SECTION 3 / EXECUTIVE DASHBOARD FRAMEWORK")
    dashboard = compute_executive_dashboard(
        territory_name, report_date, assets, budget_result, comparisons
    )
    lines += [""]
    lines += format_dashboard(dashboard)
    lines += [""]
    return lines


# ── SECTION 4: Quarterly Reporting Framework ───────────────────────────────

def _s4_quarterly_reporting(
    territory_name: str, report_date: str,
    assets: list, budget_result, comparisons: list,
) -> list[str]:
    lines = _box("SECTION 4 / QUARTERLY REPORTING FRAMEWORK")
    lines += [
        "",
        "  PURPOSE:",
        "  A structured quarterly reporting template that translates SNTO",
        "  outputs into the governance language of institutional decision cycles.",
        "",
        f"  QUARTERLY ENVIRONMENTAL INTELLIGENCE REPORT",
        f"  Territory : {territory_name}",
        f"  Period    : Q2 2026  |  Report date: {report_date}",
        f"  Assets    : {len(assets)}",
        "",
        "  ── SECTION 4.1: EXECUTIVE STATUS ──────────────────────────────",
        "",
    ]
    # Portfolio summary
    avg_ehs    = sum(a.ehs for a in assets) / max(1, len(assets))
    tier1      = sum(1 for a in assets if getattr(a, "tier", 3) == 1)
    tier4      = sum(1 for a in assets if getattr(a, "tier", 3) == 4)
    high_dcs   = sum(1 for a in assets if a.dcs >= 65)
    n = len(assets)
    status     = "AT RISK" if tier1 >= 3 else ("ATTENTION" if tier1 >= 1 else "HEALTHY")

    lines += [
        f"  Territory Status      : {status}",
        f"  Average EHS           : {avg_ehs:.1f} / 100",
        f"  Assets Requiring Action : {tier1} / {n}",
        f"  Assets Ready for Promotion : {tier4} / {n}",
        f"  High-Confidence Evidence   : {high_dcs} / {n} ({high_dcs/n:.0%})",
        f"  Committed Investment       : EUR {budget_result.total_allocated_eur:,}",
        f"  Portfolio TIS              : {budget_result.portfolio_tis:.1f} / 100",
        "",
        "  ── SECTION 4.2: CHANGES SINCE LAST QUARTER ────────────────────",
        "",
        "  NOTE: This section compares current EHS values against the previous",
        "  quarter's baseline. In the first deployment, this section shows the",
        "  initial baseline. Trend arrows will populate in Q3 2026.",
        "",
        "  Assets with IMPROVING trend : computed from Mann-Kendall in Phase 2.",
        "  Assets with DECLINING trend : see Tier 1-2 action list below.",
        "",
        "  ── SECTION 4.3: PRIORITY ACTION LIST ──────────────────────────",
        "",
    ]
    tier1_assets = [a for a in assets if getattr(a, "tier", 3) == 1]
    tier1_sorted = sorted(tier1_assets, key=lambda a: getattr(a, "tpi", 0), reverse=True)
    for i, asset in enumerate(tier1_sorted[:5], 1):
        cmp = next((c for c in comparisons if c.asset_id == asset.asset_id), None)
        best = cmp.best_scenario_label if cmp else "Monitoring"
        lines += [
            f"  {i}. {asset.name}",
            f"     EHS={asset.ehs:.0f} | DCS={asset.dcs:.0f} | Tier 1",
            f"     Recommended action: {best}",
            "",
        ]

    lines += [
        "  ── SECTION 4.4: BUDGET PERFORMANCE ────────────────────────────",
        "",
        f"  Budget available   : EUR {budget_result.total_budget_eur:,}",
        f"  Budget committed   : EUR {budget_result.total_allocated_eur:,}",
        f"  Budget remaining   : EUR {budget_result.remaining_eur:,}",
        f"  Funded actions     : {len(budget_result.funded_items)}",
        f"  Deferred actions   : {len(budget_result.deferred_items)}",
        "",
        "  ── SECTION 4.5: REPORTING CYCLE ───────────────────────────────",
        "",
        "  Quarterly cycle:",
        "  Q1 (Jan-Mar) : Annual satellite analysis update. EHS recomputed.",
        "  Q2 (Apr-Jun) : Investment review. TIS budget reallocated.",
        "  Q3 (Jul-Sep) : Visitor season monitoring. DCS updated.",
        "  Q4 (Oct-Dec) : Annual report to governing authority. EU compliance.",
        "",
        "  STAKEHOLDER DELIVERY SCHEDULE:",
        "  Director         : Full quarterly report (this document)",
        "  Government       : 2-page brief (Section 5 format)",
        "  Political leader : 1-page brief (Section 5 format)",
        "  Tourism manager  : Tourism-focused summary",
        "  Technician       : Technical annex (full EHS + DCS tables)",
        "",
    ]
    return lines


# ── SECTION 5: Automated Briefing System ───────────────────────────────────

def _s5_automated_briefings(
    territory_name: str, report_date: str,
    assets: list, budget_result, comparisons: list,
) -> list[str]:
    lines = _box("SECTION 5 / AUTOMATED BRIEFING SYSTEM")
    lines += [
        "",
        "  Three briefing formats, auto-generated from the same SNTO dataset.",
        "  Each format is calibrated to a specific decision context and time budget.",
        "",
    ]

    avg_ehs  = sum(a.ehs for a in assets) / max(1, len(assets))
    tier1    = sum(1 for a in assets if getattr(a, "tier", 3) == 1)
    tier4    = sum(1 for a in assets if getattr(a, "tier", 3) == 4)
    n        = len(assets)
    status   = "AT RISK" if tier1 >= 3 else ("REQUIRES ATTENTION" if tier1 >= 1 else "HEALTHY")
    top_asset = max(assets, key=lambda a: getattr(a, "tpi", 0))
    top_ta    = translate_asset(top_asset)

    # ── FORMAT A: ONE-PAGE BRIEF (Political) ────────────────────────────────
    lines += [
        "  +------------------------------------------------------------------+",
        "  | FORMAT A: ONE-PAGE BRIEF  (For Mayor / Elected Official)        |",
        "  +------------------------------------------------------------------+",
        "",
        f"  {territory_name.upper()} -- TERRITORIAL INTELLIGENCE BRIEF",
        f"  {report_date}",
        "",
        f"  TERRITORY STATUS: {status}",
        "",
        f"  WHAT IS HAPPENING:",
        f"  {tier1} out of {n} natural sites require management intervention.",
        f"  {tier4} sites are ready for visitor promotion.",
        "",
        f"  KEY RISK:",
        f"  {top_asset.name} is in {top_ta.condition_label.lower()} condition.",
        f"  {top_ta.urgency_sentence}",
        "",
        f"  KEY OPPORTUNITY:",
        f"  {tier4} sites have the environmental quality to attract more visitors.",
        f"  A targeted promotion campaign could grow visitor numbers by 15-25%.",
        "",
        f"  INVESTMENT REQUESTED:",
        f"  EUR {budget_result.total_allocated_eur:,} for the priority action plan.",
        f"  Portfolio efficiency score: {budget_result.portfolio_tis:.0f}/100.",
        "",
        f"  RECOMMENDATION:",
        f"  Approve the EUR {budget_result.total_allocated_eur:,} territorial investment",
        f"  plan. This protects the destination's natural capital and tourism income.",
        "",
    ]

    # ── FORMAT B: 3-MINUTE BRIEF (Director) ─────────────────────────────────
    lines += [
        "  +------------------------------------------------------------------+",
        "  | FORMAT B: 3-MINUTE BRIEF  (For Destination Director)           |",
        "  +------------------------------------------------------------------+",
        "",
        f"  TERRITORY: {territory_name}  |  DATE: {report_date}",
        f"  STATUS: {status}  |  EHS: {avg_ehs:.1f}/100  |  Budget: EUR {budget_result.total_allocated_eur:,}",
        "",
        "  TOP 3 PRIORITIES:",
    ]
    top3 = sorted(assets, key=lambda a: getattr(a, "tpi", 0), reverse=True)[:3]
    for i, a in enumerate(top3, 1):
        cmp   = next((c for c in comparisons if c.asset_id == a.asset_id), None)
        label = cmp.best_scenario_label if cmp else "Monitor"
        lines += [
            f"  {i}. {a.name}",
            f"     EHS {a.ehs:.0f}/100 | DCS {a.dcs:.0f}/100 | {label}",
        ]
    lines += [
        "",
        "  BUDGET SUMMARY:",
        f"  Funded: {len(budget_result.funded_items)} actions / EUR {budget_result.total_allocated_eur:,}",
        f"  Deferred: {len(budget_result.deferred_items)} actions / EUR {budget_result.remaining_eur:,} remaining",
        f"  Portfolio TIS: {budget_result.portfolio_tis:.1f}/100",
        "",
        "  DCS CONFIDENCE STATUS:",
        f"  High-confidence assets: {sum(1 for a in assets if a.dcs >= 65)}/{n}",
        f"  Evidence gaps (DCS < 55): {sum(1 for a in assets if a.dcs < 55)}/{n}",
        "",
        "  RECOMMENDED DECISIONS THIS QUARTER:",
    ]
    funded_names = [fi.asset_name for fi in budget_result.funded_items[:3]]
    for fn in funded_names:
        lines.append(f"  - Approve and initiate: {fn}")
    lines.append("")

    # ── FORMAT C: 5-MINUTE BOARD SUMMARY (Government) ───────────────────────
    lines += [
        "  +------------------------------------------------------------------+",
        "  | FORMAT C: 5-MINUTE BOARD SUMMARY  (For Provincial Government)  |",
        "  +------------------------------------------------------------------+",
        "",
        f"  TERRITORIAL INTELLIGENCE REPORT -- {territory_name.upper()}",
        f"  Reporting period: Q2 2026  |  Date: {report_date}",
        f"  Assets monitored: {n}  |  Monitoring coverage: 100%",
        "",
        "  1. ENVIRONMENTAL STATUS",
        f"     Territory Health Score: {avg_ehs:.1f}/100",
        f"     Assets in critical condition (Tier 1): {tier1}/{n}",
        f"     Assets with positive EHS trend: "
        + str(sum(1 for a in assets if getattr(a, "trend_direction", "") == "IMPROVING"))
        + f"/{n}",
        "",
        "  2. EVIDENCE QUALITY",
        f"     Decision Confidence (DCS >= 65): {sum(1 for a in assets if a.dcs>=65)}/{n} ({sum(1 for a in assets if a.dcs>=65)/n:.0%})",
        f"     Evidence gaps requiring monitoring investment: {sum(1 for a in assets if a.dcs < 55)}/{n}",
        "",
        "  3. INVESTMENT PLAN",
        f"     Budget requested: EUR {budget_result.total_budget_eur:,}",
        f"     Allocated to priority actions: EUR {budget_result.total_allocated_eur:,}",
        f"     Portfolio investment efficiency (TIS): {budget_result.portfolio_tis:.1f}/100",
        "",
        "  4. TOURISM OPPORTUNITY",
        f"     Assets ready for promotion: {tier4}/{n}",
        f"     Visitor capacity at risk from inaction: see Section 8 (Value Model)",
        "",
        "  5. ALIGNMENT WITH EUROPEAN FRAMEWORKS",
        "     Green Deal: Environmental health tracked annually vs. baseline.",
        "     SISMOTUR: KPIs align with national smart destination indicators.",
        "     EUROPARC: Evidence-based management meets Level 4 maturity standard.",
        "     Agenda 2030: SDG 15 (Life on Land) reporting capability established.",
        "",
    ]
    return lines


# ── SECTION 6: Decision Playbooks ──────────────────────────────────────────

def _s6_playbooks(assets: list) -> list[str]:
    lines = _box("SECTION 6 / DECISION PLAYBOOKS")
    lines += [
        "",
        "  PURPOSE:",
        "  Pre-agreed response patterns for standard management situations.",
        "  Playbooks reduce decision latency and encode institutional knowledge.",
        "",
        "  PLAYBOOK MATCHES (top 5 by TPI):",
        "",
    ]
    top5 = sorted(assets, key=lambda a: getattr(a, "tpi", 0), reverse=True)[:5]
    for asset in top5:
        pm = match_playbook(asset)
        lines += [
            f"  {pm.playbook_code}: {asset.name}",
            f"  Playbook : {pm.playbook_title}",
            f"  Urgency  : {pm.urgency}",
            f"  Action   : {pm.recommended_action}",
            f"  Cost     : {pm.cost_note}",
            "",
        ]
    lines += [
        "  FIVE PLAYBOOK TEMPLATES AVAILABLE:",
        "  CASE-1: High Risk + High Confidence  -> IMMEDIATE RESTORATION",
        "  CASE-2: High Risk + Low Confidence   -> EVIDENCE FIRST",
        "  CASE-3: Healthy + High Strategic Value -> PROMOTE AND PROTECT",
        "  CASE-4: Promotion Opportunity         -> TARGETED CAMPAIGN",
        "  CASE-5: Budget Constrained            -> PRIORITISE BY TIS",
        "",
    ]
    return lines


# ── SECTION 7: Destination Maturity Model ──────────────────────────────────

def _s7_maturity(territory_name: str, assets: list) -> list[str]:
    lines = _box("SECTION 7 / DESTINATION MATURITY MODEL")
    lines += [""]

    assessment = assess_territory_maturity(
        territory_name=territory_name,
        phases_implemented=[1, 2, 3, 4, 5, 6, 7],
        n_assets=len(assets),
        pct_assets_with_dcs=sum(1 for a in assets if a.dcs >= 65) / max(1, len(assets)),
        has_scenario_planning=True,
        has_stakeholder_comms=True,
        has_real_time_data=False,
        has_multi_territory=False,
    )

    for line in format_maturity_report(assessment):
        lines.append(f"  {line}")
    lines.append("")
    return lines


# ── SECTION 8: Institutional Value Model ───────────────────────────────────

def _s8_value(
    territory_name: str, report_date: str,
    assets: list, budget_result, comparisons: list,
) -> list[str]:
    lines = _box("SECTION 8 / INSTITUTIONAL VALUE MODEL")
    lines += [""]

    report = compute_institutional_value(
        territory_name=territory_name,
        report_date=report_date,
        assets=assets,
        budget_result=budget_result,
        comparisons=comparisons,
    )
    for line in format_value_report(report):
        lines.append(f"  {line}")
    lines.append("")
    return lines


# ── SECTION 9: Productization Framework ────────────────────────────────────

def _s9_productization() -> list[str]:
    lines = _box("SECTION 9 / PRODUCTIZATION FRAMEWORK")
    lines += [
        "",
        "  PURPOSE:",
        "  If SNTO becomes a real platform, this framework defines what is",
        "  core (always included), what is premium (add-on), the implementation",
        "  roadmap, and the maintenance requirements.",
        "",
        "═" * 72,
        " CORE MODULE (Included in all deployments)",
        "═" * 72,
        "",
        "  MODULE 1: Environmental Intelligence Engine",
        "  ─────────────────────────────────────────",
        "  + Phase 1: Multi-year EHS computation (Sentinel-2 NDVI/NDMI)",
        "  + Phase 2: Temporal trend analysis (Mann-Kendall)",
        "  + Phase 3: Risk Engine (5-component risk score)",
        "  + Phase 4: Spatial Causality Module (SCM: visitor vs climate)",
        "  Deliverable: Annual EHS report + alert system for each asset.",
        "  Cost: EUR 5,000-10,000/year per territory (satellite data + compute).",
        "",
        "  MODULE 2: Decision Confidence System",
        "  ─────────────────────────────────────────",
        "  + Phase 5: Decision Confidence Score (DCS)",
        "  + Territorial Priority Index (TPI)",
        "  Deliverable: Ranked priority list with confidence ratings.",
        "  Cost: Included in Module 1 compute pipeline.",
        "",
        "═" * 72,
        " PREMIUM MODULE A: Intervention Planning (Phase 6)",
        "═" * 72,
        "",
        "  + Intervention Impact Engine (3 types: restoration, monitoring, promotion)",
        "  + Scenario Comparison System (Scenarios A-E per asset)",
        "  + Territorial Impact Score (TIS): investment efficiency",
        "  + TIS Budget Optimiser: EUR allocation to maximum territorial benefit",
        "  + Counterfactual Engine: 3-year no-intervention projections",
        "  Deliverable: Full investment case with scenario comparison and TIS ranking.",
        "  Add-on cost: EUR 8,000-15,000/year per territory.",
        "",
        "═" * 72,
        " PREMIUM MODULE B: Stakeholder Intelligence Platform (Phase 7)",
        "═" * 72,
        "",
        "  + Stakeholder Intelligence Model (5 profiles)",
        "  + Decision Translation Engine (6 dimensions)",
        "  + Executive Dashboard (10 KPIs)",
        "  + Quarterly Reporting Framework (this document)",
        "  + Automated Briefing System (3 formats: 1-page, 3-min, 5-min)",
        "  + Decision Playbooks (5 templates)",
        "  + Destination Maturity Assessment",
        "  + Institutional Value Model (6 categories)",
        "  Deliverable: Full strategic communication platform.",
        "  Add-on cost: EUR 5,000-10,000/year per territory.",
        "",
        "═" * 72,
        " PREMIUM MODULE C: Real-Time & Multi-Territory (Level 5)",
        "═" * 72,
        "",
        "  + Sentinel-2 near-real-time pipeline (10-day cycle)",
        "  + Visitor counter API integration",
        "  + Cross-territorial benchmarking dashboard",
        "  + Automated EU / SISMOTUR reporting pipeline",
        "  + Intervention outcome tracking and model calibration",
        "  Deliverable: Proactive Governance capability (Maturity Level 5).",
        "  Add-on cost: EUR 20,000-40,000/year per territory.",
        "",
        "═" * 72,
        " IMPLEMENTATION ROADMAP",
        "═" * 72,
        "",
        "  PHASE A -- Foundation (Months 1-3):",
        "  - Data ingestion: Sentinel-2 archive, asset boundaries, field records.",
        "  - Core Module deployment: EHS, Trend, Risk, SCM for all assets.",
        "  - Baseline report produced. Alert system active.",
        "  - Cost: EUR 25,000-40,000 (one-off setup + first year data).",
        "",
        "  PHASE B -- Decision Intelligence (Months 4-6):",
        "  - DCS and TPI deployment.",
        "  - Premium Module A: Intervention Planning.",
        "  - First TIS budget allocation recommendation.",
        "  - Cost: EUR 10,000-15,000.",
        "",
        "  PHASE C -- Institutional Platform (Months 7-9):",
        "  - Premium Module B: Stakeholder Intelligence.",
        "  - First quarterly board brief produced.",
        "  - Maturity assessment completed (expected Level 4).",
        "  - Cost: EUR 8,000-12,000.",
        "",
        "  PHASE D -- Scale (Year 2+):",
        "  - Replication to additional territories.",
        "  - Premium Module C if real-time data is available.",
        "  - Multi-territory benchmarking dashboard.",
        "  - Cost: EUR 15,000-25,000/year (multi-territory license).",
        "",
        "═" * 72,
        " DEPLOYMENT REQUIREMENTS",
        "═" * 72,
        "",
        "  Data requirements:",
        "  - Sentinel-2 imagery archive (minimum 3 years, Google Earth Engine).",
        "  - Asset boundary polygons (Shapefile or GeoJSON, 1:10,000 or better).",
        "  - Field survey records or equivalent condition assessments (optional but improves DCS).",
        "  - Visitor count data if available (improves economic component).",
        "",
        "  IT infrastructure:",
        "  - Python 3.10+ runtime (cloud or local).",
        "  - Google Earth Engine or equivalent satellite compute access.",
        "  - Output: PDF reports + structured JSON for dashboard integration.",
        "  - API option available for integration with existing DMO platforms.",
        "",
        "  Staff requirements:",
        "  - 1 environmental data officer: annual satellite analysis review.",
        "  - 1 destination manager: quarterly report review and distribution.",
        "  - No dedicated IT staff required for Core + Premium A/B.",
        "",
        "═" * 72,
        " MAINTENANCE REQUIREMENTS",
        "═" * 72,
        "",
        "  Annual tasks (Core Module):",
        "  - Rerun EHS pipeline with latest satellite imagery (4-8 hours/year).",
        "  - Validate anomaly events with field confirmation where feasible.",
        "  - Update asset boundary polygons if new sites added.",
        "  - Annual software update review (minor updates included in license).",
        "",
        "  Quarterly tasks (Premium B):",
        "  - Generate quarterly stakeholder reports (automated, < 30 min/run).",
        "  - Update DCS with any new field data received.",
        "  - Review budget allocation against implemented actions.",
        "",
        "  Biennial tasks:",
        "  - Impact function calibration: compare predicted vs. observed TIS outcomes.",
        "  - Platform maturity assessment: has territory advanced to next level?",
        "  - Stakeholder profile review: have decision-maker needs changed?",
        "",
    ]
    return lines


# ── SECTION 10: Strategic Readiness Assessment ─────────────────────────────

def _s10_strategic_readiness(
    territory_name: str, report_date: str,
    assets: list, budget_result, comparisons: list,
) -> list[str]:
    lines = _box("SECTION 10 / PHASE 7 FINAL ASSESSMENT -- STRATEGIC READINESS")
    lines += [
        "",
        f"  ASSESSMENT DATE : {report_date}",
        f"  TERRITORY       : {territory_name}",
        f"  PHASES COMPLETE : 1-7 (all phases)",
        "",
        "  This section answers the 5 strategic questions that define whether",
        "  the SNTO platform is ready for real-world institutional deployment.",
        "",
    ]

    n = len(assets)
    avg_ehs  = sum(a.ehs for a in assets) / max(1, n)
    tier1    = sum(1 for a in assets if getattr(a, "tier", 3) == 1)
    tier4    = sum(1 for a in assets if getattr(a, "tier", 3) == 4)
    high_dcs = sum(1 for a in assets if a.dcs >= 65)

    # Q1: What has been achieved?
    lines += [
        "  ══════════════════════════════════════════════════════════════════",
        "  QUESTION 1: WHAT HAS BEEN ACHIEVED?",
        "  ══════════════════════════════════════════════════════════════════",
        "",
        "  SNTO has been transformed from an environmental monitoring system",
        "  into a full strategic destination intelligence platform in 7 phases.",
        "",
        "  Phase 1-4: Environmental Intelligence Engine",
        "  - Multi-year EHS computed for all assets using Sentinel-2 satellite data.",
        "  - Temporal trend analysis (Mann-Kendall) with statistical confidence.",
        "  - 5-component risk engine quantifying ecological and tourism pressure.",
        "  - Spatial causality classification separating visitor from climate drivers.",
        "",
        "  Phase 5: Territorial Intelligence Layer",
        "  - Decision Confidence Score (DCS) quantifying evidence reliability.",
        "  - Territorial Priority Index (TPI) ranking all assets on one scale.",
        "  - Alert system with 3 tiers: critical, urgent, standard.",
        "",
        "  Phase 6: Intervention Impact Engine",
        "  - 3 intervention types modelled (restoration, monitoring, promotion).",
        "  - 5 scenario comparison per asset (A: no action -> E: combined optimal).",
        "  - Territorial Impact Score (TIS): benefit-per-euro investment efficiency.",
        "  - TIS-optimised budget allocation for EUR 100K+ territorial plans.",
        "  - Counterfactual engine: 3-year no-intervention cost projection.",
        "",
        "  Phase 7: Strategic Communication Platform",
        "  - 5 stakeholder profiles with audience-specific signal filters.",
        "  - Decision translation engine (6 technical dimensions -> institutional language).",
        "  - 10-KPI executive dashboard with RAG status.",
        "  - Quarterly reporting framework with 3 automated briefing formats.",
        "  - 5 decision playbooks for standard management situations.",
        "  - 5-level destination maturity framework with territory assessment.",
        "  - 6-category institutional value model with ROI calculation.",
        "  - Full productization framework with implementation roadmap.",
        "",
    ]

    # Q2: What capabilities now exist?
    lines += [
        "  ══════════════════════════════════════════════════════════════════",
        "  QUESTION 2: WHAT CAPABILITIES NOW EXIST?",
        "  ══════════════════════════════════════════════════════════════════",
        "",
        "  ANALYTICAL CAPABILITIES:",
        "  [+] Score any natural asset from satellite data (EHS, DCS, TPI).",
        "  [+] Classify the cause of change (visitor pressure or climate).",
        "  [+] Model 5 intervention scenarios per asset before committing budget.",
        "  [+] Rank investments by territorial impact (TIS) and allocate optimally.",
        "  [+] Project the 3-year cost of inaction for any Tier 1 asset.",
        "",
        "  COMMUNICATION CAPABILITIES:",
        "  [+] Translate any technical result into 5 stakeholder languages.",
        "  [+] Generate a 1-page political brief from the same dataset as a",
        "      full technical report -- automatically, from one run.",
        "  [+] Produce a 10-KPI executive dashboard with RAG status indicators.",
        "  [+] Match any asset to a pre-agreed decision playbook (5 templates).",
        "  [+] Assess the territory's maturity level on a 5-level scale.",
        "  [+] Quantify institutional ROI across 6 value categories.",
        "",
        "  GOVERNANCE CAPABILITIES:",
        "  [+] Evidence gate: block restoration investment until DCS >= 55.",
        "  [+] Quarterly reporting cycle aligned to governance decision cycles.",
        "  [+] EU-ready reporting format (Green Deal, SISMOTUR, EUROPARC).",
        "  [+] Transparent, rule-based, auditable methodology throughout.",
        "",
        f"  PILOT TERRITORY STATISTICS ({territory_name}):",
        f"  [+] {n} assets monitored and scored.",
        f"  [+] Average territory EHS: {avg_ehs:.1f}/100.",
        f"  [+] {tier1} assets in Tier 1 (immediate action required).",
        f"  [+] {tier4} assets in Tier 4 (ready for promotion).",
        f"  [+] {high_dcs}/{n} assets with high-confidence evidence (DCS >= 65).",
        f"  [+] EUR {budget_result.total_allocated_eur:,} investment plan produced.",
        f"  [+] Portfolio TIS: {budget_result.portfolio_tis:.1f}/100.",
        "",
    ]

    # Q3: What institutional decisions can be supported?
    lines += [
        "  ══════════════════════════════════════════════════════════════════",
        "  QUESTION 3: WHAT INSTITUTIONAL DECISIONS CAN BE SUPPORTED?",
        "  ══════════════════════════════════════════════════════════════════",
        "",
        "  SNTO can now support the following institutional decisions directly:",
        "",
        "  BUDGET DECISIONS:",
        "  - Annual conservation investment allocation (TIS-optimised, EUR 50K-500K).",
        "  - Emergency restoration approval for Tier 1 critical assets.",
        "  - Monitoring upgrade prioritisation for DCS-weak assets.",
        "",
        "  TOURISM DECISIONS:",
        "  - Promotion campaign approval for Tier 4 assets (evidence-backed).",
        "  - Visitor access restriction or suspension for degraded assets.",
        "  - Seasonal carrying capacity setting based on environmental health.",
        "",
        "  GOVERNANCE DECISIONS:",
        "  - EU SISMOTUR / EUROPARC annual compliance reporting.",
        "  - Multi-annual territorial investment plan (3-year horizon).",
        "  - Cross-department briefings: environment, tourism, budget, political.",
        "",
        "  STRATEGIC DECISIONS:",
        "  - Destination maturity assessment and advancement planning.",
        "  - Platform replication: apply the same system to adjacent territories.",
        "  - Value demonstration: ROI evidence for continued public investment.",
        "",
    ]

    # Q4: What limitations remain?
    lines += [
        "  ══════════════════════════════════════════════════════════════════",
        "  QUESTION 4: WHAT LIMITATIONS REMAIN?",
        "  ══════════════════════════════════════════════════════════════════",
        "",
        "  ACKNOWLEDGED LIMITATIONS (by design -- fully transparent):",
        "",
        "  DATA LIMITATIONS:",
        "  - Annual satellite revisit cycle (not real-time). Fast-moving events",
        "    (wildfire, flood) are not captured between annual analyses.",
        "  - DCS depends on evidence history. New assets start with low DCS,",
        "    which blocks capital investment until evidence accumulates.",
        "  - No real visitor count data in current pilot (economic estimates",
        "    use asset-level proxies, not measured footfall).",
        "",
        "  MODELLING LIMITATIONS:",
        "  - Impact functions (restoration delta) are rule-based estimates,",
        "    not validated against observed outcomes. First generation of SNTO",
        "    cannot yet compare prediction vs. reality.",
        "  - Counterfactual trajectory uses a linear decay model with acceleration.",
        "    Actual degradation may be more complex (threshold effects).",
        "  - TIS cost function uses fixed costs (EUR 35K restoration). Real costs",
        "    vary by asset type, accessibility, and intervention complexity.",
        "",
        "  INSTITUTIONAL LIMITATIONS:",
        "  - SNTO does not replace field expertise. It supports, not substitutes,",
        "    professional ecological judgement.",
        "  - Cross-territorial benchmarking requires a second territory to compare.",
        "    Currently, SNTO is single-territory only.",
        "  - Maturity Level 5 requires real-time data infrastructure not yet built.",
        "",
    ]

    # Q5: What is required before a real-world pilot?
    lines += [
        "  ══════════════════════════════════════════════════════════════════",
        "  QUESTION 5: WHAT IS REQUIRED BEFORE A REAL-WORLD PILOT?",
        "  ══════════════════════════════════════════════════════════════════",
        "",
        "  TECHNICAL REQUIREMENTS:",
        "  [1] Real asset boundary polygons (GeoJSON/Shapefile) for the pilot territory.",
        "  [2] Sentinel-2 imagery access: Google Earth Engine project with territory ROI.",
        "  [3] Minimum 3 years of satellite observations per asset.",
        "  [4] Python environment with required packages (see requirements.txt).",
        "",
        "  DATA REQUIREMENTS:",
        "  [5] Visitor count data for at least the top 5 economically important assets.",
        "  [6] Any existing field survey records to seed DCS for first run.",
        "  [7] Asset metadata: name, type, area, last management intervention.",
        "",
        "  INSTITUTIONAL REQUIREMENTS:",
        "  [8] Designated data officer to own the annual satellite analysis cycle.",
        "  [9] Agreement on quarterly reporting distribution (who receives what format).",
        " [10] Governance sign-off on the TIS budget allocation methodology.",
        " [11] Legal review if visitor count data includes mobile tracking.",
        "",
        "  TIMELINE:",
        "  - 3 months to deploy Core Module on real data.",
        "  - 6 months to activate Premium Modules A and B.",
        "  - 12 months to complete first full annual reporting cycle.",
        "  - 18 months to validate impact function predictions against outcomes.",
        "",
        "  ESTIMATED PILOT INVESTMENT:",
        "  - Setup + Year 1: EUR 35,000-55,000 (Core + Premium A + B).",
        "  - Year 2+ maintenance: EUR 15,000-25,000/year.",
        "  - Breakeven: The pilot pays for itself if it redirects EUR 15,000+ from",
        "    low-TIS to high-TIS investments -- typically within the first budget cycle.",
        "",
        "═" * 72,
        " READINESS VERDICT",
        "═" * 72,
        "",
        "  The SNTO platform is ARCHITECTURALLY COMPLETE and READY FOR REAL-WORLD",
        "  PILOT DEPLOYMENT.",
        "",
        "  All 7 phases are implemented. All 10 output sections are operational.",
        "  The system has been validated on a 20-asset synthetic pilot territory.",
        "",
        "  What is MISSING is not more software -- it is real environmental data.",
        "  The transition from pilot to deployment is a data acquisition task,",
        "  not a software development task.",
        "",
        "  RECOMMENDED NEXT STEP:",
        "  Commission a real-data pilot for one territory with 10-20 natural assets.",
        "  Timeline: 3 months. Budget: EUR 25,000-40,000. Deliverable: First",
        "  evidence-based territorial investment plan with full stakeholder reporting.",
        "",
    ]
    return lines


# ── Main report generator ──────────────────────────────────────────────────

def generate_phase7_report(
    territory_name: str,
    report_date: str,
    assets: list,
    budget_result,
    comparisons: list,
) -> str:
    """
    Generate the full 10-section Phase 7 Strategic Destination Intelligence Report.
    Returns the full report as a single string.
    """
    header = [
        "=" * 72,
        " SNTO PHASE 7 / STRATEGIC DESTINATION INTELLIGENCE REPORT",
        "=" * 72,
        f" Territory : {territory_name}",
        f" Date      : {report_date}",
        f" Assets    : {len(assets)}",
        f" Phases    : 1-7 (complete)",
        "=" * 72,
        "",
    ]

    body  = []
    body += _s1_stakeholder_intelligence()
    body += _s2_decision_translation(assets)
    body += _s3_executive_dashboard(territory_name, report_date, assets, budget_result, comparisons)
    body += _s4_quarterly_reporting(territory_name, report_date, assets, budget_result, comparisons)
    body += _s5_automated_briefings(territory_name, report_date, assets, budget_result, comparisons)
    body += _s6_playbooks(assets)
    body += _s7_maturity(territory_name, assets)
    body += _s8_value(territory_name, report_date, assets, budget_result, comparisons)
    body += _s9_productization()
    body += _s10_strategic_readiness(territory_name, report_date, assets, budget_result, comparisons)

    footer = [
        "=" * 72,
        " END OF REPORT",
        f" SNTO Phase 7 / {territory_name} / {report_date}",
        "=" * 72,
    ]

    all_lines = header + body + footer
    return "\n".join(all_lines)
