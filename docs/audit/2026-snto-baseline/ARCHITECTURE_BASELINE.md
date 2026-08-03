# Architecture Baseline

## 1. Entry points

| Entry point | Path | Role |
|---|---|---|
| Dashboard | `app.py` (346 lines) | Streamlit composition + navigation only. Deployed. |
| Stateless API | `src/api/main.py` → `src/api/routers/{evaluate,ranking,alerts}.py` | Legacy v1 surface. **Not deployed.** |
| Persistent API | `src/api/v2/` (10 modules) | Read + write over persistence. **Not deployed** (ADR-012). |
| Mobile client | `mobile/` (Expo/TypeScript) | Separate app, own CI, defaults to mock repository. |
| ETL / pipeline scripts | 25 `.py` files at repository root | Offline, manually invoked. |
| Ops scripts | `scripts/` | `build_dossier.py`, `export_openapi.py`, `sync_readme.py`, `export_gis.py`, GEE `.js` exporters. |

`app.py` is genuinely composition-only — the Fase 4 modularization succeeded.
Its body is: page config → sidebar → `load_dashboard()` → asset-route check →
4 layer tabs × 14 module tabs dispatched by `NavigationModule.key` → footer.
The only logic in it is the socio-economic overlay assembly (`app.py:190-202`)
and the executive-KPI gate on `_view.home_layer == "decidir"` (`app.py:227`).

## 2. Module map

```
src/
├── ingestion/          GEE / STAC / mock / calibrated / multiyear adapters
├── features/           spectral index computation (NDVI, NDMI, EVI)
├── geospatial/         geometry + zonal aggregation (shapely / rasterio)
├── time_series/        Mann-Kendall, Sen, prewhitening, decomposition,
│                       climatology, changepoint, anomaly, volatility, confidence
├── temporal/           DataStatus manifest, series spec, trend_gate
├── risk_engine/        EHS composite, risk components, baselines, human_pressure
├── spatial_causality/  SCM analyzer + real-zone loader (zones dir absent)
├── decision_confidence/DCS assessor
├── territorial/        TerritorialAsset model, TPI, tiers, budget, allocator,
│                       fixtures (hard-coded assets), manifest, reporter
├── intervention/       TIS, scenarios, impact, planning, reporter
├── platform/           dashboard KPIs, map_layers, charts, evidence, provenance,
│                       calibration, enrichment, real_trails, lineage, views,
│                       methodology, maturity, stakeholders, value, translator,
│                       playbooks, lac_ros, pressure_capacity, telemetry,
│                       satellite_trends, territory_registry, confidence_explain
├── forecasting/        Sen projection + seasonal (always SIMULATED)
├── mobility/           MITMA loader/bridge (snapshot absent)
├── socioeconomic/      INE/ALMUDENA loader, SVI, indicators, series
├── validation/         field agreement (Spearman/Cliff), confusion, cross_sensor
├── calibration/        EHS sensitivity, validator
├── benchmarking/       OAPN cross-park rollup
├── reporting/          risk_brief, territorial_brief, gis_export, cets_readiness,
│                       prug_monitoring, institutional_dossier, report_builder
├── persistence/        SQLAlchemy 2.0 models, repositories, services, migrations
├── api/                v1 routers + v2 persistence surface
├── config/             settings, constants, territories, logging, run_context
└── ui/                 layout, navigation, render_helpers, render_widgets,
                        asset_detail, asset_navigation, kpi_sections,
                        tabs/ (14), services/ (4)
```

Total: ~10 371 statements measured by coverage, across ~210 Python modules.

## 3. Module boundaries — assessment

**Clean and well-separated:**

- `time_series/`, `temporal/`, `validation/`, `forecasting/`, `metrics/` — pure
  functions, no Streamlit, well tested.
- `persistence/` — textbook layering (models → repositories → services →
  session), typed, with Alembic migrations and a real-Postgres CI job.
- `platform/evidence.py` — the canonical vocabulary. Every other module that
  needs a provenance tier should read from here; most do.

**Boundary problems:**

| Issue | Evidence | Impact |
|---|---|---|
| `src/platform/` is a grab-bag | 27 modules spanning KPI computation, map rendering, chart building, provenance, playbooks, stakeholder models, maturity scoring, value modelling | No coherent responsibility; the name conveys nothing; new work has no obvious home. |
| Presentation logic inside `platform/` | `map_layers.py` (660 lines, Deck.gl), `charts.py` (713 lines, Plotly) | Rendering concerns sit below the UI layer; `src/ui/` imports *up* into `platform` for view construction. |
| Narrative text embedded in computation | `platform/dashboard.py` (564 lines) mixes KPI arithmetic with Spanish/English management prose and recommended actions | Cannot change a claim without editing computation; cannot unit-test the claim separately from the number. See `SCIENTIFIC_CLAIMS_REGISTER.md`. |
| Fixture data inside a domain package | `src/territorial/fixtures.py` (561 lines of hard-coded assets) is imported by `src/ui/layout.py:17` at dashboard load | Demo data is on the production path, not behind a flag — and per the Q-01 owner decision it is **`SYNTHETIC`**, a class the gating matrix permits for no decision use at all. |
| Root-level scripts import into tests | `tests/unit/test_operational_ehs.py` imports `calculate_delta_ehs`; `tests/unit/test_tis_causal_budget.py` imports `tis_engine` | Both root modules call `load_dotenv()` at import → process-wide env mutation → test-order-dependent failure (`TEST_BASELINE.md`). |

