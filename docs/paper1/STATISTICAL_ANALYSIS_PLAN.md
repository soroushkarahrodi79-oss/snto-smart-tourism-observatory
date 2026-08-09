# Statistical Analysis Plan (SAP) — Paper 1

**Status:** DRAFT, to be **frozen before the first field observation is collected** · **Date:** 2026-08-09 · **Phase 5 deliverable**

Freezing this document before data collection is what makes the analysis confirmatory rather than exploratory. After freeze, every deviation is recorded as a dated amendment in the Scientific Contract and reported in the manuscript.

---

## 0. Analysis inputs

| Input | Source | Class |
|---|---|---|
| `field_degradation_index` (corridor mean, 0–100 stress) | Campaign CSV, strict 3-component definition (Contract §H) | `real` |
| `satellite_stress` = 100 − EHS at the plot's 20 m cell | Campaign-matched composite, frozen constants | `real` |
| `is_impact`, `stratum`, `elevation`, `segment_id` | Field record / cartography | design / `real` |
| `sig_segment` (trail-to-landscape contrast) | Real zonal extraction, H4 only | `real` |

One row per plot. **No asset-level aggregation at any stage.** Nothing classed `simulated`, `synthetic`, `estimated` or `missing` enters any analysis.

---

## 1. Primary analysis (H1)

**Spearman rank correlation** between `satellite_stress` and `field_degradation_index` across all valid plots.

| Element | Specification |
|---|---|
| Estimator | Spearman ρ, tie-corrected (`src/validation/agreement.py::spearman_correlation`) |
| Interval | **BCa bootstrap 95 % CI, 10 000 resamples**, resampled at the **trail-segment** level (cluster bootstrap) to respect within-segment dependence |
| Reporting | ρ **and** CI **and** n, always together. ρ is never reported bare. |
| Hypothesis test | Two-sided, α = 0.05, reported as a p-value alongside the CI — the CI is the primary inferential object |
| Direction | Positive ρ supports H1 (both scales run in the stress direction) |

**Pre-specified departures from the current implementation:**

- `spearman_correlation` returns the *value* `0.0` when n < 3 or the input is constant, which is indistinguishable from a true null. Paper-1 analysis code must return an explicit "not computable" state. See Backlog **B-07**.
- The verdict strings in `validate_satellite_vs_field` (ρ ≥ 0.6 → *"concordancia fuerte"*) are **not used in the manuscript**. Interpreting a correlation through fixed verbal bands discards the interval. The paper reports the estimate and its uncertainty and interprets them in context.
- The docstring claim that ρ ≥ 0.6 *"elevates EHS from demo to validated indicator"* (Phase 0 audit, D-07) is **rejected**. No single-park, single-campaign correlation validates an indicator, at any magnitude.

**Pearson r on ranks vs Kendall τ:** Spearman is pre-specified. Kendall τ-b is reported as a robustness check only, not as an alternative primary.

---

## 2. Control–impact analysis (H2, H3)

**Cliff's δ**, computed **within stratum** and combined, not on pooled groups.

The current `control_impact_contrast` pools all impact plots against all control plots, which discards the stratum matching that the entire sampling design exists to provide, and lets between-stratum habitat differences leak into the effect estimate. Paper 1 uses:

| Element | Specification |
|---|---|
| Per-stratum estimate | Cliff's δ (impact vs control) within each stratum |
| Combined estimate | Sample-size-weighted mean of stratum δ, with a cluster-bootstrap CI |
| Paired variant | Where impact/control pairs are 1:1, the paired difference in `field_degradation_index` is also reported with its bootstrap CI |
| Interpretation bands | Romano et al. (2006): 0.147 small / 0.33 medium / 0.474 large — cited, and reported alongside the interval, never instead of it |
| H2 | δ on `field_degradation_index` |
| H3 | δ on `satellite_stress`, same pairing |

