# Figure Plan — Paper 1

**Status:** DRAFT · **Date:** 2026-08-09 · **Phase 9 deliverable**

Seven figures + two tables. Every figure lists its **required source data** and whether that data **exists today**. Nothing here may be drawn with invented numbers; figures whose data does not exist are marked and stay unmade.

Rule applied throughout: **a figure that cannot be drawn from committed data is not a figure, it is a plan for one.**

---

## Figure 1 — Study area, trail network and plot locations

| | |
|---|---|
| **Purpose** | Orient the reader; show the sample is real and spatially distributed |
| **Panels** | (a) PNSG in Spain, inset · (b) park boundary + 218 trails coloured by satellite stress + plot pairs · (c) one zoomed pair showing impact/control geometry against the 20 m grid |
| **Required data** | Park boundary (OAPN WFS ✅ path exists) · 218 trails ✅ **exists** · `ehs_summer` per segment ✅ **exists** · plot coordinates ❌ **MISSING** · DEM hillshade ⚠️ fetchable |
| **Status** | **Partially drawable today** — (b) can be produced now from committed data; plot layer awaits the campaign |
| **Design note** | Panel (c) is the panel that earns reviewer trust: it shows visually that impact and control fall in **non-adjacent** support cells. It is also the panel the current template would fail, since its plots share coordinates. |
| **Caption must state** | Coordinate system, 20 m grid = B11 native support, trail centrelines are official cartography |

## Figure 2 — Analytical pipeline

| | |
|---|---|
| **Purpose** | Make the method auditable at a glance |
| **Content** | Sentinel-2 L2A → SCL mask → NDVI/NDMI → per-scene percentile anchors (P90/P10) → EHS at 20 m cells → plot matching (spatial + temporal gates) → field index from 5 subplots → Spearman / Cliff's δ / confusion |
| **Required data** | None — schematic |
| **Status** | ✅ **Drawable today** |
| **Design note** | Colour-code each box by evidence class (`real` / `expert-defined constant`). Exclusion gates drawn as gates, with their thresholds on the diagram. This figure is where the paper's transparency claim becomes visible; do not make it decorative. |

## Figure 3 — Satellite vs field scatter **(primary result)**

| | |
|---|---|
| **Purpose** | The paper's headline |
| **Content** | x = `satellite_stress` (100 − EHS); y = `field_degradation_index`; point shape = impact/control; colour = stratum; size = valid-pixel fraction; ρ + bootstrap CI + n annotated; per-plot subplot SD as y-error bars |
| **Required data** | Paired plot table ❌ **MISSING (requires the campaign)** |
| **Status** | ❌ Not drawable |
| **Design note** | **No fitted line unless a model was pre-specified in the SAP.** A LOESS smoother added post hoc is a visual claim the analysis plan does not license. Show the raw points and the CI. |

## Figure 4 — Impact vs control distributions

| | |
|---|---|
| **Purpose** | H2 and H3 side by side |
| **Content** | Two panels — (a) field degradation index, (b) satellite stress — each faceted by stratum; raincloud or box+jitter (never bar-and-error-bar, which hides n and shape at this sample size); paired lines where 1:1 pairs exist; Cliff's δ + CI per stratum |
| **Required data** | Same paired table ❌ **MISSING** |
| **Status** | ❌ Not drawable |
| **Design note** | Showing H2 and H3 in one figure is what lets a reader see the diagnostic case: field separation present, satellite separation absent ⇒ the sensor misses what the ground shows. |

## Figure 5 — Sample flow (CONSORT-style)

| | |
|---|---|
| **Purpose** | Account for every plot; the anti-cherry-picking figure |
| **Content** | Planned → visited → measured → satellite-matched → analysed, with each exclusion rule (L-1…L-8) as a labelled side-branch carrying its count |
| **Required data** | Campaign log + exclusion counts ❌ **MISSING** |
| **Status** | ❌ Not drawable |
| **Design note** | Reviewers of validation studies look for this early. Its absence reads as concealment even when nothing is concealed. |

