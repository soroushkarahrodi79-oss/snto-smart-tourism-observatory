# Audit — Visual Change Explorer (Earth Engine before/after + animated GIF)

- **Status:** AUDIT ONLY — no application code was modified.
- **Date:** 2026-08-02
- **Scope:** whole repository; deep read of `app.py`, `src/`, `tests/`, `docs/`,
  `requirements.txt`, `pyproject.toml`, Docker/deploy files, `src/config/settings.py`.
- **Companion docs:** `docs/decisions/ADR-015-earth-engine-change-explorer.md`,
  `docs/plans/visual_change_explorer_implementation_plan.md`.

## 1. Executive summary

SNTO already contains a **production-grade Earth Engine *analytical* core** — a
Sentinel-2 SR adapter that masks clouds, computes NDVI/NDMI/EVI, builds median
composites and reduces them to per-asset statistics
(`src/ingestion/gee_adapter.py`). It also has a mature territory / AOI registry,
real park-boundary and route geometries, and a WebGL (pydeck) map surface in the
dashboard.

What is **entirely absent** is the *visualization* half that the Visual Change
Explorer needs: there is **no** code that turns an Earth Engine image into a map
tile (`getMapId`), a thumbnail PNG (`getThumbURL`), or an animated GIF
(`getVideoThumbURL`); there is **no** before/after swipe component; and there is
**no** in-app NDVI-difference layer. `earthengine-api` is not even a declared
dependency — every `ee` call is a deferred import used only by offline extraction.

**Conclusion:** the feature is roughly **60 % composition, 40 % new integration.**
The masking / index / composite *logic* is reusable knowledge, but the EE→image
rendering path, the change-detection composite/diff builders, the orchestration
service, and the swipe UI are all new and must be built to the architecture in
ADR-015. See §5 for the composition-vs-new verdict.

## 2. Feature inventory

| # | Capability | Status | Relevant files / symbols | Reusable? | Debt / risk |
|---|-----------|--------|--------------------------|-----------|-------------|
| 1 | Earth Engine init & auth | **partial** | `src/ingestion/gee_adapter.py::GEEAdapter._initialize` (service-account **and** personal auth, project-scoped `ee.Initialize`); `src/config/settings.py` (`gee_project_id`, `gee_service_account`, `gee_key_file`); `.env.example` (`GEE_*`) | **Yes — extract as shared client** | Init lives inside the ingestion adapter; not reusable as-is. `earthengine-api` NOT in `requirements.txt` (deferred `import ee`). No shared singleton → double-init risk under Streamlit reruns. |
| 2 | Sentinel-2 SR collection access | **complete (offline path)** | `gee_adapter._S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"`, `_build_masked_collection`, band constants (B2/B4/B8/B11/SCL) | **Yes** | Returns an `ee.ImageCollection` reduced to scalars only — never surfaced as an image/tile. |
| 3 | Cloud & cloud-shadow masking | **complete** | `gee_adapter._cloud_mask_scl`, `_SCL_BAD_VALUES=[0,1,3,8,9,10,11]` (SCL-based, supersedes QA60) | **Yes — lift verbatim** | Fixed SCL list; no user-tunable cloud threshold (feature needs a % control → `s2cloudless`/`CLOUDY_PIXEL_PERCENTAGE` filter to add). |
| 4 | Spectral indices (NDVI/NDMI/EVI) | **complete** | `gee_adapter._compute_scaled_indices`; scalar helpers `src/features/spectral.py::compute_ndvi/compute_ndmi/…` | **Yes** | NBR/dNBR referenced in the data model (`AssetObservation.nbr`) but **not** computed in the EE path. True-colour (B4/B3/B2) visualization not defined. |
| 5 | Median compositing | **complete (server-side logic)** | `gee_adapter._fetch_monthly_observation` (`collection.filterDate(...).median()`) | **Yes** | Composites a monthly window then reduces to numbers; never kept as an image for display. |
| 6 | Valid-pixel / quality metadata | **complete** | `gee_adapter` `_MIN_VALID_PIX_PCT=0.30`, `NDVI_count`, `valid_pixel_pct`, `cloud_cover_pct`; `SpatialStats` (`src/assets/models.py`) | **Yes** | Computed for scalar reductions; must be re-derived for the composite images the explorer shows. |
| 7 | Raster compositing (offline, non-EE) | **complete** | `prepare_raster.py`, `etl_raster_processor.py`, `calculate_delta_ehs.py`, `src/geospatial/geometry.py` (rasterio/rasterstats) | Partially (ΔEHS concept) | Local `.SAFE`/GeoTIFF pipeline, 900 MB rasters — **not** the interactive path; do not reuse for the explorer. |
| 8 | Map component (in-app) | **partial** | `src/platform/map_layers.py` (pydeck `GeoJsonLayer`, `build_pydeck_deck[_spectral]`); `src/ui/tabs/tab_diagnostic.py` (`st.pydeck_chart`) | Vector overlay only | **Folium & streamlit-folium were deliberately removed** (RAM); pydeck renders vector GeoJSON, **cannot** natively drive a draggable raster swipe. |
| 9 | geemap / leafmap / folium | **absent** | — (all removed from `requirements.txt`) | No | Reintroducing folium fights an explicit past decision; MVP should avoid a per-session tile server (see ADR-015). |
| 10 | Before/after swipe / side-by-side | **absent** | — (no `swipe`/`juxtapose`/`split-map`/`DualMap` hits) | No | 100 % new; no comparison widget of any kind exists. |
| 11 | NDVI-difference / dNDVI layer | **absent** | (ΔEHS exists offline in `calculate_delta_ehs.py`; not an in-app EE image) | Concept only | New EE `after.subtract(before)` band + diverging palette required. |
| 12 | GIF / video / ImageCollection animation | **absent** | — (no `getVideoThumbURL`/`imageio`/`to_gif`; only `ee.batch.Export.table` in `scripts/gee_cloudshell_pnsg.py`) | No | 100 % new; the animated-GIF requirement has zero prior art. |
| 13 | GeoTIFF / image export | **partial (offline)** | `scripts/export_gis.py`, `src/reporting/gis_export.py` (vector GeoJSON), rasterio writers | Vector export yes | No EE `getDownloadURL`/`getThumbURL` image export exists. |
| 14 | Caching | **partial** | `@st.cache_data` (5 uses, e.g. `src/ui/layout.py::load_dashboard`, `satellite_trends`); `streamlit-autorefresh` | Pattern reusable | No cache keyed on (AOI, dates, index, cloud%); no on-disk artifact cache for PNG/GIF; no TTL discipline for EE calls. |
| 15 | Background jobs / result persistence | **absent** | — | No | All work is request-synchronous. GIF generation is slow → a job/async or aggressive cache is needed (see risks §Plan). |
| 16 | AOI / park boundary / routes | **complete** | `src/config/territories.py` (`bbox_wgs84`, PNSG `(-4.21,40.65,-3.58,41.08)`, `s2_tile`); `data/raw_assets/vector_data/oapn/oapn_limite_pn.geojson`; `clean_assets/pnsg_assets.geojson`; `src/assets/models.py` (`TourismAsset`, `GeoJSONGeometry` Point/LineString/Polygon) | **Yes — strong** | Boundaries/routes ready to become an EE geometry; only a lightweight AOI-selection UI (registry pick / draw / bbox) is missing. |
| 17 | Offline GEE extraction tooling | **complete (out of process)** | `scripts/build_gee_js.py`, `scripts/gee_code_editor_pnsg.js`, `scripts/extract_gee_timeseries_pnsg.py`, `scripts/gee_cloudshell_pnsg.py`, `scripts/download_s2_pnsg.py` (CDSE, no EE) | Reference only | Confirms the S2/index recipe but targets Drive/CSV exports, not interactive rendering. |
| 18 | EE test strategy | **partial** | `tests/unit/test_gee_adapter.py` (injects an `ee` stub via `sys.modules`, fully mocked/offline) | **Yes — reuse pattern** | Establishes the "mock `ee`, run offline in CI" convention the new layer must follow. |

