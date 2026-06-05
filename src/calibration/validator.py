from __future__ import annotations

"""
Calibration validator: compare mock-generated observations against a
reference dataset (literature-calibrated or live GEE) and quantify biases.

Outputs:
  - per-month deviation table
  - aggregated bias statistics (mean absolute error, mean bias, RMSE)
  - bias direction (mock is optimistic / pessimistic relative to reference)
  - risk model impact analysis (how much does the bias shift the risk score?)
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from src.assets.models import AssetObservation
from src.features.spectral import extract_spectral_features
from src.risk_engine.components import (
    RiskComponents,
    compute_ecological_degradation,
    compute_human_pressure_proxy,
    compute_vulnerability_index,
)
from src.risk_engine.scorer import RiskScore, RiskScorer
from src.time_series.anomaly import compute_anomaly
from src.time_series.trend import compute_linear_trend
from src.time_series.volatility import compute_volatility


@dataclass(frozen=True)
class MonthlyDeviation:
    month: int
    mock_ndvi: float
    ref_ndvi: float
    ndvi_abs_error: float     # |mock - reference|
    ndvi_pct_error: float     # (mock - reference) / reference * 100
    mock_ndmi: float
    ref_ndmi: float
    ndmi_abs_error: float
    ndmi_pct_error: float


@dataclass
class CalibrationReport:
    asset_id: str
    reference_source: str

    monthly_deviations: list[MonthlyDeviation]

    # NDVI aggregate statistics
    ndvi_mean_abs_error: float
    ndvi_mean_bias: float      # positive = mock is above reference (overestimate)
    ndvi_rmse: float
    ndvi_bias_direction: str   # "optimistic" | "pessimistic" | "neutral"

    # NDMI aggregate statistics
    ndmi_mean_abs_error: float
    ndmi_mean_bias: float
    ndmi_rmse: float
    ndmi_bias_direction: str

    # Risk model impact
    mock_risk_score: float
    ref_risk_score: float
    risk_score_delta: float    # ref - mock (positive = ref is higher/worse)
    risk_score_pct_change: float
    alert_level_changed: bool

    # Spatial statistics available in reference
    has_spatial_stats: bool
    mean_spatial_std_ndvi: float | None   # average pixel std dev from reference

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "reference_source": self.reference_source,
            "ndvi": {
                "mean_absolute_error": round(self.ndvi_mean_abs_error, 4),
                "mean_bias": round(self.ndvi_mean_bias, 4),
                "rmse": round(self.ndvi_rmse, 4),
                "bias_direction": self.ndvi_bias_direction,
            },
            "ndmi": {
                "mean_absolute_error": round(self.ndmi_mean_abs_error, 4),
                "mean_bias": round(self.ndmi_mean_bias, 4),
                "rmse": round(self.ndmi_rmse, 4),
                "bias_direction": self.ndmi_bias_direction,
            },
            "risk_model": {
                "mock_score": round(self.mock_risk_score, 4),
                "reference_score": round(self.ref_risk_score, 4),
                "delta": round(self.risk_score_delta, 4),
                "pct_change": round(self.risk_score_pct_change, 2),
                "alert_level_changed": self.alert_level_changed,
            },
            "spatial_quality": {
                "has_pixel_distribution": self.has_spatial_stats,
                "mean_spatial_std_ndvi": (
                    round(self.mean_spatial_std_ndvi, 4)
                    if self.mean_spatial_std_ndvi is not None
                    else None
                ),
            },
            "monthly_detail": [
                {
                    "month": d.month,
                    "mock_ndvi": round(d.mock_ndvi, 4),
                    "ref_ndvi": round(d.ref_ndvi, 4),
                    "ndvi_pct_error": round(d.ndvi_pct_error, 2),
                    "mock_ndmi": round(d.mock_ndmi, 4),
                    "ref_ndmi": round(d.ref_ndmi, 4),
                    "ndmi_pct_error": round(d.ndmi_pct_error, 2),
                }
                for d in self.monthly_deviations
            ],
        }


class CalibrationValidator:
    """
    Compare two sets of observations for the same asset (mock vs reference)
    and produce a CalibrationReport.
    """

    def validate(
        self,
        mock_observations: list[AssetObservation],
        reference_observations: list[AssetObservation],
        elevation_m: float | None = None,
    ) -> CalibrationReport:
        """
        Align observations by month, compute per-month deviations and
        aggregate statistics, then evaluate the risk model impact.
        """
        if not mock_observations or not reference_observations:
            raise ValueError("Both mock and reference observation lists must be non-empty.")

        asset_id = mock_observations[0].asset_id
        ref_source = reference_observations[0].data_source

        # Align by month
        mock_by_month = {o.month: o for o in mock_observations}
        ref_by_month = {o.month: o for o in reference_observations}
        common_months = sorted(set(mock_by_month) & set(ref_by_month))

        if not common_months:
            raise ValueError("No overlapping months between mock and reference observations.")

        # Per-month deviations
        deviations: list[MonthlyDeviation] = []
        for month in common_months:
            m_obs = mock_by_month[month]
            r_obs = ref_by_month[month]
            ndvi_bias = m_obs.ndvi - r_obs.ndvi
            ndmi_bias = m_obs.ndmi - r_obs.ndmi
            deviations.append(
                MonthlyDeviation(
                    month=month,
                    mock_ndvi=m_obs.ndvi,
                    ref_ndvi=r_obs.ndvi,
                    ndvi_abs_error=abs(ndvi_bias),
                    ndvi_pct_error=(ndvi_bias / r_obs.ndvi * 100.0) if r_obs.ndvi != 0 else 0.0,
                    mock_ndmi=m_obs.ndmi,
                    ref_ndmi=r_obs.ndmi,
                    ndmi_abs_error=abs(ndmi_bias),
                    ndmi_pct_error=(ndmi_bias / r_obs.ndmi * 100.0) if r_obs.ndmi != 0 else 0.0,
                )
            )

        ndvi_biases = np.array([d.mock_ndvi - d.ref_ndvi for d in deviations])
        ndmi_biases = np.array([d.mock_ndmi - d.ref_ndmi for d in deviations])

        def _bias_direction(mean_bias: float) -> str:
            if abs(mean_bias) < 0.01:
                return "neutral"
            return "optimistic" if mean_bias > 0 else "pessimistic"

        # Risk score computation for both datasets
        mock_aligned = [mock_by_month[m] for m in common_months]
        ref_aligned = [ref_by_month[m] for m in common_months]

        mock_score = self._compute_risk(mock_aligned, elevation_m)
        ref_score = self._compute_risk(ref_aligned, elevation_m)

        risk_delta = ref_score.score - mock_score.score
        risk_pct_change = (
            (risk_delta / mock_score.score * 100.0) if mock_score.score != 0 else 0.0
        )

        # Check if delta would change alert level
        from src.alerts.engine import AlertEngine
        from src.time_series.trend import compute_linear_trend

        mock_trend = compute_linear_trend([o.ndvi for o in mock_aligned])
        ref_trend = compute_linear_trend([o.ndvi for o in ref_aligned])

        alert_engine = AlertEngine()
        mock_alert = alert_engine.evaluate_asset(mock_score, mock_trend)
        ref_alert = alert_engine.evaluate_asset(ref_score, ref_trend)
        alert_changed = mock_alert.level != ref_alert.level

        # Spatial statistics summary
        has_stats = any(o.ndvi_stats is not None for o in reference_observations)
        mean_spatial_std: float | None = None
        if has_stats:
            stds = [o.ndvi_stats.std for o in reference_observations if o.ndvi_stats is not None]
            mean_spatial_std = float(np.mean(stds)) if stds else None

        return CalibrationReport(
            asset_id=asset_id,
            reference_source=ref_source,
            monthly_deviations=deviations,
            ndvi_mean_abs_error=float(np.mean(np.abs(ndvi_biases))),
            ndvi_mean_bias=float(np.mean(ndvi_biases)),
            ndvi_rmse=float(np.sqrt(np.mean(ndvi_biases**2))),
            ndvi_bias_direction=_bias_direction(float(np.mean(ndvi_biases))),
            ndmi_mean_abs_error=float(np.mean(np.abs(ndmi_biases))),
            ndmi_mean_bias=float(np.mean(ndmi_biases)),
            ndmi_rmse=float(np.sqrt(np.mean(ndmi_biases**2))),
            ndmi_bias_direction=_bias_direction(float(np.mean(ndmi_biases))),
            mock_risk_score=mock_score.score,
            ref_risk_score=ref_score.score,
            risk_score_delta=risk_delta,
            risk_score_pct_change=risk_pct_change,
            alert_level_changed=alert_changed,
            has_spatial_stats=has_stats,
            mean_spatial_std_ndvi=mean_spatial_std,
        )

    @staticmethod
    def _compute_risk(observations: list[AssetObservation], elevation_m: float | None) -> RiskScore:
        features = extract_spectral_features(observations)
        trend = compute_linear_trend(features.ndvi_series)
        volatility = compute_volatility(features.ndvi_series)
        anomaly = compute_anomaly(
            current_value=features.ndvi_series[-1],
            historical_series=features.ndvi_series[:-1],
        )
        components = RiskComponents(
            ecological_degradation=compute_ecological_degradation(features, trend),
            human_pressure_proxy=compute_human_pressure_proxy(features, volatility, {}),
            vulnerability_index=compute_vulnerability_index(features, anomaly, elevation_m),
        )
        return RiskScorer().compute_risk_score(observations[0].asset_id, components)
