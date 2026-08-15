# Implementation Backlog — Paper 1

**Status:** DRAFT for owner approval · **Date:** 2026-08-09 · **Phase 11 deliverable**

**No code in this backlog has been written.** Phase 11 requires the backlog to exist before any code changes, and several items touch scientific output, which requires explicit owner approval under change control. This document is the approval request.

Scope rule: **the minimum code required to execute the scientific plan.** No product features. Nothing here adds a dashboard surface, an endpoint, a deployment or a commercial capability.

### Change-control classification

| Class | Meaning | Approval |
|---|---|---|
| 🟢 **Additive** | New code path; no existing output changes | Normal review |
| 🟡 **Behavioural** | Changes behaviour of an existing path, not a scientific number | Review + tests |
| 🔴 **Scientific-output-changing** | Could change a published or displayed scientific value | **Owner approval + before/after comparison + methodological rationale + tests** |

---

## Priority 0 — Blocks the field campaign

### B-01 · Regenerate the field campaign template with real, distinct plot coordinates 🟢 ✅ **DONE (2026-08-15) — jurisdiction now authoritative**

| | |
|---|---|
| **Scientific reason** | The shipped template gave impact and control plots **identical coordinates** (both Porrones rows `40.7405, -3.9251`) — void control–impact contrast — and targeted a climbing polygon and a paragliding point rather than trails. |
| **Files** | `scripts/paper1/generate_plot_plan.py` (engine) · `scripts/run_field_validation.py` (`--init` no longer emits the identical-coordinate seed) · `clean_assets/field_validation/pnsg_field_observations_template.csv` (reset header-only) · `clean_assets/field_validation/pnsg_plot_plan.{csv,gpx,csv.provenance.json}` (final plan, no `_PROVISIONAL` suffix) · `clean_assets/field_validation/reference/madrid_boundary_osm.geojson` (owner-supplied 2026-08-15) + README · `tests/unit/test_plot_plan.py` |
| **Depends on** | ✅ Contract §F frozen to F-1 · ✅ Madrid-only scope · ✅ B-04 grid snapping · ✅ **real Madrid boundary supplied by owner (2026-08-15)** |
| **Acceptance criteria** | ✅ Segment pool filtered to the Madrid sector via a **real administrative boundary** — OpenStreetMap relation 349055 (6 294 vertices, ODbL), fetched by the owner and validated against two known landmarks before use (La Pedriza → inside ✓, Valsaín → outside ✓); a nested-shells topology defect was repaired with `buffer(0)` (area Δ 0.015%, far from PNSG). 41/218 trails eligible at a 1000 m inward margin. `--boundary-authoritative` passed → output carries no `_PROVISIONAL` suffix. · ✅ every plot has a distinct surveyed coordinate · ✅ every impact/control pair passes SM-1 · ✅ every control ≥ 100 m from all trails (SM-3) · ✅ no two plots share a 20 m cell (SM-2) · ⚠️ stratified by **satellite-stress tercile** for now; ecological stratum (S1–S4) still deferred to A-4 (blocked on a DEM) — the `stratum` column carries `sat_stress_{low,mid,high}`, honestly labelled · ✅ exports GPX · ✅ records seed + commit + boundary SHA-256 + per-plot cell id and control clearance |
| **Tests** | 13 tests: distinct coordinates · SM-1/SM-2/SM-3 independently re-verified on the emitted plan · 1:1 stratum-matched pairing · deterministic given the seed · PROVISIONAL marking present/absent by the flag · GPX written · missing boundary fails loudly · **the real OSM boundary produces a non-provisional plan** · **the real boundary classifies both landmarks correctly**. Full suite: 1536 passed |
| **Risk** | Low. The jurisdiction determination is now backed by a validated real boundary, not a heuristic. |
| **Changes scientific output?** | **No** — old template's void-contrast + wrong-universe rows removed, not silently mutated; `cets_readiness.count_measured_field_plots` stays 0. |

> **One follow-up remains, owner-side:** **A-4's DEM is still needed** — supply a DEM (Copernicus GLO-30 / IGN MDT05, both proxy-blocked here) to produce the S1–S4 strata table, then pass it to the planner via `--strata` so `stratum` carries the ecological band instead of the satellite-stress tercile.