**H2 and H3 are reported together and interpreted jointly**, as set out in the Contract §D: H2 without H3 means the field detects impact the satellite misses; H2 failing means the sample did not capture an impact gradient and H1 is uninterpretable — which would be reported as such rather than glossed.

---

## 3. Classification analysis (secondary)

The operational question: *when the satellite flags a location, is it degraded on the ground?*

### 3.1 Why the existing confusion path cannot be used

`src/validation/confusion.py` cross-tabulates `AssetTrend.is_alert` (significant decreasing Mann-Kendall trend) against a field verdict. Across the 21 Universe-A assets, **exactly one** asset is alert-positive (`pnsg_escalada_maliciosa_porrones`, τ = −0.369, p < 0.0001). A 2×2 table with one positive supports no κ worth reporting, and κ is severely unstable under that imbalance.

The mathematics in the module is correct and is reused. The **unit and the positive-class definition change**: plot level, not asset level; threshold on plot-level `satellite_stress`, not on a multi-year asset trend.

### 3.2 Design

| Element | Specification |
|---|---|
| Unit | Plot |
| Positive (satellite) | `satellite_stress ≥ T_sat` |
| Positive (field) | `field_degradation_index ≥ T_field` |
| Metrics | Confusion matrix, accuracy, precision, recall/sensitivity, specificity, F1, **Cohen's κ**, explicit FP and FN counts |
| Intervals | Cluster-bootstrap CI on every metric. Point estimates alone are not reported. |

### 3.3 Threshold discipline — the non-negotiable

**Thresholds must not be optimised on the sample that is then reported as validation.** Concretely:

- `FIELD_DEGRADED_THRESHOLD = 50.0` in the current code is an uncalibrated round number (Phase 0 audit §4). It is **not** adopted by default.
- `T_field` is fixed **before unblinding**, from the field measurement scale alone (a domain-defined degradation level, or the pre-declared upper tercile of the pilot distribution), **never** from its performance against the satellite.
- `T_sat` is calibrated with **strict separation** from evaluation.

Given the expected n (30–60 plots), a held-out split would waste too much data. Pre-specified design:

