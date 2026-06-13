"""SNTO analysis utilities — cross-cutting quantitative tools (F4).

Weight sensitivity, ranking stability and Monte-Carlo uncertainty for turning
expert-based weighted scores into defensible, robustness-checked rankings.
"""
from src.analysis.sensitivity import (
    RankStability,
    ScoreCI,
    WeightBand,
    deficit,
    monte_carlo_ci,
    ranking_stability,
    stress_score,
    weight_band,
)

__all__ = [
    "RankStability",
    "ScoreCI",
    "WeightBand",
    "deficit",
    "monte_carlo_ci",
    "ranking_stability",
    "stress_score",
    "weight_band",
]
