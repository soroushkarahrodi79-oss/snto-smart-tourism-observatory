from __future__ import annotations

from dataclasses import dataclass

from src.risk_engine.scorer import RiskScore


@dataclass(frozen=True)
class RankedAsset:
    rank: int
    asset_id: str
    risk_score: float
    normalized_score: float  # relative to current cohort [0, 1]
    percentile: float        # 0–100, higher = worse


class AssetRanker:
    def rank_assets(self, scores: list[RiskScore]) -> list[RankedAsset]:
        """Sort descending by risk score and assign ranks and percentiles."""
        if not scores:
            return []

        sorted_scores = sorted(scores, key=lambda s: s.score, reverse=True)
        raw = [s.score for s in sorted_scores]
        normalized = self.normalize_scores(raw)
        n = len(sorted_scores)

        ranked: list[RankedAsset] = []
        for i, (score_obj, norm) in enumerate(zip(sorted_scores, normalized)):
            # Percentile: position from the bottom (worst = 100th percentile)
            percentile = 100.0 * (n - i) / n
            ranked.append(
                RankedAsset(
                    rank=i + 1,
                    asset_id=score_obj.asset_id,
                    risk_score=score_obj.score,
                    normalized_score=norm,
                    percentile=round(percentile, 1),
                )
            )
        return ranked

    def normalize_scores(self, scores: list[float]) -> list[float]:
        """Min-max normalisation within the cohort. Returns [0, 1] values."""
        if not scores:
            return []
        lo, hi = min(scores), max(scores)
        if hi == lo:
            return [1.0] * len(scores)
        return [(s - lo) / (hi - lo) for s in scores]
