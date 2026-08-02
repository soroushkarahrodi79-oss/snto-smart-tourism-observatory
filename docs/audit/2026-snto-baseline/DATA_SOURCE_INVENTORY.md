# Data Source and Provenance Inventory

## D-01 · Sentinel-2 L2A — scene rasters (Pipeline A)

| Field | Value |
|---|---|
| Provider | ESA / Copernicus (products carry the modified-Copernicus attribution, `app.py:339`) |
| Access | Manual `.SAFE` download; also `src/ingestion/gee_adapter.py` (GEE) and a STAC path via `pystac-client` / `planetary-computer` |
| Geographic coverage | MGRS tile **T30TVL** — covers both PNSG and Sierra del Rincón |
| Temporal coverage | **2 scenes**: `S2A_MSIL2A_20250810` and `S2B_MSIL2A_20260410` |
| Update frequency | manual, ad-hoc |
| Licence | Copernicus open data; attribution present in the footer |
| Status | **raw** |
| Transformation | `prepare_raster.py` → `etl_raster_processor.py` → `calculate_delta_ehs.py`: band math (NDVI B08/B04, NDMI B08/B11), SCL cloud/shadow masking, 50 m trail buffer, scene-percentile anchors P90/P10, stress score, SCM, budget |
| Caching | none at raster level; the derived GeoJSON is the cache |
| Provenance retention | `data/outputs/pnsg/run_context.json` records tool, git SHA, dirty flag, timestamp, params. Scene dates are re-derived from `.SAFE` filenames by `provenance.detect_scene_dates` |
| Quality checks | SCL masking; `valid_pixel_pct`; the trail buffer is excluded from its own reference percentiles |
| Failure behaviour | 🔴 **Unsafe.** `provenance.snapshot_provenance` returns `status=DataStatus.REAL` **unconditionally** and substitutes `n_scenes = 2` when no scenes are detected (`src/platform/provenance.py:129,153`). On a fresh clone (rasters are git-ignored) the UI still shows the "🛰️ Dato satelital real" badge. |
| Tracked in git | **No** — rasters are local-only (~900 MB). Only the derived GeoJSON is committed. |

**Comparability caveats not currently surfaced:** cross-satellite (S2A vs S2B),
cross-year (2025 vs 2026), and 8-month separation for a delta labelled
"seasonal".

**Correction — the fix is not "collapse to `MISSING`".** The failure-behaviour
row above documents a genuine defect (an unconditional REAL badge with no
raster-presence check), but the correct remedy distinguishes four things the
current code conflates into one boolean, rather than substituting one
unconditional state (`REAL`) for another (`MISSING`):

1. **Derived output availability** — `data/outputs/pnsg/pipeline_a_results.geojson`
   is itself **committed to git** and can be genuinely present and
   REAL-derived independent of whether the raw rasters are on disk.
2. **Raw-source availability** — are the `.SAFE` products present locally?
   Today: no, on any fresh clone.
3. **Provenance completeness** — can the acquisition dates/sensors be
   re-derived from the raw source? Today: no, without the rasters.
4. **Reproducibility** — could a fresh clone regenerate the derived output
   from scratch? Today: no.

A committed derived GeoJSON remaining available while its raw source cannot be
locally inspected is a normal, honest state for a versioned research artifact
— not the same as having no evidence. The recommended degraded state is:
*"Derived from real Sentinel-2 observations; raw source scenes unavailable in
this environment; provenance incomplete and not locally reproducible."* Full
recommendation: `PHASE_1_RECOMMENDATIONS.md` PR 0.5.2.

## D-02 · Sentinel-2 — multi-year time series (GEE Code Editor)

| Field | Value |
|---|---|
| Provider | ESA/Copernicus via Google Earth Engine |
| Access | `scripts/gee_code_editor_pnsg.js` run manually in the GEE Code Editor; CSV export |
| Coverage | PNSG (21 assets) + 15 OAPN park templates |
| Temporal | 2021–2026, monthly cadence |
| Licence | Copernicus open |
| Status | **processed** |
| Transformation | CSV → `scripts/run_timeseries_analysis.py` → deseasonalisation (harmonic), Yue–Pilon prewhitening, tie-corrected Mann-Kendall, Sen slope + Gilbert 1987 95 % CI → `clean_assets/timeseries/analysis/mk_trends_<park>.json` |
| Caching | `@st.cache_data` around the loader (`satellite_trends`) |
| Provenance | `mk_trends_*.json` per park; `available_parks()` only offers parks with a computed JSON |
| Quality checks | significance at p < 0.05; `n_observations` carried through to the GIS export |
| Failure behaviour | park absent from the selector; GIS features get explicit nulls and `has_trend=false` |
| Tracked in git | **partially.** `mk_trends_pnsg.json` and two pilot parks are committed. **12 OAPN park CSVs are currently untracked in the working tree** (see `git status`) — they are neither committed nor ignored. |

