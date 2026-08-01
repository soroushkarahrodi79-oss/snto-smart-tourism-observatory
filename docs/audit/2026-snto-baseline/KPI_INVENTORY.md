# KPI and Indicator Inventory

## Reading key

- **Evidence** — the class of the *inputs on the live PNSG dashboard*, not the
  class the formula could support with better data.
- **Threshold origin** — `literature` (a cited source), `expert` (stated expert
  elicitation), `arbitrary` (no stated basis found in code or docs).
- **Validated** — whether any empirical validation against ground truth exists.
  For every indicator below the answer is **no**; the field-validation campaign
  (#26) has not run and `clean_assets/field_validation/pnsg_field_observations_template.csv`
  has empty measurement columns.

---

## A. Composite scientific indices

### K-01 · EHS — Environmental / Ecological Health Score

| | |
|---|---|
| Code | `src/risk_engine/ehs.py::compute_ehs` (multi-year); `calculate_delta_ehs.py::_trail_stress_score` + `src/platform/real_trails.py` (Pipeline A, 2-scene) |
| Formula (multi-year) | `EHS = 100 × (1 − Σ wᵢ·riskᵢ)` over baseline / trend / anomaly / recovery / stability |
| Weights | 0.30 / 0.25 / 0.25 / 0.10 / 0.10, shifting to 0.20 / 0.30 / 0.30 / 0.10 / 0.10 above the dense-canopy NDVI threshold |
| Formula (Pipeline A) | `Dₓ = clamp((P₉₀ − x̄)/(P₉₀ − P₁₀))`; `EHS = 100(w_NDVI·D_NDVI + w_NDMI·D_NDMI)`, then `health = 100 − stress` |
| Unit | dimensionless 0–100 |
| Domain | vegetation condition of a trail buffer / asset footprint |
| Source | Sentinel-2 L2A B04/B08/B11 (real path); hard-coded literal (fixture path) |
| Evidence | **REAL** for the 218 trails; **CALIBRATED** for the 8 dashboard assets |
| Threshold origin | `expert` — weights cited to Pellizzaro 2007, Lloret 2012, Fernández-Manso 2016; `_BASELINE_NDVI = 0.55`, `_MAX_TREND_SLOPE = 0.005`, `_MAX_RESIDUAL_FRACTION = 0.20` are stated constants without per-constant citation |
| Uncertainty | none propagated into the score itself |
| Claim | "Salud Ecológica"; interpretation bands Excellent→Critical |
| Decision | tiering, budget, alerting — everything downstream |
| **Recommendation** | **Retain**, with two fixes: (a) publish a single sign-convention statement (the stress↔health inversion is handled correctly in `real_trails._summary_to_health` but is a standing trap); (b) attach an uncertainty band, since EHS drives euro figures. |

Two independent EHS implementations coexist (multi-year composite vs 2-scene
percentile deficit) under one brand name and one 0–100 scale. They are **not the
same quantity**. Nothing in the UI distinguishes them.

### K-02 · ΔEHS — seasonal delta

| | |
|---|---|
| Code | `src/metrics/semantics.delta_stress_to_delta_health`; surfaced `tab_diagnostic.py:410` |
| Formula | `ΔEHS = health_spring − health_summer` |
| Unit | EHS points |
| Evidence | REAL |
| Threshold origin | sign convention only (`< 0` = deterioration) |
| Uncertainty | none |
| Claim | "deterioro estival"; "Sendas en deterioro: 46" |
| **Recommendation** | **Redesign.** The two scenes are 2025-08-10 and 2026-04-10 — 8 months apart, across two years, across two satellites (S2A/S2B), and in the reverse of the implied chronology. Either restrict the claim to "difference between two dated scenes" with both dates on screen, or acquire same-year paired scenes. |

### K-03 · SIG — Spatial Impact Gradient (and the SCM classification)

| | |
|---|---|
| Code | `src/spatial_causality/analyzer.py` |
| Formula | `SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)`, plus cross-zone Pearson r |
| Zones | core ≤ 50 m, near ≤ 200 m, landscape ≤ 1 000 m |
| Thresholds | `SIG > 0.15` → LOCALIZED_IMPACT; `< 0.07` → LANDSCAPE_DRIVEN; between → MIXED. `r > 0.85` landscape, `r < 0.70` localized |
| Source | **observed zones if `src/spatial_causality/zones/<id>.json` exists — it does not.** Falls back to α-decay simulation: `NDVI_core = NDVI_landscape × (1 − HP·0.12)`, `α_near = 0.05`, `γ = 0.025` |
| Evidence | **SIMULATED** (verified: `resolve_signals('pnsg')['scm_real_zones'] == 0`) |
| Threshold origin | `literature` for the α coefficients (Pickering 2011: 5–20 %; Šmída 2018: 3–8 %); **`arbitrary` for the 0.07 / 0.15 / 0.85 / 0.70 decision boundaries** — no source is given in code or `docs/methodology/` |
| Uncertainty | a confidence label (HIGH/MODERATE/LOW), no interval |
| Claim | "Impacto localizado (uso del sendero)" — a **causal** claim about tourism |
| Decision | drives KPI 7, TPI causality clarity, DCS spatial consistency, and the map tooltip |
| **Recommendation** | **Suspend the causal wording until real zones are ingested.** The gate and loader are already built (`zone_loader.py`); running `scripts/gee_scm_zones_pnsg.js` upgrades this to REAL with zero code change. Until then the classification is a simulation whose input (`human_pressure`) is itself a geographic proxy. Report it as a hypothesis, never as "cause". |

### K-04 · DCS — Decision Confidence Score

| | |
|---|---|
| Code | `src/decision_confidence/assessor.py` |
| Formula | `DCS = DQ(0-25) + TR(0-25) + SC(0-20) + MS(0-15) + SS(0-15)` |
| Unit | 0–100 |
| Evidence | **CALIBRATED** on the dashboard — `dcs` is a literal field on every fixture asset (e.g. `dcs=79.0`), not computed at render time |
| Threshold origin | `arbitrary` — the 25/25/20/15/15 budget, the 80/60/40 classification bands, and the sub-score divisors (`/0.5`, `/0.25`, `/2.0`, `/0.30`) carry no citation |
| Uncertainty | it *is* the uncertainty instrument; has none of its own |
| Claim | "act with full confidence" / "NOT YET" |
| Decision | gates `can_act`; feeds TPI evidence strength and TIS |
| **Recommendation** | **Retain the concept, redesign the delivery.** Two defects: (a) it is a fixture constant on the live path, so a "confidence" score is itself unearned; (b) `_explain_factors` emits the hard-coded sentence *"Significant inter-annual variability (driven by the 2022 drought)"* whenever `model_stability < 8` (`assessor.py:467-471`) — a fabricated causal attribution independent of the data. Fix (b) immediately; it is a one-line scientific misstatement. |

### K-05 · TPI — Territorial Priority Index

| | |
|---|---|
| Code | `src/territorial/tpi.py` |
| Formula | `TPI = ConditionUrgency(0-40) + EvidenceStrength(0-25) + StrategicValue(0-20) + CausalityClarity(0-15)` |
| Sub-formulas | `ES = 25·DCS/100`; `SV = 20·(0.40·visitor_norm + 0.35·economic_importance + 0.25·accessibility)`; `CC` from a 9-entry (SCM class × confidence) lookup |
| Unit | 0–100 |
| Evidence | CALIBRATED (all four inputs are fixture literals) |
| Threshold origin | **`arbitrary`** — the 40/25/20/15 budget, the urgency factors (0.70, 0.20, 1.12, 0.38…), the CC lookup values (15/12/10/8/6/5/4/3), and the tier cut-points (75, 0.35, 55, 45, 38, 50, 38) have no cited basis |
| Uncertainty | none |
| Claim | ranking of "where to allocate attention first" |
| Decision | tier assignment → KPIs 2, 3, 4, 7 → budget allocation |
| **Recommendation** | **Retain, document, and expose.** The *design reasoning* in the module docstring is excellent and defensible; what is missing is any statement that the weights are a declared editorial policy rather than a calibrated model. Publish them as a versioned, owner-approved policy object and show them in the UI. |

### K-06 · TIS — Territorial Impact Score

| | |
|---|---|
| Code | `src/intervention/impact.py::compute_tis` |
| Formula | `TIS = 100 · impact · cost_factor`, `impact = 0.55·(0.60·ΔEHS_norm + 0.40·Δrisk_norm) + 0.30·Δvisitors_norm + 0.15·min(1, ΔDCS/15)` |
| Unit | 0–100 (interpreted as benefit per euro) |
| Evidence | **SIMULATED** — built on modelled intervention effects (e.g. promotion adds "25 % more visitors" for EHS ≥ 80, `impact.py:252`) |
| Threshold origin | **`arbitrary`** — 0.55/0.30/0.15, 0.60/0.40, `_MAX_DELTA_RISK = 0.20`, `_MAX_DELTA_DCS = 15`, and the visitor-uplift rates 0.25/0.15/0.08/0.05 |
| Uncertainty | the simulator exposes cost and effectiveness sliders; the point value has none |
| Claim | "cada euro invertido entrega beneficio territorial"; KPI 8 says "EXCELLENT EFFICIENCY" at TIS ≥ 12 |
| Decision | budget allocation across the portfolio |
| **Recommendation** | **Suspend the efficiency claim; retain the ranking.** A "25 % more visitors from promotion" coefficient has no evidence anywhere in the repository. Present TIS as an ordering heuristic, not as euro efficiency, and drop the "EXCELLENT" label until the coefficients have a source. |

### K-07 · Human pressure proxy

| | |
|---|---|
| Code | `src/risk_engine/human_pressure.py` |
| Formula | `P = 0.35·road + 0.25·settlement + 0.20·POI + 0.10·trail + 0.10·slope` |
| Sub-formulas | `exp(−1.5·d_road_km)`, `exp(−0.4·d_settlement_km)`, `n_POI/15`, `path_km/8`, `1 − slope/30` |
| Unit | 0–1 |
| Evidence | CALIBRATED — geographic accessibility, **not** a visitor measurement |
| Threshold origin | `literature` (Arnberger 2012, Grinberger 2018) for the rationale; the decay constants and saturation points are `expert`/`arbitrary` |
| Uncertainty | limitations documented well (Euclidean not travel-time, OSM completeness, no seasonality) |
| **Recommendation** | **Retain.** This module is the healthiest in the repository: it explains *why the previous proxy was wrong* (NDVI volatility saturating at 1.0 for every asset), states its own limitations, and never claims to count people. Use it as the template for documenting every other indicator. |

---

## B. Dashboard KPIs (`src/platform/dashboard.py`) — all 10 computed from the 8 fixture assets

| # | KPI | Formula (`technical_basis`) | Unit | Thresholds | Evidence | Recommendation |
|---|---|---|---|---|---|---|
| K-08 | **Territory Health Index** | mean EHS across assets | 0–100 | 75 / 60 / 45 | CALIBRATED | **Retain**, re-source to the 218 real trails. Note the two universes disagree sharply: fixtures average ≈ 55, real trails average **88.5**. |
| K-09 | **Assets Requiring Action** | count Tier 1, Tier 2 | count | ≥3 urgent → RED | CALIBRATED | Retain. |
| K-10 | **Visitor Capacity at Risk** | Σ `visitor_capacity_annual` for Tier 1+2 | "visitors/yr" | 40 % / 20 % | **CALIBRATED, mislabelled** | **Redesign.** Renders as `"X,XXX visitors/yr (NN%)"` and the narrative says *"X annual visitors … are visiting sites in deteriorating condition"*. The input is a hand-written *capacity* constant, not a visitor count. Rename the unit or drop the KPI. |
| K-11 | **Conservation Investment Backlog** | Σ best-scenario cost for Tier 1+2 | € | — | SIMULATED | **Redesign** — euro-precise output from constant inputs. Show a range. |
| K-12 | **Decision Confidence Rate** | % assets with DCS ≥ 65 | % | 65 | CALIBRATED | Retain; note DCS is itself a fixture literal (K-04). |
| K-13 | **Promotion Pipeline** | count Tier 4 | count | — | CALIBRATED | Retain. |
| K-14 | **Human Pressure Alerts** | count(`scm_classification == LOCALIZED_IMPACT` **and** tier ∈ {1,2}) | count | ≥3 / ≥1 | **SIMULATED** | 🔴 **Suspend.** See below. |
| K-15 | **Budget Efficiency Index** | budget-weighted portfolio TIS | 0–100 | 12 / 7 | SIMULATED | **Redesign** — see K-06. |
| K-16 | **Recovery Progress** | Mann-Kendall trend direction per asset | count | — | CALIBRATED (`trend_direction` is a fixture literal) | Retain, re-source. |
| K-17 | **Evidence Coverage Gap** | count DCS < 55 | count | 55 | CALIBRATED | Retain — the most honest of the ten. |

### 🔴 K-14 in detail — the highest-risk indicator in the product

`src/platform/dashboard.py:380-417` emits, verbatim:

> *"N sites are experiencing measurable environmental damage caused by visitor
> pressure"* … *"N site(s) show **confirmed** visitor-driven environmental
> damage. This is the most direct form of tourism pressure on the destination's
> assets."* … and when N = 0: *"Environmental changes appear to be driven by
> natural climate variability."*

Recommended action: *"Consider seasonal closures"* / *"visitor quotas or
guided-only access"* — i.e. it recommends restricting public access to a
national park.

The chain behind "measurable" and "confirmed" is:
`scm_classification` (a **hard-coded string** on the fixture asset, e.g.
`scm_classification="LOCALIZED_IMPACT"` at `fixtures.py:448`) — and where it *is*
computed, it comes from zones **simulated** by α-decay from the geographic
`human_pressure` proxy, because `src/spatial_causality/zones/` does not exist.

There is **no measurement of visitors anywhere in the system**. No turnstile, no
MITMA snapshot (`src/mobility/snapshot/` absent), no counter, no field
observation. The words "measurable" and "confirmed" are unsupported at every
link.

**Recommendation: suspend the narrative text immediately** (Phase 1), keep the
count under a hypothesis-framed label, and restore a causal claim only after
real SCM zones plus field validation exist.

---

## C. Classifications, badges and traffic lights

| # | Indicator | Code | Origin | Recommendation |
|---|---|---|---|---|
| K-18 | **LAC standard EHS** per ROS class (75 / 65 / 55 / 45) | `platform/lac_ros.py:53` | `arbitrary` — framework is cited (Stankey 1985), the numbers are not | **Retain**, label as declared standards (the docstring already does). |
| K-19 | **`capacity_at_standard`** | `lac_ros.py:107` | derived: `P_std = P·(100 − standard)/(100 − EHS)` | **Redesign.** The linear model assumes *every* EHS point below 100 is caused by visitor pressure. For a trail classified LANDSCAPE_DRIVEN (165 of 218 real trails), it converts climate- or geology-driven deficit into a visitor quota. The docstring calls it a planning estimate but the formula embeds a causal assumption the SCM explicitly contradicts. |
| K-20 | **Capacity range** (± 15/25/35 % by DCS) | `pressure_capacity.py:195` | `arbitrary` | Retain; disclose the mapping in the UI. |
| K-21 | **Seasonal multipliers** (0.55/0.90/1.55/1.00) | `pressure_capacity.py:75` | `arbitrary` | Retain as an explicitly labelled scenario — the module already forbids presenting them as observations. |
| K-22 | **Tier 1–4** classification | `territorial/tpi.py:310` | `arbitrary` cut-points | Retain; publish as policy. |
| K-23 | **Alert levels** (CRITICAL / URGENT / PREVENTIVE / NORMAL) | `src/alerts/engine.py`, mirrored in `platform/enrichment.py:50` | `src/config/constants.py` | **Merge** — two implementations of one threshold set. |
| K-24 | **Priority bands** (0/30/45/60/75) | `platform/real_trails.py:56` | `arbitrary`, cross-referenced to `constants.py` | Retain; unify with the EHS legend bands (three inconsistent labellings exist). |
| K-25 | **`priority_index` = (100 − salud) × peso PRUG** | `reporting/prug_monitoring.py` | protection weights from OAPN zonification | **Retain.** Real cartography × real signal, framed as early warning. Well done. |
| K-26 | **Evidence badges** (🛰️/📐/🎛️/🧪/—) + gating matrix | `platform/evidence.py` | declared editorial policy | **Retain — this is the asset to build on.** |
| K-27 | **SVI** — Social Vulnerability Index | `socioeconomic/indicators.py` | INE/ALMUDENA real inputs × fixture asset risk | **Redesign** — the real-data half is genuine; the join multiplies it by calibrated exposure, which the tab does not disclose. |
| K-28 | **Jobs at risk** | `socioeconomic/indicators.jobs_at_risk` | hospitality affiliates × environmental exposure | Retain — `app.py:233-238` already captions it correctly as real-data-backed, distinguishing it from the visitor proxy. |
| K-29 | **DCS quality gate** (`DCS_MIN_DQ_FOR_ACTION`, `DCS_MIN_TR_FOR_ACTION`) | `assessor.py:248` | `src/config/constants.py` | **Retain.** Downgrades HIGH→MODERATE when foundational data is weak — a genuine safeguard. |

---

## D. Summary of flagged indicators

| Flag | Indicators |
|---|---|
| **Causal overclaiming** | K-14 (visitor damage "confirmed"), K-03 (SCM cause from simulation), K-04 (hard-coded "2022 drought" attribution), K-19 (capacity assumes visitor-caused deficit) |
| **Hidden synthetic/simulated data** | K-04, K-05, K-14 (fixture literals rendered as computed); K-03, K-06 (simulation presented without the label at the point of display) |
| **Unclear or wrong units** | K-10 ("visitors/yr" from a capacity constant), K-15 (TIS as "efficiency") |
| **Unsupported thresholds** | K-03, K-04, K-05, K-06, K-18, K-20, K-21, K-22 — all `arbitrary` by the definition above |
| **No uncertainty** | K-01, K-02, K-05, K-06, and all 10 dashboard KPIs |
| **Duplicated meaning** | K-23 (alert thresholds ×2), K-24 vs the EHS legends (×3), K-22 vs K-24 vs `LEGEND_ITEMS` |
| **No associated management action** | none — every indicator has an action, which is a strength; the risk is the opposite (actions are attached to unvalidated evidence) |
| **Undefined formula** | none found. Every indicator has an explicit formula in code. |
