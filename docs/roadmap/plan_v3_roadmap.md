# Plan: SNTO Roadmap v2.1 → v3.0 (and beyond)

Execution plan for the post-v2.0 frontier. Complements the high-level
[`v3.0.md`](v3.0.md) (the *what*) with the sequenced *how*, the same way
[`plan_fase5_v2_foundations.md`](plan_fase5_v2_foundations.md) and
[`plan_fase6_v2_ui_evolution.md`](plan_fase6_v2_ui_evolution.md) did for v2.0.
Traces to the priority matrix
[`../reviews/2026/08-priority-roadmap.md`](../reviews/2026/08-priority-roadmap.md)
(actions A05/A07/A14/A15/A16) and ADR-002/003/004/005/008/009/011/012.

## Context

**Why now.** `main` is code-complete at `2.0.0`: the roadmap's whole "v2.0"
vision — modular architecture (Fase 4), persistent backend (Fase 5), role-based
UI (Fase 6) — is shipped. What remains is no longer "finish the UI"; it is the
harder, more professional work the project deliberately deferred, across three
lenses: **tourism-data analytics, tourism management, web/platform engineering.**

**Three honest truths from the codebase that shape every decision below:**

1. **The scientific validation gate has never run once.** The field campaign
   (#26 / **A05**) is tooling-only:
   `docs/field_validation_protocol.md` + `src/validation/{field,agreement}.py`
   exist, but `clean_assets/field_validation/pnsg_field_observations_template.csv`
   has **empty measurement columns**. Per ADR-003 and
   `docs/informe_tecnico_limites.md`, *"satellite EHS ↔ field degradation"* is
   **not defensible today**, and cross-territory transfer (**A14**) depends on
   it. Nothing in v3.0's multi-park / international ambition is legitimate until
   this runs.
2. **The biggest analytical gaps are forward-looking and behavioral.** No
   forecasting anywhere in `src/` (retrospective trend *detection* only); no
   real visitor/mobility data (`etl_tourist_traffic.py` seeds `mock` counts;
   `visitor_capacity_annual` is a curated estimate in
   `src/territorial/fixtures.py`); carrying capacity is a heuristic
   (`src/platform/pressure_capacity.py`); SCM causal attribution runs on
   *simulated* zone signals when multi-scale GEE is absent.
3. **The platform surface is deliberately minimal.** `/api/v2` is built and
   tested but **never deployed** (ADR-012); auth is a single shared API key with
   **no users/roles/orgs** (ADR-005 unmet); territory is only a filterable column
   (no real multi-tenancy); geometry is opaque `Text` (PostGIS unused); deploy
   fires on every push **decoupled from CI** (ADR-009 unmet); UI is entirely
   Streamlit.

**Governing constraint (non-negotiable — `CLAUDE.md` / ADR-004 / UX spec §9,§12):**
never blur real/calibrated/synthetic/simulated evidence; never overclaim
scientific validity before validation; **"more evidence separation than today,
never less"**; **do not launch a public/institutional surface before the
evidence behind it is auditable.** Every phase is gated on this.

**Intended outcome.** A sequenced, honest path from a validated single-park
prototype to an enterprise, multi-park, forecast-capable decision platform where
each release earns its claims — executed as before: **small PRs, per-PR human
merge approval, docs plan first, evidence discipline never relaxed.**

## Design principles (every phase)

- **Validation gates capability** — no transferability/forecast/portal claim
  ships before its evidence is collected and auditable.
- **Analytics before surface** — deepen the model before dressing it in more
  institutional UI (avoids ADR-004 / risk R05 overclaim).
- **Reuse the seams Fase 5 left**: `require_write_auth` (→ SSO), the `Territory`
  table (→ tenancy), the `DataStatus` manifest (→ curated layer), `/api/v2`
  (deploy as-is).
- **Every phase ships a deliverable + tests** and updates the evidence register
  (`docs/informe_tecnico_limites.md`) with what it did and did *not* prove.

## Phase 0 — Land v2.0 & commit this roadmap (docs-only)

1. **Owner:** push `v2.0.0` tag + GitHub Release + rebuild/redeploy the image.
2. **This document** (the committed roadmap; supersedes the `v3.0.md` bullet list
   by expanding it).
3. Follow-up dev-marker bump to `2.1.0.dev0` after the tag (mirrors
   v1.5.0 → 1.6.0.dev0).

## v2.1 — Activation & Governance  *(web/platform; zero new scientific claims)*

Make what already exists reachable and operable. Code-ready or pure ops.

| Action | What | Key files / ADR |
|---|---|---|
| **Deploy `/api/v2`** | ADR-012 Option C: second scale-to-zero Container App `snto-api` from the same image (`uvicorn src.api.main:app`), **`SNTO_API_KEY` set before first exposure**. | `src/api/main.py`, ADR-012, deploy workflow |
| **Deployment governance** | ADR-009: **CI-green gates deploy** (fix deploy-on-every-push), staging→prod promotion, rollback runbook, observability, release approval. | `.github/workflows/*`, `DEPLOY.md` |
| **Secrets hardening** | `SNTO_DB_*` / `SNTO_API_KEY` → **Azure Key Vault via managed identity**; ACR pull via managed identity. | `src/config/settings.py`, workflows |
| **CI hardening** | Coverage gate (`--cov-fail-under`), `mypy` on the typed core, shrink the report-only ruff zone, one **real-Postgres** integration job. | `.github/workflows/ci.yml`, `pyproject.toml` |
| **Repo hygiene** | `git filter-repo` the committed `data/` history bloat; fix two-RG naming; resolve inverted-EHS convention. | `DEPLOY.md`, `src/metrics/semantics.py` |
| **Evidence-tracking gap** | Wrap the curated territorial layer (`fixtures.py`) in a `DataStatus` manifest — machine-tracked "calibrated", matching the satellite series. | `src/temporal/manifest.py`, `src/territorial/models.py` |

**Exit:** API reachable + authed; deploy only on CI-green with rollback; secrets
in Key Vault; coverage/type gates live; evidence class machine-tracked. No change
to any scientific claim.

## v2.2 — Analytical Depth: Forecasting & Real Pressure  *(the biggest capability leap)*

SNTO stops being purely retrospective. Every output carries its evidence class
and uncertainty; nothing is presented as observation.

| Action | What | Key files |
|---|---|---|
| **Forecasting module** | New `src/forecasting/`: NDVI/degradation projection + seasonal-pressure projection on the real 2021–2026 series. Output = band with explicit uncertainty, class `SIMULATED`/`CALIBRATED`, never `REAL`. | new `src/forecasting/`, reuse `src/time_series/{decomposition,confidence}.py` |
| **Real visitor/mobility (pilot)** | Replace the `mock` `etl_tourist_traffic.py` + curated `visitor_capacity_annual` with **one real feed** (INE experimental mobility / telco passive / trail counters). De-circularizes SCM, unlocks real capacity. | new `src/mobility/`, `src/territorial/fixtures.py` |
| **Carrying-capacity upgrade** | Once real footfall exists, move `pressure_capacity.py` to a **LAC/ROS** framework with threshold estimation. Until then, keep it labeled "planning model". | `src/platform/pressure_capacity.py` |
| **Multi-scale real GEE zones** | Export core-vs-landscape NDVI so SCM attribution moves from simulated to **observed** (removes the α-decay simulation). | `scripts/*gee*`, `src/spatial_causality/` |
| **Socioeconomic time-series** | Extend the single 2026-06 INE/ALMUDENA snapshot toward a series so SVI gains a trend. | `src/socioeconomic/`, `etl_socioeconomic.py` |

**Exit:** a labeled forecast surface with honest uncertainty; ≥1 real visitor
feed replacing a mock; SCM backed by observed zones where data allows.

## v2.5 — Validation Enablement  *(the scientific gate; campaign is owner field-work)*

Code makes the campaign possible and capturable; the owner (with PNSG / EUROPARC)
runs it. **v3.0 cannot legitimately start until this produces real numbers.**

| Action | What | Key files |
|---|---|---|
| **Field-capture workflow** | Mobile-friendly capture over the now-deployed `POST …/field-verifications`, writing real `FieldVerification` rows. | `src/api/v2/field_verifications.py`, new capture UI |
| **Run the agreement analysis** | On ≥3 (ideally ≥15+15) co-located plots, run the already-built Spearman ρ + Cliff's δ and publish the verdict honestly. | `src/validation/agreement.py` |
| **MODIS cross-sensor run** | Execute the built-but-never-run cross-sensor validation. | `src/validation/cross_sensor.py`, `scripts/gee_modis_validation_pnsg.js` |
| **Per-biome SCL mask correction** | Fix the retained 12 OAPN parks whose MK yields artifacts (Teide/Timanfaya malpaís, Islas Atlánticas water) before any 2nd park is exposed. | `scripts/gee_templates_oapn/`, `src/platform/satellite_trends.py` |

**Exit (the gate):** a real PNSG field dataset + a published satellite↔field
agreement result (pass *or* fail, stated honestly). Converts SNTO from
"decision-support prototype" to "validated for PNSG".

## v3.0 — Enterprise & Network  *(gated on v2.5)*

| Action | What | ADR / files |
|---|---|---|
| **Identity, RBAC & multi-tenancy** | `User`/`Role`/`Org` tables; **SSO/Entra ID** by swapping `require_write_auth`; enforce **row-level territory scoping**. | ADR-002/005; `src/persistence/models/`, `src/api/v2/deps.py` |
| **Writable territory registry** | Replace read-only `tab_config.py` (6.7f) with real registration/threshold/role management. | `src/platform/territory_registry.py`, `src/ui/tabs/tab_config.py` |
| **PostGIS geometry** | `ManagedAsset.geometry_geojson` opaque `Text` → real PostGIS geometry (in-DB spatial queries). | `src/persistence/models/`, Alembic migration |
| **Multi-park scale-out** | Incremental park-by-park validation (A14), then OAPN rollups + cross-park benchmarking (A15). | `src/territorial/`, new `src/benchmarking/` |
| **Partner/integration ecosystem** | Publish the OpenAPI contract; GIS/BI surfaces over the API (ADR-008); optional field mobile app. | `src/api/`, ADR-008 |
| **(Optional) decoupled web frontend** | A real SPA consuming `/api/v2` (ADR-012 trigger #3) — true RBAC UX, embedding, white-labeling — only if the product outgrows single-audience Streamlit. | new frontend, `/api/v2` |
| **Institutional productization** | CETS/PRUG reporting pack, OAPN dossier automation, procurement-ready paid-pilot package (A07), EUROPARC engagement. | `docs/product/`, `docs/dossier_institucional_OAPN.md` |

**Exit:** ≥2 protected areas live with tenant isolation + RBAC; national
rollup/benchmarking; a procurement-ready pilot; every park carries its own
validation state.

## v3.x / Future — Category Leadership  *(only after evidence is auditable)*

- **Public transparency portal** (A16) — explicitly gated: never before internal
  evidence is auditable (`v3.0.md`, UX §12 / R05).
- **International validation & case studies** across habitat types (A14 at scale).
- **Persona deepening** — split the 3 view profiles into the full 6-persona model
  (UX §4) if Director-vs-public-decider divergence becomes real.
- **BFAST / multi-breakpoint** temporal decomposition (declared future work).

## Sequencing & the one hard gate

```
Phase 0 ──▶ v2.1 (activation/governance) ──▶ v2.2 (analytics depth)
                                                      │
                                    v2.5 VALIDATION GATE ◀── (owner field campaign)
                                                      │  [hard dependency]
                                                      ▼
                                              v3.0 (enterprise/network)
                                                      │
                                                      ▼
                                          v3.x (portal / international)
```

- **v2.1 and v2.2 run in parallel** (platform vs analytics) — neither asserts new
  science, so neither is gated.
- **v2.5 is the pivot.** If the campaign can't run soon, v2.2 is still fully
  legitimate meanwhile — it claims projection with uncertainty, not validation.
- **The portal is last, always.**

## Verification (per phase)

- **v2.1:** deployed `snto-api` `/health` + an authed write; a forced CI failure
  blocks deploy; secrets resolve from Key Vault; coverage + `mypy` gates green;
  real-Postgres integration job green.
- **v2.2:** unit tests for `src/forecasting/` (band + uncertainty); a real
  visitor feed flows end-to-end; a test asserting every forecast output carries a
  non-`REAL` evidence class.
- **v2.5:** the agreement script emits ρ/δ on real rows; MODIS metrics produced;
  the 12 parks' MK no longer yields artifacts.
- **v3.0:** RBAC/tenancy tests (org A cannot read org B's territory); PostGIS
  spatial-query test; benchmarking rollup test; each new park gated by its own
  `DataStatus`.
- Throughout: `scripts/sync_readme.py --check-version`, full suite green,
  `docs/informe_tecnico_limites.md` updated per phase (proven vs unproven).

## Deliberately de-prioritized (and why)

- **Public portal first** — violates "evidence before surface"; it is last.
- **6-persona UI split now** — the 3-profile model (2.2-A) covers personas today.
- **Full SPA rewrite** — Streamlit suffices until multi-tenant RBAC UX requires a
  decoupled frontend; early is cost without payoff.
- **All 15 OAPN parks at once** — each biome needs its own SCL correction +
  validation; scale is earned park-by-park, not declared.