> **Nested leave-one-cluster-out cross-validation, clustered by trail segment.**
> For each held-out segment: choose `T_sat` on the remaining segments only (maximising Youden's J on the training folds), then classify the held-out segment's plots with that threshold. The reported confusion matrix pools the held-out predictions. Every plot is predicted by a threshold chosen without seeing it.

Reported alongside:
- the **distribution of `T_sat` across folds** — if it is unstable, the threshold is not a real property of the indicator and the manuscript says so;
- a **threshold-free ROC AUC** with cluster-bootstrap CI, as the primary discrimination summary (it avoids the threshold question entirely);
- the confusion matrix **at the fixed literature/domain threshold** if one can be justified, reported separately and labelled as non-calibrated.

**Prohibited and stated as prohibited in the manuscript:** selecting `T_sat` on the full sample and reporting the resulting matrix as validation; reporting only the best-performing threshold; reporting a matrix without its FP/FN counts; reporting κ without n and without the marginal distribution.

### 3.4 Small-sample honesty

If, after exclusions, n < 30 or the positive class has < 8 members, the classification analysis is reported as **descriptive only**, with κ and F1 explicitly labelled unstable, or omitted with the reason stated. The correlation and control–impact analyses stand on their own; the paper does not need a confusion matrix to be publishable, and forcing one on inadequate data would be exactly the overclaim this project forbids.

---

## 4. Secondary model (proposed, not committed)

```
field_degradation_index ~ satellite_stress + stratum + elevation + is_impact
```

**Fitted only if** ≥ 60 valid plots **and** ≥ 4 strata with ≥ 8 plots each.
**Mixed effects** (random intercept for `segment_id`) **only if** ≥ 5 segments with ≥ 5 plots each.

If the conditions are not met, the model is **not fitted**, and its absence is stated in the manuscript with the reason. It is not replaced by a simpler model chosen after seeing the data.

Rationale for the gate: with n ≈ 40 and 4 strata, a 4-predictor model has ~8 observations per estimated parameter and a random-effects variance estimated from a handful of clusters. Fitting it would produce coefficients with no inferential content and a false impression of multivariate control.

**No stepwise selection. No interaction terms not listed here. No model chosen after seeing outcomes.**

---

## 5. H4 — does the spatial contrast add discrimination?

| Element | Specification |
|---|---|
| Comparison | ROC AUC for `satellite_stress` alone vs `satellite_stress + sig_segment` |
| Test | DeLong test for correlated ROC curves, or cluster-bootstrap ΔAUC CI |
| Evidence rule | `sig_segment` must come from **real** zonal extraction. The α-decay simulated SCM path is excluded (Contract §K). |
| Interpretation | A positive ΔAUC shows the **spatial contrast** adds information. It does **not** show that the contrast identifies human causation (see `SCM_REFRAMING.md`). |

If real zonal data is unavailable for the sampled segments, **H4 is not tested** and is reported as not tested. It is not tested with simulated zones.

---

## 6. Sensitivity analyses (all pre-specified, all reported regardless of outcome)

| # | Analysis |
|---|---|
| S1 | ρ excluding plots with temporal offset 16–30 days |
| S2 | ρ excluding plots with valid-pixel fraction 70–90 % |
| S3 | ρ at 10 m NDVI-only support vs 20 m primary support |
| S4 | ρ with tread-only field mean vs corridor field mean (dilution quantification) |
| S5 | ρ under EHS weight variants (0.5/0.5 primary; 0.7/0.3; 0.3/0.7) — **reported, never used to select** |
| S6 | ρ under baseline percentile variants (P90/P10 primary; P95/P5) — same rule |
| S7 | Effect of compaction censoring at 3.0 MPa: ρ with compaction excluded from the index |
| S8 | ρ excluding plots where GPS drifted > 5 m from the planned cell centre |
| S9 | Leave-one-stratum-out stability of ρ and δ |
| S10 | ρ with erosion class dropped, if inter-observer weighted κ < 0.6 |

**S5 and S6 are reported as sensitivity, not as tuning.** The headline result always uses the frozen operational constants. If a variant performs better, that is a *finding about parameter sensitivity to report*, not a licence to change the headline. Changing any constant requires owner approval, before/after comparison and methodological rationale (change control).

---

## 7. Multiplicity

- **One primary hypothesis (H1), one primary test.** No correction applied to it.
- H2, H3, H4 are secondary and pre-specified; reported with intervals, and interpreted as a family. No p-value from a secondary analysis is presented as a headline finding.
- Sensitivity analyses (S1–S10) are **not** hypothesis tests and no p-values are attached to them.
- The manuscript states the total number of tests performed.

## 8. Handling dependence

Plots are nested in segments, segments in strata. Ignoring this inflates apparent precision. Therefore:

- Every bootstrap is a **cluster bootstrap at segment level**.
- Cross-validation folds are **whole segments**, never individual plots.
- The intraclass correlation of `field_degradation_index` within segments is estimated and reported, so a reader can judge how much independent information the sample carries.
- The **effective sample size** is reported alongside n.

## 9. Reporting standard

Every reported quantity carries: point estimate, interval, n, and the exclusions upstream of it. A CONSORT-style flow diagram accounts for every plot from planned → measured → satellite-matched → analysed, with each exclusion rule counted separately.

Results are reported **whatever they show**. A null ρ with a tight CI around zero is a real finding about the indicator's plot-scale sensitivity and is written up as such. A wide CI spanning zero is a finding about the campaign's power and is written up as such. Neither is reframed, and neither is grounds for adding analyses until something is significant.

## 10. Freeze

| Field | Value |
|---|---|
| SAP version | 0.1 (draft) |
| Frozen on | — |
| Frozen at commit | — |
| Approved by | — |

> This SAP must be frozen **before the first field observation is recorded**. Freezing it afterwards makes every choice in it unfalsifiable, and a reviewer is entitled to assume the worst.
