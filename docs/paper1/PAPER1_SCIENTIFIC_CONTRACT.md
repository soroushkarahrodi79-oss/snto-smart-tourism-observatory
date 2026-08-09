# Paper 1 — Scientific Contract

**Status:** DRAFT, awaiting owner freeze · **Version:** 0.1 · **Date:** 2026-08-09

This is the governing document for Paper 1. It is deliberately short. Once frozen, **no analysis choice may be changed without an explicit, dated amendment recorded at the bottom of this file.** Its purpose is to make it impossible to select the analysis after seeing the results.

Frozen items are marked 🔒. Items requiring an owner decision before freeze are marked 🔲.

---

## A. Working title

> **Can Sentinel-2 spectral stress track field-observed trail degradation? A control–impact validation in a Mediterranean protected mountain landscape (Sierra de Guadarrama National Park, Spain)**

The title poses a question. It does not assert an answer, and it does not use the word *causality*, *visitor*, or *carrying capacity*.

## B. Primary research question 🔒

Do Sentinel-2-derived ecological stress values (EHS) at trail locations covary with an independently measured field degradation index at co-located plots?

**This is an association question.** It is answerable with the design below. It is the only question the paper's headline claim may address.

## C. Secondary research questions 🔒

1. Are trail-corridor (impact) plots measurably more degraded than matched control plots in the same ecological stratum?
2. Does a trail-to-landscape **spatial contrast** (the SIG quantity) discriminate field degradation better than the absolute satellite stress score alone?
3. What are the sensitivity, specificity, false-positive and false-negative characteristics of the satellite indicator when used as a binary "inspect this trail" trigger?

## D. Hypotheses 🔒

| ID | Hypothesis | Direction | Test |
|---|---|---|---|
| **H1** | Satellite stress at a plot's support is positively rank-associated with the plot's field degradation index. | ρ > 0 | Spearman, primary |
| **H2** | Impact plots have higher field degradation than their stratum-matched controls. | δ > 0 | Cliff's δ, paired-by-stratum |
| **H3** | Satellite stress is higher at impact than at matched control locations. | δ > 0 | Cliff's δ on the satellite side |
| **H4** | Adding the trail-to-landscape spatial contrast improves discrimination over absolute stress alone. | ΔAUC > 0 | Pre-specified comparison, secondary |

**H0 for each is "no association / no difference."** A null result is a publishable result and the manuscript is written to accommodate it (see §Q, §R).

Note on H3 vs H2: H2 tests the *field* premise (trails are more degraded). H3 tests whether the *satellite* sees it. Both can fail independently, and distinguishing them is scientifically informative — if H2 holds and H3 fails, the satellite indicator lacks sensitivity at this scale; if H2 fails, the site selection did not capture an impact gradient and H1 is uninterpretable.

## E. Unit of analysis 🔒

**The field plot** — one georeferenced quadrat, paired to one satellite support cell.

**Not** the asset. **Not** the trail. Asset-level pairing (the current `src/ui/services/field_agreement.py` behaviour) assigns the same satellite value to every plot in an asset, which is pseudo-replication with near-total ties. It is excluded from Paper 1.

Because plots are nested within trail segments and strata, non-independence is expected and is handled explicitly in the Statistical Analysis Plan.

## F. Target population 🔲

**Recommended (default if no other decision is taken):** mapped OAPN trail segments within Parque Nacional de la Sierra de Guadarrama — the 218-trail, 1 035 km network in `data/outputs/pnsg/pipeline_a_results.geojson`, restricted to segments that are (a) legally accessible, (b) reachable within a field day, and (c) span the observed EHS range rather than clustering at its floor.

🔲 **OWNER DECISION REQUIRED — sampling frame.** Phase 0 established that the repository contains two disjoint asset universes and that the currently seeded field template targets a climbing crag and a paragliding launch site, neither of which is a trail. Three options:

| Option | Frame | Consequence |
|---|---|---|
| **F-1 (recommended)** | 218 OAPN trails (Universe B) | Matches the paper's question and title. Requires a new campaign-matched satellite acquisition (which is required anyway, §3 of the audit). Forfeits the 2021–2026 time series. |
| **F-2** | 21 curated assets (Universe A) | Inherits the defensible 5-year Mann-Kendall record — but 15 of 21 are crags, launch sites and reserves, so the paper cannot be a trail-impact study. The title and question must change. |
| **F-3** | Hybrid: trails as the frame, plus the 6 Universe-A cycling routes as a bridge | Keeps the trail framing and gains a small subset with real temporal depth. Highest scientific value, highest field cost. |

This decision changes the title, the sampling design, the satellite acquisition and the manuscript framing. **It must be made before the pilot round.** Until it is made, the rest of this contract assumes **F-1**.