## 4. Duplication

| Duplicated concept | Locations | Notes |
|---|---|---|
| RdYlGn EHS colour ramp | `platform/map_layers.py:627` `_SPECTRAL_RAMP`; `platform/real_trails.py:261` `ramp`; `ui/tabs/tab_diagnostic.py:184` `_spectral_legend`; `ui/tabs/tab_diagnostic.py:358` `_legend` | Four copies of the same six anchor colours, with **two different band labellings** (`≥75 Saludable` vs `EHS 75-85 Bueno / >85 Óptimo`). |
| Alert-level thresholds | `src/alerts/engine.py::_classify_level`; re-implemented in `platform/enrichment.py:50` `_alert_from_risk` | Explicitly acknowledged in the docstring as a mirror ("Espeja src/alerts/engine.py"). Two sources of truth. |
| Evidence vocabulary | `platform/evidence.py::EvidenceClass`; `temporal/manifest.DataStatus`; `platform/methodology.DataType`; `platform/provenance.StatusBadge` | Three enums + a badge table for one concept. `evidence.py` reconciles them, but four vocabularies remain in circulation and `provenance._STATUS_BADGE` duplicates `evidence._DESCRIPTORS` strings verbatim. |
| Trail geometry synthesis | `map_layers._trail_path` (synthetic) vs `real_trails.build_real_trails_geojson` (real) | Two geometry producers feeding two maps in one tab. |
| Priority band definitions | `real_trails.PRIORITY_BANDS`; `territorial/tpi._classify_tier`; `map_layers.LEGEND_ITEMS` | Three separate classifications of "how urgent is this asset". |

## 5. Persistence model

- **ORM:** SQLAlchemy 2.0, `src/persistence/models/` — `Territory`,
  `ManagedAsset`, `Observation`, `Alert`, `FieldVerification`, `Intervention`,
  `Decision`, `Recommendation`, `AuditLog`, plus v3.0 `Organization` / `User`.
- **Engine selection:** `src/config/settings.py:41` `database_url` property —
  explicit override > Postgres (when `SNTO_DB_HOST` set) > SQLite at
  `data/outputs/snto.db`.
- **Migrations:** Alembic, single head `b2c3d4e5f6a7`. Three revisions:
  initial schema, v3.0 identity/tenancy, v3.0 PostGIS geometry.
- **Authorization:** `require_write_auth` (shared API key) + `authz_gate.py`
  (`authorize_territory_write`). The latter is **dormant** — it has no effect
  until real `User` rows exist, and none do.
- **Live consumers:** only `src/ui/services/` (in-process, from Streamlit).
  `/api/v2` has no deployed endpoint; `mobile/` targets it but defaults to mocks.

**Gap:** nothing in `src/` writes the dashboard's assets into `managed_assets`.
The persistence layer and the analytical layer are not connected in either
direction on the live path — the dashboard reads fixtures, not the database.

## 6. Data ingestion paths