This is a **different satellite record** from D-01. The dashboard presents both
under the "Sentinel-2" banner without distinguishing them.

## D-03 · OAPN official cartography

| Field | Value |
|---|---|
| Provider | Organismo Autónomo Parques Nacionales (Red de Parques Nacionales) |
| Access | WFS (`etl_oapn_wfs.py`), KML visor exports under `data/raw_assets/vector_data/oapn/` |
| Coverage | PNSG — 218 homologated trails, park boundary, ZPP, **PRUG zonification** |
| Temporal | static reference cartography |
| Licence | OAPN; attributed in the footer. **Specific licence terms are not recorded in the repository.** |
| Status | raw → processed (`etl_vector_cleaner.py`, `etl_oapn_to_trails.py`, `etl_prug_enrich.py`) |
| Caching | derived GeoJSON on disk |
| Provenance | folder structure only |
| Failure behaviour | `get_park_boundary` returns `None` → boundary layer omitted; `prug_monitoring` returns `available=False` |
| Tracked in git | boundary **yes**; the rest local-only |

The PRUG zonification is the most valuable institutional asset in the data
inventory — it is real, official, and it is what makes `prug_monitoring`
defensible.

## D-04 · OpenStreetMap

| Field | Value |
|---|---|
| Provider | OSM contributors |
| Access | extracts under `data/raw_assets/vector_data/` |
| Coverage | Sierra del Rincón trails; POI/road/settlement inputs for the human-pressure proxy |
| Licence | **ODbL** — attributed in the footer (`app.py:340`). ODbL share-alike obligations for derived databases are not analysed anywhere in the repo. |
| Status | raw |
| Failure behaviour | asset falls back to the centroid path |

## D-05 · INE / ALMUDENA socio-economic

| Field | Value |
|---|---|
| Provider | Instituto Nacional de Estadística; ALMUDENA (Comunidad de Madrid) |
| Access | `etl_socioeconomic.py` |
| Coverage | PNSG municipalities |
| Temporal | **one dated snapshot, `2026-06`** |
| Licence | INE/ALMUDENA open data; attributed |
| Status | processed |
| Transformation | municipality attributes → SVI, community impact, jobs at risk (`socioeconomic/indicators.py`), joined to assets by name→INE code |
| Caching | JSON snapshot on disk |
| Provenance | dated snapshot filename |
| Failure behaviour | `snapshot_exists()` false → `_socio = None` → dashboard uses the legacy proxy model (`app.py:190-202`). Honest. |
| Gap | `svi_history_available()` needs ≥ 2 dated snapshots; `src/socioeconomic/snapshot/history/` **does not exist** → **no real socio-economic trend** |
| Tracked in git | yes (2 files) |

## D-06 · MITMA mobility

| Field | Value |
|---|---|
| Provider | Ministerio de Transportes y Movilidad Sostenible (mobile-phone-derived trip matrices) |
| Access | `etl_mobility.py` |
| Coverage | 4 of 6 PNSG zones resolved in the committed crosswalk `src/mobility/reference/pnsg_mobility_zones.json` |
| Temporal | n/a |
| Status | **not ingested.** `src/mobility/snapshot/` **does not exist**; `mobility_snapshot_exists()` is `False` (verified) |
| Failure behaviour | `tab_portfolio._real_municipal_pressure` returns `None`; capacity uses the curated proxy; `pressure_source` stays `"Curada (estimada)"` |
| Semantic caveat (already documented) | a municipal inbound-trip count is **not** trail footfall; when ingested it attaches as **context only** (`pressure_capacity.py:14-16`) |

This is the only pathway in the system toward an actual visitor-pressure
measurement, and it is not connected.

## D-07 · Curated territorial fixtures

| Field | Value |
|---|---|
| Provider | **the project authors** |
| Access | `src/territorial/fixtures.py` — Python literals |
| Coverage | 20 SNR assets + **8 PNSG assets** |
| Temporal | undated |
| Licence | n/a |
| Status | **synthetic / expert-authored demo data** |
| Transformation | `enrich_assets_with_satellite` conservatively overrides `ehs` where the satellite reads more degraded; `rank_assets` then computes TPI/tier/budget |
| Caching | `@st.cache_data load_dashboard` |
| Provenance retention | **none** — no per-field source, no author, no date |
| Quality checks | none |
| Failure behaviour | n/a — always available; this is the default path |
| Tracked in git | yes, on the production import path (`src/ui/layout.py:17`) |

