# Field Campaign Execution Plan — PNSG (issue #26)

**Status:** DRAFT for owner approval · **Date:** 2026-08-09
**Governed by:** `PAPER1_SCIENTIFIC_CONTRACT.md` · **Spatial rules:** `SPATIAL_MATCHING_PROTOCOL.md` · **Temporal rules:** `SATELLITE_FIELD_MATCHING_PLAN.md`

This plan is executable. A researcher should be able to take §7 into the field and complete a day's work from it.

---

## 1. Audit of the existing protocol

`docs/field_validation_protocol.md` is a good scientific starting point — the control–impact logic, the stratum-matching rule and the honest "this is not a campaign already performed" framing are all correct. It is **not** ready to execute. Six defects, in order of severity:

| # | Defect | Why it blocks | Fix |
|---|---|---|---|
| **P-1** | **Control plots have no coordinates.** The shipped template gives impact and control identical `lat`/`lon`, differing only in `distance_to_trail_m`. | The field team cannot navigate to a control plot, and both plots would draw the **same satellite pixel** — the contrast is void by construction. | §4: every plot gets its own surveyed coordinate, generated before the campaign and checked for non-adjacency of supports. |
| **P-2** | **Plot size is never specified.** No quadrat dimension appears anywhere in the protocol or the code. | Without a defined plot footprint there is no defined spatial support, so satellite↔field matching is undefined (Phase 3). | §3: 20 m plot as 5 subplots of 1 × 1 m. |
| **P-3** | **The seeded targets are not trails.** Porrones is a climbing polygon; El Nevero is a paragliding point. | A trail-impact paper cannot be built on them. | Contract §F 🔲, then §2 below. |
| **P-4** | **No QA/QC, no repeatability, no observer protocol.** Vegetation cover and erosion class are visual estimates, and no inter-observer agreement is planned. | Two of the three index components are subjective. Without a repeatability estimate the measurement error is unknown and ρ cannot be interpreted. | §5, §6. |
| **P-5** | **"15–20 + 15–20" is asserted, not derived.** | It is a plausible number with no stated basis. Presenting it as a target implies a power calculation that has not been done. | §2: two-stage design. |
| **P-6** | **No temporal rule.** The protocol says "in the phenological window of the satellite scene used" but names no window, no maximum offset, and no behaviour when the scene is missing. | Field-to-image offset is uncontrolled. | `SATELLITE_FIELD_MATCHING_PLAN.md`. |

**Retained from the existing protocol unchanged:** the control–impact (BACI-simplified-to-CI) logic; stratum matching as the confound control; the seven core field variables; the stress-direction convention of the degradation index; the refusal to claim validation before data exists.

---

## 2. Sampling strategy — two-stage, because the honest alternative is false precision

No variance estimate for the field degradation index in PNSG exists anywhere — not in this repository, and (to our knowledge) not in a directly comparable published study of this landscape. **A power calculation done today would require inventing σ, and an invented σ produces an invented sample size dressed in statistical authority.** We refuse that.

Instead:

### Stage 1 — Pilot round (1–2 field days)

| Parameter | Value | Rationale |
|---|---|---|
| Impact plots | **8** | Minimum to estimate σ with a usably wide interval; deliberately not presented as an analysis sample. |
| Control plots | **8** (paired) | One per impact plot, same stratum. |
| Strata | **2** (see §3) | Tests whether stratification is operable at all. |
| Repeat plots | **3**, measured twice by two observers | Yields the inter-observer repeatability estimate (§5). |

**Pilot outputs — the only things the pilot is for:**
1. σ of `field_degradation_index` within stratum, for impact and control separately.
2. Observed effect magnitude (impact − control), as a *range*, not a point estimate.
3. Inter-observer agreement for cover (%) and erosion class.
4. Measured time per plot, including travel — the real determinant of campaign size.
5. Whether the 20 m plot geometry (§3) is physically realisable on PNSG trails, or whether terrain forces a change.

**The pilot is not analysed for H1.** Its plots may be re-used in the main sample only if the protocol did not change between rounds; if it changed, they are reported separately and excluded from the primary test.

### Stage 2 — Main campaign, sized from pilot variance

Target computed **after** the pilot, using the pilot's σ and a pre-declared minimum effect of scientific interest. Recorded as an amendment to the Scientific Contract before fieldwork resumes.

Planning envelope only, for logistics and budgeting — **not a target**:

| Scenario (from pilot) | Indicative n per group |
|---|---|
| Large separation (δ ≈ 0.6+) | ~15 |
| Moderate separation (δ ≈ 0.4) | ~25–30 |
| Small separation (δ ≈ 0.25) | ~50+ → reconsider whether the question is answerable at this scale, and say so |

The Contract's GO floor (≥ 30 valid plots, ≥ 12 pairs, ≥ 3 strata) is a **minimum for publishability**, not the target. The pilot decides the target.

### Stratification across the satellite range — mandatory, and declared

