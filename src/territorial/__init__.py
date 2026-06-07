"""SNTO Phase 5 — Territorial Intelligence module."""

from src.territorial.models import (
    AssetType,
    TerritorialAsset,
    TPIComponents,
    TPIResult,
    RecommendedAction,
    PortfolioKPIs,
    BudgetAllocation,
    BudgetScenario,
    TerritorialReport,
    TIER_LABELS,
    TIER_DESCRIPTIONS,
)
from src.territorial.tpi import compute_tpi, rank_assets
from src.territorial.allocator import allocate
from src.territorial.portfolio import (
    compute_portfolio_kpis,
    tier_summary,
    ehs_distribution,
    scm_distribution,
    asset_type_breakdown,
)
from src.territorial.budget import allocate_budget
from src.territorial.reporter import generate_report

__all__ = [
    "AssetType",
    "TerritorialAsset",
    "TPIComponents",
    "TPIResult",
    "RecommendedAction",
    "PortfolioKPIs",
    "BudgetAllocation",
    "BudgetScenario",
    "TerritorialReport",
    "TIER_LABELS",
    "TIER_DESCRIPTIONS",
    "compute_tpi",
    "rank_assets",
    "allocate",
    "compute_portfolio_kpis",
    "tier_summary",
    "ehs_distribution",
    "scm_distribution",
    "asset_type_breakdown",
    "allocate_budget",
    "generate_report",
]
