# Claude Code Context: SNTO

SNTO means Smart Natural Tourism Observatory. The active case study is Parque Nacional de la Sierra de Guadarrama (PNSG). Sierra del Rincon is archived and is no longer the active pilot. The project is currently a Python 3.12 / Streamlit scientific-product prototype with research and SaaS ambitions.

## Current Status

- v1.0.0 → v1.5.0 are all released and tagged in `main`. `main` is on `1.6.0.dev0` (a development marker, not a release): pyproject.toml / `src/_version` / CITATION.cff all read `1.6.0.dev0`, and the last stable tag is `v1.5.0` (2026-07-18).
- v1.2.0 (OAPN multi-park expansion), v1.3.0 (statistical rigor), and v1.4.0 (decision integration: risk brief #12, GIS export #25, evidence separation #10, positioning #9, field-validation tooling #26) are merged. Only the manual GEE field-validation campaign for the pilot parks remains open work, not a code blocker.
- **v1.5.0 consolidates Fase 4, #28, and Fase 5** (see below) into one tagged, published release (GitHub Release live at the `v1.5.0` tag).
- **Fase 4 (`app.py` modularization, #27) is COMPLETE.** `app.py` went from ~3,170 lines to ~285 (composition/navigation only); the UI was extracted to `src/ui/`.
- **Audience-views rescue (#28) is COMPLETE.** The `claude/tourism-observatory-views-audit-jyl38k` branch was rescued (re-implemented, not cherry-picked) onto the modular structure.
- **Fase 5 (v2.0 persistent-backend foundations, ADR-011 / `docs/roadmap/plan_fase5_v2_foundations.md`) is COMPLETE in code and in production.** All 10 steps 5.0–5.9 are merged (PR #61 design; #62–#70 implementation): SQLAlchemy models + Alembic, typed repositories, a read+write `/api/v2` surface, lifecycle state machines with validated transitions, the alert & field-verification persistence bridges, an audit trail on every write, minimal API-key write-auth (reads open), and the first UI consumer ("Acciones urgentes" tab). **The production Postgres cutover (ADR-011 §4bis) was executed by the owner on 2026-07-18** — see "Next Recommended Actions" #2 for the live-infra facts. No cloud resource was provisioned by any Fase 5 code PR.
- The operational roadmap is `docs/roadmap/plan_fases_post_v1.2.md`. With Fase 5 foundations in place, the next milestone is **Fase 6 — v2.0 role-based UI evolution** (`docs/roadmap/plan_fase6_v2_ui_evolution.md`, implementing `docs/ux/ui-evolution-v2-spec.md`): plan drafted, **awaiting owner sign-off on open navigation/persona decisions (§2 of the Fase 6 plan)** before implementation PRs begin.

## Pull Requests

- No SNTO release PRs are currently pending. Fase 3 (#33–#37), Fase 4 modularization (#38–#53), the #28 audience-views rescue (#54–#59), Fase 5 v2.0 foundations (#61–#70), ADR-012 (#72), and the v1.5.0 release (#73–#74) are all merged.
- Historical note: PR #1 (v1.1.0) merged; the statistical-rigor work formerly on `research/statistical-rigor` reached `main` via the v1.3.0 rescue.

## Architecture Facts

- `app.py` is composition/navigation only: page setup + sidebar/KPI assembly + `st.tabs(...)` + the nine `with tab_x: render_tab_x(...)` calls (the 9th, "Acciones urgentes", is the Fase 5.9 UI consumer) + footer.
- The UI lives in `src/ui/`: `layout.py` (page config, institutional CSS, territory registry, cached `load_dashboard`), `render_helpers.py` (presentation primitives), `render_widgets.py` (`st.`-rendering widgets), `src/ui/tabs/` (one module per tab), and `src/ui/services/` (persistence-backed query services, e.g. `urgent_actions.py`).
- Audience views: `src/platform/views.py` (`ViewProfile.section()` is the single layered-disclosure contract), `src/platform/telemetry.py` (local opt-in usage telemetry, `SNTO_TELEMETRY=1`). Financial figures are invariant across views (verified by `tests/integration/test_view_modulation.py`).
- **Persistence layer (Fase 5, ADR-011):** `src/persistence/` — SQLAlchemy 2.0 models (`models/`), typed repositories (`repositories/`), services (`services/`: the alert & field-verification bridges, lifecycle state machines, and the single audit choke-point), `session.py` (engine/session reading `settings.database_url`), and Alembic migrations (`migrations/`). `src/api/v2/` is the read+write surface over it; write endpoints are gated by `require_write_auth` (API key, `SNTO_API_KEY`), reads are open. Built against SQLite by default; Postgres is env-gated (`SNTO_DB_*`) and never auto-provisioned by code — production now runs against Azure Postgres (`snto-db`) since the 2026-07-18 owner cutover. **The FastAPI app itself is not deployed**; the deployed Streamlit Container App consumes persistence in-process (`src/ui/services/`), so `/api/v2` currently exists as code + tests only.
- The analytical core under `src/` is well separated. The v2 API (`src/api/v2/`) is now the persistence-backed integration surface; the older stateless routers (`/evaluate_asset`, `/ranking`, `/alerts`) remain unchanged.
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

v1.5.0 is released (Fases 0–4, the #28 rescue, and Fase 5 all shipped in it). Remaining / next:

1. **Owner cleanup:** issue #28 is closed. Old merged branches (`feature/v1.5.0-*`, `release/v1.4.0`) can be deleted whenever convenient — none are referenced by anything live.
2. **Production DB cutover (ADR-011 §4bis): ✅ EXECUTED by the owner on 2026-07-18.** Azure Postgres Flexible Server `snto-db` (v16, Burstable B1ms, PostGIS, Sweden Central, same RG as the Container App), narrow firewall (Azure services + owner IP), Alembic created all 9 tables, and the five `SNTO_DB_*` secrets are wired into the `snto-observatory` Container App. Verified live: the "Acciones Urgentes" tab shows the connected-but-empty state. `SNTO_API_KEY` intentionally left unset (writes open) for now. Rollback: unset the 5 `SNTO_DB_*` Container App vars → automatic fallback to local SQLite. Ops gotcha: Container Apps in Single-revision mode do NOT pick up updated secret values without an explicit `az containerapp revision restart`.
3. **Field-validation campaign (#26):** the tooling/protocol are merged (and Fase 5.6 added persistent `FieldVerification` records); the real ground-truth campaign (penetrometer/cover/erosion on PNSG priority assets) is manual field work, still pending — do not claim validation until collected.
4. **Deploy the `/api/v2` HTTP surface:** scoped in **ADR-012** (`docs/decisions/ADR-012.md`) — status quo (not deployed) until a named external consumer appears, then a second scale-to-zero Container App (`snto-api`) from the same image with `SNTO_API_KEY` set before first exposure. Awaiting owner go/no-go on the trigger; no resource provisioned by the ADR.
5. **Fase 6 — v2.0 role-based UI evolution** (`docs/roadmap/plan_fase6_v2_ui_evolution.md`, implementing `docs/ux/ui-evolution-v2-spec.md`): the persistence gate is lifted (Fase 5 shipped). Plan drafted, mapping all 9 current tabs to the spec's 4 IA layers with no functionality rebuilt from scratch — but **3 product/navigation decisions are open for the owner** (plan §2: tabs vs. native multi-page navigation, how the 3 existing view modes map to the spec's 6 personas, and asset-as-a-page routing). Two low-risk steps (6.1 design-system polish, 6.2 close the Urgent Actions P1 gap) are unblocked and can start before those decisions land.

When cutting the next release, bump `pyproject.toml` from `1.5.0.dev0`, run `scripts/sync_readme.py`, and tag.

