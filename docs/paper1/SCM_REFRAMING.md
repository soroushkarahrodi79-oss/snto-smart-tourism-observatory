# SCM Reframing — spatial contrast is not causal attribution

**Status:** DRAFT for owner approval · **Date:** 2026-08-09 · **Phase 6 deliverable**

**This document changes no code and no threshold.** It establishes the terminology and evidence status the SCM carries into Paper 1.

---

## 1. What the module actually computes

`src/spatial_causality/analyzer.py` and `run_scm_operational.py` compute a **spatial impact gradient**:

```
SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)
```

over three concentric rings around a trail axis (core 0–50 m, near 50–200 m, landscape 200–1 000 m), plus the Pearson correlation between the core and landscape series where a temporal series exists. It then maps those two numbers onto three labels: `LOCALIZED_IMPACT`, `MIXED`, `LANDSCAPE_DRIVEN`.

Stated without interpretation: **SIG measures how much lower the vegetation index is near the trail than far from it.** That is a real, measurable spatial contrast, and on the 218 PNSG trails it is computed from real rasters over real ring buffers — genuine measurement, not simulation.

## 2. What it does not compute

The inferential chain the module's naming implies is:

> vegetation is lower near trails → this is *localized* → localized means *human* → human means *tourism/visitors* → therefore visitor pressure caused the degradation.

Each arrow is an assumption:

| Step | Status | Why |
|---|---|---|
| Contrast is real | **Measured** | Real zonal NDVI, real buffers |
| Contrast is spatially localized | **Measured** | That is what SIG is |
| Localized ⇒ human-caused | **Assumption** | Localized contrasts also arise from soil depth, bedrock outcrop, aspect, slope, drainage, natural clearings, roads, livestock, firebreaks, and — critically — **the trail's own physical construction**, independent of any current use |
| Human ⇒ tourism/visitors | **Assumption** | No visitor measurement is ingested anywhere in the live decision layer |
| Association ⇒ causation | **Not established** | No manipulation, no counterfactual, no temporal before–after at the plot scale |

There is also an inherent circularity that must be stated: a trail is a *built linear feature*. Vegetation is lower on a trail because a trail exists there. SIG will be positive at a trail whether or not a single person has walked it this decade. **SIG detects the trail, not necessarily its use.** This is the strongest single objection a reviewer will raise, and the manuscript must raise it first.

The current UI text already fails this test: `docs/audit/2026-snto-baseline/SCIENTIFIC_CLAIMS_REGISTER.md` C-01 and C-02 record *"measurable environmental damage caused by visitor pressure"* and *"changes appear to be driven by natural climate variability"* as **MISLEADING** — the second being an argument from ignorance (absence of a localized signal asserted as positive evidence of climatic causation). Owner decision Q-02 suspended that text. Paper 1 must not reintroduce it in scientific prose.

## 3. Terminology for the manuscript

| Do not write | Write instead |
|---|---|
| Spatial Causality Module | **trail-to-landscape spatial contrast**; or *spatial attribution heuristic* when describing the classifier |
| `LOCALIZED_IMPACT` | *localized spatial contrast* / *trail-proximal vegetation deficit* |
| `LANDSCAPE_DRIVEN` | *landscape-scale pattern* / *no detectable trail-proximal contrast* |
| causal attribution | **spatial pattern classification** |
| "caused by visitor pressure" | "co-located with the trail corridor" |
| "human pressure alerts" | "trail-proximal contrast flags" |
| "confirms tourism impact" | "is consistent with trail-associated vegetation difference; alternative explanations are not excluded" |

**Recommendation on renaming production code: do not rename.** `src/spatial_causality/` is referenced across the persistence layer, the reporting layer, the PRUG monitoring roll-up, the dossier automation and the tests. A rename would be a large, risky, scientifically empty diff. The manuscript uses correct language; the code keeps its name with a corrected module docstring stating plainly what it measures and what it does not (Backlog **B-08** — docstring only, no behaviour change).

## 4. Threshold provenance

Required by Phase 6: classify every SCM constant by evidential basis.

