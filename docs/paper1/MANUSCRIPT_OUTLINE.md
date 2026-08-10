# Manuscript Outline — Paper 1

**Status:** SKELETON · **Date:** 2026-08-09 · **Phase 8 deliverable**

Written from the **current verified state of the repository**, not copied from `WHITEPAPER_SNTO_Architecture_Blueprint.md` or the TFM. The whitepaper tracks the latest *stable* methodological baseline and is not a manuscript source; where this outline and the whitepaper differ, this outline reflects what the code and data actually do.

**Every quantity that does not yet exist is marked `[TBD — requires empirical result]`. No placeholder number appears anywhere in this file.** A reviewer skimming this skeleton should be able to see exactly which sentences are already supportable and which are promises.

Target length: 7 000–9 000 words. Target: one focused empirical validation study.

---

## Title

**Can Sentinel-2 spectral stress track field-observed trail degradation? A control–impact validation in a Mediterranean protected mountain landscape**

## Abstract `[TBD — write last]`

Structure (250 words): protected-area managers increasingly rely on satellite indicators for trail monitoring, but such indicators are rarely validated against field measurement in Mediterranean montane settings → we tested whether a Sentinel-2 composite stress indicator (EHS) covaries with a field degradation index at `[TBD n]` co-located plots on `[TBD n]` trail segments in Sierra de Guadarrama National Park (Spain), using a stratified control–impact design → Spearman ρ = `[TBD]` (95 % CI `[TBD]`); impact–control Cliff's δ = `[TBD]` → interpretation `[TBD]` → conclusion, stated at the strength the evidence supports, with the sub-pixel limitation named in the abstract itself.

**Abstract discipline:** no causal verb; no "validated"; the sample size and the single-park scope appear in the abstract, not only in the limitations.

---

## 1. Introduction

**1.1 Problem.** Visitor use on trails in protected areas produces soil compaction, vegetation loss and erosion. Managers need to know *where* to intervene across networks too large to survey exhaustively — PNSG alone has 1 035 km of mapped trails across 218 segments.

**1.2 Promise of Earth observation.** Sentinel-2's 5-day revisit and 10–20 m resolution make network-wide monitoring conceivable at zero marginal cost.

**1.3 The gap — the paper's motivation.** Spectral indicators for trail condition are widely proposed and rarely validated against field measurement, particularly in Mediterranean montane landscapes where phenology is water-limited and terrain is steep. Two specific under-examined issues:
- **spatial support** — trail treads (1–3 m) are sub-pixel at 10 m and strongly sub-pixel at 20 m, so any spectral indicator necessarily describes the corridor matrix rather than the tread;
- **causal framing** — spatial contrast between a trail corridor and its surroundings is routinely read as evidence of visitor impact, though a trail is a constructed feature that produces such a contrast independently of use.

**1.4 Contribution.** (i) A transparent, reproducible spectral stress formulation applied to a complete real trail network; (ii) a stratified control–impact field campaign designed to match the satellite's spatial support; (iii) an explicit error-structure characterisation (FP/FN) of the indicator as a management trigger; (iv) an evidence-provenance framework that prevents simulated and real evidence from being conflated.

**1.5 Scope statement.** This is an association study. It does not test causation, does not measure visitor numbers, and does not evaluate carrying capacity.

**1.6 Objectives and hypotheses.** H1–H4 from the Scientific Contract, stated verbatim.

---

## 2. Study area

- Parque Nacional de la Sierra de Guadarrama, Central System, Spain; established 2013; Mediterranean montane, `[TBD — confirm area, elevation range, annual visitation from official OAPN sources; do not estimate]`.
- Vegetation gradient: *Pinus sylvestris* montane forest → high-mountain shrubland → psicroxerophilous grassland.
- Trail network: **218 mapped segments, 1 035.1 km** (OAPN official cartography) — *verified*.
- Management zoning: PRUG zones (Uso Restringido / Moderado / Especial) — *verified, available per segment*.
- High visitor pressure due to proximity to Madrid `[TBD — cite official visitation statistics; do not assert without a source]`.
- Figure 1 (study area, network, plots).

---

## 3. Data

**3.1 Sentinel-2.** L2A, tile T30TVL, campaign-matched composite; window, scene IDs, sensor mix, cloud rules — all `[TBD — from the committed acquisition manifest]`. State the SCL policy including the deliberate asymmetry (class 5 retained for plot extraction, excluded from baseline computation) and its rationale.

**3.2 Trail cartography.** OAPN WFS; 218 segments; download date `[TBD]`; licence `[TBD — confirm]`. State the centreline-only limitation and that informal trails are unmapped.

**3.3 Stratification layers.** OAPN vegetation polygons + DEM; four strata (S1–S4).

