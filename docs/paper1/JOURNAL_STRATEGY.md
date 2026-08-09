# Journal Strategy — Paper 1

**Status:** DRAFT for owner decision · **Date:** 2026-08-09 · **Phase 10 deliverable**

Journals are assessed on **fit, required novelty, validation expectations, rejection risk and manuscript positioning** — not impact factor. Metrics change yearly and are deliberately not quoted here; check current values at submission time.

**An important dependency:** the best target depends on what the data shows. A clear positive association, a clear null, and an underpowered result are three different papers with three different natural homes. The decision is therefore **staged** (§6), not made now.

---

## 1. The manuscript's honest profile

Before assessing fit, an honest self-description — journals are chosen against this, not against an aspiration:

| Dimension | Reality |
|---|---|
| Methodological novelty | **Low–moderate.** NDVI/NDMI, Mann-Kendall, control–impact designs and Cliff's δ are all established. The EHS composite is a transparent recombination, not a new algorithm. |
| Validation novelty | **Moderate–high.** Field-validated spectral trail-condition indicators in Mediterranean montane protected areas are genuinely scarce. This is the paper's real currency. |
| Scale | **Single park, single season, single round.** |
| Sample size | **Small** (tens of plots). |
| Application relevance | **High.** National park, official cartography, real management zoning, a decision-support context. |
| Reproducibility | **High and unusually well documented.** Open code, DOI, frozen SAP, committed provenance. |
| Causal claim | **None** — deliberately. |
| Distinctive angles | (a) Explicit sub-pixel support analysis and dilution quantification; (b) a machine-enforced evidence-provenance framework; (c) willingness to publish a null. |

**Where this profile is strongest: applied validation with methodological honesty.** Where it is weakest: novelty of technique and sample size. Target journals that reward the former and tolerate the latter.

---

## 2. Candidate assessment

### 2.1 *Remote Sensing Applications: Society and Environment* (RSASE) — **recommended primary**

| Criterion | Assessment |
|---|---|
| Scope fit | **Excellent.** Applied EO for environmental and societal problems is precisely the remit. |
| Required novelty | **Moderate** — application novelty accepted; a new algorithm is not required. |
| Validation expectations | **Strong fit.** Field validation is welcomed rather than treated as a hurdle. |
| Tolerance of small n | **Good**, if the design is rigorous and limitations are explicit. |
| Null-result tolerance | **Moderate** — helped considerably by the pre-registered SAP. |
| Rejection risk | **Moderate-low** |
| Positioning | *"First field validation of a Sentinel-2 trail-condition indicator in a Mediterranean protected mountain landscape, with explicit spatial-support analysis."* |
| Risk | Perceived as incremental if the sub-pixel/dilution contribution is not made central. **Mitigation: lead with it.** |

### 2.2 *Ecological Indicators* — strong alternative, higher bar

| Criterion | Assessment |
|---|---|
| Scope fit | **Very good** — indicator development and validation is the journal's core. |
| Required novelty | **High.** Expects the indicator itself to be a contribution, and reviewers will press hard on whether EHS is a genuinely new indicator or a recombination of NDVI/NDMI. It is closer to the latter, and the paper should not pretend otherwise. |
| Validation expectations | **High** — likely to want larger n, and quite possibly temporal replication. |
| Tolerance of small n | **Low–moderate.** The most likely rejection reason. |
| Null-result tolerance | **Low.** A journal about useful indicators is a difficult home for "this indicator has limited plot-scale skill". |
| Rejection risk | **Moderate-high**, especially if n < 40 |
| Positioning | *"A transparent composite spectral stress indicator with declared uncertainty and empirical field agreement."* |
| Verdict | **Best home for a strong positive result with n ≥ 40.** Poor home for a null. |

### 2.3 *Journal of Outdoor Recreation and Tourism* (JORT) — best domain fit, weakest EO fit

| Criterion | Assessment |
|---|---|
| Scope fit | **Excellent on the domain side** — trail impact, recreation ecology, visitor management are core. |
| Required novelty | **Moderate** |
| Validation expectations | **Moderate.** Recreation-ecology reviewers know trail impact deeply and will scrutinise the field protocol closely — which this design should survive well. |
| Tolerance of small n | **Good.** Plot counts in the tens are normal in recreation ecology. |
| Null-result tolerance | **Good** — a well-designed null about remote-sensing limits is genuinely interesting to this readership. |
| Rejection risk | **Low–moderate** |
| Positioning | *"Can remote sensing substitute for field monitoring of trail condition? A control–impact test."* |
| Risk | Reviewers may be less equipped to assess the EO methodology, which cuts both ways — less depth of scrutiny, but also less credit for the EO contribution. |
| Note | The paper would need reframing toward the management question. That reframing is honest and easy. |

### 2.4 *Journal of Environmental Management* (JEM) — broadest reach, weakest fit

