"""
SNTO Phase 5 — Territorial Intelligence Data Models
====================================================
Unified representations for multi-asset territorial analysis.

A TerritorialAsset is the convergence point of all SNTO Phase 1-4 outputs
plus the strategic metadata needed for resource prioritisation.

The data contract is deliberately flat:
  - All SNTO outputs are pre-computed scalars (no nested modules).
  - Strategic metadata is supplied by the destination management organisation.
  - The territorial engine (TPI, Classifier, Allocator) writes its results
    back as optional fields that start as None.

NORMALISATION STRATEGY
======================
All scores that enter territorial comparison are normalised to [0, 1] or
[0, 100] BEFORE any cross-asset formula is applied:

  EHS           : already 0-100 (no change)
  risk_score    : already 0-1 (no change)
  DCS           : already 0-100 (no change)
  visitor_capacity : normalised within-territory against the territorial
                     maximum. A park with 75,000 visitors/year scores 1.0;
                     a trail with 3,000 scores 0.04. This prevents large
                     natural parks from dominating the strategic component
                     for every asset type.
  economic_importance : 0-1 expert estimate (survey or proxy). No formula
                        transformation needed.
  accessibility_score : 0-1 composite (road quality, distance from towns,
                        parking availability). No transformation needed.

Asset types (TRAIL, VIEWPOINT, RECREATIONAL_AREA, NATURAL_PARK,
CYCLING_ROUTE) are compared on the same normalised dimensions rather than
on raw physical metrics (km, ha). Type-specific physical attributes
(length_km, area_ha) are stored for reporting but do not enter scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Asset type vocabulary ─────────────────────────────────────────────────

class AssetType:
    TRAIL             = "TRAIL"
    VIEWPOINT         = "VIEWPOINT"
    RECREATIONAL_AREA = "RECREATIONAL_AREA"
    NATURAL_PARK      = "NATURAL_PARK"
    CYCLING_ROUTE     = "CYCLING_ROUTE"


# ── Tier labels ───────────────────────────────────────────────────────────

TIER_LABELS = {
    1: "IMMEDIATE ATTENTION",
    2: "PREVENTIVE ACTION",
    3: "ROUTINE MONITORING",
    4: "PROMOTION OPPORTUNITY",
}

TIER_DESCRIPTIONS = {
    1: "Asset requires urgent management intervention. Evidence supports immediate action.",
    2: "Asset shows warning signals. Preventive maintenance will avoid future deterioration.",
    3: "Asset is stable. Standard annual monitoring is sufficient.",
    4: "Asset is healthy and evidence is strong. Ready for active tourism promotion.",
}


# ── Core territorial asset ────────────────────────────────────────────────

@dataclass
class TerritorialAsset:
    """
    Unified representation of a natural tourism asset with all SNTO
    Phase 1-4 outputs plus strategic territorial metadata.

    Fields are organised in four groups:
      1. Identity
      2. SNTO system outputs (pre-computed)
      3. Strategic metadata (DMO-supplied)
      4. Territorial results (filled by Phase 5 engine)
    """

    # ── Identity ──────────────────────────────────────────────────────────
    asset_id: str
    name: str
    asset_type: str                 # use AssetType constants
    region: str

    # ── SNTO Phase 1-4 outputs ────────────────────────────────────────────
    ehs: float                      # 0-100  Environmental Health Score
    risk_score: float               # 0-1    Overall risk
    dcs: float                      # 0-100  Decision Confidence Score
    alert_level: str                # CRITICAL_INTERVENTION | URGENT_MONITORING
                                    # | PREVENTIVE_ACTION | NORMAL
    scm_classification: str         # LANDSCAPE_DRIVEN | LOCALIZED_IMPACT | MIXED
    scm_confidence: str             # HIGH | MODERATE | LOW
    trend_direction: str            # increasing | decreasing | no_trend
    mk_p_value: float               # Mann-Kendall p-value (0-1)

    # ── Strategic metadata ────────────────────────────────────────────────
    visitor_capacity_annual: int    # estimated annual visitor volume
    economic_importance: float      # 0-1 regional economic significance
    accessibility_score: float      # 0-1 ease of visitor access

    # ── Optional physical context (reporting only, not in scoring) ────────
    elevation_m: Optional[float] = None
    length_km: Optional[float] = None     # trails / cycling routes
    area_ha: Optional[float] = None       # parks / recreational areas
    description: str = ""

    # ── Territorial results (set by Phase 5 engine) ───────────────────────
    tpi: Optional[float] = None
    tier: Optional[int] = None
    tier_label: Optional[str] = None
    recommended_action_code: Optional[str] = None
    recommended_action_label: Optional[str] = None
    budget_estimate_eur: Optional[int] = None
    priority_rank: Optional[int] = None
    # Exact assessor output when the pipeline persists DCS decomposition.
    # ``None`` is meaningful: total DCS exists, component propagation pending.
    dcs_components: Optional[dict[str, float]] = None


# ── TPI component breakdown ───────────────────────────────────────────────

@dataclass(frozen=True)
class TPIComponents:
    """
    Full transparency breakdown of a TPI score into its four dimensions.

    Component weights (max values):
      condition_urgency  : 0-40  How far from ideal + alert severity
      evidence_strength  : 0-25  DCS — how much we can trust the evidence
      strategic_value    : 0-20  Visitor importance + economic weight + accessibility
      causality_clarity  : 0-15  SCM certainty about cause of environmental change

    Total maximum = 100.
    """
    condition_urgency:  float   # 0-40
    evidence_strength:  float   # 0-25
    strategic_value:    float   # 0-20
    causality_clarity:  float   # 0-15
    total:              float   # 0-100 (capped)
    detail: dict                # sub-score audit trail


# ── TPI result ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TPIResult:
    """Full output of the TPI computation for one asset."""
    asset_id: str
    tpi: float                  # 0-100 Territorial Priority Index
    components: TPIComponents
    tier: int                   # 1-4
    tier_label: str
    tier_rationale: str         # plain-language classification logic
    promotion_ready: bool       # True if Tier 4
    evidence_gap: bool          # True if DCS < 55 despite bad condition


# ── Resource allocation ───────────────────────────────────────────────────

@dataclass(frozen=True)
class RecommendedAction:
    """
    Management action recommendation for one asset.

    The confidence_level field reflects whether DCS is sufficient to act:
      HIGH   : DCS >= 70, act now
      MODERATE: DCS 55-69, act with documentation
      LOW    : DCS < 55, gather evidence first, then act
    """
    action_code: str            # machine-readable action identifier
    action_label: str           # human-readable label
    justification: str          # plain-language WHY this action
    confidence_level: str       # HIGH | MODERATE | LOW
    expected_value: str         # what this action achieves
    estimated_cost_eur: int     # point estimate for budgeting
    priority_rank: int          # 1 = highest priority in territory
    dcs_gate_passed: bool       # True = DCS sufficient to act now


# ── Portfolio summary ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class PortfolioKPIs:
    """
    Territorial KPI dashboard — 10 actionable indicators.
    All values are manager-facing (no NDVI, no statistical jargon).
    """
    # 1
    territory_health_score: float       # 0-100 mean EHS across all assets
    # 2
    assets_immediate_attention: int     # count of Tier 1
    # 3
    assets_promotion_ready: int         # count of Tier 4
    # 4
    evidence_confidence_rate: float     # % assets with DCS >= 60
    # 5
    human_driven_degradation_alerts: int  # LOCALIZED_IMPACT + Tier 1 or 2
    # 6
    visitor_capacity_at_risk: int       # sum annual visits in Tier 1+2
    # 7
    total_investment_estimate_eur: int  # sum budget estimates for Tier 1+2
    # 8
    territory_trend: str                # "IMPROVING" | "STABLE" | "DECLINING"
    # 9
    data_gaps_count: int                # assets with DCS < 50
    # 10
    promotion_potential_visitors: int   # sum annual visits in Tier 4


# ── Budget allocation ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class BudgetAllocation:
    """Result of the budget prioritisation engine for one asset."""
    asset_id: str
    asset_name: str
    tier: int
    action_label: str
    allocated_eur: int
    allocation_rank: int        # 1 = allocated first
    allocation_rationale: str
    funded: bool                # True if budget was available


@dataclass(frozen=True)
class BudgetScenario:
    """Complete budget scenario output."""
    total_budget_eur: int
    allocations: list[BudgetAllocation]
    total_allocated_eur: int
    remaining_eur: int
    funded_assets: int
    unfunded_assets: int
    coverage_summary: str


# ── Institutional report sections ─────────────────────────────────────────

@dataclass(frozen=True)
class ReportSection:
    title: str
    content: list[str]          # paragraphs / bullet lines


@dataclass(frozen=True)
class TerritorialReport:
    """Structure of a quarterly institutional report."""
    territory_name: str
    report_date: str
    period: str
    n_assets: int
    sections: list[ReportSection]
