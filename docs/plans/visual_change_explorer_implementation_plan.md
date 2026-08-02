# Implementation Plan — Visual Change Explorer

- **Status:** In progress — **Foundation + Analysis/Static-PNG core + Service
  orchestration + Swipe UI (backlog steps 1–8, 10) implemented.** GIF (step 9)
  and live verification (step 12) not started.
- **Date:** 2026-08-02 (foundation landed 2026-08-02)
- **Companions:** `docs/audits/visual_change_feature_audit.md`,
  `docs/decisions/ADR-015-earth-engine-change-explorer.md`

## 0c. Service orchestration + Swipe UI (implemented)

The first complete user-facing vertical slice. **No** GIF, tiles, pan/zoom or API.

- **Files.** `src/services/change_explorer_service.py`,
  `src/ui/tabs/tab_change_explorer.py`; registered via `src/ui/navigation.py`
  (new `change_explorer` module in the Evidenciar layer) + one dispatch line in
  `app.py` (composition only — no domain/EE logic there).
- **Service public interface.** `run_change_explorer(request, *,
  app_settings=None, territory_resolver=None) -> ChangeExplorerResult` (pure,
  testable) and `cached_run_change_explorer(request)` (the `st.cache_data`
  boundary) + `clear_change_explorer_cache()`. Models:
  `ChangeExplorerRequest`, `RenderedArtifact`, `ChangeExplorerResult`,
  `ResultStatus` — all frozen, no EE object, no secrets.
- **Territory → EE geometry.** The UI lists only registered territories with a
  usable `bbox_wgs84` (`usable_territories`); the bbox becomes an
  `ee.Geometry.Rectangle` in **one** helper
  (`collections.bbox_to_ee_rectangle`), preserving `(W, S, E, N)` order
  explicitly. Unknown ids raise a clear `ValueError`.
- **Evaluation boundary.** Exactly **one combined `getInfo` per window** — an
  `ee.Dictionary` of scene count, mean scene cloud, valid-pixel count (one
  `reduceRegion`) and AOI pixel count — evaluated in the service, never in
  dataclasses/builders/UI, never at import. dNDVI reuses the two NDVI composites
  (no extra collection build). No fabricated URLs for no-data windows.
- **dNDVI.** Always computed from the same two collections (`after − before`),
  shown as a static PNG with the fixed diverging legend and an explicit
  *observational, not causal / not field-validated* note.
- **Caching.** Cache key = `request.cache_key(bbox)` (territory, bbox, both
  EE-exclusive windows, product, cloud, dimensions, dataset id, composite &
  visualisation versions) — no credentials, no URLs, no Settings, no EE objects.
  `TTL = 600 s`, deliberately conservative because the EE signed-thumbnail URL
  lifetime is **not guaranteed by the API**; the UI degrades gracefully if a
  cached URL has expired. Analysis runs only on explicit form submit; exceptions
  are never cached as successes.
- **UI.** One `st.form` (territory, product True-Colour/NDVI, before/after
  dates, scene-cloud %, dimensions, *Analizar cambios*); draggable swipe via
  `streamlit-image-comparison` (`in_memory=True`, signed URL never shown as
  text); separate before/after quality panels distinguishing *scene cloud*
  (`CLOUDY_PIXEL_PERCENTAGE`) from *SCL AOI valid-pixel coverage*; evidence label
  "Observación real Sentinel-2 … no validada en campo". Feature-flag gated (a
  disabled state when `SNTO_ENABLE_CHANGE_EXPLORER=false`); all EE errors mapped
  to safe, actionable Spanish messages with no traceback/URL leakage; a failed
  submit never leaves a stale result labelled as current.

## Manual live smoke test (not yet run — no live verification claimed)

This procedure is documented for later manual execution; **CI never runs it** and
the feature is **not** live-verified until it has actually been performed.

1. **Credentials & flag** (local dev):
   - `earthengine authenticate` (personal) *or* set `GEE_KEY_FILE` to a
     service-account JSON and `GEE_SERVICE_ACCOUNT` to its email;
   - set `GEE_PROJECT_ID=<your-ee-project>`;
   - set `SNTO_ENABLE_CHANGE_EXPLORER=true`;
   - `pip install -r requirements.txt` (brings `earthengine-api`,
     `streamlit-image-comparison`).
