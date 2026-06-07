"""
SNTO Phase 5 — Multi-Asset Territorial Intelligence
Pilot Territory: Villuercas-Ibores-Jara Geopark, Extremadura, Spain

20 synthetic assets (10 trails, 5 viewpoints, 3 recreational areas, 2 parks)
with realistic EHS / DCS / SCM / trend values derived from the SNTO model
calibrated on the Masatrigo case study.

Demonstrates:
  Section 1   Territorial Intelligence Concept
  Section 2   Territorial Asset Model + Normalisation
  Section 3   Territorial Priority Index (TPI)
  Section 4   Priority Categories (4-tier table)
  Section 5   Resource Allocation (full table)
  Section 6   Portfolio KPIs
  Section 7   Budget Prioritisation (EUR 100,000 scenario)
  Section 8   Management Confidence Layer
  Section 9   Institutional Report Structure
  Section 10  Pilot Territory Dashboard
"""
from __future__ import annotations

from src.territorial.models import AssetType, TerritorialAsset
from src.territorial.tpi import rank_assets
from src.territorial.allocator import allocate
from src.territorial.portfolio import (
    compute_portfolio_kpis, tier_summary,
    ehs_distribution, scm_distribution, asset_type_breakdown,
)
from src.territorial.budget import allocate_budget
from src.territorial.reporter import generate_report

SEP  = "=" * 76
DIV  = "-" * 76
THIN = "." * 76

TERRITORY_NAME = "Villuercas-Ibores-Jara Geopark Territory"
REPORT_DATE    = "2025-Q2"
PERIOD         = "January – June 2025"
BUDGET_EUR     = 100_000


# ── 20-asset synthetic dataset ────────────────────────────────────────────