## Figure 6 — Confusion matrix and error structure

| | |
|---|---|
| **Purpose** | The management-relevant result |
| **Content** | (a) 2×2 matrix with counts and marginals · (b) ROC curve with cluster-bootstrap band and AUC + CI · (c) distribution of `T_sat` across cross-validation folds |
| **Required data** | Classified plot table ❌ **MISSING** |
| **Status** | ❌ Not drawable |
| **Design note** | Panel (c) is unusual and should be kept: an unstable threshold across folds is itself the finding, and showing it pre-empts the reviewer question "how did you pick 50?". If n is insufficient (SAP §3.4), this figure is **omitted with a stated reason**, not drawn on inadequate data. |

## Figure 7 — Spatial error map

| | |
|---|---|
| **Purpose** | Where does the indicator succeed and fail? |
| **Content** | Plot locations symbolised TP / TN / **FP** / **FN**, over the trail network, with stratum shading; FP/FN emphasised |
| **Required data** | Classified plot table with coordinates ❌ **MISSING** |
| **Status** | ❌ Not drawable |
| **Design note** | If errors cluster by stratum or elevation, that is a substantive result about the indicator's operating envelope and belongs in the Discussion, not just the figure. |

## Figure 8 (optional) — Sensitivity / dilution

| | |
|---|---|
| **Purpose** | Show the conclusion does not hinge on arbitrary constants, and quantify the sub-pixel cost |
| **Content** | (a) tornado plot of ρ under S1–S10 variants, with the frozen operational setting marked · (b) ρ for corridor-mean vs tread-only field values |
| **Required data** | Plot table + re-extraction under variants ❌ **MISSING** |
| **Status** | ❌ Not drawable |
| **Design note** | Panel (b) is the visual form of the paper's most transferable finding. Mark the operational setting clearly so no reader mistakes the tornado plot for tuning. |

---

## Tables

| Table | Content | Data status |
|---|---|---|
| **T1** | Study design: strata, n planned/measured, elevation, habitat, satellite-stress range per stratum | ❌ requires campaign |
| **T2** | All constants with value, source, and evidential class (literature / expert / heuristic / locally validated) | ✅ **producible today** — the Phase 0 audit §4 table is the draft |
| **T3** | Full results: ρ, δ per stratum, classification metrics, all with CIs and n | ❌ requires campaign |
| **T4** (suppl.) | Per-plot analysis table with complete provenance (cell ID, scene IDs, offset days, valid-pixel fraction, SCL classes) | ❌ requires campaign |

**T2 is worth flagging: it is publishable today and it is unusual.** Most remote-sensing papers do not state which of their constants are literature-derived and which are expert guesses. Doing so is cheap, honest, and differentiating.

---

## What can be produced right now

Two figures and one table are drawable from committed data before a single field day:

- **Figure 1(b)** — the 218-trail network coloured by `ehs_summer` (real cartography × real Sentinel-2 signal)
- **Figure 2** — the pipeline schematic
- **Table T2** — the constants-and-provenance table

Producing these three now is a good early test of the figure-generation scripts (Backlog **B-09**) and would surface rendering and CRS problems long before they can hold up a submission.

**Everything else waits for real data. No figure in this paper will be drawn from synthetic, simulated or placeholder values, including for internal drafts** — a draft figure with plausible fake numbers has a way of surviving into a final manuscript.

---

## Figure production requirements

| Requirement | Rule |
|---|---|
| Reproducibility | Every figure generated by a committed script from committed data; no manual editing after generation |
| Provenance | Each script prints its input file checksums and the commit hash into the figure's sidecar metadata |
| Format | Vector (PDF/SVG) for line art; 300+ dpi raster only for maps |
| Colour | Colourblind-safe palettes throughout; never colour as the sole channel — pair with shape or pattern |
| Captions | State n, the evidence class of every layer, and the coordinate system for every map |
| Honesty | No axis truncation that exaggerates an effect; no smoothing not pre-specified in the SAP; no significance stars without the underlying values |
