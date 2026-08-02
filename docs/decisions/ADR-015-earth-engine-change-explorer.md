# ADR-015 — Earth Engine Visual Change Explorer (before/after swipe + animated GIF)

- **Status:** Accepted — foundation implemented (fixed decisions confirmed; see
  the plan's "Foundation status" for what shipped and how it differs from the
  draft). The `errors.py` base subclasses `RuntimeError` to preserve the existing
  adapter contract; the MVP composites/rendering/GIF/UI remain unbuilt.
- **Date:** 2026-08-02
- **Deciders:** Owner (pending)
- **Related:** ADR-011 (persistence), ADR-012 (`/api/v2` deploy gate), ADR-003
  (validation gate #26), `docs/audits/visual_change_feature_audit.md`,
  `docs/plans/visual_change_explorer_implementation_plan.md`
- **Supersedes / conflicts:** none. Reaffirms the "no folium tile server" intent
  recorded in `requirements.txt`.

## Context

We want an interactive **Visual Change Explorer**: pick an AOI and two date
ranges, choose a cloud threshold, and compare **true-colour** and **NDVI**
median composites in a **draggable before/after swipe**, with an **NDVI-difference
layer**, **valid-pixel/quality metadata**, and an **Earth Engine animated GIF** of
the interval.

The audit found a strong Earth Engine *analytical* core
(`src/ingestion/gee_adapter.py`: SCL masking, NDVI/NDMI/EVI, median composites,
valid-pixel accounting, retry/backoff, dual auth) and solid AOI assets
(`src/config/territories.py` bboxes, park boundary + route GeoJSON), but **no**
EE image-rendering path (no `getMapId`/`getThumbURL`/`getVideoThumbURL`), **no**
swipe widget, and **no** GIF generation. `earthengine-api` is not a declared
dependency. Folium/streamlit-folium were deliberately removed for constant
server RAM; the app renders maps with pydeck (Deck.gl/WebGL).

## Decision

Build a **new, thin Earth Engine visualization + change-detection layer** that
**composes** the existing masking/index logic, under this placement:

- `src/integrations/earth_engine/` — all EE I/O: a cached client/init singleton,
  S2 collection building (masking, cloud-% filter), and **image rendering**
  (`getThumbURL` PNG, `getMapId` XYZ tiles, `getVideoThumbURL` GIF). No SNTO
  domain logic here.
- `src/analysis/change_detection/` — pure, EE-object-in/EE-object-out
  change logic: true-colour & NDVI median composites for a window, the NDVI
  difference band + diverging palette, valid-pixel/quality derivation. No
  Streamlit, no network beyond the EE objects passed in.
- `src/services/` — orchestration: `(AOI, before_range, after_range, index,
  cloud%) → ChangeExplorerResult(before_png, after_png, diff_png, gif_url,
  metadata)`, owning caching and typed error states.
- **UI** — a new page/tab under the existing `src/ui/tabs/` + `src/ui/`
  structure that renders the swipe, controls, and metadata. `app.py` stays
  composition/navigation only (registered via `src/ui/navigation.py`), with
  **no new domain or processing logic**, per the CLAUDE.md non-negotiable.

**MVP swipe technique:** server-render **static PNG composites** via EE
`getThumbURL` and compare them with a lightweight image-comparison widget
(`streamlit-image-comparison`, a small static React component — no per-session
tile server). This honours the no-folium-RAM decision and keeps EE calls
cache-friendly. A `getMapId`/XYZ-tile pan-zoom experience and/or a **custom
Leaflet Streamlit component** are deferred to a later phase, justified only when
users need deep pan/zoom beyond a fixed AOI extent.

**Evidence labelling:** all output is **REAL Sentinel-2** imagery but is **not**
field-validated. It is surfaced as a *visual / seasonal early-warning* product
and must never emit a satellite↔field validation claim (ADR-003 / #26).

## Options considered

1. **geemap/leafmap + streamlit-folium split map (`geemap.foliumap`,
   folium `DualMap`).** Richest interactivity, native EE swipe.
   *Rejected for MVP:* reintroduces the folium stack the project removed for RAM
   reasons; heavier per-session server object; larger dependency surface.
2. **pydeck `TileLayer` fed by EE `getMapId` XYZ tiles.** Stays on the existing
   WebGL stack. *Deferred:* pydeck has **no built-in draggable swipe**; a swipe
   would need a custom component anyway, and tiles add a live EE-tile dependency
   per pan/zoom (quota + latency).
3. **EE `getThumbURL` static PNGs + `streamlit-image-comparison` swipe
   (CHOSEN for MVP).** One cached EE render per composite; draggable swipe with a
   tiny static component; zero tile server. GIF via `getVideoThumbURL`.
   *Trade-off:* fixed AOI extent, no live pan/zoom — acceptable for an MVP whose
   job is before/after change reading, not GIS navigation.
4. **Custom Leaflet Streamlit component (bidirectional).** Best long-term UX
   (draw AOI, pan/zoom, native raster swipe). *Deferred:* real front-end build +
   maintenance cost; only justified once the fixed-extent MVP proves demand.

## Consequences

**Positive:** reuses the validated masking/index core; keeps `app.py` clean and
the analytical/visualization seam explicit; no new server-side tile daemon; EE
renders are cacheable by `(aoi, dates, index, cloud%)`; testable offline with the
existing `ee`-stub convention.

**Negative / costs:** adds `earthengine-api` (+ `streamlit-image-comparison`) —
heavier than the current wheels-only Docker build assumes; introduces a live EE
quota dependency into the serving process for the first time; GIF generation is
slow and must be cached or backgrounded; requires EE credentials in production
(secret handling per below).

**Neutral:** `/api/v2` deploy gate (ADR-012) is **unchanged** — this is a
Streamlit in-process feature, not a new HTTP surface.

## Configuration & secrets

- Reuse `Settings.gee_project_id / gee_service_account / gee_key_file` and the
  existing `GEE_*` `.env.example` block — do **not** add a parallel config.
- **Local dev:** personal auth (`earthengine authenticate`) or a service-account
  JSON path in `GEE_KEY_FILE` (kept out of the repo; `.env` is git-ignored).
- **Production:** service-account JSON delivered via secret (Azure Key Vault /
  Container App secret, per `docs/runbooks/keyvault-secrets.md`), never baked
  into the image. Add a feature flag (e.g. `SNTO_ENABLE_CHANGE_EXPLORER`) so the
  page degrades to a clear "Earth Engine not configured" state when creds are
  absent — matching the repo's honest-fallback pattern.

## Open decisions (require a human)

1. **Ship in-process vs. behind `/api/v2`?** ADR-012 gate says in-process for
   now; confirm.
2. **Cloud-mask upgrade:** keep the SCL list, or add `s2cloudless` /
   `CLOUDY_PIXEL_PERCENTAGE` for the user cloud-% control? (recommend the latter,
   layered on SCL.)
3. **GIF cost control:** synchronous with hard caching, or a background job /
   pre-bake for canonical AOIs?
4. **Production EE quota/billing** account ownership and limits.
5. Whether to promote the swipe to a **custom Leaflet component** in phase 2.
