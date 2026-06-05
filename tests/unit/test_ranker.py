from __future__ import annotations

from src.ranking.ranker import AssetRanker
from src.risk_engine.components import RiskComponents
from src.risk_engine.scorer import RiskScore


def _make_score(asset_id: str, score: float) -> RiskScore:
    comp = RiskComponents(
        ecological_degradation=score,
        human_pressure_proxy=score,
        vulnerability_index=score,
    )
    return RiskScore(
        asset_id=asset_id,
        score=score,
        components=comp,
        computation_trace={},
    )


def test_ranking_order():
    scores = [_make_score("A", 0.9), _make_score("B", 0.5), _make_score("C", 0.2)]
    ranked = AssetRanker().rank_assets(scores)
    assert [r.asset_id for r in ranked] == ["A", "B", "C"]
    assert [r.rank for r in ranked] == [1, 2, 3]


def test_empty_returns_empty():
    assert AssetRanker().rank_assets([]) == []


def test_single_asset_rank_1():
    ranked = AssetRanker().rank_assets([_make_score("X", 0.6)])
    assert ranked[0].rank == 1
    assert ranked[0].normalized_score == 1.0


def test_normalized_scores_0_to_1():
    scores = [_make_score("A", 0.2), _make_score("B", 0.9)]
    ranked = AssetRanker().rank_assets(scores)
    norms = [r.normalized_score for r in ranked]
    assert max(norms) == 1.0
    assert min(norms) == 0.0


def test_all_same_score_normalized_to_one():
    scores = [_make_score("A", 0.5), _make_score("B", 0.5)]
    ranked = AssetRanker().rank_assets(scores)
    assert all(r.normalized_score == 1.0 for r in ranked)


def test_percentile_highest_risk_is_100():
    scores = [_make_score("A", 0.9), _make_score("B", 0.3)]
    ranked = AssetRanker().rank_assets(scores)
    assert ranked[0].percentile == 100.0
