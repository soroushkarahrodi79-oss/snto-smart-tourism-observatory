# Claude Code Context: SNTO

SNTO means Smart Natural Tourism Observatory. The active case study is Parque Nacional de la Sierra de Guadarrama (PNSG). Sierra del Rincon is archived and is no longer the active pilot. The project is currently a Python 3.12 / Streamlit scientific-product prototype with research and SaaS ambitions.

## Current Status

- v1.0.0 is already released/deployed.
- v1.1.0 exists as PR #1 and focuses on the real Sentinel-2 temporal layer for 2021-2026.
- v1.2.0 and statistical-rigor work exist as future branches/work.
- v2.0 should not start before v1.1/v1.2 integration and app modularization.

## Pull Requests

- PR #1, `feat: v1.1.0 - capa temporal Sentinel-2 real 2021-2026`, is a functional v1.1.0 PR. It is coherent but high risk and is not safe to merge until conflicts, checks, generated assets, dependencies, and implementation details are reviewed.
- PR #7, `docs: add SNTO strategic knowledge base 2026`, was intended as docs-only but is contaminated with functional changes. Do not merge it as-is.
- A clean docs-only branch has been recreated from `main`: `docs/strategic-knowledge-base-2026-clean`. It should contain only `docs/**`, `MASTER_STRATEGIC_INDEX.md`, and later AI handoff Markdown if included intentionally.

## Architecture Facts

- `app.py` is currently a monolith of around 2,890 lines.
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

1. Open a new PR from `docs/strategic-knowledge-base-2026-clean`.
2. Verify the clean docs PR contains only documentation/context files.
3. Close contaminated PR #7 only after the clean PR exists and is verified.
4. Keep PR #1 open.
5. Resolve PR #1 conflicts and run CI/checks.
6. Review `app.py`, requirements, `pyproject.toml`, workflows, and generated assets in PR #1.
7. Convert v1.1 roadmap items into actionable tickets.
8. Modularize `app.py` before any major UI redesign.

