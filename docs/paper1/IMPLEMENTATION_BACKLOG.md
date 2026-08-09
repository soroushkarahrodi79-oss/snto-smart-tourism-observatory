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

### B-01 · Regenerate the field campaign template with real, distinct plot coordinates 🟢

| | |
|---|---|
| **Scientific reason** | The shipped template gives impact and control plots **identical coordinates** (both Porrones rows are `40.7405, -3.9251`). A field team cannot navigate to the control, and both plots would draw the same satellite cell — voiding the control–impact contrast by construction. It also has only 4 rows, and targets a climbing polygon and a paragliding point rather than trails. |
| **Files** | `clean_assets/field_validation/pnsg_field_observations_template.csv` (regenerated) · `scripts/run_field_validation.py` (`--init`) · new `scripts/generate_plot_plan.py` |
| **Depends on** | ✅ Contract §F frozen to F-1 (218 OAPN trails, 2026-08-09) · B-04 (grid snapping) |
| **Acceptance criteria** | Every plot has a distinct surveyed coordinate · every impact/control pair passes SM-1 (≥ 40 m, non-adjacent cells) · plots stratified by ecological stratum × satellite-stress tercile · exports GPX waypoints · records the generation seed and commit hash |
| **Tests** | No two plots share a 20 m cell · every impact has exactly one control in the same stratum · all coordinates inside the park boundary · regeneration is deterministic given the seed |
| **Risk** | Low. New artefact; the old template is superseded, not silently mutated |
| **Changes scientific output?** | **No** |

### B-02 · Field schema: strict index, GPS accuracy, subplots 🔴

| | |
|---|---|
| **Scientific reason** | Three defects. (a) `degradation_index()` averages *whatever components are present*, so a 1-component and a 3-component index are placed on incommensurable scales yet compared as equals. (b) No GPS accuracy field exists, so exclusion rule L-1 is unenforceable. (c) No subplot structure exists, so the 5-subplot aggregation the spatial protocol requires cannot be recorded. |
| **Files** | `src/validation/field.py` · `src/validation/io.py` · `tests/unit/test_validation.py` |
| **Design** | Add `degradation_index_strict()` returning `None` unless all three core components are present — **as a new method**. The existing permissive `degradation_index()` is **unchanged** so no product output moves. Add `gps_accuracy_m`, `subplot_id`, `bare_soil_pct`, `observer_id`, `notes`. Paper 1 uses `_strict` exclusively (Contract §H). |
| **Acceptance criteria** | Existing method byte-identical in behaviour · new method returns `None` on any missing core component · CSV round-trips all new columns · blanks still load as `None`, never 0 |
| **Tests** | Strict returns `None` for each single-missing-component case · permissive method's existing tests pass unchanged · round-trip preserves `None` |
| **Risk** | **Medium** — touches the module that defines the scientific outcome variable |
| **Changes scientific output?** | **No, if implemented as specified** (additive method). It is classified 🔴 because a careless implementation that modified the existing method *would* change output. The before/after comparison must demonstrate the existing method is untouched. |

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

### B-04 · Plot ↔ satellite cell matching 🟢

| | |
|---|---|
| **Scientific reason** | **Nothing in the repository maps a field plot to the satellite support that produced its value.** The nearest existing thing, `src/ui/services/field_agreement.py`, pairs at *asset* level: every plot in an asset receives the same `satellite_stress`, producing pseudo-replication and near-total ties. This is the largest missing piece of Paper-1 machinery. |
| **Files** | new `src/validation/spatial_match.py` · new `tests/unit/test_spatial_match.py` |
| **Functions** | `snap_to_support_grid(lat, lon)` → 20 m B11-grid cell in EPSG:25830 · `check_pair_independence(impact, control)` → SM-1…SM-5 · `extract_plot_values(plots, composite)` → per-plot NDVI/NDMI/EHS + full provenance |
| **Acceptance criteria** | Deterministic cell assignment · grid alignment verified against a real S2 B11 raster footprint · every provenance field emitted (cell ID, centre, GPS-to-centre distance, valid-pixel fraction, SCL classes, scene IDs) · raises rather than silently returning a value when coverage < 70 % |
| **Tests** | Two points 5 m apart map to the same cell; 25 m apart to different cells · SM-1…SM-5 each fire on crafted inputs · a plot with 60 % valid coverage is excluded, not averaged |
| **Risk** | **Medium** — CRS handling is where this class of code fails silently |
| **Changes scientific output?** | **No** — new path; the existing asset-level service is untouched and stays in the product |

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

