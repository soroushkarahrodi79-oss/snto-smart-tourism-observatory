# Feature Inventory

## How to read this

- **Evidence** uses the project's own vocabulary (`src/platform/evidence.py`):
  `REAL` / `CALIBRATED` / `SIMULATED` / `SYNTHETIC` / `MISSING`, plus
  `FALLBACK` where the surface silently substitutes a default, and `MIXED`
  where one surface combines classes.
- **Status**: `Live` (renders on the deployed dashboard), `Gated` (renders only
  when data exists), `Inert` (code present, no live consumer).
- Personas follow `src/platform/views.py` (`ViewMode`): **Gestor** (director),
  **Técnica** (analyst), **Tribunal/Auditoría** (methodological review — the
  *default* view, `app.py:97`).

## 0. Shell and global surfaces

| # | Feature | Code | Persona | Decision supported | Data dependency | Status | Evidence | Limitations / duplication |
|---|---|---|---|---|---|---|---|---|
| S-1 | Territory selector | `app.py:77-91` | all | choose park | `_VISIBLE_TERRITORIES` | Live | n/a | Only PNSG visible; renders as a static label, not a control. |
| S-2 | View / audience selector | `app.py:98-120` | all | set disclosure depth | `views.py` | Live | n/a | Defaults to **Tribunal**, not Gestor — the audit view is what a first-time visitor sees. |
| S-3 | Alert panel (sidebar counts) | `app.py:144-150` | Gestor | triage | `dashboard.kpis` statuses | Live | CALIBRATED | Counts KPI statuses, not asset alerts — the label "indicador(es) crítico(s)" is accurate but easily read as "sites". |
| S-4 | Map legend (tiers) | `app.py:153-159`, `map_layers.LEGEND_ITEMS` | all | read map | static | Live | n/a | Duplicated in `tab_diagnostic.py:212`. |
| S-5 | Dynamic territory banner | `render_widgets._render_banner` | Gestor | orientation | dashboard + counts | Live | CALIBRATED | — |
| S-6 | Live-alerts strip + 60 s autorefresh | `app.py:180-185`, `render_widgets._render_live_alerts` | Gestor | urgency | `ranked_assets` | Live | CALIBRATED | Pulsing "live" affordance over a dataset that only changes when an offline pipeline is re-run. See `SCIENTIFIC_CLAIMS_REGISTER.md` C-14. |
| S-7 | Executive KPI strip (4 tiles) | `app.py:227-238`, `render_widgets._compute_exec_kpis` | Gestor only | headline decisions | fixtures + budget (+ real SVI jobs) | Live | MIXED | Only the "empleos en riesgo" tile is REAL when the socio snapshot loads; the rest are CALIBRATED. Correctly captioned. |
| S-8 | Asset-as-a-page route | `app.py:207-222`, `ui/asset_detail.py` | all | drill into one asset | `ranked_assets` + calibration | Live | MIXED | Session-state routing, no URL — not linkable or shareable. |
| S-9 | Footer data-source attribution | `app.py:328-345` | all | licensing | static | Live | n/a | Accurate attributions (Copernicus, OSM/ODbL, OAPN, INE, ALMUDENA). |

## 1. Layer *Decidir* — "¿Qué debe decidirse esta semana?"

