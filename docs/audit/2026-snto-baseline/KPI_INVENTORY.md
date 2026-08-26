# KPI and Indicator Inventory

## Reading key

- **Evidence** — the class of the *inputs on the live PNSG dashboard*, not the
  class the formula could support with better data. **Post-audit
  reclassification (Q-01):** indicators fed by `src/territorial/fixtures.py`
  were **initially classified as `CALIBRATED` during the audit**; the **owner
  decision after audit is `SYNTHETIC`**, and that decision governs Phase 0.5
  and later work. This is a change in how the audit classifies the data — no
  machine-readable evidence field existed on fixture assets at audit time, and
  none exists today (Phase 0.5 item I-5 makes it so).
- **Threshold origin** — vocabulary revised after owner review (see
  `CONTRADICTIONS_AND_OPEN_QUESTIONS.md` "Owner decisions after audit", Q-04).
  The original two-tier `literature` / `expert` / `arbitrary` scheme collapsed
  "no citation is present in this repository" into "arbitrary," which asserts
  more than the evidence shows — the repository not containing a citation does
  not establish that a value was chosen carelessly or without any method.
  Revised terms:
  - `literature` — a cited external source.
  - `expert` — a stated expert-elicitation rationale, even without a
    per-constant citation.
  - `DECLARED_POLICY` — an explicit, owner-authored editorial choice (a
    weighting or cut-point the project *owns* as policy, not an empirical
    claim about the world). The doc already treats several thresholds this
    way in their Recommendation text; the origin column now says so directly.
  - `EXPERIMENTAL_HEURISTIC` — an operating rule the system runs on in
    production today, with no cited or demonstrated validation — reserved for
    decision boundaries inside an active classification or scoring model.
  - `UNDOCUMENTED_ORIGIN` / `UNSOURCED_IN_REPOSITORY` — no basis is stated in
    code or docs, and design rationale may exist without a specific numeric
    citation. The narrower, softer default when nothing indicates the value is
    a deliberate policy or an active heuristic boundary — just that this
    repository does not cite one.
  - `arbitrary` — reserved for cases where the implementation or authoring
    history *demonstrates* a value was selected without any stated method
    (e.g. a comment admitting an unmotivated choice). Not used as a default
    label for "no citation found."
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
| Evidence | **REAL** for the 218 trails (Pipeline A path); **SYNTHETIC** for the 8 dashboard assets (fixture path — initially classified as CALIBRATED during the audit; owner decision after audit: SYNTHETIC, Q-01) |
| Threshold origin | `expert` — weights cited to Pellizzaro 2007, Lloret 2012, Fernández-Manso 2016; `_BASELINE_NDVI = 0.55`, `_MAX_TREND_SLOPE = 0.005`, `_MAX_RESIDUAL_FRACTION = 0.20` are stated constants without per-constant citation |
| Uncertainty | none propagated into the score itself |
| Claim | "Salud Ecológica"; interpretation bands Excellent→Critical |
| Decision | tiering, budget, alerting — everything downstream |
| **Recommendation** | **Retain**, with two fixes: (a) publish a single sign-convention statement (the stress↔health inversion is handled correctly in `real_trails._summary_to_health` but is a standing trap); (b) attach an uncertainty band, since EHS drives euro figures. |

Two independent EHS implementations coexist (multi-year composite vs 2-scene
percentile deficit) under one brand name and one 0–100 scale. They are **not the
same quantity**. Nothing in the UI distinguishes them.

### K-02 · ΔEHS — two-scene health difference

