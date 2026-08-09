# Phase 0 — Factual Repository Audit (Paper 1 scope)

**Audit date:** 2026-08-09 · **Branch audited:** `main` @ `c1661e1` · **Auditor mode:** implementation- and data-first; documentation treated as a claim to be tested, not as evidence.

This document classifies every Paper-1-relevant capability. It **supersedes documentation prose where the two disagree**, and every contradiction found is recorded in §7.

It does **not** duplicate `docs/audit/2026-snto-baseline/` (the Phase 0 system baseline, PR #143). That audit is broader (UI, KPIs, maps, claims) and remains valid. This one is narrower and deeper: it asks only *"what can Paper 1 actually stand on?"*

Legend:

| Status | Meaning |
|---|---|
| **READY** | Implemented, tested, and the data it needs exists. Usable in Paper 1 as-is. |
| **PARTIAL** | Implemented but with a defect, a scope mismatch, or an unvalidated constant that must be resolved before use. |
| **BLOCKED_BY_EVIDENCE** | Code is fine; the empirical input does not exist. No code change unblocks it. |
| **NOT_NEEDED_FOR_PAPER_1** | Real capability, out of manuscript scope. |

---

## 1. The single most important finding: two disjoint asset universes

Everything else in this audit follows from this. SNTO does not have one satellite dataset over one set of places. It has **two**, they do not overlap, and different parts of the validation stack are wired to different ones.

| | **Universe A — "curated assets"** | **Universe B — "OAPN trails"** |
|---|---|---|
| File | `clean_assets/pnsg_assets.geojson` | `data/outputs/pnsg/pipeline_a_results.geojson` |
| n | **21** | **218** |
| Geometry | 12 Polygon, 6 LineString, 3 Point | 197 LineString, 21 MultiLineString (1 035.1 km) |
| What they are | 7 climbing crags, 6 cycling routes, 3 paragliding launch sites, 5 nature reserves | Real OAPN trail cartography |
| Satellite signal | Monthly GEE `S2_SR_HARMONIZED` NDVI/NDMI/EVI, **2021-01 → 2026-06**, 58–66 obs/asset (1 365 rows) | **Two scenes only** → `ehs_spring`, `ehs_summer`, `delta_ehs` |
| Trend analysis | Harmonic-deseasonalised Mann-Kendall + Sen's slope (`analysis/mk_trends_pnsg.json`) | **None** |
| SCM | α-decay **simulation** (`src/spatial_causality/analyzer.py`) | **Real** zonal NDVI from actual rasters (`run_scm_operational.py`) → `scm_class` |
| PRUG zone | No | Yes |
| Wired to `confusion.py` | **Yes** (via `AssetTrend.is_alert`) | No |
| Wired to the field template | **Yes** (2 of the 21) | **No** |

**Consequence for Paper 1.** The primary scientific question is about *trails*. Universe B is the only real trail geometry in the repository — but it has no defensible temporal signal (§3). Universe A has the defensible temporal signal — but **only 6 of its 21 members are linear route features, and neither of the two assets seeded into the field-validation template is a trail at all**: `pnsg_escalada_maliciosa_porrones` is a climbing **polygon**, `pnsg_vuelo_libre_el_nevero` is a paragliding **point**.

The field campaign as currently seeded would therefore validate the satellite indicator against a crag and a launch site, and the resulting paper could not honestly be titled or framed as a trail-impact study. **This is a design decision that must be made before any field day is spent** — see the Scientific Contract §E and the Implementation Backlog item B-01.

---

## 2. Capability classification

### 2.1 Satellite / spectral

| Capability | Status | Verified basis |
|---|---|---|
| Sentinel-2 raster pipeline (`prepare_raster.py`) | **READY** | Reads L2A `.SAFE`, reprojects B04/B08/B11 → EPSG:25830, resamples B11 20 m → 10 m B04 grid, writes 2-band NDVI/NDMI GeoTIFF. Band math is explicit and correct. |
| NDVI | **READY** | `(B08 − B04) / (B08 + B04 + 1e-8)`, both native 10 m. |
| NDMI | **PARTIAL** | `(B08 − B11) / (B08 + B11 + 1e-8)`. B11 is **natively 20 m**, resampled to a 10 m grid. The 10 m grid is a *representation*, not the *support*. NDMI's true spatial support is 20 m. See `SPATIAL_MATCHING_PROTOCOL.md`. |
| EHS calculation (`calculate_delta_ehs.py`) | **PARTIAL** | Implemented and internally coherent: `EHS = 100 × (W_NDVI·D_ndvi + W_NDMI·D_ndmi)`, with per-scene percentile anchoring (`P_BASE=90` → healthy, `P_FLOOR=10` → floor), computed over pixels that are neither SCL-masked nor inside trail buffers. Defect: **every constant is expert-defined and none is empirically calibrated** (§4). |
| Dense-canopy reweighting | **PARTIAL** | Above `NDVI > 0.80` the weights flip from 0.5/0.5 to `W_NDVI=0.20 / W_NDMI=0.80` to handle NDVI saturation. Methodologically sound in principle, **numerically arbitrary and unvalidated**, and it introduces a discontinuity in the indicator at a hard threshold. Must be declared in the manuscript as a piecewise definition. |
| SCL cloud/shadow masking | **PARTIAL** | Excludes SCL {3, 5, 6, 8, 9, 10}. Correct set. **But masking is optional**: if `spring_scl.tif` / `summer_scl.tif` are absent the script prints a warning and proceeds unmasked. For a publication this must be a hard failure, not a warning. |
| Current scenes / composites | **BLOCKED_BY_EVIDENCE** | See §3 — this is the most serious satellite-side defect. |
| Provenance (`src/platform/provenance.py`) | **PARTIAL** | Parses real `.SAFE` product names to recover sensor + acquisition date — good design. **But `data/raw_assets/raster_data/` does not exist in this checkout**, so on a clean clone provenance degrades to "no scenes detected". PR #149 made that degradation honest; it did not make the rasters reproducible. Paper 1 needs a committed, machine-readable scene manifest, not a directory scan. |
| Cross-sensor validation (`src/validation/cross_sensor.py`) | **READY (code) / BLOCKED_BY_EVIDENCE (data)** | Pearson r, RMSE, MAE, bias, Willmott's d, Bland-Altman. Correctly notes HR-VPP is *not* independent of S2. No MODIS/Landsat series is ingested. |

### 2.2 Trail geometry and spatial framework

| Capability | Status | Verified basis |
|---|---|---|
| Real trail geometry | **READY** | 218 OAPN trails, 1 035.1 km, real cartography, with official PRUG management zones. This is genuine, publication-grade input. |
| Asymmetric trail buffer | **READY (as a method) / PARTIAL (as a parameter)** | `UPSLOPE_M = 15`, `DOWNSLOPE_M = 60`, symmetric `BUFFER_M = 50` fallback when the DEM fetch fails. Cited to Wemple et al. (2001). The *asymmetry* is literature-motivated; the *specific 15/60 values* are not derived from PNSG data. The silent fallback to 50 m symmetric must become a recorded per-trail flag — a paper cannot have an unlogged switch between two different spatial supports. |
| SCM zone rings | **READY (geometry)** | Core 0–50 m, near 50–200 m, landscape 200–1 000 m, EPSG:25830. Core radius cited to Marion & Leung (2001). |
| Plot ↔ pixel matching | **MISSING** | No code anywhere maps a field plot's coordinates to the satellite support that produced the EHS it will be compared against. This is the single largest missing piece of Paper-1 machinery. See Backlog B-04. |

### 2.3 Field validation

| Capability | Status | Verified basis |
|---|---|---|
| Field schema (`src/validation/field.py`) | **PARTIAL** | `FieldObservation` is clean and correctly optional-typed. Two defects: (a) `degradation_index()` averages *whatever components are present*, so a plot with only erosion measured and a plot with all three measured are placed on incommensurable scales yet compared as if equal; (b) `SOIL_COMPACTION_MAX_MPA = 3.0` **censors** all readings above 3 MPa to the same value — severe compaction is invisible to the index. |
| Field CSV I/O (`src/validation/io.py`) | **READY** | Blank cells → `None`, never 0. Comment rows skipped. Column order pinned. Correct discipline. |
| Field campaign template | **BLOCKED_BY_EVIDENCE + PARTIAL** | `clean_assets/field_validation/pnsg_field_observations_template.csv` has **4 rows and every measurement column empty**. Worse, it is structurally wrong: **impact and control plots carry identical `lat`/`lon`** (e.g. both Porrones rows are `40.7405, -3.9251`), differing only in `distance_to_trail_m`. The control plot has no actual location. A field team cannot navigate to it, and the satellite value extracted for it would be the *same pixel* as the impact plot — which would make any control–impact contrast meaningless by construction. |
| Campaign runner (`scripts/run_field_validation.py`) | **READY** | `--init` generates the template; without it, produces the contrast report. |
| Field data QA | **MISSING** | No range checks, no duplicate-plot detection, no control/impact pairing validation, no photo-reference existence check. See Backlog B-03. |
| **Real field observations** | **BLOCKED_BY_EVIDENCE** | **Zero.** This is the paper's binding constraint. Issue #26 is open, created 2026-07-11, never executed. |

### 2.4 Agreement statistics

| Capability | Status | Verified basis |
|---|---|---|
| Spearman ρ (`agreement.py`) | **READY (math) / PARTIAL (contract)** | Tie-corrected average ranks, Pearson on ranks. Correct. Defect: returns `0.0` — a *value*, not a sentinel — for `n < 3` **and** for constant input. A caller that reads only `.spearman` cannot distinguish "no correlation" from "not computable". |
| Cliff's δ (`agreement.py`) | **READY** | `P(a>b) − P(a<b)`, correct. Large-effect threshold 0.474 correctly cited to Romano et al. (2006). |
| Control–impact contrast | **READY (math) / PARTIAL (design)** | Correct arithmetic. But it compares *pooled* impact vs *pooled* control, discarding the stratum pairing that the protocol says is the whole point of the design. A stratified/paired contrast is what the sampling design earns. |
| Confusion matrix (`confusion.py`) | **READY (math) / BLOCKED (design)** | Accuracy, precision, recall, F1, Cohen's κ all implemented; refuses to fabricate when `n = 0`. **But the positive class is nearly empty**: `is_alert = (trend == "decreasing" and significant)`, and across all 21 Universe-A assets **exactly one** qualifies (`pnsg_escalada_maliciosa_porrones`, τ = −0.369, p < 0.0001). A 2×2 table with one positive supports no κ worth reporting. See §5. |
| `FIELD_DEGRADED_THRESHOLD = 50.0` | **PARTIAL** | Hard-coded, never calibrated, never justified against any literature. It is the hinge of the entire classification analysis and is currently a round number. |
| Field agreement service (`src/ui/services/field_agreement.py`) | **PARTIAL — statistically unsound as written** | Pairs at **asset** level: every plot belonging to an asset receives the *same* `satellite_stress = 100 − EHS`. With ~20 plots across 2 assets, the satellite vector has **two distinct values**, so ρ is computed over massively tied, pseudo-replicated data. This inflates `n` while destroying the information. Paper 1 must pair **plot ↔ plot-local satellite support**, not plot ↔ asset mean. |

### 2.5 Spatial causality (SCM)

| Capability | Status | Verified basis |
|---|---|---|
| SCM on Universe B (218 trails) | **READY (as a spatial contrast)** | `run_scm_operational.py` extracts genuine zonal mean NDVI from the real rasters for real ring buffers. Result: 24 LOCALIZED, 29 MIXED, 165 LANDSCAPE, 0 NULL. This is real measurement. |
| SCM on Universe A (21 assets) | **PARTIAL — simulated** | `src/spatial_causality/analyzer.py` derives zone signals by α-decay from the single-buffer series. `src/spatial_causality/zones/` **does not exist**, so `real_zones_exist()` is `False` and the simulated path is what runs. Correctly labelled in code. |
| SCM thresholds | **PARTIAL** | `SIG > 0.15` → localized, `SIG < 0.07` → landscape, cross-zone `r > 0.85` → climate, `r < 0.70` → localized. Zone *radii* are literature-cited; **the four decision thresholds are not** — no citation, no calibration, no sensitivity analysis. They are expert heuristics presented with three-significant-figure confidence. |
| Causal language | **PARTIAL — must be reframed** | The module is named "Spatial Causality" and emits `LOCALIZED_IMPACT` = "human pressure / tourism-related". A spatial gradient is not a causal attribution. See `SCM_REFRAMING.md`. |

### 2.6 Evidence discipline

| Capability | Status | Verified basis |
|---|---|---|
| Evidence classes (`src/platform/evidence.py`, ADR-004) | **READY** | Five classes (`real`/`calibrated`/`simulated`/`synthetic`/`missing`) with a machine-readable gating matrix. `DataType.Calculada` correctly refuses to collapse to one class. Genuinely good work and directly reusable as the paper's provenance framework. |
| Fixture classification | **READY** | Owner decision Q-01 resolved territorial fixtures to `SYNTHETIC` (PR #151); `SYNTHETIC` supports no decision use. |
| Score convention | **READY** | `health = 100 − stress`, single conversion point in `src/metrics/semantics.py`, applied at one boundary, test-enforced. No ambiguity. |
| Visitor-pressure gating | **READY — preserve unchanged** | `INSUFFICIENT_EVIDENCE` is the correct and current state. NDVI/NDMI/EVI/EHS are explicitly barred from substituting for visitor counts; `annual_visitors` is synthetic; `visitor_capacity_annual` is a static planning range. **Paper 1 must not touch this.** |

### 2.7 Explicitly out of Paper-1 scope

**NOT_NEEDED_FOR_PAPER_1:** `/api/v2` HTTP deployment · Azure/Container Apps · PostGIS `geom` column and spatial queries (#133) · identity/tenancy/RBAC (#109–#113) · mobile client (#116–#120) · ArcGIS Experience Builder productization (#134–#142) · CETS readiness report (#123) · OAPN dossier automation (#127) · OpenAPI contract (#128) · commercial pilot package (#129) · LAC/ROS carrying capacity · forecasting (`src/forecasting/`) · SVI socioeconomic trend · OAPN cross-park benchmarking (#117).

These are legitimate engineering work. None is a scientific contribution of Paper 1, and none should appear in the manuscript beyond, at most, one sentence in §Reproducibility.

**MITMA mobility** — optional secondary context only. Municipal inbound trips are **not** trail footfall and must never be reported as such. Snapshot not ingested (`src/mobility/snapshot/` does not exist).

---

## 3. The satellite temporal problem (most serious non-field defect)

The two scenes behind every `ehs_spring` / `ehs_summer` / `delta_ehs` value on all 218 trails are:

- `S2A_MSIL2A_20250810T110701_…_T30TVL` — labelled **"summer"**
- `S2B_MSIL2A_20260410T110619_…_T30TVL` — labelled **"spring"**

Therefore:

1. **The delta runs backwards in time.** `delta_ehs = EHS_summer − EHS_spring` subtracts a 2026-04-10 observation from a 2025-08-10 observation. The "later" scene is chronologically **earlier**. Any sentence of the form *"deterioro estacional primavera→verano"* describes the reverse of what was computed.
2. **The pair spans two calendar years and 8 months**, so it confounds seasonal phenology with inter-annual change (including drought recovery).
3. **The pair spans two satellites** (S2A and S2B). Cross-sensor offsets are small but non-zero and are not corrected.
4. **The EHS baselines are per-scene percentiles**, so `EHS_spring` and `EHS_summer` are anchored to *different reference distributions*. Their difference is not a difference in a fixed unit.

`docs/audit/2026-snto-baseline/KPI_INVENTORY.md` already reached the same conclusion and recommended restricting all surfaces to "difference between two dated scenes". **This audit goes further for publication purposes: `delta_ehs` in its current form is not a publishable quantity.**

Paper 1 must not validate against these two scenes. It requires a **campaign-matched acquisition** (see `SATELLITE_FIELD_MATCHING_PLAN.md`). This is not a defect to patch — it is an input to acquire.

---

## 4. Unvalidated constants inventory

Every number below is currently expert-set and drives a scientific output. None has been calibrated against PNSG data.

| Constant | Value | Where | Basis | Sensitivity analysis required |
|---|---|---|---|---|
| `EHS_P_BASE` | 90 | `src/config/constants.py:50` | Expert | **Yes** |
| `EHS_P_FLOOR` | 10 | `:51` | Expert | **Yes** |
| `EHS_W_NDVI` / `EHS_W_NDMI` | 0.5 / 0.5 | `:52–53` | Expert | **Yes** |
| `EHS_DENSE_CANOPY_NDVI_THRESHOLD` | 0.80 | `:78` | Saturation literature (qualitative) | **Yes** |
| `EHS_W_NDVI_DENSE` / `..._NDMI_DENSE` | 0.20 / 0.80 | `:79–80` | Expert | **Yes** |
| `UPSLOPE_M` / `DOWNSLOPE_M` | 15 / 60 | `etl_raster_intersection.py:53–54` | Wemple et al. (2001), qualitative | Yes |
| `BUFFER_M` fallback | 50 | `:55` | Convention | Log when used |
| SCM `CORE_OUTER_M` | 50 | `analyzer.py:107` | Marion & Leung (2001) | No — cited |
| SCM `NEAR_OUTER_M` | 200 | `:108` | Expert | Yes |
| SCM `_SIG_LOCALIZED` | 0.15 | `:119` | **Uncited heuristic** | **Yes** |
| SCM `_SIG_LANDSCAPE` | 0.07 | `:120` | **Uncited heuristic** | **Yes** |
| SCM `_CORR_LANDSCAPE` | 0.85 | `:121` | **Uncited heuristic** | **Yes** |
| SCM `_CORR_LOCALIZED` | 0.70 | `:122` | **Uncited heuristic** | **Yes** |
| `FIELD_DEGRADED_THRESHOLD` | 50.0 | `confusion.py` | **Uncited round number** | **Yes — and it must be calibrated out-of-sample** |
| `SOIL_COMPACTION_MAX_MPA` | 3.0 | `field.py:23` | Root-restriction range, qualitative | Yes (censoring) |
| Spearman `strong` / `moderate` | 0.6 / 0.3 | `agreement.py` | Convention | Report ρ + CI instead |
| Cliff's δ large | 0.474 | `agreement.py` | Romano et al. (2006) | No — cited |

**No threshold in this table may be changed without owner approval, a before/after comparison, and a methodological rationale** (change-control rule).

---

## 5. Statistical power reality check

Facts, not projections:

- Universe A satellite alerts: **1 positive out of 21** (Porrones). One asset is increasing-significant in the same crag category (`escalada_valsain`, τ = +0.256), which is itself worth noting.
- Universe A significant trends overall: 6 increasing, 1 decreasing, 14 no trend.
- Universe B: `ehs_summer` mean 11.51 (range 0–71.96) on the 0–100 **stress** scale — i.e. the great majority of trails register as low-stress. 46 of 218 have a positive `delta_ehs`.
- Field observations: **0**.

Implications the Statistical Analysis Plan must honour:

1. A confusion matrix built on `AssetTrend.is_alert` over Universe A **cannot be the paper's classification analysis** — the positive class has one member.
2. The classification analysis must be built at **plot level** against a **plot-level satellite score**, with the positive class defined by a threshold that is calibrated on a set disjoint from the evaluation set.
3. Because `ehs_summer` is strongly floor-concentrated, the sampling design **must deliberately span the EHS range** rather than sample trails at random — otherwise nearly every plot lands in the same narrow band and correlation is unidentifiable. This is a stratification requirement, not an optimisation, and it must be pre-declared (see `STATISTICAL_ANALYSIS_PLAN.md` §Exclusion and §Bias).

---

## 6. Test verification

`tests/unit/test_validation.py`, `test_field_validation_confusion.py`, `test_spatial_causality.py`, `test_scm_real_zones.py` → **48 passed** (0.84 s), on a clean install of `requirements.txt`.

The tests verify *arithmetic* well. They do **not** verify:
- that impact and control plots have distinct coordinates;
- that a plot's satellite value comes from that plot's own location;
- that the scenes compared are temporally ordered or same-sensor;
- that a `degradation_index` built from 1 component is not compared against one built from 3.

All four gaps are Paper-1 blocking and appear in the Implementation Backlog.

---

## 7. Documentation ↔ implementation contradictions

Reported as required by the operating mode. Each is a statement in repository prose that the code or data does not support.

| # | Claim in docs | What the repo actually shows |
|---|---|---|
| **D-01** | `CLAUDE.md`: *"`src/spatial_causality/zones/` does not exist → the α-decay simulated path is still what runs."* | True **only for Universe A**. `run_scm_operational.py` computes SCM from **real rasters** over the 218 trails, and those real classes are what `pipeline_a_results.geojson`, PRUG monitoring and the dossier consume. The doc conflates two different SCM implementations and understates the real one. |
| **D-02** | `docs/dossier_institucional_OAPN.md:44`, `docs/informe_tecnico_limites.md:16`: *"primavera 2026-04-10 + verano 2025-08-10"* framed as a seasonal spring→summer signal. | The "spring" scene is **8 months after** the "summer" scene. The seasonal framing inverts the actual chronology (§3). |
| **D-03** | `docs/field_validation_protocol.md` §2: control plots are *"lejos del sendero, en el mismo estrato"*. | The shipped template gives control plots **the same coordinates as their impact plots**. The protocol's central design element is not expressed in the only artefact a field team would carry. |
| **D-04** | `docs/methodology/validation.md`: lists the confusion matrix as "listo" infrastructure for issue #26. | It is ready as code, but over Universe A it has **one positive case**. Readiness of the function is not readiness of the analysis. |
| **D-05** | `CLAUDE.md` §Current Status describes v2.1/v2.2/v3.0 milestones at length. | Accurate as engineering status, but PRs **#143–#152** (Phase 0 baseline audit, Phase 0.5A–0.5F claim-safety work) have merged and are **not reflected** in `CLAUDE.md`. The file is stale by ten PRs. Not Paper-1 blocking; flagged for the owner. |
| **D-06** | `docs/field_validation_protocol.md` §5: *"Mínimo 3 parcelas co-localizadas"*. | Correct as a software guard, and the document says so. Restating for emphasis: **3 is a technical floor, not a scientific target**, and no part of the repository currently states a defensible target. Addressed in `FIELD_CAMPAIGN_EXECUTION_PLAN.md`. |
| **D-07** | `src/validation/agreement.py` docstring: ρ ≥ 0.6 *"is the evidence that elevates EHS from demo to validated indicator."* | A single Spearman ρ on one park, one season, one campaign, with no independent replication, does not constitute validation of an indicator. This sentence is the exact overclaim the project's own non-negotiables forbid. |

---

## 8. Bottom line

**What Paper 1 can already stand on (REAL, verified):**
real OAPN trail cartography (218 trails, 1 035 km) · real Sentinel-2 L2A processing to NDVI/NDMI · a transparent, reproducible EHS formulation · real multi-scale zonal extraction on real rasters · a 2021–2026 monthly S2 record for 21 sites with defensible deseasonalised Mann-Kendall trends · a rigorous, machine-enforced evidence-class framework · correct agreement/effect-size/confusion mathematics with tests.

**What Paper 1 cannot yet stand on (MISSING):**
**any field observation whatsoever** · a temporally coherent satellite acquisition matched to a field window · plot-level (not asset-level) satellite↔field pairing · any empirical calibration of any threshold · any independent verification.

**The honest one-line statement of current status:**
*The satellite indicator is **plausible but unvalidated**. The spatial contrast is **measured but not causally attributed**. The field evidence is **MISSING**.*

Everything in the rest of `docs/paper1/` is built on exactly that statement.
