# Removal Candidates

**Nothing was deleted, renamed, moved, or modified.** This is a list of
candidates for a *future, separately approved* phase. Every entry states its
evidence, dependencies, migration path, risk and confidence. Several entries
conclude **"do not remove"** — they are listed because a reader might reasonably
expect them here.

Confidence scale: **High** (evidence is conclusive), **Medium** (evidence is
strong, one unknown remains), **Low** (needs an owner decision first).

---

## R-01 · Hard-coded narrative strings in `src/platform/dashboard.py`

| | |
|---|---|
| **Component** | `what_it_means` / `recommended_action` literals in `_kpi_*` functions, especially `_kpi_human_pressure_alerts` (`dashboard.py:380-417`) and the "2022 drought" line in `src/decision_confidence/assessor.py:467-471` |
| **Reason** | They assert measured, confirmed causal attribution of ecological damage to visitors from fixture constants and a simulation. See `SCIENTIFIC_CLAIMS_REGISTER.md` C-01, C-02, C-03. |
| **Evidence** | `resolve_signals('pnsg')['scm_real_zones'] == 0`; `src/spatial_causality/zones/` absent; `scm_classification` is a literal at `fixtures.py:448`; no operational visitor measurement is currently ingested or used by the live decision layer (the MITMA mobility pathway exists in code — `etl_mobility.py`, an honest `mobility_snapshot_exists()` gate — but its snapshot is absent; see `DATA_SOURCE_INVENTORY.md` D-06) |
| **Affected users** | Gestor persona (the KPI strip is their home surface); any external reader of the exported executive brief |
| **Dependencies** | `tab_kpis.py`, `kpi_sections.py`, `render_widgets.py`; `tests/unit/test_dashboard_kpis_empty.py` tests the empty case only |
| **Replacement** | Move claims out of computation into a reviewable claim layer. The correct gate is not "`EvidenceClass == REAL`" alone — it is REAL evidence **+** a validated method **+** a supported attribution **+** independent verification (`PHASE_1_RECOMMENDATIONS.md` PR 0.5.1); no current SNTO indicator clears all four, so no indicator may emit "measurable"/"confirmed"/"caused by" today, regardless of its evidence class. |
| **Risk of removal** | **Low.** Text-only; numbers unchanged; no downstream computation reads these strings. |
| **Confidence** | **High** |
| **Owner decision applied (Q-02)** | Suspend immediately — this is Phase 0.5 work (`PHASE_1_RECOMMENDATIONS.md` PR 0.5.1), not deferred pending real SCM zones. |

## R-02 · Spectral map mode (M-02)

| | |
|---|---|
| **Component** | `map_layers.build_pydeck_deck_spectral` + `_assets_to_geojson_spectral` (`map_layers.py:662-783`); the radio option and legend in `tab_diagnostic.py:117-231` |
| **Reason** | Duplicates M-01's geometry exactly with one attribute swapped; labels calibrated constants as "gradiente espectral NDVI/NDMI"; answers a question the real-trail map (M-03) answers better with real geometry and real spectra. |
| **Evidence** | `MAP_INVENTORY.md` M-02; `map_layers.py:733` vs the module's own "simulating" docstring at `:666` |
| **Affected users** | Técnica and Auditoría personas — this is their *default* map mode (`tab_diagnostic.py:116`) |
| **Dependencies** | `src/platform/__init__.py:35,67` exports; the map-mode radio; spectral legend block; `tests/` reference to `build_pydeck_deck_spectral` |
| **Replacement** | Promote M-03 (real trails) to the top of the tab and make it the technical default. If a spectral view over the curated portfolio is still wanted, it must be relabelled to state that colour encodes EHS (which may be calibrated), not a spectral measurement. |
| **Risk of removal** | **Medium** — removes the default view for two of three personas; needs the M-03 promotion to land first. |
| **Confidence** | **Medium** |

## R-03 · Synthetic trail-geometry generator

| | |
|---|---|
| **Component** | `map_layers._jitter`, `_heading_from_id`, `_trail_endpoints`, `_trail_path`, `_REGION_CENTROIDS`, `_DEFAULT_CENTROID` (`map_layers.py:46-223`) |
| **Reason** | Non-reproducible across processes (`hash()` salting), contradicts its own docstrings, and manufactures switchback realism for features with no survey basis. |
| **Evidence** | `SCIENTIFIC_CLAIMS_REGISTER.md` C-06, C-07; verified hash divergence between interpreter runs |
| **Affected users** | all personas viewing M-01/M-02 |
| **Dependencies** | `_trail_feature`, `_point_feature`, both deck builders, `tests/unit/` map tests |
| **Replacement** | Three options, in order of preference: (a) render only assets with real geometry and list the rest in a table — honest and simple; (b) keep the centroid position but drop the fabricated line shape, drawing a point with an explicit "approximate location" ring; (c) if synthesis must stay, seed from a stable hash (`hashlib.blake2b(asset_id)`) so it is at least reproducible. Option (c) is a 3-line fix and should happen regardless. |
| **Risk of removal** | **Medium** — 8 PNSG assets would lose map presence under option (a) until matched to real trails; the map would look emptier, which is the accurate state. |
| **Confidence** | **High** on the determinism defect; **Medium** on full removal. |