| | |
|---|---|
| Code | `src/metrics/semantics.delta_stress_to_delta_health`; surfaced `tab_diagnostic.py:410` |
| Formula | `ΔEHS = health_spring − health_summer` (field names are the code's own; see caveat below) |
| Unit | EHS points |
| Evidence | REAL |
| Threshold origin | sign convention only (`< 0` = **negative two-date health difference under the current sign convention** — per Q-03 this may *not* be read as deterioration) |
| Uncertainty | none |
| Claim | "deterioro estival"; "Sendas en deterioro: 46" |
| **Owner decision applied (Q-03)** | The Aug-2025 / Apr-2026 scene pair **cannot support** a seasonal, trend, recovery, deterioration, or causal claim of any kind. This section's original title ("seasonal delta") asserted the audit's own seasonal framing rather than describing what the data supports; it is corrected here. The correct description is: **mean two-date health difference under the current sign convention** — not interpretable as a seasonal or longitudinal result. |
| **Recommendation** | **Redesign.** The two scenes are 2025-08-10 and 2026-04-10 — 8 months apart, across two calendar years, across two satellites (S2A/S2B), and in the reverse of the implied chronology. Restrict every UI and report surface to "difference between two dated scenes" with both dates and both sensor IDs on screen, and remove any spring/summer, seasonal, or recovery framing until same-year, same-sensor paired scenes exist. |

### K-03 · SIG — Spatial Impact Gradient (and the SCM classification)

| | |
|---|---|
| Code | `src/spatial_causality/analyzer.py` |
| Formula | `SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)`, plus cross-zone Pearson r |
| Zones | core ≤ 50 m, near ≤ 200 m, landscape ≤ 1 000 m |
| Thresholds | `SIG > 0.15` → LOCALIZED_IMPACT; `< 0.07` → LANDSCAPE_DRIVEN; between → MIXED. `r > 0.85` landscape, `r < 0.70` localized |
| Source | **observed zones if `src/spatial_causality/zones/<id>.json` exists — it does not.** Falls back to α-decay simulation: `NDVI_core = NDVI_landscape × (1 − HP·0.12)`, `α_near = 0.05`, `γ = 0.025` |
| Evidence | **SIMULATED** (verified: `resolve_signals('pnsg')['scm_real_zones'] == 0`) |
| Threshold origin | `literature` for the α coefficients (Pickering 2011: 5–20 %; Šmída 2018: 3–8 %); **`EXPERIMENTAL_HEURISTIC` for the 0.07 / 0.15 / 0.85 / 0.70 decision boundaries** (owner decision, Q-04) — an operating rule the classifier runs on today, locally unvalidated until its basis is documented and tested; no source is given in code or `docs/methodology/`, but nothing in the repository shows the values were chosen without any method, so `arbitrary` does not apply |
| Uncertainty | a confidence label (HIGH/MODERATE/LOW), no interval |
| Claim | "Impacto localizado (uso del sendero)" — a **causal** claim about tourism |
| Decision | drives KPI 7, TPI causality clarity, DCS spatial consistency, and the map tooltip |
| **Owner decision applied (Q-02)** | Suspend the causal wording **immediately** — not conditional on real-zone ingestion. This is Phase 0.5 work (`PHASE_1_RECOMMENDATIONS.md` PR 0.5.1). |
| **Recommendation** | **Suspend the causal wording now; upgrade the evidence class separately, later.** The gate and loader are already built (`zone_loader.py`); running `scripts/gee_scm_zones_pnsg.js` upgrades this to REAL with zero code change — but per the corrected causal gate (`PHASE_1_RECOMMENDATIONS.md` PR 0.5.1), REAL evidence alone would still not license causal language without a validated method, a supported attribution, and independent verification. Until then the classification is a simulation whose input (`human_pressure`) is itself a geographic proxy. Report it as a hypothesis, never as "cause". |

### K-04 · DCS — Decision Confidence Score

| | |
|---|---|
| Code | `src/decision_confidence/assessor.py` |
| Formula | `DCS = DQ(0-25) + TR(0-25) + SC(0-20) + MS(0-15) + SS(0-15)` |
| Unit | 0–100 |
| Evidence | **SYNTHETIC** on the dashboard (Q-01) — `dcs` is a literal field on every fixture asset (e.g. `dcs=79.0`), not computed at render time. A *confidence* score that is itself a synthetic constant is the sharpest case in this inventory. |
| Threshold origin | `UNDOCUMENTED_ORIGIN` — the 25/25/20/15/15 budget, the 80/60/40 classification bands, and the sub-score divisors (`/0.5`, `/0.25`, `/2.0`, `/0.30`) carry no citation; the module docstring gives a thorough design rationale for *why* each dimension matters, just not for the specific numbers, so this is undocumented origin rather than demonstrated arbitrariness |
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
| Evidence | **SYNTHETIC** (Q-01) — all four inputs are fixture literals |
| Threshold origin | **`DECLARED_POLICY`** — the 40/25/20/15 budget, the urgency factors (0.70, 0.20, 1.12, 0.38…), the CC lookup values (15/12/10/8/6/5/4/3), and the tier cut-points (75, 0.35, 55, 45, 38, 50, 38) have no cited empirical basis, but the module docstring frames them as a deliberate editorial design (see Recommendation) — treated here as owned policy, not an empirical claim in need of a citation |
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
| Threshold origin | **`DECLARED_POLICY`** for the score-composition weights (0.55/0.30/0.15, 0.60/0.40, `_MAX_DELTA_RISK = 0.20`, `_MAX_DELTA_DCS = 15`) — an owned weighting scheme, not claimed as empirical. **Owner decision (Q-05): the visitor-uplift rates 0.25/0.15/0.08/0.05 are illustrative scenario assumptions only** — they may not be presented as an observed or forecast effect, and are distinguished here from the score weights because they masquerade as a measured elasticity in the current UI text (see `SCIENTIFIC_CLAIMS_REGISTER.md` C-10). |
| Uncertainty | the simulator exposes cost and effectiveness sliders; the point value has none |
| Claim | "cada euro invertido entrega beneficio territorial"; KPI 8 says "EXCELLENT EFFICIENCY" at TIS ≥ 12 |
| Decision | budget allocation across the portfolio |
| **Recommendation** | **Suspend the efficiency claim; retain the ranking.** The "25 % more visitors from promotion" coefficient is an illustrative scenario assumption (Q-05), not an observed elasticity — no evidence for it as a real-world effect exists anywhere in the repository. Present TIS as an ordering heuristic, not as euro efficiency, and drop the "EXCELLENT" label until the coefficients have a validated source. |

### K-07 · Human pressure proxy

| | |
|---|---|
| Code | `src/risk_engine/human_pressure.py` |
| Formula | `P = 0.35·road + 0.25·settlement + 0.20·POI + 0.10·trail + 0.10·slope` |
| Sub-formulas | `exp(−1.5·d_road_km)`, `exp(−0.4·d_settlement_km)`, `n_POI/15`, `path_km/8`, `1 − slope/30` |
| Unit | 0–1 |
| Evidence | CALIBRATED — geographic accessibility, **not** a visitor measurement |
| Threshold origin | `literature` (Arnberger 2012, Grinberger 2018) for the rationale; the decay constants and saturation points are `expert`/`UNDOCUMENTED_ORIGIN` (no per-constant citation, but a stated rationale accompanies each) |
| Uncertainty | limitations documented well (Euclidean not travel-time, OSM completeness, no seasonality) |
| **Recommendation** | **Retain.** This module is the healthiest in the repository: it explains *why the previous proxy was wrong* (NDVI volatility saturating at 1.0 for every asset), states its own limitations, and never claims to count people. Use it as the template for documenting every other indicator. |

---

## B. Dashboard KPIs (`src/platform/dashboard.py`) — all 10 computed from the 8 fixture assets

| # | KPI | Formula (`technical_basis`) | Unit | Thresholds | Evidence | Recommendation |
|---|---|---|---|---|---|---|
| K-08 | **Territory Health Index** | mean EHS across assets | 0–100 | 75 / 60 / 45 | **SYNTHETIC** (Q-01) | **Retain**, re-source to the 218 real trails. **Correction:** the fixture-portfolio mean (≈ 55) and the real-trail mean (88.5) are **not directly comparable** — different unit of analysis (8 curated assets vs. 218 real trails), different formula (multi-year composite risk model vs. 2-scene percentile deficit, see K-01), and different temporal record. This is not a case of "the datasets disagree": **two non-equivalent metrics share the same EHS name and scale, creating semantic incompatibility in the product.** The raw means are reported for reference only, not as evidence of a factual disagreement between two comparable measurements. |
| K-09 | **Assets Requiring Action** | count Tier 1, Tier 2 | count | ≥3 urgent → RED | **SYNTHETIC** (Q-01) | Retain. |
| K-10 | **Visitor Capacity at Risk** | Σ `visitor_capacity_annual` for Tier 1+2 | "visitors/yr" | 40 % / 20 % | **SYNTHETIC, mislabelled** (Q-01) | **Redesign.** Renders as `"X,XXX visitors/yr (NN%)"` and the narrative says *"X annual visitors … are visiting sites in deteriorating condition"*. The input is a hand-written *capacity* constant, not a visitor count. Rename the unit or drop the KPI. |
| K-11 | **Conservation Investment Backlog** | Σ best-scenario cost for Tier 1+2 | € | — | SIMULATED | **Redesign** — euro-precise output from constant inputs. Show a range. |
| K-12 | **Decision Confidence Rate** | % assets with DCS ≥ 65 | % | 65 | **SYNTHETIC** (Q-01) | Retain; note DCS is itself a fixture literal (K-04). |
| K-13 | **Promotion Pipeline** | count Tier 4 | count | — | **SYNTHETIC** (Q-01) | Retain. |
| K-14 | **Human Pressure Alerts** | count(`scm_classification == LOCALIZED_IMPACT` **and** tier ∈ {1,2}) | count | ≥3 / ≥1 | **SYNTHETIC on the live path** (the `scm_classification` string is a fixture literal, Q-01); **SIMULATED on the computed fallback path** (α-decay `simulate_zones`, used when the SCM is actually run and `zones/` is absent) | 🔴 **Suspend.** Neither class licenses the claim; see below. |
| K-15 | **Budget Efficiency Index** | budget-weighted portfolio TIS | 0–100 | 12 / 7 | **MIXED**: SIMULATED intervention model × **SYNTHETIC** fixture inputs (Q-01) | **Redesign** — see K-06. |
| K-16 | **Recovery Progress** | Mann-Kendall trend direction per asset | count | — | **SYNTHETIC** (Q-01) — `trend_direction` is a fixture literal | Retain, re-source. Note the KPI name asserts *recovery*, which Q-03 forbids reading into the two-scene record; the fixture literal is a separate problem from the naming. |
| K-17 | **Evidence Coverage Gap** | count DCS < 55 | count | 55 | **SYNTHETIC** (Q-01) | Retain — the most honest of the ten in *intent*, though it too counts synthetic DCS literals. |

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

The chain behind "measurable" and "confirmed" has **two distinct paths, neither
of which supports the claim**:

- **Live dashboard path — `SYNTHETIC` (Q-01).** `scm_classification` is a
  **hard-coded string** on the fixture asset, e.g.
  `scm_classification="LOCALIZED_IMPACT"` at `fixtures.py:448`. Under the
  gating matrix `SYNTHETIC` authorizes no decision use whatsoever.
- **Computed fallback path — `SIMULATED`.** Where the SCM actually runs, it
  derives zones by α-decay from the geographic `human_pressure` proxy, because
  `src/spatial_causality/zones/` does not exist. `SIMULATED` likewise
  authorizes nothing.

**No operational visitor measurement is currently ingested or used by the live
decision layer.** No turnstile, no counter, no field observation feeds any
indicator today. This is not the absence of a pathway: the MITMA mobility
ingestion pathway exists in code (`etl_mobility.py`, a committed zone crosswalk
at `src/mobility/reference/pnsg_mobility_zones.json`, an honest
`mobility_snapshot_exists()` gate) — its *snapshot* is what is absent
(`src/mobility/snapshot/` does not exist; see `DATA_SOURCE_INVENTORY.md` D-06).
Even once ingested, a municipal inbound-trip count would attach as **context
only**, never as trail footfall (documented in `pressure_capacity.py`). The
words "measurable" and "confirmed" are unsupported at every link regardless.

**Owner decision applied (Q-02):** suspend the narrative text **immediately** —
this is Phase 0.5 work (`PHASE_1_RECOMMENDATIONS.md` PR 0.5.1), not contingent
on SCM-zone ingestion or field validation landing first.

**Recommendation: suspend the narrative text now** (Phase 0.5), keep the count
under a hypothesis-framed label, and restore a causal claim only once the
four-part gate in `PHASE_1_RECOMMENDATIONS.md` PR 0.5.1 (REAL evidence +
validated method + supported attribution + independent verification) is met —
real SCM zones and field validation are necessary inputs to that gate, not a
substitute for it.

---

## C. Classifications, badges and traffic lights

| # | Indicator | Code | Origin | Recommendation |
|---|---|---|---|---|
| K-18 | **LAC standard EHS** per ROS class (75 / 65 / 55 / 45) | `platform/lac_ros.py:53` | `DECLARED_POLICY` — framework is cited (Stankey 1985), the numbers are declared standards, not empirical measurements | **Retain**, label as declared standards (the docstring already does). |
| K-19 | **`capacity_at_standard`** | `lac_ros.py:107` | derived: `P_std = P·(100 − standard)/(100 − EHS)` | **Redesign.** The linear model assumes *every* EHS point below 100 is caused by visitor pressure. For a trail classified LANDSCAPE_DRIVEN (165 of 218 real trails), it converts climate- or geology-driven deficit into a visitor quota. The docstring calls it a planning estimate but the formula embeds a causal assumption the SCM explicitly contradicts. |
| K-20 | **Capacity range** (± 15/25/35 % by DCS) | `pressure_capacity.py:195` | `UNSOURCED_IN_REPOSITORY` | Retain; disclose the mapping in the UI. |
| K-21 | **Seasonal multipliers** (0.55/0.90/1.55/1.00) | `pressure_capacity.py:75` | `DECLARED_POLICY` | Retain as an explicitly labelled scenario — the module already forbids presenting them as observations. |
| K-22 | **Tier 1–4** classification | `territorial/tpi.py:310` | `DECLARED_POLICY` cut-points | Retain; publish as policy. |
| K-23 | **Alert levels** (CRITICAL / URGENT / PREVENTIVE / NORMAL) | `src/alerts/engine.py`, mirrored in `platform/enrichment.py:50` | `src/config/constants.py` | **Merge** — two implementations of one threshold set. |
| K-24 | **CANONICAL CORE RESOLVED — TRANSLATOR FOLLOW-UP OPEN.** Canonical EHS(health) condition partition (0/40/60/75/90 — CRITICAL/POOR/MODERATE/GOOD/EXCELLENT) | `src/risk_engine/ehs.py::EHS_CONDITION_BANDS` (bounds in `config/constants.py`), presentation in `platform/ehs_presentation.py` | `DECLARED_POLICY`, owner-approved pending validation (#26) | The core pure-EHS condition partition has been canonicalized: the dashboard map legends, real-trails priority bands, the spectral colour ramps, and the portfolio EHS-distribution summary all now derive from one source (`interpret_ehs()`, `real_trails.PRIORITY_BANDS`, the `map_layers`/`real_trails` spectral ramps, the `tab_diagnostic.py` legends, `territorial/portfolio.ehs_distribution()`). Old literal 0/30/45/60/75 and 0/30/45/60/75/85 copies removed. Tier (K-22) and `LEGEND_ITEMS` remain intentionally separate multi-factor / investment-priority systems — not unified with this partition, and not in scope. **Not yet resolved:** `platform/translator.py::translate_ehs()` is a distinct, structurally different 6-tier EHS-only vocabulary (85/70/55/40/25, with an extra "DETERIORATING" state) that also embeds management-action/timing/promotion/closure prose alongside the condition label. It has no clean 1:1 mapping onto this 5-tier partition and mixes environmental condition with management-action language — an explicitly identified, independent follow-up requiring a separate owner-level design decision (see the "Duplicated meaning" row below), not implemented here. |
| K-25 | **`priority_index` = (100 − salud) × peso PRUG** | `reporting/prug_monitoring.py` | protection weights from OAPN zonification | **Retain.** Real cartography × real signal, framed as early warning. Well done. |
| K-26 | **Evidence badges** (🛰️/📐/🎛️/🧪/—) + gating matrix | `platform/evidence.py` | declared editorial policy | **Retain — this is the asset to build on.** |
| K-27 | **SVI** — Social Vulnerability Index | `socioeconomic/indicators.py` | **MIXED: REAL socioeconomic data × SYNTHETIC fixture exposure** (Q-01) | **Redesign** — the real-data half is genuine; the join multiplies it by **synthetic fixture** exposure, which the tab does not disclose. The product of a real factor and a synthetic factor is not real. |
| K-28 | **Jobs at risk** | `socioeconomic/indicators.jobs_at_risk` | hospitality affiliates × environmental exposure | Retain — `app.py:233-238` already captions it correctly as real-data-backed, distinguishing it from the visitor proxy. |
| K-29 | **DCS quality gate** (`DCS_MIN_DQ_FOR_ACTION`, `DCS_MIN_TR_FOR_ACTION`) | `assessor.py:248` | `src/config/constants.py` | **Retain.** Downgrades HIGH→MODERATE when foundational data is weak — a genuine safeguard. |

---

## D. Summary of flagged indicators

| Flag | Indicators |
|---|---|
| **Causal overclaiming** | K-14 (visitor damage "confirmed"), K-03 (SCM cause from simulation), K-04 (hard-coded "2022 drought" attribution), K-19 (capacity assumes visitor-caused deficit) |
| **Hidden synthetic/simulated data** | K-04, K-05, K-14 (fixture literals rendered as computed); K-03, K-06 (simulation presented without the label at the point of display). **After Q-01, every fixture-fed indicator (K-01 fixture path, K-04, K-05, K-08–K-14, K-16, K-17, and the exposure half of K-27) is `SYNTHETIC`** — a class the gating matrix permits for *no* decision use, while these indicators currently drive tiering, budget and alerting. |
| **Unclear or wrong units** | K-10 ("visitors/yr" from a capacity constant), K-15 (TIS as "efficiency") |
| **Unsupported thresholds** | K-03 (`EXPERIMENTAL_HEURISTIC`), K-04 (`UNDOCUMENTED_ORIGIN`), K-05/K-18/K-21/K-22 (`DECLARED_POLICY`), K-06 (`DECLARED_POLICY` for weights, illustrative scenario assumption for the visitor-uplift rates), K-20 (`UNSOURCED_IN_REPOSITORY`) — none is empirically cited; see the Reading Key for what each label does and does not claim |
| **No uncertainty** | K-01, K-02, K-05, K-06, and all 10 dashboard KPIs |
| **Duplicated meaning** | K-23 (alert thresholds ×2, merged); K-24 (EHS condition bands ×4, canonical core merged — see K-24 row); K-22 (Tier) and `LEGEND_ITEMS` remain intentionally separate, non-EHS systems; `platform/translator.py::translate_ehs()` is a newly-identified, structurally distinct 6-tier EHS vocabulary that also embeds management-action prose — an **open follow-up**, not merged into K-24's partition, pending a separate owner decision |
| **No associated management action** | none — every indicator has an action, which is a strength; the risk is the opposite (actions are attached to unvalidated evidence) |
| **Undefined formula** | none found. Every indicator has an explicit formula in code. |
