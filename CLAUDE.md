# Claude Code Context: SNTO

SNTO means Smart Natural Tourism Observatory. The active case study is Parque Nacional de la Sierra de Guadarrama (PNSG). Sierra del Rincon is archived and is no longer the active pilot. The project is currently a Python 3.12 / Streamlit scientific-product prototype with research and SaaS ambitions.

## Current Status

- v1.0.0, v1.1.0, and v1.1.1 are released and tagged in `main` (PR #1 merged 2026-07-09; statistical fix via PRs #19/#20).
- v1.2.0 (OAPN multi-park expansion) is code-complete in open PRs #21 + #22 (stacked). Only the manual GEE data export for the pilot parks (Tablas de Daimiel, Monfragüe) is pending; the code merge does not depend on it (default `park="pnsg"` keeps behavior identical).
- Statistical-rigor work lives in `research/statistical-rigor` (cut from an old `main`; must be rescued via cherry-pick, not merged directly) → planned as v1.3.0.
- The operational roadmap is `docs/roadmap/plan_fases_post_v1.2.md` (Fases 0–5), tracked in issues #24–#28.
- v2.0 should not start before v1.2/v1.3 integration and app modularization.

## Pull Requests

- PR #21 (`feature/v1.2.0-oapn-network-expansion-clean` → `main`): GEE templates for 15 OAPN parks + pilot plan. Additive, low risk. Merge first.
- PR #22 (`feature/v1.2.0-oapn-integration`, stacked on #21): multi-park generalization of the temporal flow. Backward compatible by design. Merge after #21.
- PR #1 (v1.1.0) and PR #7 (contaminated docs) are resolved history: #1 merged; #7's docs content reached `main` and its functional commits are preserved on `research/statistical-rigor`.

## Architecture Facts

- `app.py` is currently a monolith of around 3,170 lines (and growing).
- The analytical core under `src/` is healthier and better separated.
- The main architectural risk is concentration of UI, orchestration, state, copy, and product logic in `app.py`.
- A FastAPI API exists but is secondary and under-integrated.
- The Streamlit dashboard is feature-rich but cognitively dense.

## Product Direction

SNTO has the intellectual core of a reference product but the body of an advanced academic prototype. It should become a decision-intelligence layer for protected natural tourism destinations. It should not try to replace ArcGIS, Google Earth Engine, Sentinel Hub, Tableau, or Power BI. It should integrate with or sit above GIS, Earth observation, and BI tools.

## Roadmap Discipline

- v1.1: integration, stabilization, real temporal evidence, evidence clarity.
- v1.2: controlled expansion and pilot readiness.
- v2.0: modular architecture, UI evolution, backend/platform foundations.
- v3.0: enterprise/institutional maturity and multi-park scaling.

## Non-Negotiables

- Do not modify `main` directly.
- Do not merge PRs without explicit human approval.
- Do not mix documentation PRs with functional changes.
- Do not begin major UI evolution before modularizing `app.py`.
- Do not blur real, calibrated, synthetic, or simulated evidence.
- Do not overclaim scientific validity before validation.
- Preserve scientific transparency and methodological caveats.

## Next Recommended Actions

Follow `docs/roadmap/plan_fases_post_v1.2.md`:

1. Fase 0 (code): review and merge PR #21, then PR #22 (human approval required).
2. Fase 0 (data): run the GEE exports for Tablas de Daimiel and Monfragüe, ingest via `run_timeseries_analysis.py --park <key>`, QA per biome, then tag `v1.2.0`.
3. Fase 1 (remaining): delete the superseded branches listed in the plan (verified against `main`; requires explicit owner confirmation).
4. Fase 2: rescue `research/statistical-rigor` via clean cherry-pick branch → v1.3.0 (issue #24).
5. Fase 3: pilot readiness — GIS export (#25), field validation (#26), risk brief (#12), evidence separation (#10), positioning copy (#9) → v1.4.0.
6. Fase 4: modularize `app.py` (#27) before any major UI redesign, then rescue the audience-views branch (#28).