## R-04 · Legacy v1 API routers

| | |
|---|---|
| **Component** | `src/api/routers/evaluate.py`, `ranking.py`, `alerts.py` (137 lines total) + their mount in `src/api/main.py` |
| **Reason** | Superseded by `/api/v2`. Stateless, not deployed, no documented consumer, absent from `docs/api/openapi.json`'s described integration surface. |
| **Evidence** | ADR-012 scopes deployment around `/api/v2` only; `mobile/` targets v2; nothing in `src/ui/` calls them |
| **Affected users** | none known |
| **Dependencies** | `tests/integration/test_api_endpoints.py` exercises them |
| **Replacement** | None needed; `/api/v2` covers the surface. |
| **Risk of removal** | **Low**, but non-zero: an undocumented external consumer cannot be ruled out from inside the repository. |
| **Confidence** | **Medium** — needs one owner confirmation that no one calls them. |

## R-05 · Root-level `run_phase*_report.py` runners

| | |
|---|---|
| **Component** | `run_phase3_report.py`, `run_phase4_report.py`, `run_phase5_report.py`, `run_phase6_report.py`, `run_phase7_report.py`, `run_dcs_report.py`, `run_scm_report.py`, `run_masatrigo_validation.py`, `make_pipeline_a_figures.py` |
| **Reason** | Named for a phase numbering superseded by the v1/v2/v3 release scheme. No CI reference, no test reference, no entry in `docs/roadmap/` or `README.md`. |
| **Evidence** | absent from `ci.yml`; absent from `pyproject.toml`; not imported by `src/` |
| **Affected users** | possibly the owner, for ad-hoc reporting |
| **Dependencies** | unknown — they import from `src/`, not vice versa |
| **Replacement** | Move to `scripts/legacy/` with a README noting they are historical, or delete after owner confirmation. |
| **Risk of removal** | **Low** technically; **unknown** operationally. |
| **Confidence** | **Low** — this is an owner decision, not an audit conclusion. |

## R-06 · `load_dotenv()` at import in root scripts

| | |
|---|---|
| **Component** | module-level `load_dotenv()` in `calculate_delta_ehs.py:106`, `tis_engine.py:52`, `db_production_seeder.py:40`, `etl_raster_intersection.py:42`, `etl_tourist_traffic.py:43`, `get_bounding_box.py:30`, `run_scm_operational.py:99`, `seed_pnsg_trails.py:39` |
| **Reason** | Mutates `os.environ` process-wide on import, causing the order-dependent test failure and defeating `Settings(_env_file=None)` isolation. Also risks printing secrets into test output. |
| **Evidence** | `TEST_BASELINE.md` §3 — reproduced and isolated to two importing test files |
| **Affected users** | developers; potentially CI logs |
| **Dependencies** | `tests/unit/test_operational_ehs.py`, `tests/unit/test_tis_causal_budget.py` |
| **Replacement** | Move `load_dotenv()` inside `if __name__ == "__main__":` / a `main()` entry point. Behaviour when run as a script is identical; the import side effect disappears. |
| **Risk of removal** | **Very low.** |
| **Confidence** | **High** |

## R-07 · Sierra del Rincón dual-territory scaffolding

| | |
|---|---|
| **Component** | `fixtures.build_territory()` (20 assets, `fixtures.py:18-426`); the `"snr"` branches in `layout._TERRITORY_CONFIG`, `real_trails._DASHBOARD_TO_TERRITORY`, `provenance._DASHBOARD_TO_TERRITORY`, `tab_diagnostic.py:435`; the Sierra del Rincón centroids and default map centre in `map_layers.py:49-73` |
| **Reason** | SNR is archived (`CLAUDE.md`, `_VISIBLE_TERRITORIES = ["pnsg"]`). The scaffolding remains on the import path and the *default map centre is still SNR*. |
| **Evidence** | `map_layers.py:70-73`; `layout.py:336` |
| **Affected users** | none currently — SNR is not selectable |
| **Dependencies** | multiple tests build the SNR territory; the `"snr"` key threads through 4 modules |
| **Replacement** | **Do not remove yet.** SNR is the only second territory available for exercising multi-territory code paths, and multi-park transferability is a stated v3.0 goal. Instead: (a) fix the SNR-defaulting map constants — a real latent bug; (b) mark the SNR path explicitly as an archived test fixture. |
| **Risk of removal** | **High** — would eliminate the only multi-territory test surface. |
| **Confidence** | **High** that it should be *retained*. |