def build_territory() -> list[TerritorialAsset]:
    """
    Synthetic pilot territory with 20 assets representing the full
    condition spectrum:
      - Tier 1 critical degradation (assets in decline with human pressure)
      - Tier 2 preventive action (moderate stress, clear cause)
      - Tier 3 routine monitoring (stable, low strategic priority)
      - Tier 4 promotion opportunity (healthy, evidence-backed)
    """
    return [
        # ── Hiking Trails (10) ────────────────────────────────────────────
        TerritorialAsset(
            asset_id="trail-001", name="Masatrigo Trail",
            asset_type=AssetType.TRAIL, region="Badajoz",
            ehs=77.7, risk_score=0.318, dcs=78.7, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.107,
            visitor_capacity_annual=8_000, economic_importance=0.55,
            accessibility_score=0.65, elevation_m=420, length_km=8.3,
            description="Reference trail; 5-year Sentinel-2 record.",
        ),
        TerritorialAsset(
            asset_id="trail-002", name="Ruta de los Templos",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=83.0, risk_score=0.26, dcs=74.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.31,
            visitor_capacity_annual=15_000, economic_importance=0.72,
            accessibility_score=0.78, elevation_m=510, length_km=12.5,
            description="Well-maintained heritage trail showing improvement.",
        ),
        TerritorialAsset(
            asset_id="trail-003", name="Sendero del Rio Ibor",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=44.0, risk_score=0.62, dcs=68.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.028,
            visitor_capacity_annual=12_000, economic_importance=0.60,
            accessibility_score=0.55, elevation_m=380, length_km=9.7,
            description="Riverine trail with visible erosion at core zone.",
        ),
        TerritorialAsset(
            asset_id="trail-004", name="Camino de los Arribes",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=71.0, risk_score=0.39, dcs=55.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.19,
            visitor_capacity_annual=5_000, economic_importance=0.40,
            accessibility_score=0.45, elevation_m=480, length_km=14.2,
            description="Borderline condition; cause unclear (climate vs. use).",
        ),
        TerritorialAsset(
            asset_id="trail-005", name="Ruta de la Jara",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=37.0, risk_score=0.73, dcs=81.0, alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.009,
            visitor_capacity_annual=6_000, economic_importance=0.50,
            accessibility_score=0.70, elevation_m=440, length_km=7.1,
            description="Active degradation; high-frequency visitor erosion confirmed.",
        ),
        TerritorialAsset(
            asset_id="trail-006", name="Sendero de los Miradores",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=89.0, risk_score=0.17, dcs=85.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.44,
            visitor_capacity_annual=20_000, economic_importance=0.80,
            accessibility_score=0.85, elevation_m=620, length_km=11.0,
            description="Flagship viewpoint trail; excellent environmental condition.",
        ),
        TerritorialAsset(
            asset_id="trail-007", name="Ruta del Geoparque",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=65.0, risk_score=0.43, dcs=62.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.14,
            visitor_capacity_annual=18_000, economic_importance=0.75,
            accessibility_score=0.72, elevation_m=540, length_km=16.3,
            description="High-use geopark signature trail; moderate stress.",
        ),
        TerritorialAsset(
            asset_id="trail-008", name="Senda del Alcornocal",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=54.0, risk_score=0.55, dcs=72.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.041,
            visitor_capacity_annual=4_000, economic_importance=0.35,
            accessibility_score=0.40, elevation_m=360, length_km=5.4,
            description="Cork-oak corridor trail; declining condition.",
        ),
        TerritorialAsset(
            asset_id="trail-009", name="Camino Real de la Serena",
            asset_type=AssetType.TRAIL, region="Badajoz",
            ehs=79.0, risk_score=0.30, dcs=48.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.22,
            visitor_capacity_annual=11_000, economic_importance=0.65,
            accessibility_score=0.60, elevation_m=390, length_km=19.8,
            description="Good condition but only 3 years of satellite data.",
        ),
        TerritorialAsset(
            asset_id="trail-010", name="Ruta de los Montes de Toledo",
            asset_type=AssetType.TRAIL, region="Cáceres",
            ehs=34.0, risk_score=0.76, dcs=38.0, alert_level="URGENT_MONITORING",
            scm_classification="MIXED", scm_confidence="LOW",
            trend_direction="decreasing", mk_p_value=0.047,
            visitor_capacity_annual=3_000, economic_importance=0.30,
            accessibility_score=0.35, elevation_m=750, length_km=22.0,
            description="Critical condition but sparse satellite record; need field survey.",
        ),
        # ── Viewpoints (5) ────────────────────────────────────────────────
        TerritorialAsset(
            asset_id="view-001", name="Mirador Castillo de Belvis",
            asset_type=AssetType.VIEWPOINT, region="Cáceres",
            ehs=91.0, risk_score=0.13, dcs=88.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.51,
            visitor_capacity_annual=25_000, economic_importance=0.85,
            accessibility_score=0.90, elevation_m=580,
            description="Castle viewpoint; exceptional condition, high tourist traffic.",
        ),
        TerritorialAsset(
            asset_id="view-002", name="Mirador de Guadalupe",
            asset_type=AssetType.VIEWPOINT, region="Cáceres",
            ehs=84.0, risk_score=0.23, dcs=78.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.38,
            visitor_capacity_annual=30_000, economic_importance=0.90,
            accessibility_score=0.95, elevation_m=640,
            description="Guadalupe monastery viewpoint; flagship tourism asset.",
        ),
        TerritorialAsset(
            asset_id="view-003", name="Mirador de las Villuercas",
            asset_type=AssetType.VIEWPOINT, region="Cáceres",
            ehs=58.0, risk_score=0.48, dcs=65.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.11,
            visitor_capacity_annual=8_000, economic_importance=0.50,
            accessibility_score=0.60, elevation_m=1232,
            description="Summit viewpoint; footpath erosion around viewing platform.",
        ),
        TerritorialAsset(
            asset_id="view-004", name="Mirador del Tajo",
            asset_type=AssetType.VIEWPOINT, region="Cáceres",
            ehs=72.0, risk_score=0.36, dcs=52.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.17,
            visitor_capacity_annual=12_000, economic_importance=0.60,
            accessibility_score=0.65, elevation_m=490,
            description="River gorge viewpoint; moderate condition, weak evidence.",
        ),
        TerritorialAsset(
            asset_id="view-005", name="Mirador del Monfrague",
            asset_type=AssetType.VIEWPOINT, region="Cáceres",
            ehs=41.0, risk_score=0.68, dcs=83.0, alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.013,
            visitor_capacity_annual=35_000, economic_importance=0.95,
            accessibility_score=0.92, elevation_m=380,
            description="Highest-traffic viewpoint; active human-driven degradation.",
        ),
        # ── Recreational Areas (3) ────────────────────────────────────────
        TerritorialAsset(
            asset_id="rec-001", name="Area Recreativa Los Pilones",
            asset_type=AssetType.RECREATIONAL_AREA, region="Cáceres",
            ehs=68.0, risk_score=0.40, dcs=71.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.09,
            visitor_capacity_annual=22_000, economic_importance=0.70,
            accessibility_score=0.80, area_ha=18.5,
            description="River swimming area; summer visitor pressure evident.",
        ),
        TerritorialAsset(
            asset_id="rec-002", name="Area Recreativa Rio Almonte",
            asset_type=AssetType.RECREATIONAL_AREA, region="Cáceres",
            ehs=30.0, risk_score=0.81, dcs=76.0, alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.004,
            visitor_capacity_annual=18_000, economic_importance=0.65,
            accessibility_score=0.75, area_ha=12.0,
            description="CRITICAL: severe riparian degradation from overuse.",
        ),
        TerritorialAsset(
            asset_id="rec-003", name="Area Recreativa Navalvillar",
            asset_type=AssetType.RECREATIONAL_AREA, region="Badajoz",
            ehs=86.0, risk_score=0.20, dcs=69.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.40,
            visitor_capacity_annual=9_000, economic_importance=0.55,
            accessibility_score=0.65, area_ha=25.0,
            description="Well-maintained meadow area; recovering strongly.",
        ),
        # ── Natural Parks (2) ─────────────────────────────────────────────
        TerritorialAsset(
            asset_id="park-001", name="Parque Natural de Monfrague",
            asset_type=AssetType.NATURAL_PARK, region="Cáceres",
            ehs=87.0, risk_score=0.17, dcs=92.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.58,
            visitor_capacity_annual=75_000, economic_importance=0.98,
            accessibility_score=0.88, area_ha=18_396.0,
            description="UNESCO Biosphere Reserve; flagship territorial asset.",
        ),
        TerritorialAsset(
            asset_id="park-002", name="Reserva Natural Galapagos",
            asset_type=AssetType.NATURAL_PARK, region="Cáceres",
            ehs=48.0, risk_score=0.60, dcs=58.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.053,
            visitor_capacity_annual=7_000, economic_importance=0.45,
            accessibility_score=0.50, area_ha=4_820.0,
            description="Turtle reserve; declining condition with unclear cause.",
        ),
    ]