| # | Feature | Code | Persona | Decision | Data | Status | Evidence | Limitations |
|---|---|---|---|---|---|---|---|---|
| D-1 | **Panorama ejecutivo** — 10 KPI cards with meaning + recommended action | `ui/tabs/tab_kpis.py`, `platform/dashboard.py` | Gestor | portfolio triage, funding | 8 PNSG fixture assets | Live | **CALIBRATED presented with REAL-grade confidence** | The 10 KPIs and all their narrative text derive from `fixtures.py` constants. See `KPI_INVENTORY.md`. |
| D-2 | Critical-asset cards + "ver ficha" | `tab_kpis.py:54`, `render_widgets` | Gestor | drill-down | fixtures | Live | CALIBRATED | — |
| D-3 | **Acciones urgentes** — persistence-backed triage queue | `ui/tabs/tab_urgent_actions.py`, `ui/services/urgent_actions.py` | Gestor | assign / close alerts | `alerts` table | Gated | MISSING in practice | Reads the DB. `managed_assets`/`alerts` are **not populated by any `src/` path**, so this surface is empty on the live deployment. |
| D-4 | Alert search + action buttons | `tab_urgent_actions.py:119-137` | Gestor | workflow | DB | Gated | MISSING | Same as D-3. |
| D-5 | **Simulador de presupuesto** — 3 sliders (budget, cost uncertainty, effectiveness) | `ui/tabs/tab_simulator.py:40-57` | Gestor | allocation | fixtures + `intervention/` scenarios | Live | **SIMULATED** | Correct class. The output euro figures are precise to the euro from constant inputs. |
| D-6 | Annual-portfolio comparison chart | `tab_simulator.py:83,133,317` | Gestor | allocation | scenarios | Live | SIMULATED | — |
| D-7 | **Impacto socioeconómico** — SVI, jobs at risk, ROI, per-municipality filter | `ui/tabs/tab_socioeco.py` | Gestor | justify investment | INE/ALMUDENA snapshot × fixture asset risk | Live (PNSG) | **MIXED: REAL demographics × CALIBRATED risk** | The real INE/ALMUDENA figures are multiplied by fixture-derived asset exposure. The product is not REAL, and the tab's framing does not make the join explicit. Single dated snapshot → no trend. |

## 2. Layer *Diagnosticar* — "¿Es real la señal y dónde ocurre?"

| # | Feature | Code | Persona | Decision | Data | Status | Evidence | Limitations |
|---|---|---|---|---|---|---|---|---|
| G-1 | Context KPI grid (6 indicators) | `tab_diagnostic.py:61-73`, `ui/kpi_sections.py` | Técnica | context | fixtures | Live | CALIBRATED | Re-renders 6 of the same 10 KPIs from D-1 — duplication by design ("trasladados desde el panorama"). |
| G-2 | Methodological note (NDVI/NDMI/EHS formulas, sign convention) | `tab_diagnostic.py:76-107` | Técnica/Auditoría | audit | static | Live | n/a | Genuinely good. States the stress↔health inversion and the conservative override explicitly. |
| G-3 | **Territorial map** (Tiers / Spectral toggle) | `tab_diagnostic.py:109-244` | all | spatial reading | fixtures + partial real geometry | Live | **MIXED / partly SYNTHETIC geometry** | See `MAP_INVENTORY.md` M-01/M-02. |
| G-4 | Map-mode radio (Gestión ↔ Espectral) | `tab_diagnostic.py:117` | all | switch encoding | — | Live | n/a | Default follows the audience view. |
| G-5 | Tier distribution / spectral legend + EHS stats | `tab_diagnostic.py:180-231` | all | interpret | fixtures | Live | CALIBRATED | Two legends with **inconsistent band labels** (see `ARCHITECTURE_BASELINE.md` §4). |
| G-6 | **Sendas reales** — Pipeline A real-trail map, 5 KPIs, PRUG card, ranked table | `tab_diagnostic.py:246-442` | Técnica | prioritise real trails | `pipeline_a_results.geojson` (218 trails) | Live | **REAL** | The strongest evidence surface in the product. Sits *below the fold* of a tab, subordinate to the curated map. |
| G-7 | Provenance / trend-gate card | `tab_diagnostic.py:272-312`, `platform/provenance.py` | Auditoría | trust | scene detection | Live | REAL (with FALLBACK risk) | `snapshot_provenance` hard-codes `status=DataStatus.REAL` and substitutes `n_scenes=2` when no scenes are detectable (`provenance.py:129`). |
| G-8 | **Catálogo de activos** + tier/type/region filters | `ui/tabs/tab_assets.py` | Técnica | browse, compare | fixtures + calibration | Live | CALIBRATED | Three `multiselect` filters; ranking by TPI. |
| G-9 | **Presión y capacidad de carga** (LAC/ROS) | `ui/tabs/tab_portfolio.py:204-283`, `platform/lac_ros.py`, `pressure_capacity.py` | Gestor/Técnica | visitor management | `visitor_capacity_annual` (fixture) | Live | CALIBRATED, correctly labelled | Well-documented as a *planning estimate*. But `capacity_at_standard` attributes **all** EHS deficit to visitor pressure — see `KPI_INVENTORY.md` K-18. |
| G-10 | Seasonal TPI profile chart | `tab_portfolio.py:168-202` | Gestor | seasonality | fixed multipliers (0.55/0.90/1.55/1.00) | Live | **SIMULATED** | Multipliers are constants averaging to 1; the module docstring correctly forbids presenting them as observations. |
| G-11 | Territorial pressure/risk matrix | `tab_portfolio.py:303-352` | Gestor | portfolio view | fixtures | Live | CALIBRATED | — |
| G-12 | Active-alerts panel | `tab_portfolio.py:353-382` | Gestor | triage | fixtures | Live | CALIBRATED | Duplicates S-6 and D-3 in a third place. |
| G-13 | **Proyección de tendencia** + park selector | `ui/tabs/tab_forecast.py`, `forecasting/` | Técnica | early warning | `mk_trends_<park>.json` | Gated | **SIMULATED** (enforced) | Best-disciplined feature in the repo: `Forecast.__post_init__` makes `EvidenceClass.REAL` unconstructible. |