## R-08 · `src/territorial/fixtures.py` on the production path

| | |
|---|---|
| **Component** | the import at `src/ui/layout.py:17` and the `_BUILD_FN` dispatch at `:327` |
| **Reason** | Demo data authored backwards from a target tier distribution feeds every headline KPI, tier, budget and alert on the deployed dashboard, with no feature flag and no provenance record. |
| **Evidence** | `DATA_SOURCE_INVENTORY.md` D-07; `SCIENTIFIC_CLAIMS_REGISTER.md` C-04 |
| **Affected users** | **all** — this is the primary data path |
| **Dependencies** | `load_dashboard` → `enrich_assets_with_satellite` → `rank_assets` → `compare_scenarios` → `allocate_tis_budget` → `compute_executive_dashboard` → 10 KPIs → every Decidir surface. Dozens of tests. |
| **Replacement** | **This is a later-phase inversion, not a removal — not Phase 0.5.** It falls under the Phase 1 "Ecosystem State" pillar (`PHASE_1_RECOMMENDATIONS.md`, scope only, not designed there either) once Phase 0.5 lands; no phase beyond that has been named or scoped by the owner. The 218 real trails already carry EHS, ΔEHS, SCM, PRUG zone and budget — the same fields the fixtures supply. A possible migration shape: build `TerritorialAsset` instances from `pipeline_a_results.geojson`, keep the fixtures behind an explicit `SNTO_DEMO_DATA=1` flag for demos, and mark every field the real data cannot supply (`economic_importance`, `accessibility_score`, `visitor_capacity_annual`) as `MISSING` rather than substituting a constant. This shape is illustrative, not a committed design. |
| **Risk of removal** | **Very high if done bluntly** — it would change every number on the dashboard at once. Must be staged, with before/after comparison published. |
| **Confidence** | **High** on the diagnosis; the sequencing is an owner decision. |

## R-09 · Duplicated EHS colour ramps and priority bands

| | |
|---|---|
| **Component** | `map_layers._SPECTRAL_RAMP`; `real_trails._health_to_rgba` ramp; `tab_diagnostic._spectral_legend`; `tab_diagnostic._legend`; `real_trails.PRIORITY_BANDS` |
| **Reason** | Five definitions of one visual encoding, with **two conflicting band labellings** for the same anchors (`≥75 Saludable` vs `75-85 Bueno / >85 Óptimo`). |
| **Evidence** | `ARCHITECTURE_BASELINE.md` §4; `MAP_INVENTORY.md` M-02 flags |
| **Affected users** | all map readers |
| **Dependencies** | four render sites |
| **Replacement** | One canonical `EHSScale` object (anchors + labels + hex) next to `platform/evidence.py`, imported everywhere. |
| **Risk of removal** | **Low** — pure consolidation, no semantic change if the canonical labelling is chosen deliberately. |
| **Confidence** | **High** |

## R-10 · Mirrored alert-threshold logic

| | |
|---|---|
| **Component** | `platform/enrichment._alert_from_risk` (`enrichment.py:50-65`), documented as *"Espeja src/alerts/engine.py"* |
| **Reason** | Two implementations of one threshold set; they can drift silently. |
| **Evidence** | the docstring names the duplication explicitly |
| **Dependencies** | `enrich_assets_with_satellite` |
| **Replacement** | Extract the classification from `AlertEngine` into a pure function both call. |
| **Risk of removal** | **Low** |
| **Confidence** | **High** |

---

## Explicitly **not** removal candidates

| Component | Why it stays |
|---|---|
| `src/platform/evidence.py` | The canonical vocabulary and gating matrix. The modernization should route *more* through it, not less. |
| `src/forecasting/` | Exemplary evidence discipline (the `REAL` guard is enforced and pinned). |
| `src/risk_engine/human_pressure.py` | The best-documented indicator in the repository; a template for the others. |
| `src/reporting/cets_readiness.py`, `prug_monitoring.py` | Real institutional value, live-probed evidence, correct framing. |
| `src/reporting/gis_export.py` | The correct ADR-008 posture. |
| `src/persistence/` | Clean, typed, migrated, integration-tested. Currently unfed — that is a wiring gap, not a reason to remove. |
| `mobile/`, `/api/v2`, PostGIS queries | Inert but coherent and cheap to keep; removing them would discard the only prepared path to a decoupled frontend. |
| `scripts/build_dossier.py`, `export_openapi.py`, `sync_readme.py` | Drift gates that have already caught real errors. |