2. **Launch:** `streamlit run app.py` → open **Evidenciar → Explorador de cambio
   visual**.
3. **AOI:** pick **Parque Nacional Sierra de Guadarrama** (small, registered bbox).
4. **Windows known to contain S2 scenes:** ANTES `2023-07-01 → 2023-08-31`,
   DESPUÉS `2024-07-01 → 2024-08-31`; cloud ≤ 20 %; dimensions 512; product NDVI.
5. **Run:** press *Analizar cambios*.
6. **Expected visible outputs:** a draggable before/after NDVI swipe, a static
   dNDVI PNG with the diverging legend, and two quality panels with non-zero
   scene counts and a valid-pixel coverage ≥ 30 %.
7. **Confirm alignment:** drag the divider fully left/right — the two panels must
   register pixel-for-pixel (same extent, same size, same NDVI 0–0.9 stretch).
8. **Confirm quality metadata:** the *scene cloud %* (per-granule) and the *AOI
   valid-pixel coverage %* (SCL-derived) are shown as **separate** numbers.
9. **Product switch:** re-run with product **Color real** — the swipe shows true
   colour while the dNDVI layer remains (computed from the same collections).
10. **Disable/clear afterward:** set `SNTO_ENABLE_CHANGE_EXPLORER=false` (the tab
    shows the disabled state); in dev you may also call
    `clear_change_explorer_cache()` to drop cached results.

## 0b. Analysis + static PNG rendering core (implemented)

The next backend slice is in place — **no** service orchestration, UI, GIF, map
tiles or API. What shipped and the methodological decisions locked in:

- **Files.** `src/integrations/earth_engine/{collections,palettes,render}.py` and
  `src/analysis/change_detection/{__init__,models,composites,difference,quality}.py`.
- **Shared Sentinel-2 refactor (one source of truth).** Collection id, band
  names, SR scale, SCL bad-class list, the SCL pixel mask, the NDVI definition
  and the minimum-valid-pixel convention (0.30) now live in
  `earth_engine/collections.py`. `GEEAdapter` imports them (private aliases),
  delegates masking to `collections.mask_scl` and NDVI to `collections.add_ndvi`,
  and no longer carries its own SCL list/band constant or NDVI formula. Adapter
  behaviour is unchanged (NDVI is scale-invariant); its tests stay green.
- **Collection builder.** `build_sentinel2_collection(*, ee_module, geometry,
  start_date, end_date, max_cloud_percentage)` → `COPERNICUS/S2_SR_HARMONIZED`,
  `filterBounds`, `filterDate` (**end-exclusive**), `CLOUDY_PIXEL_PERCENTAGE`
  scene pre-filter, `mask_scl` pixel mask; retains all bands; **no `getInfo`**.
- **Date-window semantics.** `DateWindow` (frozen, `datetime.date` only —
  `datetime` rejected, timezone-free, never reads "today"). User dates are
  **inclusive** by default; the inclusive→**EE-exclusive** end conversion happens
  in exactly one place (`ee_end_date` = `end + 1 day`). Reversed/empty windows
  raise; same-day inclusive is valid (one day).
- **Cloud scene-filter vs SCL pixel-mask (kept distinct).**
  `CLOUDY_PIXEL_PERCENTAGE` is whole-**scene** metadata used only as a
  user-controlled scene pre-filter and surfaced as `mean_scene_cloud_pct`. The
  **SCL** mask is per-**pixel**; valid-pixel coverage within the AOI is a
  separate `valid_pixel_fraction`. `QualityMetadata` never conflates them.
- **NDVI composite methodology.** `ndvi_composite` = **median of per-scene
  NDVI** (mask → per-scene NDVI → `median`), *not* `NDVI(median reflectance)`.
  Documented and tested at the EE-operation-order level.
- **dNDVI.** `ndvi_difference` = `after_ndvi − before_ndvi`, band `dNDVI`. Sign
  convention: **negative = NDVI decrease, positive = NDVI increase**. No causal /
  tourism-impact claim; no severity thresholds this phase.