# ── Report rendering ──────────────────────────────────────────────────────

def word_wrap(text: str, width: int = 72, indent: str = "  ") -> str:
    words = text.split()
    lines: list[str] = []
    line = indent
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line.rstrip())
            line = indent + w
        else:
            line += (" " if line.strip() else "") + w
    if line.strip():
        lines.append(line.rstrip())
    return "\n".join(lines)


def print_section(title: str, lines: list[str]) -> None:
    print()
    print(SEP)
    print(f"  {title}")
    print(SEP)
    for line in lines:
        if line == "":
            print()
        elif line.startswith("--") or line.startswith("=="):
            print(f"  {line}")
        else:
            print(f"  {line}")
    print()


def main() -> None:
    # ── Build and rank territory ──────────────────────────────────────────
    assets = build_territory()
    assets = rank_assets(assets)
    actions = allocate(assets)
    kpis = compute_portfolio_kpis(assets)
    budget = allocate_budget(assets, actions, BUDGET_EUR)
    report = generate_report(
        TERRITORY_NAME, REPORT_DATE, PERIOD,
        assets, kpis, actions, budget,
    )

    # ════════════════════════════════════════════════════════════════════
    print(SEP)
    print(f"  SNTO PHASE 5 -- TERRITORIAL INTELLIGENCE")
    print(f"  {TERRITORY_NAME}")
    print(f"  Report period: {PERIOD}")
    print(f"  Assets monitored: {len(assets)}")
    print(SEP)

    # ── SECTION 1: Concept ────────────────────────────────────────────────
    print_section("SECTION 1 -- TERRITORIAL INTELLIGENCE CONCEPT", [
        "SNTO Phase 5 transforms single-asset environmental monitoring into a",
        "territory-wide decision-support platform for public administration.",
        "",
        "The core question shifts from:",
        "  'How healthy is THIS asset?'",
        "to:",
        "  'Where should we allocate public resources FIRST?'",
        "",
        "The answer requires combining four dimensions:",
        "  1. ENVIRONMENTAL CONDITION   -- Is the asset stressed or healthy?",
        "  2. EVIDENCE QUALITY          -- Can we trust the assessment?",
        "  3. STRATEGIC IMPORTANCE      -- How many visitors / how much value?",
        "  4. CAUSAL CLARITY            -- Do we know WHY it is degrading?",
        "",
        "Only when all four align does a recommendation reach full confidence.",
        "A critical asset with weak evidence triggers 'gather data urgently'",
        "rather than premature investment.",
    ])

    # ── SECTION 2: Asset Model ────────────────────────────────────────────
    print_section("SECTION 2 -- TERRITORIAL ASSET MODEL", [
        "Asset types supported: TRAIL | VIEWPOINT | RECREATIONAL_AREA |",
        "                       NATURAL_PARK | CYCLING_ROUTE",
        "",
        "NORMALISATION STRATEGY:",
        "  EHS, risk_score, DCS: already 0-100 / 0-1 scale. No transformation.",
        "  visitor_capacity: normalised against territory maximum.",
        f"    Territory max: {max(a.visitor_capacity_annual for a in assets):,} visitors/yr "
        f"(Parque Natural de Monfrague)",
        "    A trail with 8,000 visitors scores 0.11; the park scores 1.00.",
        "    This prevents parks from dominating every comparison dimension.",
        "  economic_importance: 0-1 expert estimate (DMO-supplied).",
        "  accessibility_score: 0-1 composite (road, distance, parking).",
        "",
        "ASSET INVENTORY:",
        f"  {'ID':<10} {'Name':<38} {'Type':<20} {'EHS':>5} {'DCS':>5} {'Visitors':>10}",
        "  " + "-" * 93,
    ] + [
        f"  {a.asset_id:<10} {a.name:<38} {a.asset_type:<20} "
        f"{a.ehs:>5.0f} {a.dcs:>5.0f} {a.visitor_capacity_annual:>10,}"
        for a in sorted(assets, key=lambda x: x.asset_type)
    ])

    # ── SECTION 3: TPI ────────────────────────────────────────────────────
    print_section("SECTION 3 -- TERRITORIAL PRIORITY INDEX (TPI)", [
        "TPI = ConditionUrgency [0-40]  +  EvidenceStrength [0-25]",
        "    + StrategicValue   [0-20]  +  CausalityClarity [0-15]",
        "Maximum: 100",
        "",
        f"  {'Rank':<5} {'Asset':<38} {'TPI':>5}  CU   ES   SV   CC  {'Tier'}",
        "  " + "-" * 82,
    ] + [
        f"  {a.priority_rank:<5} {a.name:<38} {a.tpi:>5.1f}  "
        + _tpi_bar(a)
        + f"  {a.tier_label}"
        for a in sorted(assets, key=lambda x: x.priority_rank or 999)
    ] + [
        "",
        "FORMULA EXPLAINED:",
        "  ConditionUrgency: alert level + EHS deviation from ideal",
        "  EvidenceStrength: DCS/100 -- how reliable is the signal?",
        "  StrategicValue: visitor share x economic importance x accessibility",
        "  CausalityClarity: SCM certainty -- do we know what to fix?",
    ])

    # ── SECTION 4: Priority Categories ───────────────────────────────────
    tier_groups = tier_summary(assets)
    print_section("SECTION 4 -- PRIORITY CATEGORIES", [])
    for tier_num in [1, 2, 3, 4]:
        group = sorted(tier_groups[tier_num], key=lambda a: -(a.tpi or 0))
        from src.territorial.models import TIER_LABELS, TIER_DESCRIPTIONS
        print(f"  TIER {tier_num}: {TIER_LABELS[tier_num]}")
        print(f"  {TIER_DESCRIPTIONS[tier_num]}")
        print(f"  ({len(group)} assets)")
        print()
        for a in group:
            evidence_note = " [EVIDENCE GAP]" if a.dcs < 55 and tier_num in (1, 2) else ""
            print(f"    [{a.priority_rank:2d}] {a.name:<40} EHS={a.ehs:.0f}  "
                  f"DCS={a.dcs:.0f}  TPI={a.tpi:.0f}{evidence_note}")
        print()

    # ── SECTION 5: Resource Allocation ───────────────────────────────────
    print_section("SECTION 5 -- RESOURCE ALLOCATION", [
        "MANAGEMENT CONFIDENCE LAYER (DCS gate applied):",
        "  DCS >= 70: HIGH confidence   -- Act immediately",
        "  DCS 55-69: MODERATE          -- Act, document uncertainty",
        "  DCS < 55:  LOW               -- Gather evidence first",
        "",
        f"  {'Rank':<5} {'Asset':<38} {'T'} {'Conf':<10} {'Action':<34} {'EUR':>9}",
        "  " + "-" * 100,
    ] + [
        f"  {a.priority_rank:<5} {a.name:<38} "
        f"T{a.tier} "
        + _conf_tag(actions[a.asset_id].confidence_level)
        + f"  {(a.recommended_action_label or ''):<34}  "
        + f"{a.budget_estimate_eur:>8,}"
        for a in sorted(assets, key=lambda x: x.priority_rank or 999)
    ])

    # ── SECTION 6: Portfolio KPIs ─────────────────────────────────────────
    print_section("SECTION 6 -- PORTFOLIO MANAGEMENT KPIs", [
        "10 actionable indicators for the executive dashboard:",
        "(No NDVI. No statistics. Manager-ready language.)",
        "",
        f"  KPI 1  Territory Health Score            : "
        f"{kpis.territory_health_score:.0f}/100",
        f"  KPI 2  Assets Requiring Immediate Attention: "
        f"{kpis.assets_immediate_attention} asset(s)",
        f"  KPI 3  Assets Ready for Promotion        : "
        f"{kpis.assets_promotion_ready} asset(s)",
        f"  KPI 4  Evidence Confidence Rate          : "
        f"{kpis.evidence_confidence_rate:.0f}% of assets actionable",
        f"  KPI 5  Human-Driven Degradation Alerts   : "
        f"{kpis.human_driven_degradation_alerts} asset(s)",
        f"  KPI 6  Visitor Capacity at Risk          : "
        f"{kpis.visitor_capacity_at_risk:,} visitors/year",
        f"  KPI 7  Investment Required (Tier 1+2)    : "
        f"EUR {kpis.total_investment_estimate_eur:,}",
        f"  KPI 8  Territory Trend                  : "
        f"{kpis.territory_trend}",
        f"  KPI 9  Data Gaps                        : "
        f"{kpis.data_gaps_count} asset(s) with DCS < 50",
        f"  KPI 10 Promotion Visitor Potential       : "
        f"{kpis.promotion_potential_visitors:,} visitors/year",
        "",
        "ENVIRONMENTAL HEALTH DISTRIBUTION:",
    ] + [
        f"  {band}: {count} asset(s)"
        for band, count in ehs_distribution(assets).items()
        if count > 0
    ] + [
        "",
        "CAUSALITY BREAKDOWN:",
    ] + [
        f"  {cls}: {count} asset(s)"
        for cls, count in scm_distribution(assets).items()
    ] + [
        "",
        "ASSET TYPE PERFORMANCE:",
        f"  {'Type':<22} {'n':>3} {'EHS':>7} {'DCS':>7} {'% Urgent':>9}",
        "  " + "-" * 52,
    ] + [
        f"  {atype:<22} {s['count']:>3} {s['mean_ehs']:>7.0f} "
        f"{s['mean_dcs']:>7.0f} {s['pct_urgent']:>8.0f}%"
        for atype, s in asset_type_breakdown(assets).items()
    ])

    # ── SECTION 7: Budget Prioritisation ─────────────────────────────────
    print_section("SECTION 7 -- BUDGET PRIORITISATION (EUR 100,000)", [
        f"Available budget : EUR {BUDGET_EUR:,}",
        f"Total allocated  : EUR {budget.total_allocated_eur:,}",
        f"Remaining        : EUR {budget.remaining_eur:,}",
        f"Assets funded    : {budget.funded_assets}",
        f"Assets deferred  : {budget.unfunded_assets}",
        "",
        "ALLOCATION RULES (applied in order):",
        "  Rule 1: Tier 1 (Immediate) processed first, by TPI desc.",
        "  Rule 2: Tier 1 + DCS < 55 -> evidence collection (EUR 3,500)",
        "           rather than full restoration (EUR 35,000).",
        "  Rule 3: Tier 2 (Preventive) before Tier 4 (Promotion).",
        "  Rule 4: Tier 4 ordered by visitor_capacity_annual desc.",
        "  Rule 5: Tier 3 data upgrades funded from remaining balance.",
        "  Rule 6: Stop when budget exhausted. No partial funding.",
        "",
        budget.coverage_summary,
        "",
        f"  {'Rank':<5} {'Asset':<38} {'T'} {'Action':<30} {'EUR':>10} {'Status':>10}",
        "  " + "-" * 99,
    ] + [
        f"  {alloc.allocation_rank:<5} {alloc.asset_name:<38} "
        f"T{alloc.tier}  {alloc.action_label[:29]:<30} "
        f"{alloc.allocated_eur:>10,}  "
        f"{'FUNDED' if alloc.funded else 'DEFERRED':>10}"
        for alloc in sorted(budget.allocations, key=lambda a: a.allocation_rank)
        if alloc.allocated_eur > 0 or not alloc.funded
    ])

    # ── SECTION 8: Management Confidence Layer ────────────────────────────
    print_section("SECTION 8 -- MANAGEMENT CONFIDENCE LAYER", [
        "DCS gates every recommendation. The matrix below shows what",
        "action type is triggered at each confidence x condition intersection:",
        "",
        "              DCS < 55 (LOW)        DCS 55-70 (MOD)     DCS > 70 (HIGH)",
        "  " + "-" * 72,
        "  EHS < 45    Urgent evidence        Field inspection     Immediate",
        "  (CRITICAL)  collection             + prepare action     restoration",
        "",
        "  EHS 45-65   Data collection        Preventive          Preventive",
        "  (MODERATE)  upgrade                maintenance         maintenance",
        "              (confirm first)        (scheduled)         (execute now)",
        "",
        "  EHS > 75    Hold promotion         Promotion           Promotion",
        "  (HEALTHY)   pending DCS >= 55      feasibility         campaign",
        "                                     study               (full spend)",
        "",
        "ASSETS CURRENTLY BLOCKED BY LOW DCS (cannot act without more data):",
    ] + [
        f"  - {a.name}: EHS={a.ehs:.0f}, DCS={a.dcs:.0f}/100, "
        f"Tier {a.tier} -> {a.recommended_action_label}"
        for a in sorted(assets, key=lambda x: x.dcs)
        if a.dcs < 55
    ] + [
        "",
        "THESE ASSETS CAN ACT NOW (DCS >= 55):",
        f"  {sum(1 for a in assets if a.dcs >= 55)} of {len(assets)} assets "
        f"({sum(1 for a in assets if a.dcs >= 55)/len(assets)*100:.0f}%) "
        "have sufficient evidence to support management action.",
    ])

    # ── SECTION 9: Institutional Report ──────────────────────────────────
    print_section("SECTION 9 -- INSTITUTIONAL REPORT STRUCTURE", [
        f"Quarterly report for: {TERRITORY_NAME}",
        f"Period: {PERIOD}  |  Generated: {REPORT_DATE}",
        "",
        "Report sections (manager-ready, no technical indicators):",
        "  1. Executive Summary      -- 4 bullet points for the director",
        "  2. Territorial Overview   -- health distribution, trends, evidence",
        "  3. Priority Assets        -- Tier 1+2 with specific actions",
        "  4. Recommended Actions    -- full priority-ranked action table",
        "  5. Budget Allocation      -- funded items with justification",
        "  6. Emerging Risks         -- declining trends, evidence gaps",
        "  7. Promotion Opportunities-- Tier 4 assets with visitor potential",
        "",
        "SAMPLE OUTPUT (Section 1 -- Executive Summary):",
        THIN,
    ] + [
        f"  {line}"
        for line in report.sections[0].content
        if line.strip()
    ] + [THIN])

    # ── SECTION 10: Dashboard ─────────────────────────────────────────────
    print_section("SECTION 10 -- PILOT TERRITORY DASHBOARD", [
        f"TERRITORY: {TERRITORY_NAME}",
        f"ANALYSIS DATE: {REPORT_DATE}  |  PERIOD: {PERIOD}",
        "",
    ])

    # Visual health gauge
    ths = kpis.territory_health_score
    bar_len = int(ths / 2)
    print(f"  TERRITORY HEALTH : {ths:.0f}/100  "
          f"[{'#' * bar_len}{'-' * (50 - bar_len)}]  "
          f"{kpis.territory_trend}")
    print()

    # Tier distribution bar chart
    tg = tier_summary(assets)
    n = len(assets)
    print("  TIER DISTRIBUTION:")
    tier_cfg = [
        (1, "!! IMMEDIATE ATTENTION  "),
        (2, "   PREVENTIVE ACTION    "),
        (3, "   ROUTINE MONITORING   "),
        (4, ">> PROMOTION OPPORTUNITY"),
    ]
    for t, lbl in tier_cfg:
        count = len(tg[t])
        bar = "#" * count + "-" * (n - count)
        pct = count / n * 100
        print(f"  {lbl}: {count:2d} assets  [{bar}]  {pct:.0f}%")
    print()

    # KPI summary box
    print("  " + "-" * 70)
    print(f"  {'Visitor capacity at risk':42}: "
          f"{kpis.visitor_capacity_at_risk:>10,} visits/year")
    print(f"  {'Promotion visitor potential':42}: "
          f"{kpis.promotion_potential_visitors:>10,} visits/year")
    print(f"  {'Investment required (Tier 1+2)':42}: "
          f"EUR {kpis.total_investment_estimate_eur:>8,}")
    print(f"  {'Budget allocated (EUR 100,000 scenario)':42}: "
          f"EUR {budget.total_allocated_eur:>8,}")
    print(f"  {'Evidence confidence rate':42}: "
          f"{kpis.evidence_confidence_rate:>9.0f}%")
    print(f"  {'Human-driven degradation alerts':42}: "
          f"{kpis.human_driven_degradation_alerts:>10}")
    print("  " + "-" * 70)
    print()

    # Top 5 priority assets
    print("  TOP 5 PRIORITY ASSETS:")
    for a in sorted(assets, key=lambda x: x.priority_rank or 999)[:5]:
        tier_sym = "!!" if a.tier == 1 else (" P" if a.tier == 2 else
                    (" M" if a.tier == 3 else ">>"))
        print(f"  [{a.priority_rank:2d}] {tier_sym}  {a.name:<38}  "
              f"TPI={a.tpi:.0f}  EHS={a.ehs:.0f}  "
              f"{a.recommended_action_label or ''}")
    print()
    print("  TOP 3 PROMOTION OPPORTUNITIES:")
    tier4 = sorted(tg[4], key=lambda x: -x.visitor_capacity_annual)
    for a in tier4[:3]:
        print(f"  [>>] {a.name:<40}  EHS={a.ehs:.0f}  DCS={a.dcs:.0f}  "
              f"{a.visitor_capacity_annual:,} visits/yr")
    print()
    print(SEP)
    print()


# ── Formatting helpers ────────────────────────────────────────────────────

def _tpi_bar(a: TerritorialAsset) -> str:
    """Format the 4 TPI sub-scores as a compact string for the ranking table."""
    from src.territorial.tpi import compute_tpi
    max_v = max(aa.visitor_capacity_annual for aa in [a])
    result = compute_tpi(a, 75_000)  # use known territory max
    c = result.components
    return (
        f"{c.condition_urgency:4.1f} "
        f"{c.evidence_strength:4.1f} "
        f"{c.strategic_value:4.1f} "
        f"{c.causality_clarity:4.1f}"
    )


def _conf_tag(conf: str) -> str:
    tags = {"HIGH": "HIGH      ", "MODERATE": "MODERATE  ", "LOW": "LOW       "}
    return tags.get(conf, conf[:9].ljust(10))


if __name__ == "__main__":
    main()