| Path | Trigger | Output | Live? |
|---|---|---|---|
| Sentinel-2 raster → EHS/ΔEHS/SCM | `run_pipeline_a_filemode.py` (manual) | `data/outputs/pnsg/pipeline_a_results.geojson` (**tracked in git**) | Yes — feeds the real-trails map + PRUG report |
| GEE Code Editor → multi-year series | `scripts/gee_code_editor_pnsg.js` → `scripts/run_timeseries_analysis.py` | `clean_assets/timeseries/analysis/mk_trends_<park>.json` | Yes — feeds trends + GIS export |
| OAPN WFS / OSM vector | `etl_oapn_wfs.py`, `etl_vector_cleaner.py`, `etl_oapn_to_trails.py` | `clean_assets/*.geojson`, `data/raw_assets/` | Offline |
| MITMA mobility | `etl_mobility.py` | `src/mobility/snapshot/mobility.json` | **Never run** — dir absent |
| INE / ALMUDENA socio-economic | `etl_socioeconomic.py` | `src/socioeconomic/snapshot/` | One dated snapshot (`2026-06`), no history |
| Multi-scale GEE zones | `scripts/gee_scm_zones_pnsg.js` | `src/spatial_causality/zones/<asset_id>.json` | **Never run** — dir absent |
| Field observations | manual campaign (#26) | `clean_assets/field_validation/*.csv` | **Never run** — template has empty measurement columns |

Only **3 files** under `data/` are tracked in git
(`git ls-files data/`): the PNSG Pipeline A GeoJSON, its summary, and the OAPN
park boundary. The rest of `data/` (including the ~900 MB rasters) is local-only
and git-ignored. A fresh clone therefore reproduces the real-trails map (the
GeoJSON is committed) but **cannot** reproduce the pipeline that produced it, and
`detect_scene_dates()` returns `[]` — at which point
`provenance.snapshot_provenance` silently substitutes `n_scenes = 2` while still
reporting `DataStatus.REAL` (`src/platform/provenance.py:129`).

## 7. Configuration

| Concern | Location | Notes |
|---|---|---|
| Runtime settings | `src/config/settings.py` | Pydantic `BaseSettings`, `env_file=".env"`. Module-level singleton `settings = Settings()` at line 53. |
| Scientific constants | `src/config/constants.py` | Alert thresholds, DCS gates. |
| Territory definitions | `src/config/territories.py` + `src/ui/layout.py:310` `_TERRITORY_CONFIG` | **Two registries.** The UI one holds budget, map centre, report date; the config one holds raster folder names. |
| Report date | `src/ui/layout.py:306` | `REPORT_DATE = "2026-06-12"` — a hard-coded literal presented as "Fecha de informe". |
| Visible territories | `src/ui/layout.py:336` | `["pnsg"]` |
| Secrets | `.env` (git-ignored, `.gitignore:48`) | Contains DB credentials and GEE service-account paths. Key Vault migration documented but not executed. |

## 8. Deployment

- `Dockerfile` + `.github/workflows/deploy-azure-container-apps.yml`.
- Deploy is gated on CI success on `main` (ADR-009).
- Azure Container App `snto-observatory`, ACR, Postgres `snto-db`, Sweden Central.
- Known ops constraint: single-revision Container Apps do not pick up updated
  secret values without an explicit `az containerapp revision restart`.
- `SNTO_API_KEY` intentionally unset in production — safe only while the sole
  writer is the in-process Streamlit UI.

## 9. Testing and CI

`.github/workflows/ci.yml` — four jobs:

1. **lint** — `ruff` blocking on an explicit allow-list of ~45 maintained paths;
   `ruff check src tests *.py` report-only for the rest. This encodes real lint
   debt outside the list.
2. **test** — import smoke, `py_compile` on 3 entry points,
   `pytest --cov=src --cov-fail-under=80`, then three `--check` gates
   (`sync_readme.py`, `build_dossier.py`, `export_openapi.py`).
3. **typecheck** — `mypy src/persistence src/api/v2 src/config`, **report-only**
   (`continue-on-error: true`); ~110 outstanding `--strict` errors per the
   workflow comment.
4. **postgres-integration** — `tests/persistence` against `postgis/postgis:16-3.4`.

`mobile-ci.yml` is path-filtered on `mobile/**` and fully decoupled.

## 10. Architectural bottlenecks (ranked)

| # | Bottleneck | Why it blocks modernization |
|---|---|---|
| B-1 | Decision layer rooted in `fixtures.py` | Every KPI, tier, budget and alert traces to hand-authored constants classified **`SYNTHETIC`** (Q-01). No amount of real-data ingestion changes the headline numbers until this is inverted. |
| B-2 | `platform/` has no responsibility boundary | Nowhere obvious to put new decision-support logic; rendering, computation and narrative all coexist. |
| B-3 | Narrative claims compiled into KPI computation | Cannot correct a scientific overclaim without touching arithmetic; cannot A/B a claim; cannot review claims as a set. |
| B-4 | Two territory registries + hard-coded report date | Blocks genuine multi-territory operation and makes "as of" dates untrustworthy. |
| B-5 | No path from analytical core → persistence | `managed_assets` is empty; PostGIS, tenancy, audit and the mobile/API surfaces have nothing to serve. |
| B-6 | Synthetic geometry on the primary map | Any spatial claim on the territorial map is not reproducible (see `MAP_INVENTORY.md`). |
| B-7 | 25 root-level scripts with import side effects | Pollutes the test process, has no packaging, and hides which pipelines are current. |
| B-8 | **46 compiled `.pyc` files are tracked in git** (`git ls-files "*.pyc"`) | Running the test suite *modifies tracked files*, so `git status` is never clean after a test run and every contributor produces spurious diffs. They are stale `cpython-314` artifacts while the project targets 3.12. `.gitignore` does not exclude `__pycache__/`. |