- **Quality metadata.** Scene count (`collection.size()`), mean scene cloud
  (`aggregate_mean`), valid-pixel count (**one** `reduceRegion(count)` on NDVI;
  `scale=10`, `maxPixels=1e8`, `bestEffort=False`, `tileScale=1` — all explicit),
  AOI pixel count via `area ÷ scale²` (no second reduceRegion); `evaluate_quality`
  is a pure assembler emitting `no_scenes` / `insufficient_valid_pixels` warnings
  against the SNTO 0.30 minimum.
- **Rendering.** `get_thumbnail_url(*, image, region, visualization, dimensions,
  image_format="png")` → EE `getThumbURL` only. Dimensions bounded [16, 2048],
  PNG-only, region explicit, EE errors mapped via the foundation typed errors,
  signed URLs never logged, no download, **no caching**, no `getMapId`/GIF.
- **Alignment contract.** `build_thumbnail_params` is a pure function of
  (region, dimensions, visualisation, format) and **independent of the image**;
  before/after render with the *same* region, dimensions and fixed-range
  `Visualization`, so panels are never independently auto-stretched.
- **Visualisation.** Centralised `palettes.py`: `TRUE_COLOUR` (B4/B3/B2, 0–3000
  DN), `NDVI` (0.0–0.9 brown→green), `DNDVI` (symmetric ±0.4 diverging, neutral
  at zero) — documented, display-only, no severity categories.
- **Still deferred (unchanged):** service orchestration, caching, `getMapId`/XYZ
  tiles, GIF/`getVideoThumbURL`, `streamlit-image-comparison`, Streamlit tab,
  navigation, AOI UI, API endpoints.

## 0. Foundation status (implemented) — how it differs from the proposal

The shared Earth Engine foundation is in place. Deltas from the audit/ADR draft,
recorded here per the "docs follow reality" rule:

- **Dependencies pinned** (backlog step 1): `earthengine-api>=1.4,<2.0` and
  `streamlit-image-comparison>=0.0.4,<0.1` added to `requirements.txt`.
- **No Dockerfile change was needed — dependency *resolution* verified, not an
  image build.** `pip install --only-binary=:all: --dry-run -r requirements.txt`
  run under **Python 3.12** (matching the `python:3.12-slim` base) resolves the
  *entire* requirements set — including earthengine-api (1.7.37) and
  streamlit-image-comparison (0.0.4) with all transitive deps — to wheels, exit 0,
  no source builds or conflicts, so the existing `--only-binary=:all:` constraint
  holds. An actual `docker build` was **not** run (no Docker daemon available in
  the verification environment); only wheel-resolution compatibility is claimed.
- **Feature flag:** `Settings.snto_enable_change_explorer: bool = False`
  (env `SNTO_ENABLE_CHANGE_EXPLORER`, added to `.env.example`). Reuses the
  existing pydantic-settings model; no parallel config.
- **`src/integrations/earth_engine/`** created: `client.py`, `errors.py`,
  `__init__.py`.