### B-06 · Satellite acquisition manifest 🟢

| | |
|---|---|
| **Scientific reason** | Provenance currently depends on scanning `.SAFE` filenames under `data/raw_assets/raster_data/`, **which does not exist in a clean checkout**. A third party cannot regenerate the composite, and the paper cannot state its inputs precisely. |
| **Files** | new `src/validation/acquisition_manifest.py` · new `clean_assets/paper1/acquisition_manifest.json` · new `tests/unit/test_acquisition_manifest.py` |
| **Content** | Window start/end, tile, cloud threshold, SCL policy (including the class-5 asymmetry), composite method, scene IDs, sensor mix, generation timestamp, commit hash |
| **Acceptance criteria** | Committed **before** extraction · schema-validated · a `--check` mode failing if the extracted data disagrees with the manifest |
| **Tests** | Schema validation; `--check` detects a mismatch |
| **Risk** | Low |
| **Changes scientific output?** | **No** |

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

### B-08 · SCM docstring reframing (documentation only) 🟢

| | |
|---|---|
| **Scientific reason** | The module is named "Spatial Causality" and emits `LOCALIZED_IMPACT` described as "human pressure / tourism-related". A spatial gradient is not causal attribution, and a trail produces a trail-proximal contrast simply by existing. |
| **Files** | `src/spatial_causality/analyzer.py` (docstring) · `run_scm_operational.py` (docstring) |
| **Design** | **Docstrings only. No rename, no logic change, no threshold change.** State what SIG measures, that the four decision thresholds are uncalibrated expert heuristics, and that localization is not causation. |
| **Acceptance criteria** | No behavioural diff · a test asserts the docstring contains the non-causal caveat |
| **Tests** | Full existing SCM suite passes unchanged (48 tests currently green) |
| **Risk** | Very low |
| **Changes scientific output?** | **No** |

### B-09 · Figure generation scripts 🟢

| | |
|---|---|
| **Scientific reason** | Figures must be reproducible from committed data, and Figure 1(b), Figure 2 and Table T2 are producible **today** — building them early surfaces CRS and rendering problems long before submission. |
| **Files** | new `scripts/paper1/figure_01_study_area.py`, `figure_02_pipeline.py`, `table_02_constants.py` (+ the rest once data exists) |
| **Acceptance criteria** | Run from a clean checkout · print input checksums and commit hash into figure metadata · vector output · colourblind-safe · **fail loudly rather than plotting anything if required data is absent** |
| **Tests** | Smoke test on committed data; a test asserting the scripts refuse to run on missing inputs |
| **Risk** | Low |
| **Changes scientific output?** | **No** |

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
B-08, B-09(partial), B-06  ← safe, no dependencies, do first
        ↓
B-04 → B-01                ← grid matching must exist before plots are planned
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
| B-01 | Low | No | No — §F resolved |
| B-02 | Medium | No (additive) | **Yes** (🔴 class) |
| B-03 | Low | No | No |
| B-04 | Medium | No | No |
| B-05 | Low | No (default preserved) | **Yes** (🔴 class) |
| B-06–B-09 | Low | No | No |
| B-10 | Medium | Creates new only | No |
| B-11 | Low | No | No |
| B-12 | Medium | No | No |
| B-13 | Low | No | No |
| B-14 | Low | No | No |

**Two items (B-02, B-05) carry the 🔴 classification and require explicit owner approval before implementation**, in both cases because a careless implementation could change existing scientific output even though the specified implementation does not. Both are specified as strictly additive, and both carry a regression test asserting the existing path is byte-identical.
