# Implementation Plan — Visual Change Explorer

- **Status:** In progress — **Foundation + Analysis/Static-PNG core + Service
  orchestration + Swipe UI (backlog steps 1–8, 10) implemented; smoke-test
  harness (step 12); runtime bug-fix pass (§0e); On-demand Temporal GIF MVP
  (backlog step 9) implemented (§0f).**
- **Swipe MVP live status: `LIVE VERIFIED — LOCAL DEVELOPMENT ENVIRONMENT`**
  (date 2026-08-04). Real live success on the owner's machine for the
  conservative AOI and the full PNSG bbox (NDVI + True Colour); the
  `valid_pixel_fraction > 1` bug is fixed; the UI blank-result issue is addressed
  with loading feedback + a non-blank fallback.
- **GIF MVP live status: `NOT LIVE VERIFIED — awaiting owner live smoke test`**
  (this Claude session has no Earth Engine credentials; the code is complete and
  fully unit/UI-tested offline, and the manual live smoke procedure is documented
  in §0f).
- **Date:** 2026-08-02 (foundation landed 2026-08-02); GIF MVP 2026-08-04
- **Companions:** `docs/audits/visual_change_feature_audit.md`,
  `docs/decisions/ADR-015-earth-engine-change-explorer.md`

## 0f. On-demand Temporal GIF MVP (backlog step 9, implemented)

A bounded, synchronous, **explicitly-triggered** temporal GIF, added **below** a
successful swipe. It **never** runs on form change, page load, automatically
after the swipe, or an ordinary rerun — only when its own separate
*Generar GIF temporal* form is submitted. Products: **NDVI** and **True Colour**
(the same product as the comparison result); **dNDVI is never animated**.

**Frame methodology.** Each frame is a **median composite over a temporal
sub-window** (True Colour: median of masked B4/B3/B2; NDVI: median of per-scene
NDVI), **pre-visualised** with the centralised fixed visualisation so every frame
shares one identical AOI, projection, dimensions and stretch/palette (**no
per-frame auto-stretch**). No scientific/causal/severity labels are baked into
the pixels.

**Adaptive month-step planner** (`plan_frame_windows`, pure/local, no network, no
current-date use): calendar-month windows with
`step_months = ceil(number_of_calendar_months / max_frames)`; contiguous,
ordered, non-overlapping; the first and last frame may be partial months; every
day belongs to exactly one frame. Rejects reversed spans, `datetime` inputs,
spans shorter than two frames, and spans longer than the 24-month cap.

**Hard limits** (enforced in the models **and** the service, rejected *before*
any EE call): span ≤ **24 months**; usable frames **min 2 / max 12** (UI default
max **8**); dimensions **256 or 384** (default **256**); FPS **1/2/3** (default
**2**); GIF response cap **8 MiB**; explicit **30 s** HTTP timeout; one GIF per
request; no full-res downloads; no permanent file storage.

**Scene-count-only frame policy.** Empty-frame handling uses **one** grouped EE
expression (`scene_counts_expr` → a single `ee.List` of every frame's
`collection.size()`) evaluated with **at most one** application-level `getInfo`.
Zero-scene frames are removed (order preserved; a warning is recorded per omitted
frame); **≥ 2 usable frames are required** or `InsufficientUsableFramesError` is
raised. Per-frame **valid-pixel coverage is deliberately out of scope** — the GIF
is exploratory/observational, not a validated measurement, so it is **not**
re-computed per frame (that would add repeated expensive `reduceRegion` work).

**URL-to-bytes.** The service calls `getVideoThumbURL` and **immediately** fetches
the signed URL to bytes (bounded read, 8 MiB cap, timeout, GIF-magic
validation), then discards the URL. The signed URL is **never** stored in session
state, the cached result, a dataclass `repr`, logs, documentation, or test
output.

**Cache.** `st.cache_data`, **TTL 900 s**; the key includes territory + bbox +
date range + product + cloud + dimensions + max frames + FPS + dataset id +
composite-method version + visualisation version + animation-planner version — and
**no** credentials/`Settings`/EE objects/signed URL. Failures are never cached;
`clear_change_animation_cache()` resets it. The 8 MiB cap keeps cached bytes
bounded.

**Disclaimer (verbatim, Spanish, surfaced under every GIF):** *"Animación
exploratoria de composiciones temporales Sentinel-2. Los cambios visibles pueden
reflejar estacionalidad, nubosidad residual, fenología, incendios, manejo
territorial u otros factores. No demuestra causalidad turística ni sustituye
validación de campo."* Colours are never labelled as damage/impact/degradation/
recovery.