Phase 0 established that `ehs_summer` across the 218 trails has mean 11.51 on a 0–100 stress scale: the distribution is floor-concentrated. **Random sampling of trails would place almost every plot in the same narrow satellite band, making the correlation unidentifiable.** Therefore trail segments are selected to **span the EHS range** — stratified by satellite-stress tercile of the segment.

This is a deliberate range-spanning design and it has two consequences that must be stated in the manuscript, not buried:

- Spearman ρ from a range-spanning sample is **not** an estimate of ρ in the trail population. It estimates the association where the association is measurable. This is standard in calibration studies and must be labelled as such.
- Selection uses the satellite value, so the satellite value is **not** blind at the selection stage. Field measurement itself is blinded (§5) to prevent this becoming a confirmation loop.

---

## 3. Plot design

### Ecological strata

Defined **before** site selection, from PNSG cartography (habitat + elevation band + aspect), not from the satellite signal:

| Stratum | Definition | Indicative elevation |
|---|---|---|
| S1 | *Pinus sylvestris* montane forest, N-facing | 1 200–1 800 m |
| S2 | *Pinus sylvestris* montane forest, S-facing | 1 200–1 800 m |
| S3 | High-mountain shrubland (*Cytisus/Juniperus*) | 1 800–2 100 m |
| S4 | Alpine/subalpine grassland (*psicroxerophilous*) | > 2 100 m |

Pilot uses S1 and S3 (maximum contrast in structure). The stratum is recorded per plot as free text matching these codes.

### Plot geometry

**One plot = a 20 × 20 m cell aligned to the satellite support grid**, sampled by **5 subplots of 1 × 1 m**: one at the cell centre and four at the midpoints of the cell quadrants.

Rationale is fully developed in `SPATIAL_MATCHING_PROTOCOL.md`. Summary: NDMI's native support is 20 m; a single 1 m² quadrat samples ~0.25 % of a 20 m cell and would be compared against a value integrating 400 m². The 5-subplot mean is the minimum defensible aggregation.

Per-plot value = **mean of subplot values**; per-plot **SD is also recorded** and reported as within-support heterogeneity.

### Impact and control placement

- **Impact plot:** centred on the trail corridor, plot centre ≤ 5 m from the trail centreline.
- **Control plot:** same stratum, same elevation band (± 50 m), same aspect (± 45°), slope within ± 5°, **≥ 100 m from any mapped trail**, and — the binding rule — **in a non-adjacent satellite support cell** (≥ 2 cells / ≥ 40 m separation from the impact cell centre).
- Control placement is chosen **on the map before the field day** and carried as a waypoint. It is not improvised in the field.
- If the pre-planned control is unreachable or invalid on arrival, the **pair is abandoned**, not relocated ad hoc. Abandonment is recorded with a reason.

---

## 4. Pre-campaign preparation (desk work — no field day is spent on this)

1. Resolve Contract §F 🔲 (sampling frame).
2. Select trail segments stratified by satellite-stress tercile **and** ecological stratum.
3. Generate impact and control plot centroids as **real, distinct coordinates**, snapped to the satellite support grid (Backlog B-04).
4. Machine-check every pair for support non-adjacency; reject and regenerate failures. **This check is what the current template would fail.**
5. Export waypoints (GPX) and a paper backup map per field day.
6. Regenerate the field CSV template with the real coordinates — replacing the current 4-row placeholder.
7. Obtain PNSG research authorisation. *Penetrometer use involves ground insertion; confirm this is covered.* Blocking, and lead time is typically weeks.
8. Confirm the satellite acquisition window (`SATELLITE_FIELD_MATCHING_PLAN.md`) and schedule field days inside it.

---

## 5. QA/QC and repeatability protocol

| Control | Procedure |
|---|---|
| **Instrument calibration** | Penetrometer zeroed at the start of every field day; the zero reading is recorded on the sheet. Model and serial number recorded once per campaign. |
| **Compaction replication** | 5 insertions per subplot; **median** recorded (not mean — penetrometers hit stones). Refusals (stone strike) recorded as `refusal`, not as a high value. |
| **Cover estimation** | Visual %, aided by a gridded 1 m² frame. Recorded in 5 % increments — false precision below that. |
| **Inter-observer repeatability** | Both observers independently measure cover and erosion on ≥ 3 plots per campaign, without conferring. Reported as Lin's concordance (cover) and weighted κ (erosion class). **If weighted κ < 0.6 for erosion, the erosion component is dropped from the composite index and the drop is reported.** |
| **Blinding** | The observer measuring the field variables **does not know** the plot's satellite stress value, nor whether the plot is high or low on the satellite indicator. Site selection used satellite data (§2); measurement must not. |
| **Impact/control blinding** | Not possible — a trail corridor is visibly a trail corridor. This is an unavoidable limitation and is stated in the manuscript, not hidden. |
| **Photographs** | 4 per plot: N/E/S/W from centre, plus 1 vertical of the centre subplot. Filename = `plot_id`. Every photograph geotagged. |
| **GPS** | Position averaged over ≥ 60 s; **accuracy value recorded**. > 5 m → plot excluded (Contract L-1). |
| **Same-day digitisation** | Paper sheets transcribed to CSV the same evening; **originals photographed and archived**. Transcription independently checked against the photographs for ≥ 20 % of rows. |
| **Automated QA** | Every CSV passes the field-QA runner (Backlog B-03) before analysis: ranges, duplicate plot IDs, orphan pairs, shared coordinates, missing photos, impossible values. |