🔴 **The docstrings mislabel this data.** `build_territory()` is documented as
*"20 activos **reales** de la Reserva de la Biosfera Sierra del Rincón"*
(`fixtures.py:20`), and both builders state *"Distribución de tiers **calibrada
contra el motor TPI**"* with per-asset comments such as
`# TPI ≈ 95 | CU=40(CRITICAL) + ES=20.5 + SV=19.3 + CC=15` and
`# Activadores garantizados` (`fixtures.py:24-35`). These are values authored
**backwards from a desired tier distribution**. The place names, descriptions and
ecological narratives are real and plausible; the numeric fields (`ehs`,
`risk_score`, `dcs`, `mk_p_value`, `scm_classification`, `scm_confidence`,
`visitor_capacity_annual`, `economic_importance`, `accessibility_score`) are
authored constants. This is legitimate demo data — it is **not** "real", and
under ADR-004 it should carry an explicit evidence class, never an unqualified
"reales".

**Owner decision applied (Q-01):** the resolved class is **`SYNTHETIC`**, not
`CALIBRATED`. Under `platform/evidence.py`'s gating matrix, `SYNTHETIC`
authorizes no decision use at all (monitoring, prioritization, intervention, or
public reporting) — the stricter of the two candidates. See
`CONTRADICTIONS_AND_OPEN_QUESTIONS.md` "Owner decisions after audit" and
`PHASE_1_RECOMMENDATIONS.md` PR 0.5.5, which also proposes (documentation-only)
attaching machine-readable evidence metadata to each fixture asset so this
classification is checkable in code, not just in a docstring.

## D-08 · Field observations (#26)

| Field | Value |
|---|---|
| Provider | would be SNTO/park field staff |
| Access | `clean_assets/field_validation/pnsg_field_observations_template.csv`; UI capture form `tab_method.py:158`; ArcGIS Survey123 (prepared, not run) |
| Coverage | 4 template plot rows (2 impact / 2 control) across 2 assets |
| Status | **empty.** Every measurement column (`soil_compaction_mpa`, `veg_cover_pct`, `erosion_class`, `trail_width_m`, `visitor_count`, `photo_ref`, `observed_at`) is blank — verified by reading the file |
| Consequence | `resolve_signals()['field_measured_plots'] == 0`; `src/validation/agreement.py` (Spearman ρ, Cliff's δ) has nothing to run on; **no satellite↔field validation exists** |

## D-09 · Operational persistence database

| Field | Value |
|---|---|
| Provider | self |
| Access | SQLAlchemy → Azure Postgres `snto-db` (prod) or SQLite `data/outputs/snto.db` (dev) |
| Coverage | 9–11 tables |
| Status | **empty of analytical content.** No `src/` code path populates `managed_assets` from the dashboard/pipeline |
| Provenance | `audit_log` table + `persistence/services/audit.py` choke-point |
| Failure behaviour | UI services return empty lists → "Acciones urgentes" renders empty |
| Schema drift | the PostGIS migration `b2c3d4e5f6a7` is **not applied to production** |

## Cross-cutting provenance findings

1. **Provenance is retained at three different fidelities.** `run_context.json`
   (excellent: tool, git SHA, dirty flag, params) for Pipeline A; a dated
   filename for socio-economic; **nothing at all** for the fixtures that drive
   the headline numbers.
2. **Only 3 files under `data/` are tracked** (`git ls-files data/`): the PNSG
   Pipeline A GeoJSON, its summary, and the OAPN boundary. Everything else is
   local. A fresh clone renders the real-trails map from the committed GeoJSON
   but cannot regenerate it, and silently loses scene-date provenance (D-01
   failure behaviour).
3. **Untracked working-tree data.** 12 OAPN GEE time-series CSVs and a UX PDF are
   untracked and un-ignored — an unresolved decision, not a bug.
4. **Fallback behaviour is honest in six places and dishonest in one.** The
   mobility, SCM-zone, SVI-history, PRUG, GIS-layer and field-validation gates
   all degrade to an explicit "not available". `snapshot_provenance` does not.
5. **Licence terms are attributed but not analysed.** ODbL share-alike and OAPN
   redistribution terms matter for the GeoJSON/GeoPackage export feature
   (B-4/M-04) and for the procurement package; no document addresses them.