**Files.** `src/analysis/change_detection/animation.py` (planner + frame
construction), `src/integrations/earth_engine/video.py` (`getVideoThumbURL`
primitive), `src/services/change_animation_service.py` (orchestration + bounded
download + cache), the GIF section in `src/ui/tabs/tab_change_explorer.py`, and
tests `tests/unit/test_change_animation.py`, `tests/unit/test_change_video.py`,
`tests/unit/test_change_animation_service.py`,
`tests/unit/test_change_animation_cache.py`,
`tests/ui/test_change_animation_ui.py`, plus the optional live
`tests/live/test_change_animation_live.py`.

**Manual live GIF smoke procedure** (`scripts/smoke_test_change_animation_live.py`,
manual only, **never in CI**):

1. Configure credentials out-of-band (`GEE_PROJECT_ID` + personal
   `earthengine authenticate` **or** `GEE_SERVICE_ACCOUNT` + `GEE_KEY_FILE`), and
   `SNTO_ENABLE_CHANGE_EXPLORER=true`.
2. Run `python scripts/smoke_test_change_animation_live.py --confirm-live-ee`
   (required opt-in; refuses with exit code 2 otherwise). Defaults: PNSG, NDVI,
   2023-07-01 → 2024-08-31, max 8 frames, 256 px, 2 FPS, cloud ≤ 20 %, on the
   conservative in-PNSG AOI (`--full-bbox` uses the registered bbox).
3. It reuses the **production** `run_change_animation` service, prints **only**
   safe metadata (frame counts, byte size, status) and **never** the signed video
   URL. It writes a GIF to disk **only** with an explicit `--output <git-ignored
   path>` and refuses to overwrite without `--force`. Distinct exit codes per
   failure class; creates no assets/exports.

**GIF MVP live status: `NOT LIVE VERIFIED — awaiting owner live smoke test`** —
this session has no Earth Engine credentials, so no GIF live verification is
claimed. The code is complete and fully unit/UI-tested offline (mocked `ee`, no
network).

## 0e. Runtime bug-fix pass (full-AOI execution + UI visibility)

Driven by a **real live run on the user's machine** (credentials valid). Confirmed
live facts: conservative-AOI **and** full registered PNSG bbox both succeed for
NDVI **and** True Colour at 256 px / cloud 20 % (scene_count 19/19, three
artifacts, status `ok`). So Earth Engine init, S2 collection construction,
metadata evaluation and thumbnail generation all work at full AOI — the backend
is **not** the cause of the blank UI.

- **Confirmed bug — `valid_pixel_fraction = 1.325` (impossible):** FIXED.
  - **Root cause:** the fraction mixed two incompatible bases — numerator was a
    `reduceRegion(count)` on the Sentinel-2 **UTM 10 m pixel grid**, denominator
    was `geometry.area()/scale²` (a **geodesic m²** area). For a lon/lat rectangle
    the two differ by ≈ `1/cos(latitude)`; at PNSG's ~40.9° N that is ≈ 1.323,
    matching the observed 1.325.
  - **Fix (not a clamp):** both counts now come from **one** `reduceRegion` over
    the NDVI mask (`src/analysis/change_detection/quality.py::pixel_counts_expr`):
    `sum` of the 0/1 mask = valid pixels, `count` = total footprint pixels, on the
    **same** grid/projection/region. `valid ≤ total` ⇒ `fraction ∈ [0, 1]` by
    construction; no footprint ⇒ counts `0`/`None` ⇒ fraction honestly `None`.
    Scene cloud (`CLOUDY_PIXEL_PERCENTAGE`) vs AOI valid-pixel coverage stay
    distinct. Still one combined `getInfo` per window.
