# Claude Code Context: SNTO

SNTO means Smart Natural Tourism Observatory. The active case study is Parque Nacional de la Sierra de Guadarrama (PNSG). Sierra del Rincon is archived and is no longer the active pilot. The project is currently a Python 3.12 / Streamlit scientific-product prototype with research and SaaS ambitions.

## Current Status

- v1.0.0 → v1.4.0 are all released and tagged in `main`. `main` is on `1.5.0.dev0` (a development marker, not a release): pyproject.toml / `src/_version` / CITATION.cff all read `1.5.0.dev0`, and the last stable tag is `v1.4.0`.
- v1.2.0 (OAPN multi-park expansion), v1.3.0 (statistical rigor), and v1.4.0 (decision integration: risk brief #12, GIS export #25, evidence separation #10, positioning #9, field-validation tooling #26) are merged. Only the manual GEE field-validation campaign for the pilot parks remains open work, not a code blocker.
- **Fase 4 (`app.py` modularization, #27) is COMPLETE.** `app.py` went from ~3,170 lines to ~285 (composition/navigation only); the UI was extracted to `src/ui/`.
- **Audience-views rescue (#28) is COMPLETE.** The `claude/tourism-observatory-views-audit-jyl38k` branch was rescued (re-implemented, not cherry-picked) onto the modular structure.
- The operational roadmap is `docs/roadmap/plan_fases_post_v1.2.md`. The next milestone is v2.0 (role-based UI evolution) — **not yet started**, by owner decision.

## Pull Requests

- No SNTO release PRs are currently pending. Fase 3 (#33–#37), Fase 4 modularization (#38–#53) and the #28 audience-views rescue (#54–#59) are all merged.
- Historical note: PR #1 (v1.1.0) merged; the statistical-rigor work formerly on `research/statistical-rigor` reached `main` via the v1.3.0 rescue.

## Architecture Facts

- `app.py` is now ~285 lines: page setup + sidebar/KPI assembly + `st.tabs(...)` + the eight `with tab_x: render_tab_x(...)` calls + footer. Composition and navigation only.
- The UI lives in `src/ui/`: `layout.py` (page config, institutional CSS, territory registry, cached `load_dashboard`), `render_helpers.py` (presentation primitives), `render_widgets.py` (`st.`-rendering widgets), and `src/ui/tabs/` (one module per tab).
- Audience views: `src/platform/views.py` (`ViewProfile.section()` is the single layered-disclosure contract), `src/platform/telemetry.py` (local opt-in usage telemetry, `SNTO_TELEMETRY=1`). Financial figures are invariant across views (verified by `tests/integration/test_view_modulation.py`).
- The analytical core under `src/` is well separated. A FastAPI API exists but is secondary and under-integrated.
- The Streamlit dashboard is feature-rich; the audience-view modulation (#28) reduces cognitive density per role.

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

Fases 0–4 of `docs/roadmap/plan_fases_post_v1.2.md` and the #28 rescue are done. Remaining / next:

1. **Owner-only cleanup (needs explicit confirmation; the environment cannot push branch/tag deletions):** delete the already-merged/rescued `claude/tourism-observatory-views-audit-jyl38k` branch and the stale `feature/v1.5.0-*` branches; close issue #28.
2. **Field-validation campaign (#26):** the tooling/protocol are merged; the real ground-truth campaign (penetrometer/cover/erosion on PNSG priority assets) is manual field work, still pending — do not claim validation until collected.
3. **v2.0 — role-based UI evolution** (`docs/ux/ui-evolution-v2-spec.md`): the natural next milestone on top of the modular `src/ui/` + audience views. **Not started, by owner decision — do not begin without explicit go-ahead.**

When cutting the next release, bump `pyproject.toml` from `1.5.0.dev0`, run `scripts/sync_readme.py`, and tag.