| Constant | Value | Basis | Classification |
|---|---|---|---|
| `CORE_OUTER_M` | 50 m | Marion & Leung (2001), *J. Park & Recreation Administration* 19(3):17–37 — cited in-module for the 0–50 m hiking-trail impact zone | **Literature-backed** ¹ |
| `NEAR_OUTER_M` | 200 m | No citation | **Expert-defined** |
| Landscape outer | 1 000 m | No citation | **Expert-defined** |
| `_SIG_LOCALIZED` | 0.15 | No citation, no calibration | **Experimental heuristic** |
| `_SIG_LANDSCAPE` | 0.07 | No citation, no calibration | **Experimental heuristic** |
| `_CORR_LANDSCAPE` | 0.85 | No citation, no calibration | **Experimental heuristic** |
| `_CORR_LOCALIZED` | 0.70 | No citation, no calibration | **Experimental heuristic** |
| Asymmetric buffer 15 m / 60 m | — | Wemple et al. (2001) cited for the *principle* that downslope effects extend further; the specific values are not derived from it | **Expert-defined**, literature-motivated |
| Symmetric fallback 50 m | — | Convention | **Expert-defined** |
| α-decay zone simulation | — | Derived from the human-pressure proxy | **Simulated** — excluded from Paper 1 entirely |

**Locally validated: none.** No SCM threshold has ever been checked against a PNSG field observation. That is precisely what issue #26 exists to change, and until it does, every one of the four decision thresholds is an expert heuristic quoted to two decimal places.

¹ *Citation accuracy was not independently verified against the sources in this audit; the classification records what the module cites, not that the citation supports the exact numeric value.* Before submission, every in-code citation must be checked against the actual publication — a threshold attributed to a paper that does not contain it is a serious integrity problem, and the check is cheap.

## 5. Role in Paper 1

| Use | Admitted? |
|---|---|
| `sig_segment` as a secondary predictor (H4), from a **fresh** real zonal extraction against the campaign-matched composite (`SATELLITE_FIELD_MATCHING_PLAN.md` §6, Backlog B-14) | **Yes** |
| `sig_segment` from the **existing** `scm_class`/SIG already computed on the 218 trails (`run_scm_operational.py`, using `spring_raster.tif`/`summer_raster.tif`) | **No** — real extraction, but from the same disqualified 2025-08-10/2026-04-10 pair as `delta_ehs`. Genuinely real ≠ temporally usable. |
| SIG described as a spatial contrast | **Yes** |
| SIG described as causal attribution | **No** |
| `LOCALIZED_IMPACT` counts reported as human-impact counts | **No** |
| α-decay simulated zones in any analysis | **No** |
| SCM thresholds presented as validated | **No** |
| SCM threshold sensitivity analysis | **Yes, required** |

If H4 shows that adding `sig_segment` improves discrimination of *field-measured* degradation, that is a meaningful result: the spatial contrast carries information about ground condition beyond the absolute index. It still does not identify the cause.

## 6. Draft manuscript text

> The trail-to-landscape spatial contrast (SIG) quantifies the relative difference in vegetation index between a trail-proximal core zone (0–50 m) and a surrounding landscape reference (200–1 000 m). The core-zone radius follows established trail-impact literature; the classification thresholds applied to SIG are expert-defined operational heuristics that have not been empirically calibrated, and are treated here as such.
>
> We emphasise that a localized spatial contrast is not evidence of causation. Trails are constructed linear features, and reduced vegetation cover along a trail corridor is expected from the physical existence of the trail independently of current visitor use. Edaphic, topographic and management factors — soil depth, bedrock exposure, aspect, drainage, grazing and fire management — produce comparable localized contrasts. This study therefore reports SIG as a spatial descriptor and as a candidate predictor of field-measured degradation. It makes no attribution to visitor pressure, which is not measured in this study and for which no operational data source is currently ingested.

## 7. Product-side implications (owner, not Paper 1)

Recorded for completeness; none is a Paper-1 task:

1. Suspended KPI-7 text (Q-02) must not return in its previous form.
2. Reports emitting `LOCALIZED_IMPACT` should carry the same caveat as §6.
3. The four SCM thresholds should carry an in-code marker of their evidential status, so downstream consumers can gate on it.
4. In-code citations should be verified (§4, note 1).
5. If real GEE zones are ever exported to `src/spatial_causality/zones/`, the SCM's evidence class rises from `simulated` to `real` on the Universe-A path — **but its causal status does not change at all.** Better data about a spatial gradient is still data about a spatial gradient.