**3.4 Field observations.** `[TBD]` plots, `[TBD]` impact / `[TBD]` control, `[TBD]` strata, collected `[TBD — exact dates]` within the target window (summer 2027, ~20 Jun – 31 Jul; 2028 fallback). Instruments and units per variable. Reference the published protocol and the open data deposit. State the low-early/high-late stratum ordering (§Methods) and its phenological rationale.

**3.5 Data and evidence provenance.** Present the four-class evidence framework (`real` / `calibrated` / `simulated` / `synthetic`, plus `missing`) and state that only `real` data enters any analysis in this paper. This is a genuine methodological contribution and belongs in the Data section, not buried in a footnote.

---

## 4. Methods

**4.1 Spectral indices.** NDVI = (B8 − B4)/(B8 + B4); NDMI = (B8 − B11)/(B8 + B11). State B11's native 20 m support explicitly and that resampling to 10 m changes representation, not information.

**4.2 Ecological Health Score (EHS).** Full transparent statement:
- per-scene percentile anchoring, P90 → healthy reference, P10 → floor;
- deficit computed per index, EHS = 100 × (w_NDVI·D_NDVI + w_NDMI·D_NDMI);
- weights 0.5/0.5, switching to 0.20/0.80 above NDVI 0.80 to handle saturation — presented as a **piecewise definition with a discontinuity**, not glossed over;
- reference pixels exclude SCL-masked pixels and the trail buffers themselves.
- **All constants are declared expert-defined and uncalibrated**, with a forward reference to the sensitivity analysis. Do not describe them as validated, tuned, or optimised.

**4.3 Trail buffers.** Asymmetric 15 m upslope / 60 m downslope (Wemple et al. 2001 for the principle; values expert-set); 50 m symmetric fallback, with the number of segments using the fallback reported `[TBD]`.

**4.4 Trail-to-landscape spatial contrast (SIG).** Core 0–50 m (Marion & Leung 2001), near 50–200 m, landscape 200–1 000 m; SIG definition; thresholds declared as **expert operational heuristics, not validated rules**. Terminology per `SCM_REFRAMING.md` — the words "causal" and "attribution" do not appear.

**4.5 Field degradation index.** Composite of compaction (normalised, censored at 3.0 MPa — censoring stated), cover deficit, erosion class; equal weights; **defined only when all three components are present**. Report the construct's limitations openly: equal weighting is a choice, not a derivation.

**4.6 Spatial matching.** 20 m support; 5-subplot aggregation; corridor vs tread-only means; independence rules SM-1…SM-5; extraction and provenance fields.

**4.7 Temporal matching.** Composite window; ≤ 15 d primary / 16–30 d flagged / > 30 d excluded; no interpolation under any circumstance.

**4.8 Statistical analysis.** Reproduce the SAP: Spearman with cluster-bootstrap BCa CI; within-stratum Cliff's δ; nested leave-one-cluster-out threshold calibration; ROC AUC; pre-specified sensitivity analyses. **State explicitly that the SAP was frozen before data collection**, and give the commit hash `[TBD]`.

**4.9 Reproducibility.** Software version, DOI, commit hash, data deposit `[TBD]`.

---

## 5. Field validation design

A short, standalone section — reviewers in this field will read it first and it is where the paper earns or loses trust.

- Stratified control–impact rationale; why control plots are matched by habitat, elevation, aspect and slope.
- **Two-stage design**: why no a priori power calculation was performed (no prior variance estimate existed for this index in this landscape), how the pilot estimated σ, and how the main sample size was fixed **before** the main campaign.
- **Range-spanning selection**: sites selected to span the satellite-stress range; the consequences stated plainly — ρ estimates the association where it is measurable, not the population association; selection used satellite data, field measurement was blinded.
- Blinding: what was blinded (field measurement) and what could not be (impact vs control is visually obvious).
- Repeatability: inter-observer design and results `[TBD]`.
- QA/QC and the exclusion cascade.

---

## 6. Statistical analysis

If §4.8 is complete this section may be merged into it. Keep separate only if the journal's structure favours it.

---

## 7. Results `[ALL TBD — requires empirical result]`

**7.1 Campaign description.** Plots planned / measured / excluded, with reasons — CONSORT-style flow diagram (Figure 5). `[TBD]`

**7.2 Field measurements.** Distributions by stratum and by impact/control; within-plot subplot SD. `[TBD]`

**7.3 Inter-observer repeatability.** Lin's concordance (cover); weighted κ (erosion). `[TBD]`

**7.4 Satellite–field association (H1).** ρ with CI; scatter (Figure 3). `[TBD]`

**7.5 Control–impact contrast (H2, H3).** Within-stratum δ with CIs; distributions (Figure 4). `[TBD]`

**7.6 Classification performance.** Confusion matrix, sensitivity, specificity, precision, F1, κ, ROC AUC, and the cross-fold threshold distribution — **or** an explicit statement that n was insufficient and the analysis is descriptive only. `[TBD]`