## 3. Key file references

- `src/ingestion/gee_adapter.py` — the single richest reusable asset (masking,
  indices, compositing, retry/backoff, dual auth).
- `src/config/settings.py` — `Settings` (pydantic-settings) already carries the
  three `GEE_*` fields; extend here, do not invent a parallel config.
- `src/config/territories.py` — `TerritoryConfig.bbox_wgs84` + `s2_tile` give a
  ready AOI seed per park.
- `src/platform/map_layers.py` / `src/ui/tabs/tab_diagnostic.py` — the current
  (pydeck, vector-only) map surface and how a tab wires a map into Streamlit.
- `tests/unit/test_gee_adapter.py` — the offline `ee`-stub testing convention.
- `docs/GEE_setup_timebox.md` — existing service-account setup runbook to cite,
  not duplicate.

## 4. Technical-debt & risk flags observed

1. **`earthengine-api` is undeclared** — works only where someone pip-installed
   it out of band. Any in-app EE feature must add it (and it is a heavier,
   transitive-dependency package than the current wheels-only Docker build
   assumes — see `Dockerfile` `--only-binary=:all:`).
2. **No shared EE client** — init is buried in `GEEAdapter`. Under Streamlit's
   rerun model this risks repeated `ee.Initialize` calls; needs a
   `@st.cache_resource` singleton.
3. **Deliberate no-folium stance** — `requirements.txt` documents folium's
   removal for O(1) server RAM. The swipe UI must respect that intent (favour
   server-rendered PNG thumbnails + a lightweight comparison widget over a
   per-session tile server).
4. **Synchronous, uncached heavy calls** — `getThumbURL`/`getVideoThumbURL` are
   slow and quota-metered; without a keyed cache each Streamlit rerun re-hits EE.
5. **No user-tunable cloud threshold** — masking is a fixed SCL list; the MVP
   requires a cloud-% control layered on top.
6. **Evidence-labelling non-negotiable** — CLAUDE.md forbids blurring
   real/simulated evidence. Explorer output is **REAL Sentinel-2** but is *not*
   field-validated (#26); it must be labelled a visual/early-warning product,
   never a validation claim.

## 5. Composition vs. new-integration verdict

**Mixed, and the split is clean along the analytical/visualization seam.**

- **Reusable by composition (the "what to compute" knowledge):** S2 collection
  id, SCL masking, NDVI/NDMI/EVI formulas, median compositing, valid-pixel
  accounting, retry/backoff, dual auth, AOI geometries, the offline-`ee`-stub
  test pattern.
- **Genuinely new (the "how to show it" path):** an Earth Engine **image
  rendering** layer (map tiles via `getMapId`, PNG thumbnails via `getThumbURL`,
  animated GIF via `getVideoThumbURL`), change-detection **composite/diff**
  builders (before/after median + dNDVI), an **orchestration service** that ties
  AOI+dates+cloud%→artifacts with caching, and the **swipe UI**.

Therefore a **new Earth Engine integration layer is required** — it is not
achievable by composition alone — but it should be built *on top of* the existing
masking/index logic (ideally by refactoring the shared parts out of
`gee_adapter.py`), not by reimplementing it. Full target tree, backlog, and
blockers are in the implementation plan.
