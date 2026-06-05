from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.config.constants import (
    WEIGHT_ECOLOGICAL,
    WEIGHT_HUMAN_PRESSURE,
    WEIGHT_VULNERABILITY,
)
from src.risk_engine.components import RiskComponents


@dataclass(frozen=True)
class RiskScore:
    asset_id: str
    score: float                         # [0, 1]
    components: RiskComponents
    computation_trace: dict[str, Any]    # full audit trail


class RiskScorer:
    def compute_risk_score(
        self,
        asset_id: str,
        components: RiskComponents,
    ) -> RiskScore:
        """
        score = 0.4 * ecological_degradation
              + 0.3 * human_pressure_proxy
              + 0.3 * vulnerability_index

        All inputs are already in [0, 1], so the output is inherently in [0, 1].
        """
        score = (
            WEIGHT_ECOLOGICAL * components.ecological_degradation
            + WEIGHT_HUMAN_PRESSURE * components.human_pressure_proxy
            + WEIGHT_VULNERABILITY * components.vulnerability_index
        )
        # Clamp to guard against floating-point edge cases
        score = max(0.0, min(1.0, score))

        trace: dict[str, Any] = {
            "weights": {
                "ecological": WEIGHT_ECOLOGICAL,
                "human_pressure": WEIGHT_HUMAN_PRESSURE,
                "vulnerability": WEIGHT_VULNERABILITY,
            },
            "components": {
                "ecological_degradation": components.ecological_degradation,
                "human_pressure_proxy": components.human_pressure_proxy,
                "vulnerability_index": components.vulnerability_index,
            },
            "weighted_contributions": {
                "ecological": WEIGHT_ECOLOGICAL * components.ecological_degradation,
                "human_pressure": WEIGHT_HUMAN_PRESSURE * components.human_pressure_proxy,
                "vulnerability": WEIGHT_VULNERABILITY * components.vulnerability_index,
            },
            "final_score": score,
        }

        return RiskScore(
            asset_id=asset_id,
            score=score,
            components=components,
            computation_trace=trace,
        )