- **UI "nothing appears" symptom:** ADDRESSED (loading feedback + guaranteed
  non-blank fallback). **Not reproduced live in this session** — this environment
  has **no** Earth Engine credentials, so I could not launch the real Streamlit UI
  or re-run the full-bbox smoke here (stated honestly; not fabricated). Fixes
  applied, all offline-tested:
  - **Loading state (B):** the service call is wrapped in `st.spinner(...)` so a
    long full-bbox run (the user's confirmed working path) no longer looks frozen.
  - **Fallback rendering (C):** if `image_comparison` raises, the page shows a
    warning **plus** before/after via `st.image` side by side; on success, a
    collapsed "ver por separado" expander still guarantees the images are
    reachable even if the slider's client-side JS/CDN silently fails to render.
    The dNDVI + quality panels always render below. No signed URL is shown as text.
  - **Observability (D):** safe `INFO` logs at service start (territory, product,
    dims, resolved bbox), service completion (status, scene counts, coverage), and
    UI submit → "service done in Xs" → swipe-rendered / fallback — so the exact
    service-vs-render boundary is visible in logs without any secret/URL.
  - **Most likely cause (hypothesis, to confirm on the user's next run):** no
    loading feedback during a multi-second full-bbox EE call (perceived hang)
    and/or the swipe component rendering blank client-side. Both are now covered.
- **Fallback path added:** yes. **Feature scope unchanged** (no GIF/tiles/API).

## 0d. Live verification

**Status: `NOT LIVE VERIFIED — no Earth Engine credentials available in the
execution environment`** (GEE_PROJECT_ID / GEE_SERVICE_ACCOUNT / GEE_KEY_FILE and
personal EE credentials all ABSENT). A successful real round trip could not be
performed; no smoke-test success is claimed or fabricated.

- **Date / environment:** 2026-08-02, sandboxed remote execution environment
  (local-development-equivalent; not production).
- **Auth mode:** none available — no personal auth, no service-account config,
  no project id. The real `ee.Initialize` was reached and failed as expected.
- **Earth Engine API:** `earthengine-api` 1.7.37, Python 3.11.15,
  `streamlit` 1.56.0, `streamlit-image-comparison` 0.0.4.
- **Environment defect repaired (not a code defect):** `import ee` initially
  crashed with a `pyo3`/`_cffi_backend` panic from a broken system `cryptography`
  build; reinstalling a working `cffi` wheel fixed it. `cffi` is a transitive
  dependency that installs correctly from a clean `pip install -r requirements.txt`,
  so **no `requirements.txt` change is warranted** — this was a pre-broken
  sandbox, documented here as an ops gotcha only.
- **Prepared / verified without credentials:**
  - imports: `ee`, `streamlit`, `streamlit_image_comparison` all import cleanly
    after the `cffi` fix; the service + client import cleanly.
  - the real `ee.Initialize(project=…)` (no creds) raises `ee.EEException`
    ("Please authorize…") **non-interactively** (no hang, no `ee.Authenticate()`
    triggered by the app) and the foundation maps it to `EarthEngineAuthError` —
    the app-level error-classification path is confirmed against the real SDK.
  - **real SDK call-contract check (by introspection, 1.7.37):** every call the
    code makes matches the actual signature —
    `ee.Geometry.Rectangle(coords, proj=, geodesic=)`,
    `Image.reduceRegion(reducer=, geometry=, scale=, maxPixels=, bestEffort=, tileScale=)`,
    `Image.getThumbURL(params)`, `Image.normalizedDifference(bandNames)`,
    `ImageCollection.aggregate_mean(property)`, `Geometry.area(maxError=)`,
    `ee.Filter.lte(name, value)`, `ee.Dictionary(...)`. **No signature-level
    defect found; no speculative code changes made.**
- **Pass/fail (live):** initialization ❌ (no creds) · metadata `getInfo` ⏭️ not
  reached · PNG `getThumbURL` ⏭️ not reached · swipe ⏭️ · dNDVI ⏭️ · cache ✅
  (offline hit/miss/no-cache-on-exception tests) · error states ✅ (real-SDK
  auth failure + config/quota/unavailable mapping).
- **Durations:** only import + the failing `ee.Initialize` were reached
  (sub-second to fail); no metadata/thumbnail timings available.
- **Manual smoke script:** `scripts/smoke_test_change_explorer_live.py` exercised
  end to end in its non-credential paths — refuses without `--confirm-live-ee`
  (exit 2), reports flag-off as CONFIG (exit 5), and reaching the real
  `ee.Initialize` without creds reports AUTH (exit 6) — all with **no URLs or
  secrets printed**.
- **Remaining limitation:** everything after a successful `ee.Initialize`
  (geometry execution, S2 filtering, SCL masking, NDVI, composites, quality
  `getInfo`, `getThumbURL`, image-byte loading in the swipe, dNDVI rendering,
  before/after visual alignment, TTL behaviour) is **unverified live** and must
  be confirmed by running the manual smoke test / gated live test in an
  environment with real Earth Engine credentials (see §"Manual live smoke test"
  and `tests/live/test_change_explorer_live.py`).

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
9. ✅ **Done.** On-demand Temporal GIF MVP (§0f): a dedicated
   `getVideoThumbURL` primitive (`integrations/earth_engine/video.py`) + local
   frame planner and frame construction (`analysis/change_detection/animation.py`)
   + orchestration/bounded-download/cache
   (`services/change_animation_service.py`), wired through the service and
   surfaced as an explicit, separate GIF form under a successful swipe.
   Code-complete and offline-tested; **not yet live verified** (no credentials in
   the implementing session).
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
