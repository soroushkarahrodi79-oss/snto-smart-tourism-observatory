"""
SNTO Phase 7 -- Strategic Destination Intelligence Platform
===========================================================
Pilot Territory: Villuercas-Ibores-Jara Geopark, Extremadura, Spain

Runs the complete Phase 5 -> Phase 6 -> Phase 7 pipeline and generates
the full 10-section Strategic Destination Intelligence Report.

OUTPUT (10 sections):
  Section 1  Stakeholder Intelligence Model
  Section 2  Decision Translation Engine
  Section 3  Executive Dashboard Framework
  Section 4  Quarterly Reporting Framework
  Section 5  Automated Briefing System
  Section 6  Decision Playbooks
  Section 7  Destination Maturity Model
  Section 8  Institutional Value Model
  Section 9  Productization Framework
  Section 10 Strategic Readiness Assessment
"""
from __future__ import annotations

import io
import sys

# Ensure UTF-8 output regardless of terminal code page (cp1256 on Arabic Windows)
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.territorial.models import AssetType, TerritorialAsset
from src.territorial.tpi import rank_assets

from src.intervention import (
    compare_scenarios,
    compute_counterfactual,
    allocate_tis_budget,
    build_explanation,
)

from src.platform import generate_phase7_report

TERRITORY_NAME = "Villuercas-Ibores-Jara Geopark Territory"
REPORT_DATE    = "2026-06-07"
BUDGET_EUR     = 100_000


# ── 20-asset synthetic pilot (identical to Phase 5/6) ─────────────────────