| Criterion | Assessment |
|---|---|
| Scope fit | **Moderate.** Broad; expects a clear management-decision contribution. |
| Required novelty | **High**, and specifically *management* novelty. |
| Validation expectations | **Moderate** |
| Tolerance of small n | **Moderate** |
| Null-result tolerance | **Low–moderate** |
| Rejection risk | **High** — a single-park, small-n validation study is likely to be desk-rejected as too narrow. |
| Positioning | Would require framing around the decision framework rather than the validation, which pulls in exactly the cloud/API/product scope Paper 1 is meant to exclude. |
| Verdict | **Not recommended for Paper 1.** A better home for a later paper about the decision-support system, once validation exists. |

---

## 3. Comparison

| | RSASE | Ecological Indicators | JORT | JEM |
|---|---|---|---|---|
| Scope fit | ●●●● | ●●●● | ●●●● | ●● |
| Novelty bar | ●● | ●●●● | ●● | ●●●● |
| Small-n tolerance | ●●● | ●● | ●●●● | ●●● |
| Null tolerance | ●●● | ● | ●●●● | ●● |
| EO expertise in review | ●●●● | ●●●● | ●● | ●● |
| Trail-ecology expertise | ●● | ●●● | ●●●● | ●● |
| **Rejection risk** | **Moderate-low** | **Moderate-high** | **Low-moderate** | **High** |

---

## 4. Recommendation

**Primary: RSASE.** It is the only candidate that scores well on scope, novelty bar, small-n tolerance *and* EO reviewer expertise simultaneously. The applied-validation framing is exactly what it publishes.

**Escalate to *Ecological Indicators* only if** the result is a clear positive association **and** n ≥ 40 **and** the sub-pixel/dilution analysis is developed into a substantive methodological section. Otherwise the higher novelty bar and low null-tolerance make it a costly first attempt.

**Fall back to JORT if** the result is null, the sample is small, or RSASE rejects on scope. JORT is not a lesser outcome — for a null result it is arguably the *better* venue, because the finding "remote sensing does not yet replace field monitoring at trail scale" matters most to that readership.

**Do not target JEM for Paper 1.**

---

## 5. Positioning by outcome

| Outcome | Framing | Venue |
|---|---|---|
| Strong association (ρ ≳ 0.6, tight CI, n ≥ 40) | "First field-validated spectral trail-condition indicator for Mediterranean montane protected areas" | Ecological Indicators → RSASE |
| Moderate association | "Spectral indicators show partial agreement with field degradation; useful for triage, not verdict" | **RSASE** |
| Null with tight CI | "Sentinel-2 spectral indicators do not resolve trail-scale degradation: a sub-pixel support analysis" | **JORT** or RSASE |
| Underpowered (wide CI) | Reframe as a **pilot / data note**: publish the protocol, the variance estimates and the sizing calculation for future campaigns | Data-descriptor or protocol venue; do **not** submit as a validation study |

The last row is the discipline that matters most. **An underpowered result must not be dressed as a validation study.** Publishing the pilot honestly is a real contribution and preserves the ability to publish the main campaign later.

---

## 6. Decision sequence

1. **Do not choose a journal now.** Choosing before results is how results get shaped to fit venues.
2. Complete the campaign and the locked analysis.
3. Run the claim audit against Contract §R.
4. Classify the outcome against §5.
5. Select the venue; write to its structure.
6. **Consider preprint deposition** (EarthArXiv / EcoEvoRxiv) at submission — consistent with the project's two-track publication policy (`docs/PUBLICATION_STRATEGY.md` Pista B) and it timestamps the pre-registered design.

## 7. Pre-submission requirements (venue-independent)

- [ ] SAP frozen **before** data collection, hash stated in Methods
- [ ] Claim audit complete against Contract §R
- [ ] Field data, analysis table and acquisition manifest openly deposited
- [ ] Code DOI (Zenodo concept **10.5281/zenodo.20818269**) cited
- [ ] Every in-code citation verified against the actual publication (`SCM_REFRAMING.md` §4 note 1)
- [ ] A genuine literature review performed — **not** assembled from the repository's existing citation set
- [ ] Native/professional English review
- [ ] Co-authorship, PNSG/OAPN acknowledgement and any data-sharing conditions agreed **before** submission

## 8. Explicitly out of the manuscript, whatever the venue

Cloud infrastructure · Azure · FastAPI deployment · mobile client · RBAC/SSO/tenancy · ArcGIS Experience Builder · PostGIS · OpenAPI contract · commercial pilot packaging · CETS accreditation · LAC/ROS carrying capacity · visitor forecasting · SVI trends · OAPN cross-park benchmarking.

These may appear **only** as a single sentence in §Reproducibility naming the software. Every one of them, if given room, converts a focused validation paper into an unfocused systems paper — which is the failure mode this whole exercise exists to prevent.
