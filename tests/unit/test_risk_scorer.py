from __future__ import annotations

from src.config.constants import (
    WEIGHT_ECOLOGICAL,
    WEIGHT_HUMAN_PRESSURE,
    WEIGHT_VULNERABILITY,
)
from src.risk_engine.components import RiskComponents
from src.risk_engine.scorer import RiskScorer


def _components(eco: float = 0.5, pressure: float = 0.5, vuln: float = 0.5) -> RiskComponents:
    return RiskComponents(
        ecological_degradation=eco,
        human_pressure_proxy=pressure,
        vulnerability_index=vuln,
    )


def test_score_is_weighted_sum():
    comp = _components(eco=0.6, pressure=0.4, vuln=0.3)
    expected = (
        WEIGHT_ECOLOGICAL * 0.6
        + WEIGHT_HUMAN_PRESSURE * 0.4
        + WEIGHT_VULNERABILITY * 0.3
    )
    score = RiskScorer().compute_risk_score("test", comp)
    assert abs(score.score - expected) < 1e-10


def test_score_in_valid_range():
    for eco, pressure, vuln in [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (0.5, 0.3, 0.8)]:
        score = RiskScorer().compute_risk_score("test", _components(eco, pressure, vuln))
        assert 0.0 <= score.score <= 1.0


def test_computation_trace_has_all_keys():
    score = RiskScorer().compute_risk_score("test", _components())
    trace = score.computation_trace
    assert "weights" in trace
    assert "components" in trace
    assert "weighted_contributions" in trace
    assert "final_score" in trace


def test_computation_trace_components_match():
    comp = _components(eco=0.7, pressure=0.2, vuln=0.5)
    score = RiskScorer().compute_risk_score("test", comp)
    trace_comp = score.computation_trace["components"]
    assert trace_comp["ecological_degradation"] == 0.7
    assert trace_comp["human_pressure_proxy"] == 0.2
    assert trace_comp["vulnerability_index"] == 0.5


def test_all_zero_components_gives_zero_score():
    score = RiskScorer().compute_risk_score("test", _components(0.0, 0.0, 0.0))
    assert score.score == 0.0


def test_all_one_components_gives_one_score():
    score = RiskScorer().compute_risk_score("test", _components(1.0, 1.0, 1.0))
    assert abs(score.score - 1.0) < 1e-10
