# Paper 1 — Scientific Validation Program

Publication-oriented working set for **one** paper: empirical validation of SNTO's Sentinel-2-derived ecological stress indicator against real field observations in Parque Nacional de la Sierra de Guadarrama.

**Start here:** [`PAPER1_MASTER_EXECUTION_PLAN.md`](PAPER1_MASTER_EXECUTION_PLAN.md)

## Documents

| # | Document | Purpose |
|---|---|---|
| 0 | [`PHASE0_REPOSITORY_AUDIT.md`](PHASE0_REPOSITORY_AUDIT.md) | What the code and data actually support, verified against implementation and tests |
| 1 | [`PAPER1_SCIENTIFIC_CONTRACT.md`](PAPER1_SCIENTIFIC_CONTRACT.md) | **Governing document.** Question, hypotheses, evidence rules, stop/go, forbidden claims |
| 2 | [`FIELD_CAMPAIGN_EXECUTION_PLAN.md`](FIELD_CAMPAIGN_EXECUTION_PLAN.md) | Two-stage sampling design + field-day checklist |
| 3 | [`SPATIAL_MATCHING_PROTOCOL.md`](SPATIAL_MATCHING_PROTOCOL.md) | Plot ↔ satellite support; the sub-pixel problem |
| 4 | [`SATELLITE_FIELD_MATCHING_PLAN.md`](SATELLITE_FIELD_MATCHING_PLAN.md) | Acquisition window, quality rules, no-interpolation rule |
| 5 | [`STATISTICAL_ANALYSIS_PLAN.md`](STATISTICAL_ANALYSIS_PLAN.md) | **Freeze before data collection.** Tests, thresholds, sensitivity |
| 6 | [`SCM_REFRAMING.md`](SCM_REFRAMING.md) | Spatial contrast ≠ causal attribution; threshold provenance |
| 7 | [`DATA_ACQUISITION_TRIAGE.md`](DATA_ACQUISITION_TRIAGE.md) | Must / secondary / future / never-fabricate |
| 8 | [`MANUSCRIPT_OUTLINE.md`](MANUSCRIPT_OUTLINE.md) | Skeleton with every absent result marked `[TBD]` |
| 9 | [`FIGURE_PLAN.md`](FIGURE_PLAN.md) | Figures + required source data |
| 10 | [`JOURNAL_STRATEGY.md`](JOURNAL_STRATEGY.md) | Venue fit; decision staged until results exist |
| 11 | [`IMPLEMENTATION_BACKLOG.md`](IMPLEMENTATION_BACKLOG.md) | Minimum code; **nothing implemented pending approval** |
| — | [`PNSG_RESEARCH_AUTHORIZATION_REQUEST.md`](PNSG_RESEARCH_AUTHORIZATION_REQUEST.md) | Draft permit application (gate G2). Technical content complete; applicant identity and territorial scope (Madrid vs. Castilla y León) still open. **Nothing submitted.** |

## Status

**No scientific threshold has been modified. No existing scientific output has changed. No field data exists.** The only code added so far is additive Paper-1 infrastructure (Backlog B-06, the acquisition manifest) that touches no existing module's behaviour.

**Decisions taken (2026-08-09):**
- **Sampling frame — the 218 real OAPN trail segments** (`PAPER1_SCIENTIFIC_CONTRACT.md` §F, F-1). Forfeits nothing the cross-sectional design needed, but the existing real SCM/SIG values on those trails are **not** usable for H4 as-is — same disqualified scene pair as `delta_ehs`; needs a fresh extraction against the campaign-matched composite (Backlog B-14).
- **Permit scope — Comunidad de Madrid sector only** (`PNSG_RESEARCH_AUTHORIZATION_REQUEST.md` §1): one application, not two; the Madrid side spans the full elevation/habitat gradient.
- **Target field season — summer 2027, ~20 Jun – 31 Jul** (2028 fallback), strata sampled low-early / high-late to bracket out snow and drought senescence (`SATELLITE_FIELD_MATCHING_PLAN.md` §2).

**Infrastructure landed (additive, no existing output changed):** the acquisition manifest (`src/validation/acquisition_manifest.py`, committed at `status=planned`) · plot↔satellite-cell matching (`src/validation/spatial_match.py`, B-04) — the 20 m-support grid, SM-1…SM-4 independence checks, and a coverage-gated extractor that raises on grid/CRS misalignment rather than resampling silently · the SCM causal-reframing caveat (B-08, docstring-only) · the three committed-data figures/table (B-09: `scripts/paper1/figure_01_study_area.py`, `figure_02_pipeline.py`, `table_02_constants.py` → `docs/paper1/figures|tables/`, each with a provenance sidecar) · the field plot-plan engine (B-01: `scripts/paper1/generate_plot_plan.py` → distinct, SM-1/2/3-validated impact/control coordinates + GPX) · the ecological-strata engine (A-4: `scripts/paper1/build_ecological_strata.py` → S1–S4 per trail from a DEM, wired into B-01 via `--strata`).

**B-01's Madrid jurisdiction filter is now finalised (2026-08-15):** the owner supplied the real Comunidad de Madrid boundary (OpenStreetMap relation 349055, 6 294 vertices), validated against known landmarks (La Pedriza in / Valsaín out) and repaired for a minor topology defect. `clean_assets/field_validation/pnsg_plot_plan.csv` is regenerated with `--boundary-authoritative` — no longer `_PROVISIONAL`.

**A-4's strata are now real (2026-08-16):** the owner supplied a Copernicus GLO-30 DEM directly; it was reprojected to the pipeline's metric CRS (`scripts/paper1/reproject_dem_to_utm.py`, verified deterministic) and used to classify all 218 trails into S1–S4, with 0 unresolved and elevations sanity-checked against Peñalara's real summit. `clean_assets/field_validation/pnsg_plot_plan.csv` now carries these real ecological strata rather than the interim satellite-stress tercile. The raw DEM itself is not committed (repo-wide raster policy); the derived strata table and its provenance sidecar are (`clean_assets/field_validation/reference/README.md`).

Remaining blocking items are marked 🔲 throughout; they are collected in the Master Execution Plan §7 — chiefly the applicant identity for the permit, and the go-ahead to file.

## Relationship to existing documentation

- **Supersedes for Paper-1 purposes:** `docs/field_validation_protocol.md` (audited and extended in #2), and the validation-readiness prose in `docs/methodology/validation.md`.
- **Builds on, does not duplicate:** `docs/audit/2026-snto-baseline/` (the broader Phase 0 system baseline, PR #143).
- **Does not modify:** `WHITEPAPER_SNTO_Architecture_Blueprint.md`, which tracks the latest *stable* methodological baseline by its own scope rule and must not be rewritten with dev-branch work.
- **Preserves unchanged:** the `INSUFFICIENT_EVIDENCE` state of visitor-pressure forecasting, and every ADR-004 evidence-class rule.

## Non-negotiables carried into every document here

Never fabricate an observation · never promote `SYNTHETIC` / `SIMULATED` / `ESTIMATED` / proxy evidence to `OBSERVED` · never substitute NDVI/NDMI/EHS/capacity/mobility for a visitor measurement · no causal claim without REAL evidence **+** validated method **+** supported attribution **+** independent verification · when evidence is missing, say **MISSING**; when a method is plausible but unvalidated, say **PLAUSIBLE BUT UNVALIDATED**; when a proxy is used, name it **and** name the target it does not measure.