### B-02 · Field schema: strict index, GPS accuracy, subplots 🔴 ✅ **DONE (2026-08-10, owner-approved)**

| | |
|---|---|
| **Scientific reason** | Three defects. (a) `degradation_index()` averages *whatever components are present*, so a 1-component and a 3-component index are placed on incommensurable scales yet compared as equals. (b) No GPS accuracy field exists, so exclusion rule L-1 is unenforceable. (c) No subplot structure exists, so the 5-subplot aggregation the spatial protocol requires cannot be recorded. |
| **Files** | `src/validation/field.py` · `src/validation/io.py` · `tests/unit/test_validation.py` |
| **Design** | Add `degradation_index_strict()` returning `None` unless all three core components are present — **as a new method**. The existing permissive `degradation_index()` is **unchanged** so no product output moves. Add `gps_accuracy_m`, `subplot_id`, `bare_soil_pct`, `observer_id`, `notes`. Paper 1 uses `_strict` exclusively (Contract §H). |
| **Acceptance criteria** | ✅ Existing method byte-identical — `degradation_index()` source SHA `24a969f9…` unchanged before/after; outputs `[100.0, 0.0, 60.0, 58.33, None]` pinned by a regression test · ✅ `degradation_index_strict()` returns `None` on any missing core component (compaction/cover/erosion) · ✅ CSV round-trips all 5 new columns · ✅ blanks load as `None`, never 0 · ✅ old CSVs without the new columns still load |
| **Tests** | 10 tests in `test_validation.py`: permissive outputs pinned; strict `None` for each single-missing case; strict == permissive when complete; new-column round-trip + blanks→None; old-CSV backward-compat; FIELDNAMES additive-not-reordered. Product paths (cets_readiness, field_agreement, confusion, persistence ingest) unchanged. Full suite: 1534 passed |
| **Before/after** | `git diff` = **34 insertions, 1 deletion** (the one deletion extends `_FLOAT_COLS` in place to parse the two new float columns; no existing column's behaviour removed). `degradation_index()` body: **zero deletions**. |
| **Risk** | **Medium** — touches the module that defines the scientific outcome variable. Mitigated: strictly additive, permissive method proven byte-identical, product paths stay on the permissive method. |
| **Changes scientific output?** | **No** — additive only. `degradation_index_strict()` is used by Paper-1 analysis (Contract §H); every existing product path keeps using the unchanged permissive `degradation_index()`. |

### B-03 · Field data QA runner 🟢

| | |
|---|---|
| **Scientific reason** | No QA exists. Field data enters analysis unchecked. A duplicated plot ID or a transcription error would silently corrupt the primary result, and there is currently nothing that would catch it. |
| **Files** | new `scripts/qa_field_data.py` · new `src/validation/qa.py` · new `tests/unit/test_field_qa.py` |
| **Checks** | Ranges (compaction 0–10 MPa, cover 0–100, erosion 0–3, accuracy > 0) · duplicate `plot_id` · orphan pairs (impact without control) · **shared coordinates between paired plots** · missing photo references · impossible values (control with `trail_width_m`) · coordinates outside the park · dates outside the campaign window · **completeness of the three core components, reported not corrected** |
| **Acceptance criteria** | Exit non-zero on any error · warnings for flags · machine-readable JSON report · **never modifies the input** |
| **Tests** | Each check fires on a crafted bad row and stays silent on a good one · runner is read-only |
| **Risk** | Low |
| **Changes scientific output?** | **No** |

### B-04 · Plot ↔ satellite cell matching 🟢 ✅ **DONE (2026-08-09)**

| | |
|---|---|
| **Scientific reason** | **Nothing in the repository maps a field plot to the satellite support that produced its value.** The nearest existing thing, `src/ui/services/field_agreement.py`, pairs at *asset* level: every plot in an asset receives the same `satellite_stress`, producing pseudo-replication and near-total ties. This is the largest missing piece of Paper-1 machinery. |
| **Files** | `src/validation/spatial_match.py` · `tests/unit/test_spatial_match.py` · exports in `src/validation/__init__.py` |
| **Functions delivered** | `snap_to_support_grid(lon, lat)` → 20 m B11-grid `SupportCell` in EPSG:25830 (deterministic, stable `cell_id`) · `check_pair_independence` (SM-1) + `find_cell_collisions` (SM-2) · `control_trail_clearance_m` / `control_clearance_ok` + `load_trail_network_utm` (SM-3) · `cell_inside_footprint` (SM-4) · `extract_plot_value(...)` → per-plot NDVI/NDMI + full provenance · `plot_stress_from_baselines(...)` composes EHS by **lazy-importing the operational `_trail_stress_score`** (formula reused, never forked; needs scene baselines the caller holds). SM-5 is clustering, recorded via `segment_id` downstream, not enforced here. |
| **Acceptance criteria** | ✅ Deterministic cell assignment · ✅ **grid alignment verified against the raster transform** — `extract_plot_value` raises `GridMisalignment`/`CRSMismatch` rather than silently resampling (the silent-CRS-failure guard) · ✅ every provenance field emitted (cell ID, centre, GPS-to-centre distance, valid-pixel fraction, SCL classes, scene IDs) · ✅ raises `InsufficientCoverage` rather than averaging when valid coverage < 70 % |
| **Tests** | 24 tests: 5 m apart → same cell, 25 m apart → different (via the real lon/lat API); SM-1…SM-4 each fire on crafted inputs; extraction against synthetic in-memory rasters — full-valid returns the mean, 75 % passes, 50 % raises, grid/CRS misalignment raises; the **SCL class-5 asymmetry** verified (a cell of bare/rock is retained, not masked); a regression guard that the asset-level service still imports |
| **Risk** | **Medium** — CRS handling is where this class of code fails silently. Mitigated by the explicit grid-alignment and CRS-equality guards, which raise instead of resampling. |
| **Changes scientific output?** | **No** — new path; the existing asset-level service is untouched and stays in the product (regression-guarded). Full suite: 1483 passed. |

### B-05 · Make SCL masking mandatory for Paper-1 processing 🔴

| | |
|---|---|
| **Scientific reason** | `calculate_delta_ehs.py` prints a warning and **proceeds unmasked** when `spring_scl.tif` / `summer_scl.tif` are absent. Unmasked cloud, shadow and snow would silently corrupt the validation composite, and at PNSG's elevations snow contamination is a live risk. |
| **Files** | `calculate_delta_ehs.py` (new `--require-scl` flag) · new Paper-1 processing entry point |
| **Design** | **Add a flag; do not change the default.** The existing permissive behaviour stays for the operational pipeline; Paper-1 processing always passes `--require-scl` and fails loudly without it. |
| **Acceptance criteria** | With the flag and no SCL → non-zero exit, no output written · without the flag → behaviour byte-identical to today |
| **Tests** | Both branches; a regression test asserting the default path is unchanged |
| **Risk** | Low as specified; **high if the default were changed** — it must not be |
| **Changes scientific output?** | **No for existing runs** (default preserved). **Yes for Paper-1 runs**, deliberately: they will be computed on properly masked data. |

---

## Priority 1 — Blocks the analysis

### B-06 · Satellite acquisition manifest 🟢 ✅ **DONE (2026-08-09)**

| | |
|---|---|
| **Scientific reason** | Provenance currently depends on scanning `.SAFE` filenames under `data/raw_assets/raster_data/`, **which does not exist in a clean checkout**. A third party cannot regenerate the composite, and the paper cannot state its inputs precisely. |
| **Files** | `src/validation/acquisition_manifest.py` · `scripts/paper1/generate_acquisition_manifest.py` (`--init`/`--validate`/`--check`) · `clean_assets/paper1/acquisition_manifest.json` · `tests/unit/test_acquisition_manifest.py` · exports added to `src/validation/__init__.py` |
| **Content** | `ManifestStatus` lifecycle (`planned` → `window_defined` → `scenes_identified` → `composite_generated` → `checked`) · window start/end, tile (`T30TVL`), cloud threshold (20 %), composite method (`median`), min scenes (3), max temporal offset (15/30 days), valid-pixel thresholds (70/90 %) · **the SCL class-5 asymmetry as two separate, checked lists** (`SCL_EXCLUDE_BASELINE` includes 5, `SCL_EXCLUDE_PLOT_EXTRACTION` excludes it) · scene IDs, sensor mix, generation timestamp, best-effort commit hash |
| **Acceptance criteria** | ✅ Committed **before** extraction — the committed manifest is honestly `planned`, with `scene_ids=()` and no window. The target *season* is now decided (summer 2027, 2026-08-09), but the manifest's `window_start`/`window_end` are the narrower ±3-week composite window anchored on the actual campaign midpoint, which awaits locked field dates — so `planned` remains correct, not false-precise · ✅ schema-validated (`validate_manifest`, lifecycle-gated: a fixed window/scenes is only required once status advances past `planned`) · ✅ `--check` mode fails (non-zero exit) on any disagreement between the manifest's declared `scene_ids` and what an extraction run actually used — verified end-to-end against the committed (empty) manifest |
| **Tests** | 25 tests: defaults match the matching plan · SCL asymmetry enforced even at `planned` stage · lifecycle gating for each status transition · out-of-range and inverted-threshold rejection · round-trip write/load · `--check` exact-match / mismatch / order-independence · the **committed manifest itself** is asserted valid and honestly `planned` (not fabricated as populated) |
| **Risk** | Low |
| **Changes scientific output?** | **No** — new artefact; touches no existing file outside `src/validation/__init__.py`'s export list (additive only) |

### B-07 · Not-computable state for Spearman 🟡

| | |
|---|---|
| **Scientific reason** | `spearman_correlation` returns the **value** `0.0` for n < 3 and for constant input. A caller reading `.spearman` cannot distinguish "no correlation" from "not computable" — a silent path to reporting a fabricated null. |
| **Files** | `src/validation/agreement.py` · `tests/unit/test_validation.py` |
| **Design** | Add `spearman_correlation_or_none()` returning `Optional[float]`; leave the existing function unchanged so no product surface moves. Paper-1 code uses the new one exclusively. |
| **Acceptance criteria** | Returns `None` for n < 3 and for constant input · existing function byte-identical |
| **Tests** | Both edge cases; existing tests pass unchanged |
| **Risk** | Low |
| **Changes scientific output?** | **No** |

### B-08 · SCM docstring reframing (documentation only) 🟢 ✅ **DONE (2026-08-09)**

| | |
|---|---|
| **Scientific reason** | The module is named "Spatial Causality" and emits `LOCALIZED_IMPACT` described as "human pressure / tourism-related". A spatial gradient is not causal attribution, and a trail produces a trail-proximal contrast simply by existing. |
| **Files** | `src/spatial_causality/analyzer.py` (docstring) · `run_scm_operational.py` (docstring) · `tests/unit/test_scm_reframing_docs.py` |
| **Design** | ✅ **Docstrings only — verified by diff: no rename, no logic change, no threshold change.** Both module docstrings now carry a "SPATIAL CONTRAST, NOT CAUSAL ATTRIBUTION" caveat stating what SIG measures, that the four decision thresholds (SIG 0.15/0.07, cross-zone r 0.85/0.70) are uncalibrated expert heuristics, and that localization is not causation (a trail produces a trail-proximal contrast by existing). The `(A)/(B)/(C)` glosses were reworded from causal language to spatial-pattern language; the `LOCALIZED_IMPACT`/`LANDSCAPE_DRIVEN`/`MIXED` output labels are preserved verbatim so downstream code and data are unaffected. |
| **Acceptance criteria** | ✅ No behavioural diff (docstring-only; the two edited files show only triple-quoted-string changes) · ✅ a test asserts each caveat phrase is present in both modules, that the thresholds are named, and that the labels are preserved |
| **Tests** | 5 new caveat-presence tests + full existing SCM suite unchanged (`test_spatial_causality.py`, `test_scm_real_zones.py`, `test_tis_causal_budget.py` → 38 green). Full suite: 1488 passed |
| **Risk** | Very low |
| **Changes scientific output?** | **No** |

### B-09 · Figure generation scripts 🟢 ✅ **PARTIAL DONE (2026-08-09)** — the 3 committed-data artifacts

| | |
|---|---|
| **Scientific reason** | Figures must be reproducible from committed data, and Figure 1(b), Figure 2 and Table T2 are producible **today** — building them early surfaces CRS and rendering problems long before submission. |
| **Files** | `scripts/paper1/_figutil.py` (shared provenance) · `figure_01_study_area.py` · `figure_02_pipeline.py` · `table_02_constants.py` · `tests/unit/test_paper1_figures.py` · outputs under `docs/paper1/figures/` and `docs/paper1/tables/`. Remaining figures (3,4,5,6,7,8; tables T1,T3,T4) wait for real field data. |
| **Acceptance criteria** | ✅ Runs from a clean checkout (matplotlib is offline figure-tooling, lazily imported; the non-render logic needs only stdlib/geopandas) · ✅ input SHA-256 + commit hash written to a `*.provenance.json` sidecar · ✅ vector output (Fig 1 PDF+PNG, Fig 2 PDF+SVG) · ✅ colourblind-safe (cividis sequential; Okabe-Ito categorical, validated with the dataviz palette validator) · ✅ **fails loudly (`MissingInput`) rather than plotting anything if an input is absent** |
| **Tests** | 10 tests: `require_inputs` raises on missing (naming only the absent file); SHA-256 + provenance structure; palette coverage; **Table T2 values match the live constants** + the committed CSV is fresh (drift guard, like the manifest `--check`); Figure 1 fails loudly on a missing input; Figure 1/2 renders produce PDF/PNG/SVG + sidecar (`importorskip('matplotlib')`) |
| **Risk** | Low |
| **Changes scientific output?** | **No** — new offline generators; no existing module touched. Full suite: 1498 passed |

---

## Priority 2 — Analysis execution (after data exists)

### B-10 · Plot-level agreement runner 🟢

| | |
|---|---|
| **Scientific reason** | Executes the SAP: plot-level Spearman with cluster-bootstrap BCa CI, within-stratum Cliff's δ, nested leave-one-cluster-out threshold calibration, ROC AUC. None of this exists — the current runner is asset-level and threshold-fixed. |
| **Files** | new `src/validation/paper1_analysis.py` · new `scripts/paper1/run_analysis.py` · tests |
| **Acceptance criteria** | Deterministic given a seed · emits every quantity in SAP §1–§5 with CIs · **refuses to run** if the SAP freeze hash is absent · never silently drops a plot (every exclusion counted and reported) |
| **Tests** | Known-answer tests on synthetic inputs *for the estimators only* · exclusion accounting sums to n_planned · cluster bootstrap respects segment grouping |
| **Risk** | Medium — this code produces the paper's headline number |
| **Changes scientific output?** | **Creates new output.** Does not modify any existing one. |

### B-11 · Analysis table export 🟢

One row per plot with the complete provenance chain (field values, satellite values, cell ID, scene IDs, offset days, valid-pixel fraction, SCL classes, exclusion flags). This becomes supplementary Table T4 and is what makes the reviewer success criterion — *trace every statement from raw evidence to claim* — actually achievable. **No aggregation.** Risk: low. Changes scientific output: no.

### B-12 · Sensitivity analysis runner 🟡

Executes S1–S10. **Reads constants; never writes them.** A test must assert the runner cannot mutate `src/config/constants.py`, so a sensitivity sweep can never become an accidental tuning run. Risk: medium (proximity to tuning). Changes scientific output: no — the headline always uses the frozen operational constants.

### B-13 · Claim audit tooling 🟢

Extends the existing `tests/test_evidence_claims_sync.py` pattern to the manuscript: greps the draft for forbidden verbs (Contract §P/§R) and for numeric claims lacking a source reference; fails CI on a hit. Cheap, and it enforces the discipline mechanically rather than relying on care during revision. Risk: low. Changes scientific output: no.

### B-14 · Fresh SIG extraction for H4 against the campaign-matched composite 🟢

| | |
|---|---|
| **Scientific reason** | The sampling frame is now the 218 OAPN trails (Contract §F, frozen 2026-08-09). H4 needs a trail-to-landscape spatial contrast per sampled segment. The **existing** `scm_class`/SIG values (`run_scm_operational.py`, already computed for all 218 trails) are real zonal extraction but from `spring_raster.tif`/`summer_raster.tif` — the same disqualified 2025-08-10/2026-04-10 pair as `delta_ehs` (Phase 0 audit §3). They cannot feed H4 without reusing the same method against a temporally valid input. |
| **Files** | new `scripts/paper1/extract_sig_campaign.py`, thin wrapper reusing `run_scm_operational.py`'s ring-buffer/SIG functions · `tests/unit/test_paper1_sig_extraction.py` |
| **Design** | Same real code path (core/near/landscape rings, `SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)`), pointed at the campaign-matched composite from B-06's manifest instead of `spring_raster.tif`/`summer_raster.tif`. Restricted to the sampled segments — not a full 218-trail rerun. **Does not touch `run_scm_operational.py` or its output.** |
| **Depends on** | B-06 (acquisition manifest) · the campaign-matched composite existing |
| **Acceptance criteria** | Numeric `sig_segment` per sampled segment, with the same provenance fields as B-04 (scene IDs, valid-pixel fraction) · explicit `None` (not `MIXED`) when a zone lacks raster coverage, matching the existing null-handling convention · zero writes to `data/outputs/pnsg/pipeline_a_results.geojson` |
| **Tests** | SIG value matches a hand-computed reference on a synthetic raster · null propagation on missing zone coverage · confirms the operational `scm_class` field is untouched |
| **Risk** | Low — reuses tested real logic against a new real input |
| **Changes scientific output?** | **No** — new artefact for H4 only; the operational `scm_class`/SIG on all 218 trails is unchanged |

---

## Explicitly NOT in this backlog

| Not doing | Why |
|---|---|
| Renaming `src/spatial_causality/` | Large risky diff across persistence, reporting, PRUG, dossier and tests; zero scientific gain. Manuscript language handles it |
| Changing any EHS constant | 🔴 Would alter existing scientific output. Paper 1 validates the **shipped** indicator |
| Changing `FIELD_DEGRADED_THRESHOLD` | Paper 1 calibrates its threshold out-of-sample instead; the product constant is untouched |
| Changing SCM thresholds | Same reasoning; sensitivity is reported instead |
| Changing the asymmetric buffer | Operational parameter, not a plot-level validation parameter |
| Fixing `delta_ehs` chronological inversion | **Real product defect** (Phase 0 §3), but a product fix, not a Paper-1 task. Paper 1 declines to use it. **Flagged to the owner as a separate issue.** |
| Modifying `src/ui/services/field_agreement.py` | Product surface. Paper 1 uses its own plot-level path |
| Deploying `/api/v2`, PostGIS geometry, mobile, ArcGIS, RBAC | Out of Paper-1 scope entirely |
| Implementing visitor forecasting | `INSUFFICIENT_EVIDENCE` is correct and preserved |
| Ingesting MITMA / SVI | Band C. Not blocking |

---

## Sequencing

```
🔲 Owner: Contract §F (sampling frame) + approve this backlog
        ↓
B-08 ✅, B-09(partial) ✅, B-06 ✅  ← safe, no dependencies, do first
        ↓
B-04 ✅ → B-01 ✅           ← engine done; jurisdiction provisional pending IGN boundary
        ↓
B-02, B-03, B-05           ← must exist before the first field day
        ↓
        [PILOT CAMPAIGN]
        ↓
   SAP + Contract frozen
        ↓
        [MAIN CAMPAIGN]
        ↓
B-07, B-10, B-11, B-12     ← analysis
        ↓
B-09 (remaining figures), B-13, B-14
```

## Risk summary

| Item | Risk | Scientific-output-changing | Owner approval required |
|---|---|---|---|
| B-01 | Low | No | No — ✅ done, jurisdiction authoritative |
| B-02 | Medium | No (additive) | ✅ owner-approved, done 2026-08-10 |
| B-03 | Low | No | No |
| B-04 | Medium | No | No — ✅ done |
| B-05 | Low | No (default preserved) | **Yes** (🔴 class) |
| B-06–B-09 | Low | No | No |
| B-10 | Medium | Creates new only | No |
| B-11 | Low | No | No |
| B-12 | Medium | No | No |
| B-13 | Low | No | No |
| B-14 | Low | No | No |

**Two items (B-02, B-05) carry the 🔴 classification and require explicit owner approval before implementation**, in both cases because a careless implementation could change existing scientific output even though the specified implementation does not. Both are specified as strictly additive, and both carry a regression test asserting the existing path is byte-identical. **B-02 is done (2026-08-10, owner-approved)** — implemented additively with the permissive method proven byte-identical (source SHA + pinned outputs). **B-05 (mandatory SCL masking flag) remains** — same additive discipline applies when it is built.
