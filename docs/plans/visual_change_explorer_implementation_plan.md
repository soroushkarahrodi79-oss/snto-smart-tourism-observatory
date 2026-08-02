# Implementation Plan — Visual Change Explorer

- **Status:** In progress — **Foundation (backlog steps 1–2) implemented.**
- **Date:** 2026-08-02 (foundation landed 2026-08-02)
- **Companions:** `docs/audits/visual_change_feature_audit.md`,
  `docs/decisions/ADR-015-earth-engine-change-explorer.md`

## 0. Foundation status (implemented) — how it differs from the proposal

The shared Earth Engine foundation is in place. Deltas from the audit/ADR draft,
recorded here per the "docs follow reality" rule:

- **Dependencies pinned** (backlog step 1): `earthengine-api>=1.4,<2.0` and
  `streamlit-image-comparison>=0.0.4,<0.1` added to `requirements.txt`.
- **No Dockerfile change was needed.** Verified with
  `pip install --only-binary=:all: --dry-run` for both packages: earthengine-api
  (1.7.37) and all its transitive deps, and streamlit-image-comparison (0.0.4),
  resolve to wheels, so the existing `--only-binary=:all:` constraint holds.
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
  added for tests/credential rotation.
- **`GEEAdapter._initialize` refactored** to delegate to
  `initialize_earth_engine` (service-account/personal modes preserved; behaviour
  unchanged; existing adapter tests stay green). Masking/collection/index logic
  was **not** moved (deferred to later steps, per scope).
- **CI:** `src/integrations` + `tests/unit/test_earth_engine_client.py` added to
  the blocking ruff allow-list. New package coverage 99%; full suite green,
  total coverage ~83.7%.
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
3. Refactor shared masking/index helpers into
   `earth_engine/collections.py`; point `gee_adapter.py` at them (adapter tests
   stay green).
4. `earth_engine/render.py` + `palettes.py` — `getThumbURL` PNG for a given
   composite + vis params (true-colour, NDVI, dNDVI).
5. `analysis/change_detection/composites.py` + `models.py` — median true-colour &
   NDVI composites per window; unit tests (mocked ee).
6. `analysis/change_detection/quality.py` — valid-pixel/cloud/scene metadata.
7. `analysis/change_detection/difference.py` — NDVI-difference band.
8. `src/services/change_explorer_service.py` — orchestrate + cache + typed errors;
   unit test cache key & error mapping.
9. `render.py` GIF path (`getVideoThumbURL`) wired through the service.
10. `src/ui/tabs/tab_change_explorer.py` — AOI picker, date ranges, cloud slider,
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