---

## 6. Missing-value handling in the field

- A value that could not be measured is left **blank**. Never 0, never "approx", never a guess.
- The **reason** is recorded in the sheet's `notes` column (e.g. `compaction: bedrock`).
- A plot missing any of the three core components is still submitted — it is excluded at analysis (Contract L-2) and counted in the flow diagram. Field teams must not self-censor.
- Systematic inability to measure a component (e.g. compaction refusals on rocky S4 grassland) is a **finding about the method's operating envelope** and is reported as such.

---

## 7. Field-day operational checklist

### Night before

- [ ] Weather checked; ≥ 48 h since significant rain (soil moisture affects penetrometer readings — recent rain invalidates the day for compaction)
- [ ] Waypoints loaded on GPS **and** phone; paper map printed
- [ ] Field sheets printed (2 per planned plot) on waterproof paper
- [ ] Penetrometer, 1 m² gridded quadrat frame, 30 m tape, clinometer, compass, camera/phone charged, spare battery
- [ ] Research authorisation carried (paper copy)
- [ ] Route plan and expected return time left with a third party

### On arrival at each plot

- [ ] Navigate to the pre-planned coordinate — **do not relocate for convenience**
- [ ] GPS averaged ≥ 60 s; **record position and accuracy**
- [ ] If accuracy > 5 m: record and mark the plot as excluded; continue anyway (the data still documents the site)
- [ ] Photograph N / E / S / W + vertical centre
- [ ] Record: `plot_id`, `is_control`, `stratum`, `observed_at` (date **and** time), observer ID, slope, aspect, elevation
- [ ] Record `distance_to_trail_m` (measured with tape for impact plots, from map for controls)
- [ ] Record `trail_width_m` at the plot (impact plots only — blank for controls, not 0)

### Per subplot (×5)

- [ ] Place the 1 m² frame at the designated position
- [ ] Vegetation cover %, in 5 % increments
- [ ] Bare-soil %
- [ ] Erosion class 0–3 (0 none / 1 light / 2 moderate / 3 severe)
- [ ] Penetrometer: 5 insertions, record all five, note refusals
- [ ] Note any confounding disturbance (fire, logging, works, landslide, livestock) **with a photograph**

### Before leaving the plot

- [ ] All fields either filled or explicitly blank-with-reason
- [ ] Photograph the completed sheet
- [ ] Confirm the paired plot (impact ↔ control) is scheduled for the **same day** — pairs split across days are recorded as such and flagged

### End of day

- [ ] Transcribe to CSV; archive photographs by `plot_id`
- [ ] Run the field-QA script; resolve or record every warning
- [ ] Log: total plots, plots abandoned and why, weather, hours in field
- [ ] **Do not look at satellite values for the measured plots** until the campaign is closed

### Campaign close-out

- [ ] All CSVs merged and QA-passed
- [ ] Repeatability statistics computed and recorded
- [ ] Field CSV committed as the frozen ground-truth record, with a checksum
- [ ] **Only then** is satellite extraction run

---

## 8. Multi-day campaign shape (indicative)

| Day | Activity | Output |
|---|---|---|
| **D1** | Pilot, stratum S1 — 4 impact + 4 control + 2 repeats | Timing, σ estimate |
| **D2** | Pilot, stratum S3 — 4 impact + 4 control + 1 repeat | Cross-stratum σ, repeatability |
| **Desk** | Compute σ, effect range, per-plot time; **fix the main sample size**; amend the Contract | Frozen sample size |
| **D3–Dn** | Main campaign, ≥ 3 strata, spanning EHS terciles | Ground-truth dataset |
| **Close** | QA, freeze, checksum | Analysis-ready CSV |

Expect **6–10 plots per field day** including travel on PNSG terrain, at roughly 45–60 min per plot plus walking. The pilot replaces this estimate with a measured one — that is one of its five purposes.

---

## 9. What this campaign will and will not deliver

**Will deliver:** the first real ground-truth dataset in the project's history · an empirical association estimate with an honest confidence interval · a measured control–impact contrast · a plot-level error structure for the satellite indicator · a measured repeatability figure for the field index · a documented operating envelope for the method.

**Will not deliver:** causal attribution to visitors (no visitor measurement, no manipulation, no counterfactual) · temporal validation (single round, no before–after) · transferability to other parks (one park) · validation of any threshold not calibrated out-of-sample · a validated carrying capacity.

The campaign answers **one** question well. That is the point.