## 3. Layer *Evidenciar* — "¿Qué datos sostienen la señal?"

| # | Feature | Code | Persona | Decision | Data | Status | Evidence | Limitations |
|---|---|---|---|---|---|---|---|---|
| E-1 | **Evidencia satelital** — multi-year NDVI/NDMI series, park + asset selectors | `ui/tabs/tab_timeseries.py` | Técnica | verify signal | `clean_assets/timeseries/analysis/mk_trends_*.json` | Live | REAL | Source differs from the 2 rasters that drive ΔEHS — two distinct satellite records in one product. |
| E-2 | Real trend chart (Mann-Kendall + Sen CI) | `tab_timeseries.py:157-166`, `platform/satellite_trends.py` | Técnica | trend | GEE export | Live | REAL | 12 additional OAPN park CSVs are **untracked** in the working tree (see `git status`); the loader only offers parks with a computed JSON. |
| E-3 | Simulated monthly series chart | `tab_timeseries.py:190-253`, `platform/charts.build_time_series_chart` | Técnica | illustrate | generated | Live | **SIMULATED** | Rendered in the same tab as E-1/E-2, immediately below real series. High conflation risk. |
| E-4 | **Confianza e incertidumbre (DCS)** + asset selector | `ui/tabs/tab_confidence.py`, `decision_confidence/assessor.py` | Auditoría | trust a recommendation | fixtures (`dcs` literal) | Live | CALIBRATED | DCS is a *hard-coded field* on fixture assets, not computed at runtime for the dashboard portfolio. |
| E-5 | DCS decomposition + sensitivity charts | `tab_confidence.py:87-151` | Auditoría | improve evidence | fixtures | Live | CALIBRATED | — |
| E-6 | Evidence-gap map | `tab_confidence.py:167` | Auditoría | where to measure | fixtures | Live | CALIBRATED | Not a geographic map — a matrix. Name is misleading. |
| E-7 | **Proveniencia y linaje** — dato→indicador→decisión, per-datum registry, propagation state | `ui/tabs/tab_provenance.py`, `platform/lineage.py` | Auditoría | audit | mixed | Live | MIXED | Strong surface; the single best place to extend evidence discipline. |

## 4. Layer *Gobernar* — "¿Puede reconstruirse y auditarse la decisión?"

