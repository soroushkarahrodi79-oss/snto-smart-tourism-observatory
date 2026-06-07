from __future__ import annotations

"""
Decision Confidence Score (DCS)
================================
A transparency and reliability framework that quantifies how much a public
administration can trust each SNTO recommendation before acting on it.

DESIGN PHILOSOPHY
=================
The DCS is NOT another risk model. It measures the quality of the evidence
behind a recommendation, not the severity of the environmental condition.

Two assets can have the same alert level (e.g. NORMAL) but very different
DCS values: one backed by 5 years of cloud-free satellite data and a clear
spatial causality signal (DCS = 82), the other based on 8 months of gappy,
cloud-heavy observations (DCS = 35). Only the first is ready for action.

The DCS answers: "How much should a manager trust this specific recommendation
with this specific dataset at this specific moment in time?"

FORMULA
=======
DCS = Data Quality (0-25)
    + Temporal Robustness (0-25)
    + Spatial Consistency (0-20)
    + Model Stability (0-15)
    + Signal Strength (0-15)

Maximum: 100

COMPONENT DEFINITIONS
=====================

1. DATA QUALITY (0-25)
   Measures raw satellite data quality — the foundation of all conclusions.
   Sub-scores:
   a. Observation completeness (0-10):
      10 × n_valid / n_possible
      Perfect coverage (no cloud gaps) = 10. One missed month out of 12 = 9.2.
   b. Cloud impact on mean signal (0-8):
      8 × (1 - mean_cloud_pct / 100)
      Low cloud months (summer, Extremadura) contribute less noise.
   c. Spatial pixel density (0-7):
      7 × mean_valid_pixel_pct
      Fraction of the trail geometry covered by valid (non-masked) pixels.

2. TEMPORAL ROBUSTNESS (0-25)
   Measures how reliable the time-series conclusions are.
   Sub-scores:
   a. Series length (0-10):
      min(10, 10 × n_years / 5)  -- saturates at 5 years.
      1 year = 2pts, 3 years = 6pts, 5 years = 10pts.
      Rationale: < 3 years cannot distinguish climate cycle from degradation.
   b. Trend clarity (0-8):
      For STABLE trend: 8 × min(1, mk_p_value / 0.5)
        -- high p (clearly non-significant) = confident stability
      For DECLINING/IMPROVING: 8 × (1 - mk_p_value)
        -- low p (highly significant) = confident trend direction
      Masatrigo (stable, p=0.107): 8 × 0.214 = 1.71
      NOTE: This correctly penalises borderline p-values (ambiguous results).
   c. Seasonal signal quality (0-7):
      7 × seasonal_r_squared (from harmonic decomposition)
      Higher R2 = cleaner separation of seasonal from anomaly signal.

3. SPATIAL CONSISTENCY (0-20)
   Measures how clearly the Spatial Causality Module resolved the signal.
   Sub-scores:
   a. SCM classification confidence (0-10):
      HIGH confidence: 10  |  MODERATE: 7  |  LOW: 3
   b. SIG clarity (0-10):
      How far the SIG is from the nearest classification boundary.
      LANDSCAPE (SIG < 0.07):  10 × min(1, (0.07 - SIG) / 0.07)
      LOCALIZED (SIG > 0.15):  10 × min(1, (SIG - 0.15) / 0.10)
      MIXED:                   10 × min(1, min(SIG - 0.07, 0.15 - SIG) / 0.04)

4. MODEL STABILITY (0-15)
   Measures whether outputs are consistent across time windows.
   Sub-scores:
   a. NDVI-NDMI signal agreement (0-8):
      8 × max(0, pearson(ndvi_series, ndmi_series))
      When both indices move together, conclusions are more robust.
   b. Inter-annual NDVI stability (0-7):
      7 × (1 - min(1, annual_cv / 0.25))
      CV = std(annual_means) / mean(annual_means).
      Low inter-annual variability = stable model outputs.

5. SIGNAL STRENGTH (0-15)
   Measures how clearly interpretable the environmental signal is.
   Sub-scores:
   a. Anomaly event clarity (0-8):
      If no anomaly events: 8 (perfectly normal -- clear signal).
      If anomaly events exist: 8 × min(1, mean_abs_z / 2.0)
      Strong anomalies (z > 2) = clear and interpretable events.
   b. EHS component coherence (0-7):
      7 × (1 - min(1, std(eco, pressure, vuln) / 0.30))
      When all three EHS components tell the same story, the overall
      risk interpretation is stronger. High divergence = ambiguity.

DCS CLASSIFICATION
==================
  80-100: VERY HIGH CONFIDENCE -- act with full confidence
  60-79:  HIGH CONFIDENCE      -- act, document the residual uncertainty
  40-59:  MODERATE CONFIDENCE  -- act with caution, plan reassessment
   0-39:  LOW CONFIDENCE       -- collect more data before acting
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from src.risk_engine.components import RiskComponents
from src.risk_engine.ehs import EHSComponents
from src.spatial_causality.analyzer import SpatialCausalityResult
from src.time_series.climatology import AnomalyEvent
from src.time_series.mann_kendall import MannKendallResult


# ── Public constants ──────────────────────────────────────────────────────

DCS_VERY_HIGH: float = 80.0
DCS_HIGH: float = 60.0
DCS_MODERATE: float = 40.0

MAX_DQ: float = 25.0
MAX_TR: float = 25.0
MAX_SC: float = 20.0
MAX_MS: float = 15.0
MAX_SS: float = 15.0


# ── Input container ───────────────────────────────────────────────────────

@dataclass
class DCSInputs:
    """
    All SNTO outputs required to compute the Decision Confidence Score.
    Every field is derived from existing system modules — no new data sources.
    """

    # Identity
    asset_id: str
    recommendation: str         # e.g. "annual_monitoring" from AlertEngine

    # --- Data quality inputs ---
    n_valid_observations: int   # from MultiYearAdapter.fetch_multiyear_series()
    n_possible_observations: int  # calendar months in the period (e.g. 60)
    mean_cloud_cover_pct: float   # mean over all months (from AssetObservation.cloud_cover_pct)
    mean_valid_pixel_pct: float   # mean from SpatialStats.valid_pixel_pct

    # --- Temporal robustness inputs ---
    n_years: int                # distinct calendar years with data
    mk_result: MannKendallResult  # from mann_kendall_test() on deseasonalized series
    decomp_seasonal_r_squared: float  # from DecompositionResult.seasonal_r_squared

    # --- Spatial consistency inputs ---
    scm_result: SpatialCausalityResult  # from SpatialCausalityAnalyzer.analyse()

    # --- Model stability inputs ---
    ndvi_series: list[float]    # full multi-year NDVI series
    ndmi_series: list[float]    # full multi-year NDMI series
    annual_ndvi_means: dict[int, float]  # year -> annual mean NDVI

    # --- Signal strength inputs ---
    anomaly_events: list[AnomalyEvent]  # from detect_anomaly_events()
    ehs_components: EHSComponents       # from compute_ehs()
    risk_components: Optional[RiskComponents] = None  # from RiskScorer; used for coherence check


# ── Output containers ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class DCSComponents:
    """Breakdown of the Decision Confidence Score into five dimensions."""

    data_quality: float        # 0–25
    temporal_robustness: float # 0–25
    spatial_consistency: float # 0–20
    model_stability: float     # 0–15
    signal_strength: float     # 0–15
    total: float               # 0–100

    # Sub-score detail for transparency
    dq_detail: dict
    tr_detail: dict
    sc_detail: dict
    ms_detail: dict
    ss_detail: dict


@dataclass(frozen=True)
class DCSResult:
    """Full Decision Confidence Score output for one asset."""

    asset_id: str
    dcs: float                 # 0–100
    classification: str        # LOW | MODERATE | HIGH | VERY HIGH
    components: DCSComponents

    recommendation: str        # operational action (from alert level)
    confidence_statement: str  # management-ready one-paragraph summary
    uncertainty_factors: list[str]  # what reduces confidence (plain language)
    confidence_factors: list[str]   # what supports confidence (plain language)
    can_act: bool              # True if DCS >= 60
    can_act_reasoning: str     # plain-language answer to "can I trust this?"


# ── Main assessor ─────────────────────────────────────────────────────────

def compute_dcs(inputs: DCSInputs) -> DCSResult:
    """
    Compute the full Decision Confidence Score from SNTO module outputs.

    All sub-scores are computed independently and then summed.
    No sub-score can compensate for a missing dimension: a site with
    excellent data quality but zero spatial coverage cannot exceed 65/100.
    """
    dq, dq_d = _data_quality(inputs)
    tr, tr_d = _temporal_robustness(inputs)
    sc, sc_d = _spatial_consistency(inputs)
    ms, ms_d = _model_stability(inputs)
    ss, ss_d = _signal_strength(inputs)

    total = round(dq + tr + sc + ms + ss, 1)
    total = min(100.0, max(0.0, total))

    components = DCSComponents(
        data_quality=round(dq, 2),
        temporal_robustness=round(tr, 2),
        spatial_consistency=round(sc, 2),
        model_stability=round(ms, 2),
        signal_strength=round(ss, 2),
        total=total,
        dq_detail=dq_d,
        tr_detail=tr_d,
        sc_detail=sc_d,
        ms_detail=ms_d,
        ss_detail=ss_d,
    )

    classification = _classify_dcs(total)
    uncertainty_factors, confidence_factors = _explain_factors(components, inputs)
    confidence_statement = _confidence_statement(
        inputs, total, classification, components
    )
    can_act = total >= DCS_HIGH
    can_act_reasoning = _can_act_reasoning(total, classification, components, inputs)

    return DCSResult(
        asset_id=inputs.asset_id,
        dcs=total,
        classification=classification,
        components=components,
        recommendation=_humanise_recommendation(inputs.recommendation),
        confidence_statement=confidence_statement,
        uncertainty_factors=uncertainty_factors,
        confidence_factors=confidence_factors,
        can_act=can_act,
        can_act_reasoning=can_act_reasoning,
    )


# ── Sub-score functions ───────────────────────────────────────────────────

def _data_quality(inp: DCSInputs) -> tuple[float, dict]:
    a = 10.0 * inp.n_valid_observations / max(1, inp.n_possible_observations)
    b = 8.0 * (1.0 - inp.mean_cloud_cover_pct / 100.0)
    c = 7.0 * inp.mean_valid_pixel_pct
    total = _clamp(a + b + c, 0.0, MAX_DQ)
    return total, {"obs_completeness": round(a, 3), "cloud_impact": round(b, 3), "pixel_density": round(c, 3)}


def _temporal_robustness(inp: DCSInputs) -> tuple[float, dict]:
    a = min(10.0, 10.0 * inp.n_years / 5.0)
    mk = inp.mk_result
    if mk.trend_direction == "no_trend":
        b = 8.0 * min(1.0, mk.p_value / 0.5)
    else:
        b = 8.0 * (1.0 - mk.p_value)
    b = max(0.0, b)
    c = 7.0 * min(1.0, inp.decomp_seasonal_r_squared)
    total = _clamp(a + b + c, 0.0, MAX_TR)
    return total, {"series_length": round(a, 3), "trend_clarity": round(b, 3), "decomp_fit": round(c, 3)}


def _spatial_consistency(inp: DCSInputs) -> tuple[float, dict]:
    scm = inp.scm_result
    conf_map = {"HIGH": 10.0, "MODERATE": 7.0, "LOW": 3.0}
    a = conf_map.get(scm.confidence, 3.0)

    sig = scm.gradient.spatial_impact_gradient
    cls = scm.classification
    if cls == "LANDSCAPE_DRIVEN":
        b = 10.0 * _clamp((0.07 - sig) / 0.07, 0.0, 1.0)
    elif cls == "LOCALIZED_IMPACT":
        b = 10.0 * _clamp((sig - 0.15) / 0.10, 0.0, 1.0)
    else:
        boundary_dist = min(sig - 0.07, 0.15 - sig)
        b = 10.0 * _clamp(boundary_dist / 0.04, 0.0, 1.0)

    total = _clamp(a + b, 0.0, MAX_SC)
    return total, {"scm_confidence": round(a, 3), "sig_clarity": round(b, 3)}


def _model_stability(inp: DCSInputs) -> tuple[float, dict]:
    # NDVI-NDMI agreement
    n = min(len(inp.ndvi_series), len(inp.ndmi_series))
    if n >= 3:
        xa = np.array(inp.ndvi_series[:n], dtype=float)
        ya = np.array(inp.ndmi_series[:n], dtype=float)
        if np.std(xa) > 0 and np.std(ya) > 0:
            r = float(np.corrcoef(xa, ya)[0, 1])
        else:
            r = 0.0
    else:
        r = 0.0
    a = 8.0 * max(0.0, r)

    # Inter-annual variability
    if inp.annual_ndvi_means and len(inp.annual_ndvi_means) >= 2:
        vals = list(inp.annual_ndvi_means.values())
        mean_val = statistics.mean(vals)
        std_val = statistics.stdev(vals) if len(vals) > 1 else 0.0
        cv = std_val / mean_val if mean_val > 0 else 0.0
        b = 7.0 * (1.0 - _clamp(cv / 0.25, 0.0, 1.0))
    else:
        b = 0.0

    total = _clamp(a + b, 0.0, MAX_MS)
    return total, {"ndvi_ndmi_agreement": round(a, 3), "annual_stability": round(b, 3)}


def _signal_strength(inp: DCSInputs) -> tuple[float, dict]:
    # Anomaly clarity
    if not inp.anomaly_events:
        a = 8.0  # no anomalies = clearly normal signal
    else:
        mean_abs_z = statistics.mean(abs(e.z_score) for e in inp.anomaly_events)
        a = 8.0 * _clamp(mean_abs_z / 2.0, 0.0, 1.0)

    # Risk component coherence: when all three risk dimensions agree, interpretation
    # is unambiguous.  Prefer the full RiskComponents if provided; fall back to the
    # three most orthogonal EHS sub-risks (baseline ≈ structural, anomaly ≈ event
    # frequency, stability ≈ inter-annual noise).
    if inp.risk_components is not None:
        eco   = inp.risk_components.ecological_degradation
        press = inp.risk_components.human_pressure_proxy
        vuln  = inp.risk_components.vulnerability_index
    else:
        eco   = inp.ehs_components.baseline_risk
        press = inp.ehs_components.anomaly_risk
        vuln  = inp.ehs_components.stability_risk
    comp_std = _std3(eco, press, vuln)
    b = 7.0 * (1.0 - _clamp(comp_std / 0.30, 0.0, 1.0))

    total = _clamp(a + b, 0.0, MAX_SS)
    return total, {"anomaly_clarity": round(a, 3), "component_coherence": round(b, 3)}


# ── Classification and text generation ────────────────────────────────────

def _classify_dcs(score: float) -> str:
    if score >= DCS_VERY_HIGH:
        return "VERY HIGH"
    if score >= DCS_HIGH:
        return "HIGH"
    if score >= DCS_MODERATE:
        return "MODERATE"
    return "LOW"


def _explain_factors(
    comp: DCSComponents, inp: DCSInputs
) -> tuple[list[str], list[str]]:
    uncertainty: list[str] = []
    confidence: list[str] = []

    # Data quality
    dq_pct = comp.data_quality / MAX_DQ * 100
    if dq_pct >= 85:
        confidence.append(
            f"Excellent data coverage ({inp.n_valid_observations} of "
            f"{inp.n_possible_observations} months available, "
            f"{inp.n_valid_observations/inp.n_possible_observations*100:.0f}%)."
        )
    else:
        uncertainty.append(
            f"Incomplete data record ({inp.n_valid_observations} of "
            f"{inp.n_possible_observations} months): cloud gaps reduce "
            "the completeness of the environmental baseline."
        )
    if inp.mean_cloud_cover_pct > 30:
        uncertainty.append(
            f"High average cloud coverage ({inp.mean_cloud_cover_pct:.0f}%) "
            "during winter months limits the reliability of the seasonal signal."
        )

    # Temporal robustness
    if inp.n_years >= 5:
        confidence.append(
            f"Five-year observation record ({inp.n_years} years): sufficient "
            "to separate inter-annual climate variability from long-term trends."
        )
    elif inp.n_years >= 3:
        uncertainty.append(
            f"Time series covers {inp.n_years} years. At least 5 are needed "
            "for statistically robust trend detection in this climate zone."
        )
    else:
        uncertainty.append(
            f"Only {inp.n_years} year(s) of data. Results are highly uncertain; "
            "no trend conclusions should be drawn at this stage."
        )

    mk = inp.mk_result
    if not mk.is_significant and mk.p_value >= 0.30:
        confidence.append(
            f"Trend analysis is clear: no long-term decline detected "
            f"(Mann-Kendall p = {mk.p_value:.3f}, well above significance threshold)."
        )
    elif mk.p_value < 0.10 and not mk.is_significant:
        uncertainty.append(
            f"The trend test result is borderline (p = {mk.p_value:.3f}). "
            "More years of data are needed to confirm whether the trend is "
            "truly stable or mildly declining."
        )
    elif mk.is_significant:
        confidence.append(
            f"Statistically significant trend detected (p = {mk.p_value:.3f}), "
            f"direction = {mk.trend_direction}. The trend conclusion is reliable."
        )

    # Spatial consistency
    scm = inp.scm_result
    if scm.classification != "MIXED" and scm.confidence == "HIGH":
        confidence.append(
            f"Spatial analysis clearly indicates {scm.classification.replace('_', ' ').lower()} "
            f"(Spatial Impact Gradient = {scm.gradient.spatial_impact_gradient:.3f}). "
            "The cause of environmental stress is spatially well-defined."
        )
    elif scm.classification == "MIXED":
        uncertainty.append(
            "The spatial causality analysis produced a MIXED result. "
            "It is unclear whether environmental stress is caused by trail "
            "use or by the broader climate. Further investigation is needed."
        )

    # Model stability
    if comp.model_stability >= 11:
        confidence.append(
            "NDVI and NDMI indices move consistently together, and annual "
            "means are stable -- the risk model produces consistent outputs."
        )
    elif comp.model_stability < 8:
        uncertainty.append(
            "Significant inter-annual variability (driven by the 2022 drought) "
            "means risk scores differ between years. The model is sensitive to "
            "the year chosen as reference."
        )

    # Signal strength
    if not inp.anomaly_events:
        confidence.append(
            "No significant anomaly events detected: the environmental "
            "signal is stable and clearly within the expected range."
        )
    if comp.ss_detail.get("component_coherence", 0) < 4:
        uncertainty.append(
            "The three risk components (ecological, human pressure, vulnerability) "
            "do not all point in the same direction, introducing interpretive "
            "ambiguity in the final risk score."
        )

    return uncertainty, confidence


def _confidence_statement(
    inp: DCSInputs, dcs: float, classification: str, comp: DCSComponents
) -> str:
    action = _humanise_recommendation(inp.recommendation)
    return (
        f"Recommendation: {action}\n"
        f"Confidence: {dcs:.0f}/100 ({classification.replace('_', ' ').title()} Confidence)\n\n"
        f"The SNTO system analysed {inp.n_valid_observations} monthly Sentinel-2 "
        f"observations over {inp.n_years} years for this asset. "
        f"Data quality is {'excellent' if comp.data_quality >= 20 else 'adequate' if comp.data_quality >= 14 else 'limited'}. "
        f"The spatial analysis {'clearly identifies' if inp.scm_result.confidence == 'HIGH' else 'suggests'} "
        f"{inp.scm_result.classification.replace('_', ' ').lower()} as the primary driver of environmental change. "
        f"The Mann-Kendall trend test {'confirms' if inp.mk_result.is_significant else 'does not detect'} "
        f"a statistically significant long-term {'decline' if inp.mk_result.sens_slope < 0 else 'improvement'} "
        f"(p = {inp.mk_result.p_value:.3f}). "
        f"Environmental Health Score is {inp.ehs_components.ehs:.0f}/100 "
        f"({'Excellent' if inp.ehs_components.ehs >= 90 else 'Good' if inp.ehs_components.ehs >= 75 else 'Moderate'})."
    )


def _can_act_reasoning(
    dcs: float, classification: str, comp: DCSComponents, inp: DCSInputs
) -> str:
    if dcs >= DCS_VERY_HIGH:
        return (
            f"YES -- you can act on this recommendation with full confidence. "
            f"The evidence is strong across all five dimensions: data quality, "
            f"time series robustness, spatial clarity, model stability, and "
            f"signal strength. DCS = {dcs:.0f}/100."
        )
    if dcs >= DCS_HIGH:
        weakest = _weakest_component(comp)
        return (
            f"YES -- you can act on this recommendation, but document that "
            f"{weakest} introduces some residual uncertainty. "
            f"DCS = {dcs:.0f}/100. Reassess if new data changes any weak dimension."
        )
    if dcs >= DCS_MODERATE:
        return (
            f"YES WITH CAUTION -- the recommendation is directionally correct "
            f"but confidence is moderate (DCS = {dcs:.0f}/100). Before committing "
            f"resources, consider collecting one additional year of satellite data "
            f"and/or a field verification visit."
        )
    return (
        f"NOT YET -- confidence is too low (DCS = {dcs:.0f}/100) for formal "
        f"administrative action. The primary gap is: "
        f"{_weakest_component(comp)}. "
        f"We recommend extending the monitoring period before triggering any "
        f"management response."
    )


def _weakest_component(comp: DCSComponents) -> str:
    pct = {
        "data quality":         comp.data_quality / MAX_DQ,
        "temporal robustness":  comp.temporal_robustness / MAX_TR,
        "spatial consistency":  comp.spatial_consistency / MAX_SC,
        "model stability":      comp.model_stability / MAX_MS,
        "signal strength":      comp.signal_strength / MAX_SS,
    }
    return min(pct, key=pct.get)


def _humanise_recommendation(recommendation: str) -> str:
    mapping = {
        "annual_monitoring":        "Monitor only (annual review)",
        "routine_promotion":        "Promote for low-impact tourism",
        "quarterly_inspection":     "Preventive action (quarterly inspection)",
        "maintenance_schedule":     "Schedule preventive maintenance",
        "visitor_education":        "Deploy visitor education materials",
        "bi_weekly_monitoring":     "Urgent monitoring (bi-weekly visits)",
        "preventive_maintenance":   "Preventive maintenance",
        "visitor_limit_review":     "Review visitor limits",
        "immediate_site_inspection":"Immediate site inspection",
        "access_restriction":       "Restrict access",
        "emergency_restoration":    "Emergency ecological restoration",
    }
    return mapping.get(recommendation, recommendation.replace("_", " ").title())


# ── Utilities ─────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _std3(a: float, b: float, c: float) -> float:
    mean = (a + b + c) / 3.0
    return math.sqrt(((a - mean) ** 2 + (b - mean) ** 2 + (c - mean) ** 2) / 3.0)