def build_territory() -> list[TerritorialAsset]:
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
        ),
        TerritorialAsset(
            asset_id="trail-002", name="Ruta de los Templos",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=83.0, risk_score=0.26, dcs=74.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.31,
            visitor_capacity_annual=15_000, economic_importance=0.72,
            accessibility_score=0.78, elevation_m=510, length_km=12.5,
        ),
        TerritorialAsset(
            asset_id="trail-003", name="Sendero del Rio Ibor",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=44.0, risk_score=0.62, dcs=68.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.028,
            visitor_capacity_annual=12_000, economic_importance=0.60,
            accessibility_score=0.55, elevation_m=380, length_km=9.7,
        ),
        TerritorialAsset(
            asset_id="trail-004", name="Camino de los Arribes",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=71.0, risk_score=0.39, dcs=55.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.19,
            visitor_capacity_annual=5_000, economic_importance=0.40,
            accessibility_score=0.45, elevation_m=480, length_km=14.2,
        ),
        TerritorialAsset(
            asset_id="trail-005", name="Ruta de la Jara",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=37.0, risk_score=0.73, dcs=81.0, alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.009,
            visitor_capacity_annual=6_000, economic_importance=0.50,
            accessibility_score=0.70, elevation_m=440, length_km=7.1,
        ),
        TerritorialAsset(
            asset_id="trail-006", name="Sendero de los Miradores",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=89.0, risk_score=0.17, dcs=85.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.44,
            visitor_capacity_annual=20_000, economic_importance=0.80,
            accessibility_score=0.85, elevation_m=620, length_km=11.0,
        ),
        TerritorialAsset(
            asset_id="trail-007", name="Ruta del Geoparque",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=65.0, risk_score=0.43, dcs=62.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.14,
            visitor_capacity_annual=18_000, economic_importance=0.75,
            accessibility_score=0.72, elevation_m=540, length_km=16.3,
        ),
        TerritorialAsset(
            asset_id="trail-008", name="Senda del Alcornocal",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=54.0, risk_score=0.55, dcs=72.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.041,
            visitor_capacity_annual=4_000, economic_importance=0.35,
            accessibility_score=0.40, elevation_m=360, length_km=5.4,
        ),
        TerritorialAsset(
            asset_id="trail-009", name="Camino Real de la Serena",
            asset_type=AssetType.TRAIL, region="Badajoz",
            ehs=79.0, risk_score=0.30, dcs=48.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.22,
            visitor_capacity_annual=11_000, economic_importance=0.65,
            accessibility_score=0.60, elevation_m=390, length_km=19.8,
        ),
        TerritorialAsset(
            asset_id="trail-010", name="Ruta de los Montes de Toledo",
            asset_type=AssetType.TRAIL, region="Caceres",
            ehs=34.0, risk_score=0.76, dcs=38.0, alert_level="URGENT_MONITORING",
            scm_classification="MIXED", scm_confidence="LOW",
            trend_direction="decreasing", mk_p_value=0.047,
            visitor_capacity_annual=3_000, economic_importance=0.30,
            accessibility_score=0.35, elevation_m=750, length_km=22.0,
        ),
        # ── Viewpoints (5) ────────────────────────────────────────────────
        TerritorialAsset(
            asset_id="view-001", name="Mirador Castillo de Belvis",
            asset_type=AssetType.VIEWPOINT, region="Caceres",
            ehs=91.0, risk_score=0.13, dcs=88.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.51,
            visitor_capacity_annual=25_000, economic_importance=0.85,
            accessibility_score=0.90, elevation_m=580,
        ),
        TerritorialAsset(
            asset_id="view-002", name="Mirador de Guadalupe",
            asset_type=AssetType.VIEWPOINT, region="Caceres",
            ehs=84.0, risk_score=0.23, dcs=78.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="no_trend", mk_p_value=0.38,
            visitor_capacity_annual=30_000, economic_importance=0.90,
            accessibility_score=0.95, elevation_m=640,
        ),
        TerritorialAsset(
            asset_id="view-003", name="Mirador de las Villuercas",
            asset_type=AssetType.VIEWPOINT, region="Caceres",
            ehs=58.0, risk_score=0.48, dcs=65.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.11,
            visitor_capacity_annual=8_000, economic_importance=0.50,
            accessibility_score=0.60, elevation_m=1232,
        ),
        TerritorialAsset(
            asset_id="view-004", name="Mirador del Tajo",
            asset_type=AssetType.VIEWPOINT, region="Caceres",
            ehs=72.0, risk_score=0.36, dcs=52.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="LOW",
            trend_direction="no_trend", mk_p_value=0.17,
            visitor_capacity_annual=12_000, economic_importance=0.60,
            accessibility_score=0.65, elevation_m=490,
        ),
        TerritorialAsset(
            asset_id="view-005", name="Mirador del Monfrague",
            asset_type=AssetType.VIEWPOINT, region="Caceres",
            ehs=41.0, risk_score=0.68, dcs=83.0, alert_level="URGENT_MONITORING",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.013,
            visitor_capacity_annual=35_000, economic_importance=0.95,
            accessibility_score=0.92, elevation_m=380,
        ),
        # ── Recreational Areas (3) ────────────────────────────────────────
        TerritorialAsset(
            asset_id="rec-001", name="Area Recreativa Los Pilones",
            asset_type=AssetType.RECREATIONAL_AREA, region="Caceres",
            ehs=68.0, risk_score=0.40, dcs=71.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="MODERATE",
            trend_direction="no_trend", mk_p_value=0.09,
            visitor_capacity_annual=22_000, economic_importance=0.70,
            accessibility_score=0.80, area_ha=18.5,
        ),
        TerritorialAsset(
            asset_id="rec-002", name="Area Recreativa Rio Almonte",
            asset_type=AssetType.RECREATIONAL_AREA, region="Caceres",
            ehs=30.0, risk_score=0.81, dcs=76.0, alert_level="CRITICAL_INTERVENTION",
            scm_classification="LOCALIZED_IMPACT", scm_confidence="HIGH",
            trend_direction="decreasing", mk_p_value=0.004,
            visitor_capacity_annual=18_000, economic_importance=0.65,
            accessibility_score=0.75, area_ha=12.0,
        ),
        TerritorialAsset(
            asset_id="rec-003", name="Area Recreativa Navalvillar",
            asset_type=AssetType.RECREATIONAL_AREA, region="Badajoz",
            ehs=86.0, risk_score=0.20, dcs=69.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.40,
            visitor_capacity_annual=9_000, economic_importance=0.55,
            accessibility_score=0.65, area_ha=25.0,
        ),
        # ── Natural Parks (2) ─────────────────────────────────────────────
        TerritorialAsset(
            asset_id="park-001", name="Parque Natural de Monfrague",
            asset_type=AssetType.NATURAL_PARK, region="Caceres",
            ehs=87.0, risk_score=0.17, dcs=92.0, alert_level="NORMAL",
            scm_classification="LANDSCAPE_DRIVEN", scm_confidence="HIGH",
            trend_direction="increasing", mk_p_value=0.58,
            visitor_capacity_annual=75_000, economic_importance=0.98,
            accessibility_score=0.88, area_ha=18_396.0,
        ),
        TerritorialAsset(
            asset_id="park-002", name="Reserva Natural Galapagos",
            asset_type=AssetType.NATURAL_PARK, region="Caceres",
            ehs=48.0, risk_score=0.60, dcs=58.0, alert_level="PREVENTIVE_ACTION",
            scm_classification="MIXED", scm_confidence="MODERATE",
            trend_direction="decreasing", mk_p_value=0.053,
            visitor_capacity_annual=7_000, economic_importance=0.45,
            accessibility_score=0.50, area_ha=4_820.0,
        ),
    ]