| # | Feature | Code | Persona | Decision | Data | Status | Evidence | Limitations |
|---|---|---|---|---|---|---|---|---|
| B-1 | **Metodología y auditoría** — formulas, limitations, references | `ui/tabs/tab_method.py`, `platform/methodology.py` | Auditoría | defend | static | Live | n/a | 605-line methodology module; substantive. |
| B-2 | Field-plot registration form | `tab_method.py:158-177`, `ui/services/field_capture.py` | Técnica | capture ground truth | DB | Gated | MISSING | The #26 capture path exists in the UI. No observations have been recorded. |
| B-3 | **Informe ejecutivo** (.md / .json download) | `tab_reports.py:86-121`, `reporting/territorial_brief.py` | Gestor | share | fixtures | Live | CALIBRATED | Correctly captioned "sin validación de campo (#26)". |
| B-4 | **Capa GIS** (.geojson download) | `tab_reports.py:139-183`, `reporting/gis_export.py` | Técnica/GIS | integrate | real geometry + real trends | Live | REAL | `build_feature_collection` **defaults** `evidence_level=DataStatus.REAL` (`gis_export.py:84`) — correct for this caller, but a fragile default for any future one. |
| B-5 | **Preparación CETS Fase I** (.md / .json) | `tab_reports.py:186-258`, `reporting/cets_readiness.py` | Gestor/institutional | accreditation prep | live probes | Live | resolved per requirement | Exemplary: probes the repo, emits `missing` where evidence is absent, warns explicitly that #26 has not run. |
| B-6 | **Seguimiento PRUG por zonas** (.md / .json) | `tab_reports.py:261-320`, `reporting/prug_monitoring.py` | Gestor/institutional | management-zone priorities | 218 real trails × OAPN zonification | Live (PNSG only) | REAL | Framed as seasonal early warning, not compliance verdict. Degrades to `available=False` elsewhere. |
| B-7 | **Configuración territorial** — read-only registry + operative thresholds | `ui/tabs/tab_config.py:39-135` | Auditoría | inspect config | `platform/territory_registry.py` | Live | n/a | Reads the *second* territory registry (see `ARCHITECTURE_BASELINE.md` §7). |
| B-8 | Org / user / territory provisioning forms (v3.0) | `tab_config.py:136-291`, `persistence/services/tenancy.py` | admin | tenancy | DB | Gated | n/a | Writes real `Organization`/`User` rows. Creating the first user **activates the dormant `authz_gate`** — a live behaviour change with no warning in the UI. |
| B-9 | Benchmarking Red OAPN | `tab_config.py:292`, `benchmarking/oapn_rollup.py` | institutional | cross-park | `mk_trends_*.json` | Gated | REAL | Correctly rolls up only parks with committed real trend data (pnsg, monfragüe, tablas_daimiel); never the 13 unvalidated templates. |

## 5. Non-dashboard features

| # | Feature | Code | Status | Notes |
|---|---|---|---|---|
| X-1 | `/api/v2` REST surface (21 paths, 38 schemas) | `src/api/v2/`, `docs/api/openapi.json` | **Inert** | Not deployed (ADR-012). Contract published, CI-checked. |
| X-2 | Legacy v1 routers | `src/api/routers/` | **Inert** | `/evaluate_asset`, `/ranking`, `/alerts`. No consumer, no deployment, superseded by v2. |
| X-3 | Mobile client | `mobile/` | Inert w.r.t. live data | Defaults to mock repository; real repo needs `EXPO_PUBLIC_SNTO_USE_REMOTE_API=true` **and** a deployed API. |
| X-4 | PostGIS spatial queries | `persistence/repositories/managed_asset.py` (`list_within_distance`, `list_intersecting`) | **Inert** | Migration not applied to production; no caller anywhere. |
| X-5 | ArcGIS field-validation demo | `arcgis/demo/pnsg/`, `docs/integrations/arcgis/` | Prepared, not executed | Survey123 + Web Map owner-verified; Experience Builder app **not created**; **no real field observations exist**. |
| X-6 | Institutional dossier automation | `reporting/institutional_dossier.py`, `scripts/build_dossier.py` | Live (CI-gated) | Regenerates derived sections of the OAPN dossier; `--check` blocks CI on drift. |
| X-7 | Telemetry | `platform/telemetry.py` | Gated | Local, opt-in via `SNTO_TELEMETRY=1`. |
| X-8 | Report runners `run_phase3..7_report.py`, `run_dcs_report.py`, `run_scm_report.py` | repository root | Unknown / likely stale | No CI reference, no test reference, no documentation entry. See `REMOVAL_CANDIDATES.md`. |

## 6. Feature-level duplication summary

1. **Alert display** appears in 3 places (S-6 live strip, D-3 urgent actions, G-12 portfolio alerts) with 3 different data sources.
2. **The same 10 KPIs** render fully in D-1 and partially (6) in G-1.
3. **Two territorial maps** in one tab (G-3 synthetic-geometry, G-6 real-geometry) answering overlapping questions.
4. **Real and simulated time series** in one tab (E-1/E-2 vs E-3).
5. **Two evidence/provenance surfaces** (E-7 lineage, G-7 provenance card) plus the badges rendered inline everywhere.
6. **Two territory registries** surfaced in two tabs (B-7 vs the sidebar selector).
