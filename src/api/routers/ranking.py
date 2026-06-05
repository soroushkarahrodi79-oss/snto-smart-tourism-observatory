from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import RankedAssetOut, RankingResponse

router = APIRouter(tags=["ranking"])

# In Phase 3 this endpoint reads from a shared in-memory store populated by
# /evaluate_asset calls. For MVP it returns an empty list until assets are evaluated.
_ranking_store: list[dict] = []


def update_ranking_store(entry: dict) -> None:
    """Called by the evaluate router to persist ranked results."""
    _ranking_store.append(entry)


@router.get("/", response_model=RankingResponse)
async def get_ranking() -> RankingResponse:
    """Return all evaluated assets sorted by descending risk score."""
    sorted_entries = sorted(_ranking_store, key=lambda e: e["risk_score"], reverse=True)
    assets = [
        RankedAssetOut(
            rank=i + 1,
            asset_id=e["asset_id"],
            risk_score=e["risk_score"],
            normalized_score=e.get("normalized_score", e["risk_score"]),
            percentile=e.get("percentile", 0.0),
        )
        for i, e in enumerate(sorted_entries)
    ]
    return RankingResponse(total=len(assets), assets=assets)