**7.7 Spatial contrast contribution (H4).** ΔAUC — **or** "not tested; real zonal data unavailable for the sampled segments". `[TBD]`

**7.8 Sensitivity analyses.** S1–S10 as a single table. `[TBD]`

**7.9 Signal dilution.** Corridor vs tread-only field means and their respective associations with the satellite value — the quantitative answer to *how much trail impact does a 20 m sensor lose?* `[TBD]`

---

## 8. Discussion `[STRUCTURE ONLY — content depends on results]`

**8.1 What the result means.** Written to accommodate three outcomes, decided by the data and not before:
- *Strong association* → the indicator has plot-scale skill in this landscape, under this design, at this scale. **Not** "EHS is validated".
- *Weak / null association with a tight CI* → the indicator lacks plot-scale sensitivity here; likely mechanisms are sub-pixel dilution and the narrow observed stress range. A genuinely useful negative result.
- *Wide CI* → the campaign was underpowered; the honest conclusion is that the question remains open, and the paper reports the variance estimate that would size a future campaign.

**8.2 Spatial support as the central methodological issue.** The dilution quantification (§7.9) generalises well beyond PNSG and is likely the paper's most transferable contribution.

**8.3 Why we do not claim causation.** The trail-is-a-built-feature argument, stated as our own objection before a reviewer states it. Alternative explanations for a trail-proximal contrast: construction, edaphic and topographic gradients, drainage, grazing, fire management.

**8.4 Comparison with prior work.** `[TBD — literature review not performed in this audit; must be done properly, not assembled from the repository's existing citations, several of which support principles rather than the specific numeric thresholds they are attached to]`

**8.5 Implications for management.** Conservative. The indicator's demonstrated role, if any, is **triage** — where to send a ranger — not **verdict**. The FP/FN structure, not the correlation, is what a manager should act on.

**8.6 Implications for the operational system.** One paragraph maximum. The observatory is the reproducibility vehicle, not a contribution.

---

## 9. Limitations

Written as a substantive section, not a defensive paragraph. Known before any data exists:

1. **Sub-pixel treads.** 1–3 m treads at 10/20 m resolution; the indicator describes the corridor matrix, not the tread.
2. **Single park, single season, single round.** No transferability claim; no temporal claim.
3. **No visitor measurement.** Use intensity is unmeasured; nothing here attributes anything to visitors.
4. **Cross-sectional design.** Association only. No before–after, no manipulation.
5. **Range-spanning selection.** ρ is not a population estimate.
6. **Observer-dependent components.** Cover and erosion are visual; repeatability is measured and reported, not assumed away.
7. **Compaction censoring at 3.0 MPa.** Severe compaction is compressed to a single value.
8. **Composite index construct.** Equal component weighting is a choice; alternatives are in the sensitivity analysis.
9. **Uncalibrated constants.** EHS percentiles, weights, canopy threshold, buffer widths and all four SCM thresholds are expert-defined. Sensitivity is reported; validation is not claimed.
10. **Centreline cartography.** Mapped centrelines may differ from the walked path; informal trails are unmapped.
11. **Small sample.** `[TBD]` plots; κ and F1 are unstable at this scale and are labelled as such.
12. **SCL class-5 asymmetry.** Bare soil retained at plots, excluded from baselines — deliberate, declared, and a potential source of bias in either direction.

---

## 10. Reproducibility and software

- SNTO, Python 3.12, version `[TBD]`, commit `[TBD]`, Zenodo concept DOI **10.5281/zenodo.20818269**.
- Analysis scripts, acquisition manifest, field CSV, and the derived analysis table deposited openly `[TBD]`.
- SAP and Scientific Contract frozen pre-collection, with commit hashes `[TBD]`.
- Scene IDs listed so the composite is regenerable by a third party.
- One paragraph. The dashboard, API, mobile client, PostGIS layer, ArcGIS integration and cloud deployment are **not** described — they are not scientific contributions and mentioning them invites scope confusion.

---

## 11. Conclusion `[TBD — requires empirical result]`

Three to five sentences. Answers the title's question at exactly the strength the data supports. Contains no verb from the forbidden list (Contract §P). States the single most useful thing a manager or a subsequent researcher should take away.

---

## Author checklist before submission

- [ ] Every numeric claim traces to a committed data file or a scene ID
- [ ] No `[TBD]` remains
- [ ] Claim audit completed line by line against Contract §R
- [ ] No forbidden verb appears anywhere, including the abstract and figure captions
- [ ] Every threshold labelled with its evidential basis
- [ ] Every in-code citation verified against the actual publication
- [ ] Analysis reruns end-to-end on a clean checkout
- [ ] Field data, analysis table and manifest deposited and cited
- [ ] SAP freeze commit hash stated in Methods
- [ ] Limitations section not softened during revision