## G. Exposure / predictor variables 🔒

| Variable | Definition | Evidence class | Support |
|---|---|---|---|
| `satellite_stress` | 100 − EHS at the plot's matched support cell, from a campaign-matched composite | `real` | 20 m (NDMI-limited) |
| `ndvi_plot` | Mean NDVI over the plot's support | `real` | 10 m |
| `ndmi_plot` | Mean NDMI over the plot's support | `real` | 20 m native |
| `sig_segment` | Trail-to-landscape spatial contrast for the plot's segment (H4 only) | `real` | ring buffers |
| `is_impact` | Plot is in the trail corridor (design variable) | design | — |
| `stratum` | Habitat × elevation band (design variable) | design | — |
| `elevation` | DEM at plot | `real` | 25 m |

**Explicitly excluded as predictors:** visitor counts of any kind unless directly observed during the campaign at that plot; MITMA municipal inbound trips; `annual_visitors`; `visitor_capacity_annual`; any forecast; any simulated SCM zone.

## H. Field outcome variables 🔒

Measured per plot: soil compaction (MPa, penetrometer) · vegetation cover (%, quadrat) · visible erosion class (0–3) · trail width (m) · bare-soil fraction (%) · georeferenced photograph · GPS position with recorded accuracy · stratum · observer ID · timestamp.

**Composite outcome — `field_degradation_index`, 0–100, stress direction (0 = pristine, 100 = maximally degraded).**

🔒 **Contract amendment to the existing implementation.** `src/validation/field.py::degradation_index()` currently averages whichever components happen to be present. For Paper 1 the index is **only defined when all three core components (compaction, cover, erosion) are present**; otherwise it is `None` and the plot is excluded from the primary analysis. Rationale: an index built from one component is not on the same scale as one built from three, and averaging them silently makes them look comparable. The existing permissive behaviour stays in the product; the paper uses the strict definition. See Backlog B-02.

Compaction censoring at 3.0 MPa is retained (changing it would alter existing scientific output) but is **reported as censoring** and carried into a sensitivity analysis.

## I. Primary statistical tests 🔒

1. **Spearman rank correlation** between `satellite_stress` and `field_degradation_index` across all valid plots, with a bootstrap 95 % CI (BCa, 10 000 resamples). Point estimate **and interval always reported together**; ρ is never reported bare.
2. **Cliff's δ** for impact vs control, computed **within stratum** and then combined, with a bootstrap CI.

## J. Secondary analyses 🔒

- Confusion matrix at plot level with accuracy, precision, recall, F1, Cohen's κ, and explicit FP/FN counts — under a strictly separated calibration/evaluation design (§Statistical Analysis Plan).
- H4: discrimination with vs without `sig_segment`.
- Sensitivity of ρ to each unvalidated constant in the Phase 0 audit §4 table.
- **Proposed but not committed:** `field_degradation ~ satellite_stress + stratum + elevation + is_impact`. Fitted **only if** n ≥ 60 valid plots and ≥ 4 strata with ≥ 8 plots each. Mixed effects **only if** ≥ 5 trail segments with ≥ 5 plots each. If those conditions fail, the model is not fitted and its absence is stated.

## K. Evidence classes admissible per analysis 🔒

| Analysis | Admissible classes |
|---|---|
| Primary (H1) | `real` **only**, both sides |
| Control–impact (H2, H3) | `real` **only** |
| Classification | `real` **only** |
| Spatial contrast (H4) | `real` **only** — the α-decay simulated SCM path is **excluded** |
| Context / discussion | `calibrated` permitted, explicitly labelled |
| Any analysis | `simulated`, `synthetic`, `estimated`, `missing` — **never** |

No promotion between classes is permitted at any point, for any reason.

## L. Exclusion rules 🔒

A plot is excluded if any of the following holds. Exclusions are counted, reported, and characterised in the manuscript (a CONSORT-style flow diagram):

1. GPS accuracy worse than 5 m.
2. Any of the three core field components missing (§H).
3. No valid satellite pixel at the plot's support (SCL-masked, cloud, shadow, snow, water).
4. Valid-pixel coverage of the support below 70 % (§Satellite plan).
5. Temporal offset from the matched acquisition exceeds the pre-declared maximum.
6. Plot falls outside the mapped trail network or its designated control area.
7. Impact and control plot of a pair share the same support cell — **both are excluded** (this is what makes the current template unusable as shipped).
8. Post-hoc discovery of a confounding disturbance unrelated to trail use (fire, logging, construction, landslide), recorded with a photograph.

**No plot may be excluded after its satellite value is known**, except under rule 8, which requires a photograph and a written justification recorded before unblinding.

## M. Missing-data policy 🔒