- **Error hierarchy** (vs. the draft's ad-hoc names): a single
  `EarthEngineError(RuntimeError)` base — subclassing `RuntimeError` **on
  purpose** to preserve `GEEAdapter`'s documented "raises RuntimeError" contract
  — with `EarthEngineDisabledError`, `EarthEngineConfigError`,
  `EarthEngineAuthError`, `EarthEngineUnavailableError`, `EarthEngineQuotaError`,
  plus a credential-safe `map_ee_exception()` classifier.
- **Init path:** low-level `initialize_earth_engine(project_id, *,
  service_account, key_file)` is framework-free and idempotent via a
  process-wide, lock-guarded key `(project_id, service_account, key_file)`;
  app-facing `get_change_explorer_client(settings)` enforces the flag + config;
  `cached_earth_engine_client()` is the only `st.cache_resource` touch-point and
  degrades to a plain delegate when Streamlit is absent. `reset_earth_engine_state()`
  clears both the process guard **and** the Streamlit memo.
- **Service-account contract (corrected in the verification pass):** verified
  against the real `ee._helpers.ServiceAccountCredentials(email=None,
  key_file=None, key_data=None)` — `email` is optional and *ignored* for a JSON
  key. So the adapter's historical `email=""` is forwarded to the SDK as its
  documented `None` default (avoids a blank issuer on a legacy PEM key), and a
  **service-account email with no key file is now rejected** as a config error
  instead of silently downgrading to personal auth. A key file *without* an email
  remains valid (JSON keys self-identify) — this is the adapter's path.
- **Global-per-process honesty:** the Earth Engine client is a process-global
  singleton; the guard tracks a *single* last-initialised credential set (A→B→A
  re-initialises correctly, a failed init is never recorded as initialised). The
  module documents this rather than pretending isolated multi-project support.
- **`GEEAdapter._initialize` refactored** to delegate to
  `initialize_earth_engine` (personal + JSON-service-account modes preserved;
  existing adapter tests stay green). Masking/collection/index logic was **not**
  moved (deferred to later steps, per scope).
- **CI:** `src/integrations` + `tests/unit/test_earth_engine_client.py` added to
  the blocking ruff allow-list. New package coverage ~96%; full suite green,
  total coverage ~83.7%. Foundation CI (commit `d4483c1`) passed all four jobs
  (lint / typecheck / test / postgres-integration).
- **Not implemented (out of scope):** any collection builder, cloud-filter
  control, SCL refactor, composite/NDVI/diff logic, `getThumbURL`/
  `getVideoThumbURL`, GIF, swipe UI, new tab, or navigation registration.

## 1. Goal & MVP scope

Interactive before/after Sentinel-2 change exploration inside the Streamlit
dashboard. MVP delivers:

- user-selectable **AOI** (pick a registered territory/asset → bbox seed; optional
  bbox/drawn override later),
- **before** and **after** date ranges,
- **cloud threshold** control,
- **true-colour** and **NDVI** comparison,
- **median composites** for each window,
- **draggable before/after swipe**,
- **NDVI-difference** layer,
- **valid-pixel & quality metadata**,
- **Earth Engine animated GIF** of the interval,
- **caching** and understandable **error states**.

## 2. Architecture (per ADR-015)

```
UI (src/ui/tabs/tab_change_explorer.py)
        │  reads widgets, shows swipe + GIF + metadata; NO domain logic
        ▼
Orchestration (src/services/change_explorer_service.py)
        │  (AOI, before, after, index, cloud%) -> ChangeExplorerResult
        │  owns caching + typed error states
        ├──────────────► src/analysis/change_detection/   (pure EE logic)
        │                    composites.py  (median true-colour / NDVI)
        │                    difference.py  (dNDVI band + diverging palette)
        │                    quality.py     (valid-pixel / cloud metadata)
        └──────────────► src/integrations/earth_engine/    (EE I/O only)
                             client.py      (cached ee.Initialize singleton)
                             collections.py (S2 build, SCL mask, cloud% filter)
                             render.py       (getThumbURL PNG, getMapId tiles,
                                              getVideoThumbURL GIF)
```

`app.py` only registers the new module in `src/ui/navigation.py` and dispatches
to `render_tab_change_explorer(...)` — no new processing logic, per the
CLAUDE.md non-negotiable ("app.py is composition/navigation only").

## 3. Proposed file tree (exact)

```
src/integrations/
  __init__.py
  earth_engine/
    __init__.py
    client.py                 # cached EE init/auth singleton (reuses Settings.gee_*)
    collections.py            # S2_SR_HARMONIZED build + SCL mask + cloud% filter
    render.py                 # composite -> PNG (getThumbURL), tiles (getMapId),
                              #   GIF (getVideoThumbURL); visualization params
    palettes.py               # true-colour / NDVI / dNDVI diverging vis params
    errors.py                 # EarthEngineUnavailable, EEQuotaError, EEAuthError

src/analysis/
  __init__.py
  change_detection/
    __init__.py
    composites.py             # median true-colour & NDVI composites per window
    difference.py             # NDVI-difference band (after - before)
    quality.py                # valid-pixel %, cloud %, scene count per window
    models.py                 # frozen dataclasses: WindowSpec, CompositeResult,
                              #   ChangeExplorerResult, QualityMetadata

src/services/
  change_explorer_service.py  # orchestration + caching + typed error states

src/ui/tabs/
  tab_change_explorer.py      # Streamlit page: controls, swipe, GIF, metadata

docs/audits/visual_change_feature_audit.md            # (created)
docs/decisions/ADR-015-earth-engine-change-explorer.md # (created)
docs/plans/visual_change_explorer_implementation_plan.md # (this file)

tests/unit/
  test_ee_client.py           # offline: cached init, missing-creds fallback
  test_ee_collections.py      # SCL mask + cloud% filter (mocked ee)
  test_change_composites.py   # composite/diff logic (mocked ee)
  test_change_quality.py      # valid-pixel/quality metadata
  test_change_explorer_service.py # cache key, error-state mapping (ee mocked)
tests/ui/
  test_change_explorer_tab.py # navigation registration + degraded state
```

Config touch-points (edit, not new files): `src/config/settings.py`
(feature flag), `requirements.txt` (new deps), `.env.example` (already has
`GEE_*`; add the flag), `src/ui/navigation.py` (register the module).

## 4. Reuse map (compose, don't reinvent)

| New file | Reuses / refactors from |
|----------|-------------------------|
| `earth_engine/collections.py` | `gee_adapter._S2_COLLECTION`, `_cloud_mask_scl`, band constants, `_SCL_BAD_VALUES` |
| `earth_engine/client.py` | `gee_adapter._initialize` (dual auth) → lift to a shared `@st.cache_resource` singleton; `src/config/settings.py` |
| `analysis/change_detection/composites.py` | `gee_adapter._compute_scaled_indices`, `.median()` compositing |
| `analysis/change_detection/quality.py` | `gee_adapter` valid-pixel accounting (`_MIN_VALID_PIX_PCT`, `NDVI_count`, `cloud_cover_pct`) |
| AOI selection | `src/config/territories.py` (`bbox_wgs84`, `s2_tile`), `oapn_limite_pn.geojson`, `clean_assets/pnsg_assets.geojson`, `src/assets/models.py` geometries |
| Tab wiring | `src/ui/tabs/tab_diagnostic.py` (map-in-tab pattern), `src/ui/navigation.py` |
| Tests | `tests/unit/test_gee_adapter.py` offline `ee`-stub convention |

**Recommended refactor first:** extract the shared masking/index helpers out of
`gee_adapter.py` into `earth_engine/collections.py` and have the adapter import
them, so there is one source of truth (do this as a separate, behaviour-preserving
step with the adapter's tests green).

## 5. Required new dependencies

- `earthengine-api` — **required** (currently undeclared; only deferred-imported).
- `streamlit-image-comparison` — MVP swipe widget (small static component).
- (Optional, phase 2) `geemap` **or** a custom Leaflet component — only if live
  pan/zoom is later justified.
- **Docker note:** `earthengine-api` pulls transitive deps; verify it satisfies
  the `Dockerfile` `--only-binary=:all:` constraint or relax that line for this
  package.

## 6. Configuration & secrets

- Reuse `Settings.gee_project_id / gee_service_account / gee_key_file`.
- Add `Settings.snto_enable_change_explorer: bool = False` + `.env.example` entry.
- **Local:** `earthengine authenticate` or `GEE_KEY_FILE` path (git-ignored `.env`).
- **Production:** service-account JSON via Key Vault / Container App secret
  (`docs/runbooks/keyvault-secrets.md`); never in the image. Absent creds →
  page shows a clear "Earth Engine not configured" state.

## 7. Test strategy

- **Offline by default:** mock the `ee` module (existing `sys.modules` stub
  pattern) so CI never calls EE and needs no credentials.
- Unit-test pure logic: SCL mask composition, cloud-% filter, composite/diff band
  construction, valid-pixel/quality math, cache-key determinism, error-state
  mapping (auth/quota/empty-collection → typed states).
- UI test: navigation registration + graceful degraded render when the flag is off
  or creds are missing.
- **Optional gated live smoke test:** a `@pytest.mark.live_ee` test, skipped
  unless `GEE_*` creds are present, hitting one tiny AOI/short window — never in
  the default CI gate.
- Keep the `--cov-fail-under=80` gate green.

## 8. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| **EE quota / rate limits** in the serving process | Cache aggressively by `(aoi, before, after, index, cloud%)`; reuse `gee_adapter`'s retry/backoff; feature flag to disable. |
| **Performance** (`getThumbURL`/`getVideoThumbURL` are slow) | `@st.cache_data` on rendered PNG/GIF URLs; consider a background job / pre-bake for canonical AOIs; cap AOI size & date span. |
| **Streamlit rerun storms** re-triggering EE | Cached EE client (`@st.cache_resource`); cache render outputs; guard with `st.form`/submit so composites recompute only on explicit run, not every widget tweak. |
| **Double `ee.Initialize`** under reruns | Single cached client singleton; idempotent init guard. |
| **Docker wheels-only build** breaks on `earthengine-api` | Verify wheel availability or scope-relax `--only-binary=:all:` for that package. |
| **Evidence overclaim** | Label output REAL-but-not-validated; no field-validation claim (ADR-003 / #26). |
| **Empty / all-cloud window** | Typed error state → "no cloud-free scenes for this window/threshold", not a crash. |
| **Secret leakage** | Service-account JSON only via Key Vault/secret; `.env`/`*.json` git-ignored; verified before any deploy. |

## 9. geemap/leafmap sufficiency & custom-Leaflet question

- **MVP:** geemap/leafmap are **not** needed. EE `getThumbURL` PNGs +
  `streamlit-image-comparison` deliver the swipe without a folium tile server,
  honouring the project's no-folium-RAM decision.
- **Custom Leaflet component** is **justified later**, not now — only once users
  need live pan/zoom, draw-your-own-AOI, or raster swipe beyond a fixed extent.
  Until then the static-composite swipe is the right altitude for an MVP.

## 10. Ordered implementation backlog

0. **(Prep)** Owner decisions in ADR-015 §"Open decisions"; obtain EE
   project/service account; confirm in-process (ADR-012) placement.
1. ✅ **Done.** Add deps (`earthengine-api`, `streamlit-image-comparison`) +
   `Settings` flag + `.env.example` entry. Docker verified wheel-compatible (no
   change).
2. ✅ **Done.** `src/integrations/earth_engine/client.py` — cached init singleton
   + `errors.py`; offline unit tests incl. disabled/missing-config/quota mapping;
   `GEEAdapter` now delegates to it.
3. ✅ **Done.** Refactor shared masking/index helpers into
   `earth_engine/collections.py`; `gee_adapter.py` consumes them (adapter tests
   green).
4. ✅ **Done.** `earth_engine/render.py` + `palettes.py` — `getThumbURL` PNG +
   vis params (true-colour, NDVI, dNDVI); alignment contract.
5. ✅ **Done.** `analysis/change_detection/composites.py` + `models.py` — median
   true-colour & NDVI composites; offline tests.
6. ✅ **Done.** `analysis/change_detection/quality.py` — valid-pixel/cloud/scene
   metadata (single reduceRegion; pure assembler).
7. ✅ **Done.** `analysis/change_detection/difference.py` — dNDVI band.
8. ✅ **Done.** `src/services/change_explorer_service.py` — orchestrate + cache +
   typed errors; request/result models; service, cache and UI tests.
9. `render.py` GIF path (`getVideoThumbURL`) wired through the service. **(next
   task — not started; explicitly deferred)**
10. ✅ **Done.** `src/ui/tabs/tab_change_explorer.py` — AOI picker, date ranges, cloud slider,
    index toggle, swipe, GIF, metadata; register in `src/ui/navigation.py`.
11. UI/navigation test; degraded-state test; docs sync; keep coverage ≥80 %.
12. (Optional) live-EE smoke test (gated); (phase 2) tiles/custom Leaflet.

## 11. Blockers requiring a human decision

1. **Earth Engine production account, quota & billing** — who owns it, what
   limits (see ADR-015 open decision 4).
2. **Deploy placement** — confirm in-process Streamlit (ADR-012 gate) vs. exposing
   via `/api/v2` (open decision 1).
3. **Cloud-mask upgrade** — keep SCL only, or add `s2cloudless`/
   `CLOUDY_PIXEL_PERCENTAGE` for the user threshold (open decision 2).
4. **GIF cost strategy** — synchronous+cached vs. background/pre-baked
   (open decision 3).
5. **Docker `--only-binary=:all:`** — accept relaxing it for `earthengine-api`
   if no suitable wheel exists.
6. **Phase-2 custom Leaflet** go/no-go (open decision 5).