# ── Pipeline ───────────────────────────────────────────────────────────────

def main() -> None:
    SEP = "=" * 72

    print()
    print(SEP)
    print("SNTO PHASE 7 -- STRATEGIC DESTINATION INTELLIGENCE PLATFORM")
    print(f"Territory : {TERRITORY_NAME}")
    print(f"Date      : {REPORT_DATE}")
    print(f"Budget    : EUR {BUDGET_EUR:,}")
    print(SEP)

    # ── Phase 5: TPI ranking ──────────────────────────────────────────────
    print("\n[Phase 5] Ranking 20 assets by TPI...")
    raw_assets = build_territory()
    assets = rank_assets(raw_assets)
    assets_by_id = {a.asset_id: a for a in assets}
    territory_max_visitors = max(a.visitor_capacity_annual for a in assets)

    tier_counts = {t: sum(1 for a in assets if a.tier == t) for t in range(1, 5)}
    for t, cnt in sorted(tier_counts.items()):
        label = {1: "IMMEDIATE", 2: "PREVENTIVE", 3: "MONITORING", 4: "PROMOTION"}[t]
        print(f"  Tier {t} ({label}): {cnt} assets")

    # ── Phase 6: Scenario planning + budget ───────────────────────────────
    print("\n[Phase 6] Computing scenarios (A-E) for all 20 assets...")
    comparisons = [compare_scenarios(a, territory_max_visitors) for a in assets]
    dcs_gated = sum(1 for c in comparisons if c.dcs_constrained)
    print(f"  DCS-constrained assets (monitoring-only): {dcs_gated}")

    print("\n[Phase 6] Allocating EUR 100,000 budget by TIS rank...")
    budget = allocate_tis_budget(comparisons, assets_by_id, BUDGET_EUR)
    print(f"  Funded: {len(budget.funded_items)} / Deferred: {len(budget.deferred_items)}")
    print(f"  Portfolio TIS: {budget.portfolio_tis:.1f}/100")

    # ── Phase 7: Strategic report ─────────────────────────────────────────
    print("\n[Phase 7] Generating 10-section Strategic Intelligence Report...")
    report = generate_phase7_report(
        territory_name=TERRITORY_NAME,
        report_date=REPORT_DATE,
        assets=assets,
        budget_result=budget,
        comparisons=comparisons,
    )

    print(report)

    print()
    print(SEP)
    print("PHASE 7 COMPLETE -- SNTO FULLY OPERATIONAL")
    print(SEP)
    print(f"  Territory : {TERRITORY_NAME}")
    print(f"  Assets    : {len(assets)}")
    print(f"  Sections  : 10")
    print(f"  Phases    : 1-7 (all complete)")
    print()
    print("  The platform is architecturally complete and ready for")
    print("  real-world pilot deployment with actual environmental data.")
    print(SEP)


if __name__ == "__main__":
    main()