- Missing is `null`. Never 0, never imputed, never carried forward.
- Complete-case analysis for the primary test; the number and pattern of missing values reported.
- No multiple imputation in Paper 1 — the sample will be too small for its assumptions to be checkable.
- A field sheet returned with blanks is a data point about the protocol and is reported as such.

## N. Spatial-matching policy 🔒

Governed by `SPATIAL_MATCHING_PROTOCOL.md`. Contract-level commitments:

- The satellite value for a plot comes from **that plot's own location**, never from an asset-level aggregate.
- The matching support is **20 m**, set by NDMI's native B11 resolution, not by the 10 m grid the raster happens to be written on.
- Each plot is a cluster of **subplots** aggregated to the satellite support (§Spatial protocol), not a single point compared to a pixel.
- Impact and control plots of a pair must fall in **non-adjacent, non-overlapping supports**.

## O. Temporal-matching policy 🔒

Governed by `SATELLITE_FIELD_MATCHING_PLAN.md`. Contract-level commitments:

- Field observations are compared against imagery from a **campaign-matched acquisition window**, defined before the campaign.
- The existing 2025-08-10 / 2026-04-10 scene pair is **not** used for validation.
- `delta_ehs` as currently computed (backwards in time, cross-sensor, cross-year, per-scene-anchored baselines) is **not a validation target** and does not appear in the primary analysis.
- No interpolation across a missing scene. A missing acquisition means missing evidence.

## P. Claim-strength rules 🔒

The causal-claim gate, applied to every sentence in the manuscript:

> **REAL evidence + validated method + supported attribution + independent verification**

Until all four are satisfied, language is **observational / associative / hypothesis-generating**.

| Evidence state | Permitted verbs |
|---|---|
| Association measured, one park, one campaign | *is associated with*, *covaries with*, *tracks*, *is consistent with* |
| Spatial gradient measured | *the corridor shows lower NDVI than the surrounding landscape* |
| Nothing measured | *MISSING* — stated, not softened |
| Method plausible, unvalidated | *PLAUSIBLE BUT UNVALIDATED* — stated explicitly |
| Proxy used | name the proxy **and** name the target it does not measure |

Forbidden anywhere in Paper 1: *causes*, *caused by*, *driven by visitors*, *proves*, *validated carrying capacity*, *confirmed damage*, *demonstrates tourism impact*.

## Q. Stop / Go criteria for publication 🔒

**GO — proceed to submission** when all hold:

1. ≥ 30 valid plots after exclusions, with ≥ 12 impact/control pairs across ≥ 3 strata.
2. Every plot has a campaign-matched satellite value within the declared temporal window.
3. The primary Spearman ρ is reported with its bootstrap CI, whatever its value.
4. Every exclusion is accounted for in the flow diagram.
5. Every claim passes the §P gate, verified against §R by a line-by-line claim audit.
6. The analysis reruns end-to-end from raw inputs on a clean checkout.

**STOP — do not submit** if any holds:

1. Fewer than 20 valid plots (report as a pilot / data note instead).
2. Impact and control plots cannot be separated in space (rule L-7 fires broadly).
3. No temporally matched acquisition could be obtained.
4. Any analysis choice was made after seeing the outcome without a recorded amendment.
5. The classification threshold was tuned on the evaluation sample.

**A weak or null ρ is not a STOP condition.** A well-designed, honestly reported null is the second-most valuable outcome available, and this project's entire credibility rests on being willing to publish it.

## R. Claims Paper 1 will NOT make 🔒

1. That degradation is **caused by** visitors, tourism, or any specific use.
2. That the EHS indicator is **validated** in any general sense. A single-park, single-campaign association is *first empirical evidence*, not validation.
3. That any carrying capacity, LAC or ROS threshold is empirically supported.
4. That visitor pressure can be forecast. (`INSUFFICIENT_EVIDENCE` stands.)
5. That the method transfers to other parks. No transferability claim without a second park.
6. That `LOCALIZED_IMPACT` identifies human-caused change. It identifies a **spatial contrast**.
7. That MITMA municipal inbound trips measure trail footfall.
8. That the SCM thresholds (0.15 / 0.07 / 0.85 / 0.70) are validated. They are expert heuristics and are reported as such.
9. That any restoration budget figure is empirically grounded. `budget_eur` is a derived planning estimate and does not appear in Paper 1.
10. That the observatory is operationally authoritative for management decisions.
11. That satellite evidence substitutes for field monitoring. The paper's premise is the opposite.

---

## Amendment log

| Date | Amendment | Reason | Approved by |
|---|---|---|---|
| — | *(none — document not yet frozen)* | | |

> **Freeze procedure.** Owner resolves 🔲 F (sampling frame), then marks this document `FROZEN` with a date and commit hash. After freezing, changes require a dated row above, written **before** the affected analysis is re-run.
