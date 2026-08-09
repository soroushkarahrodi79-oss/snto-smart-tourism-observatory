# Spatial Matching Protocol — plot ↔ satellite support

**Status:** DRAFT for owner approval · **Date:** 2026-08-09 · **Phase 3 deliverable**

**No scientific threshold is changed by this document.** It defines how a field plot is matched to a satellite value, and it documents a spatial-support mismatch that is currently unaddressed anywhere in the repository.

---

## 1. The verified spatial facts

| Quantity | Value | Source |
|---|---|---|
| B04 (Red), B08 (NIR) native GSD | **10 m** | `prepare_raster.py` — `_B04_10m.jp2`, `_B08_10m.jp2` |
| B11 (SWIR) native GSD | **20 m** | `prepare_raster.py` — `_B11_20m.jp2` |
| B11 handling | Resampled to the 10 m B04 reference grid | `prepare_raster.py:421–427` |
| NDVI support | 10 m (100 m² per pixel) | derived |
| **NDMI support** | **20 m (400 m² per effective cell)** | derived — resampling changes representation, not information |
| Trail buffer (asymmetric) | 15 m upslope / 60 m downslope → **75 m wide corridor** | `etl_raster_intersection.py:53–54` |
| Trail buffer (fallback) | 50 m symmetric → 100 m wide | `:55` |
| SCM core zone | 0–50 m | `analyzer.py:107` |
| SCM near zone | 50–200 m | `:108` |
| SCM landscape zone | 200–1 000 m | docstring |
| Zonal extraction rule | `all_touched=False` — pixel centre must fall inside | `etl_raster_intersection.py:172` |
| Field plot size | **undefined anywhere in the repository** | — |
| Typical PNSG trail tread width | ~1–3 m | field expectation; to be measured |

## 2. The mismatch, stated plainly

**A Sentinel-2 pixel cannot see a trail tread.**

A 2 m-wide trail crossing a 10 m NDVI pixel occupies at most **20 %** of that pixel's area. In a 20 m NDMI cell it occupies at most **10 %**. The remaining 80–90 % of the signal comes from the vegetation matrix beside the trail. The trail tread is a **sub-pixel feature** at both bands, and it is more sub-pixel at the band (NDMI) that currently carries half the EHS weight — and 80 % of it under dense canopy.

Three consequences follow, and all three must be stated in the manuscript:

1. **EHS at a trail is not a measurement of the trail surface.** It is a measurement of the *corridor's vegetation condition*, of which the tread is a minority component. Any claim that EHS "detects trail degradation" is, at this resolution, a claim about corridor-scale vegetation state.
2. **Signal dilution biases the association toward the null.** If field measurement targets only the tread while the satellite integrates 100–400 m², the two quantities describe different things and a weak ρ would be uninterpretable — is the indicator insensitive, or were the wrong things compared?
3. **The 75 m-wide asymmetric buffer is far wider than the satellite support.** It integrates ~7 NDVI pixels across-track, deliberately including the off-trail matrix. This is a *defensible* design for a corridor-condition indicator, but it makes the "core zone" a corridor, not a tread — reinforcing point 1.

**This mismatch is a property of Sentinel-2, not a defect in SNTO.** It cannot be engineered away. It can only be handled by matching the field measurement to the satellite's support, and by saying clearly what is being measured.

## 3. Resolution: match the field to the support, not the support to the field

### The matching support

**20 m**, set by NDMI's native B11 resolution.

Using the 10 m grid would be a false-precision error: B11 has been *resampled*, not *resolved*. Two adjacent 10 m cells drawing on the same original 20 m B11 observation are not independent. All plot↔pixel matching therefore operates on **20 m cells aligned to the native B11 grid in EPSG:25830**.

NDVI is additionally reported at 10 m as a secondary predictor with its finer support declared, so a reviewer can see whether the association differs by band and by scale.

### The plot as a cluster

**One plot = one 20 × 20 m cell, sampled by 5 subplots of 1 × 1 m.**

- Subplot 0: cell centre
- Subplots 1–4: centres of the four quadrants

Coverage: 5 m² of 400 m² = **1.25 %** of the support. Low, but a defensible spatial sample of a cell; a single 1 m² quadrat would be 0.25 % and positioned arbitrarily.

Plot value = **mean of subplot values**. Plot **SD is recorded and reported** as within-support heterogeneity, and is used to distinguish "the satellite disagrees with the field" from "the field is heterogeneous within the support".

### Impact plots must sample the corridor, not only the tread

This follows directly from §2 and is the single most important design consequence in this document.

For an **impact** plot the 5 subplots are placed so that the sample reflects the corridor composition the satellite integrates:

| Subplot | Position |
|---|---|
| A | On the tread, cell centre |
| B | On the tread, 5 m along |
| C | Verge, ~2 m from the tread edge (downslope side) |
| D | Verge, ~2 m from the tread edge (upslope side) |
| E | Matrix, ~8 m from the tread, still inside the cell |

The **tread-only** mean (A, B) and the **corridor** mean (A–E) are both computed and both stored.

**The corridor mean is the primary field outcome** — it is what the satellite support corresponds to. The tread-only mean is reported as a secondary outcome, and the difference between them quantifies the dilution effect empirically. That comparison is, in itself, a genuine contribution: *how much trail impact does a 20 m sensor lose?*

For a **control** plot the 5 subplots are distributed evenly across the cell (no tread exists).

### Alignment rule

Plot centroids are **snapped to 20 m cell centres** on the native B11 grid before the field campaign, so that:
- each plot corresponds to exactly one satellite cell;
- no plot straddles a cell boundary;
- impact/control non-adjacency (§4) is checkable on the map, before anyone walks anywhere.

Implementation: Backlog **B-04**.

## 4. Independence rules

| Rule | Requirement | Consequence if violated |
|---|---|---|
| **SM-1** | An impact plot and its control must fall in **non-adjacent** 20 m cells (centre separation ≥ 40 m). | Pair excluded (Contract L-7). This is what the current template violates — identical coordinates. |
| **SM-2** | No two plots in the analysis may share a 20 m cell. | Later plot excluded; pseudo-replication. |
| **SM-3** | A control plot must be ≥ 100 m from **any** mapped trail in the 218-trail network — not merely its own trail. | Plot excluded; contamination by an unconsidered trail. |
| **SM-4** | A plot must be ≥ 1 cell inside the raster footprint (no edge cells). | Plot excluded; edge resampling artefacts. |
| **SM-5** | Plots within the same trail segment are **not** independent replicates and are modelled as clustered. | Statistical, not exclusionary — see the Statistical Analysis Plan. |

All five are machine-checkable before the campaign, and all five are re-checked after the campaign against the *actual* recorded GPS positions, which may differ from the planned ones.

## 5. Extraction rule (post-campaign)

For each plot, from the campaign-matched composite:

1. Take the 20 m B11-grid cell containing the recorded GPS position (not the planned position).
2. Require valid-pixel coverage ≥ 70 % after SCL masking, else exclude (Contract L-4).
3. Extract NDVI (mean of the four constituent 10 m pixels), NDMI (the 20 m cell), and EHS computed from them under the frozen constants.
4. Record: cell ID, cell centre coordinates, distance from GPS position to cell centre, valid-pixel fraction, SCL classes present, source scene ID(s).
5. Store one row per plot. **No aggregation to asset level at any point.**

Every one of those provenance fields is written to the analysis table, so a reviewer can audit any single plot back to its pixel and its scene.

## 6. Sensitivity analyses required by this protocol

Because the support choice is a judgement, the manuscript reports the primary result **and** its sensitivity to that judgement:

| Analysis | Purpose |
|---|---|
| ρ at 20 m support (primary) vs 10 m NDVI-only support | Does the conclusion depend on the support choice? |
| Corridor field mean vs tread-only field mean | Quantifies signal dilution empirically |
| Plot SD vs \|satellite − field\| residual | Does disagreement track within-cell heterogeneity? |
| Excluding plots with valid-pixel fraction 70–90 % | Robustness to partial masking |
| Excluding plots whose GPS drifted > 5 m from the planned cell centre | Robustness to positional error |

## 7. What this protocol does not fix

- **It does not make Sentinel-2 resolve a trail tread.** Nothing does. A study of the tread itself needs sub-metre imagery (drone/UAV or VHR commercial) — a legitimate follow-up, out of Paper-1 scope.
- **It does not remove mixed-pixel effects**; it makes them explicit and measures them.
- **It does not eliminate spatial autocorrelation** between nearby plots; that is handled statistically.
- **It does not validate the 15/60 m asymmetric buffer.** That parameter governs the operational product, not the plot-level validation, and remains an expert setting (Phase 0 audit §4).

## 8. Limitation text for the manuscript (draft)

> Sentinel-2 resolves the ground at 10 m (B4/B8) and 20 m (B11). PNSG trail treads are typically 1–3 m wide and are therefore sub-pixel features at both resolutions, occupying at most 20 % of a 10 m pixel and 10 % of a 20 m cell. The spectral indicator evaluated here consequently describes the condition of the **trail corridor's vegetation matrix**, within which the tread is a minority component, rather than the tread surface itself. Field sampling was designed to match this support: each plot aggregates five subplots distributed across a 20 m cell spanning tread, verge and adjacent matrix. Tread-only measurements were retained separately to quantify the resulting dilution. This design makes the comparison scale-consistent but does not confer sub-pixel sensitivity, and results should not be read as detection of tread-level impact.
