# SNTO Baseline Audit — 2026 (Phase 0)

## Purpose

This folder is the **factual baseline** for the controlled modernization of SNTO
from a broad geospatial tourism dashboard into a protected-area decision-support
platform. It is **diagnostic only**. No application code, configuration,
dependency, schema, test, workflow, or user-facing content was modified to
produce it.

## Scope and method

- **Branch:** `audit/2026-baseline-phase0` (cut from `docs/v3-status-sync-rebuild`).
- **Date of audit:** 2026-08-02.
- **Repository commit at audit time:** `ed25d0a`.
- **Method:** direct reading of entry points, `src/`, `tests/`, workflows,
  configuration and dependency manifests, plus **runtime probing** of the
  evidence gates (`resolve_signals`, `snapshot_provenance`, `detect_scene_dates`)
  and a full local test run. Documentation claims were checked *against code and
  data*, not accepted at face value.

Every finding below carries a code path. Where documentation and implementation
disagree, both are reported and neither is silently preferred —
see [`CONTRADICTIONS_AND_OPEN_QUESTIONS.md`](CONTRADICTIONS_AND_OPEN_QUESTIONS.md).

## Documents

| File | Contents |
|---|---|
| [`SYSTEM_BASELINE.md`](SYSTEM_BASELINE.md) | What the system is today, in one document: identity, releases, deployment reality, the two-pipeline split. |
| [`ARCHITECTURE_BASELINE.md`](ARCHITECTURE_BASELINE.md) | Entry points, module boundaries, coupling, persistence, ingestion, config, CI/CD, bottlenecks. |
| [`FEATURE_INVENTORY.md`](FEATURE_INVENTORY.md) | Every user-facing surface: 4 layers × 14 modules, asset page, exports, controls. |
| [`MAP_INVENTORY.md`](MAP_INVENTORY.md) | Every map and geospatial visualization, with evidence status and explicit risk flags. |
| [`KPI_INVENTORY.md`](KPI_INVENTORY.md) | Every metric, score, index, threshold, badge and traffic-light, with formula and recommendation. |
| [`DATA_SOURCE_INVENTORY.md`](DATA_SOURCE_INVENTORY.md) | Provider, coverage, licence, transformation, caching, fallback and failure behaviour per source. |
| [`SCIENTIFIC_CLAIMS_REGISTER.md`](SCIENTIFIC_CLAIMS_REGISTER.md) | Material claims extracted from UI text, docs, comments and variable names, each classified. |
| [`TEST_BASELINE.md`](TEST_BASELINE.md) | Commands run, results, coverage, skips, untested critical paths, reproducibility problems. |
| [`REMOVAL_CANDIDATES.md`](REMOVAL_CANDIDATES.md) | Candidates with evidence, dependencies, migration path, risk and confidence. **Nothing was deleted.** |
| [`CONTRADICTIONS_AND_OPEN_QUESTIONS.md`](CONTRADICTIONS_AND_OPEN_QUESTIONS.md) | Doc↔code disagreements and questions only the owner can settle. |
| [`PHASE_1_RECOMMENDATIONS.md`](PHASE_1_RECOMMENDATIONS.md) | Proposed Phase 1 scope with acceptance criteria. Not implemented. |

## The three things a reader should take away

1. **The dashboard shows two parallel realities in the same screens.** The
   executive portfolio (KPIs, tiers, budget, alerts) is computed from **8
   hard-coded PNSG fixture assets** (`src/territorial/fixtures.py`), while the
   real Sentinel-2 evidence covers **218 real trails**
   (`data/outputs/pnsg/pipeline_a_results.geojson`). The two sets are labelled,
   but they are not reconciled, and the headline indicators come from the
   fixtures.

2. **Sentinel-2 is not, and cannot be, a visitor-pressure measurement — but at
   least one KPI states that it is.** `Human Pressure Alerts` (KPI 7) reports
   "sites experiencing measurable environmental damage caused by visitor
   pressure" and "confirmed visitor-driven environmental damage" from an SCM
   classification that is either a fixture constant or an α-decay **simulation**
   (`src/spatial_causality/zones/` does not exist). This is the single
   highest-risk claim in the product.

3. **The evidence-class machinery is genuinely good and should be preserved.**
   `src/platform/evidence.py`, the forecasting evidence guard, the LAC/ROS
   labelling and the CETS/PRUG live-probe reporting are careful, tested work.
   The modernization should extend that discipline into the places it has not
   yet reached (maps, KPI narrative text, fixtures) rather than rebuild it.

## What this audit deliberately did not do

- No internet literature review (out of scope for Phase 0).
- No repair of the one failing test.
- No formatting, refactoring, renaming, or deletion.
- No production-dependency changes.
- No architecture proposals beyond the Phase 1 scope note.
