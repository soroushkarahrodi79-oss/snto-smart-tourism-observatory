# Data Acquisition Triage — Paper 1

**Status:** DRAFT for owner approval · **Date:** 2026-08-09 · **Phase 7 deliverable**

Classifies every dataset Paper 1 might touch into four bands, and states for each external source: authority, licence, spatial unit, temporal resolution, what it actually measures, its limitations, and **whether it measures the scientific target or is only a proxy**.

| Band | Meaning |
|---|---|
| **A — MUST COLLECT** | Paper 1 cannot be written without it |
| **B — USEFUL SECONDARY** | Strengthens the paper; its absence costs a secondary analysis, not the paper |
| **C — FUTURE PAPER / PRODUCT** | Real value, not Paper 1. Actively kept out of scope |
| **D — DO NOT FABRICATE** | Tempting substitutions that must never be made |

---

## Band A — MUST COLLECT FOR PAPER 1

### A-1 · Real PNSG field observations 🔴 **THE BINDING CONSTRAINT**

| Field | Value |
|---|---|
| Source | Original field campaign (issue #26), executed under `FIELD_CAMPAIGN_EXECUTION_PLAN.md` |
| Authority | This project; requires PNSG research authorisation |
| Licence | Project-owned; publish as open supplementary data |
| Spatial unit | 20 m plot = 5 × 1 m² subplots |
| Temporal resolution | Single round (cross-sectional) |
| Measures | Soil compaction (MPa), vegetation cover (%), erosion class (0–3), trail width (m), bare soil (%) |
| **Target or proxy?** | **Target.** This is the ground truth. The composite index is a *construct*, but its components are direct measurements. |
| Limitations | Single season, single park, single round; cover and erosion are observer-dependent (hence the repeatability protocol); compaction censored at 3.0 MPa |
| Current state | **MISSING — zero observations exist.** Template has 4 rows, all measurement columns empty, and impact/control plots share coordinates |
| Blocking | **Yes. Absolutely.** No substitute exists. |

### A-2 · Campaign-matched Sentinel-2 acquisition

| Field | Value |
|---|---|
| Source | ESA Copernicus, Sentinel-2 L2A, tile T30TVL — via GEE `S2_SR_HARMONIZED` or Copernicus Data Space |
| Authority | ESA / European Commission |
| Licence | Copernicus open data (free, redistributable, attribution required — already present in the app footer) |
| Spatial unit | 10 m (B4/B8), **20 m (B11)** → matching support 20 m |
| Temporal resolution | 5-day revisit (constellation); composite over a ±3-week window |
| Measures | Surface reflectance → NDVI, NDMI → EHS |
| **Target or proxy?** | **Proxy.** Spectral indices measure canopy greenness and moisture. They **do not** measure soil compaction, erosion severity, trail width, or visitor numbers. That gap is exactly what this paper is testing. |
| Limitations | Sub-pixel trail treads (`SPATIAL_MATCHING_PROTOCOL.md` §2); cloud/snow loss at high elevation; NDVI saturation under dense canopy; per-scene percentile anchoring |
| Current state | **MISSING for validation purposes.** The existing 2025-08-10 / 2026-04-10 pair is chronologically inverted, cross-year and cross-sensor |
| Blocking | **Yes** — but acquirable at zero cost with a defined window |

### A-3 · Trail geometry (OAPN official cartography)

| Field | Value |
|---|---|
| Source | OAPN GeoServer WFS — `UsoPublico_visor:view_vis_oapn_itinerarios_visor`, via `etl_oapn_wfs.py` |
| Authority | Organismo Autónomo Parques Nacionales (MITECO), Spain |
| Licence | **🔲 must be confirmed and cited before submission** — assumed open/reusable public-sector information; the exact terms are not recorded in the repository |
| Spatial unit | LineString / MultiLineString trail segments |
| Temporal resolution | Static cartography, versioned by download date |
| Measures | Official trail centrelines |
| **Target or proxy?** | **Target** for trail location. **Proxy** for actual walked path — informal desire lines and braiding are not mapped, and where they exist the mapped centreline may misplace the corridor by several metres, i.e. by a meaningful fraction of a 20 m cell |
| Limitations | Centreline only, no tread width; unmapped informal trails; download date not currently recorded per feature |
| Current state | ✅ **READY** — 218 segments, 1 035.1 km, committed in `data/outputs/pnsg/pipeline_a_results.geojson` |
| Blocking | No |

### A-4 · Ecological stratification layer

| Field | Value |
|---|---|
| Source | OAPN WFS `SistemasNaturales_visor:view_snl_vegetacion_visor` (already in `etl_oapn_wfs.py`), plus a DEM for elevation bands |
| Authority | OAPN (MITECO) |
| Licence | 🔲 same confirmation as A-3 |
| Spatial unit | Vegetation polygons; DEM raster (Copernicus DEM 30 m or PNOA 25 m) |
| Temporal resolution | Static |
| Measures | Vegetation community; elevation, slope, aspect |
| **Target or proxy?** | **Target** for stratum definition |
| Limitations | Polygon boundaries are generalised; a plot near a boundary may be misassigned — record the distance to the nearest boundary and use it in sensitivity analysis |
| Current state | **ENGINE BUILT (2026-08-10), input BLOCKED.** `scripts/paper1/build_ecological_strata.py` derives S1–S4 per trail from a DEM (elevation band + N/S aspect split; optional OAPN vegetation cross-check), and B-01's planner consumes it via `--strata` so the `stratum` column carries S1–S4. **But no DEM can be obtained here** — Copernicus/earth-search STAC, OpenTopography, USGS/CGIAR SRTM and IGN MDT are all proxy-blocked (only `raw.githubusercontent.com` reaches), and the OAPN vegetation WFS is blocked too. `--dem` has **no default**; the pure elevation×aspect→S1–S4 mapping is fully tested against a synthetic DEM. Until a real DEM is supplied, B-01 falls back to the labelled **satellite-stress tercile**. |
| Blocking | **Yes** for the stratified design — but now blocked only on **supplying a DEM** (Copernicus GLO-30 or IGN MDT05, both free, reachable from a normal network), not on writing code. |

> **Blocker found building B-01 (2026-08-09), resolved by the owner (2026-08-15):** the **IGN Líneas Límite** administrative boundary needed to filter trails to the Madrid sector was **unreachable from this build environment** — the outbound proxy blocks `ign.es`, Eurostat GISCO, GADM, the Overpass API, and every npm CDN, reaching only `raw.githubusercontent.com`. The cartographic-scale substitutes tried first (Natural Earth 10m, click_that_hood) misplaced the CM/Castilla y León crest border by kilometres — exactly where the trail network sits (verified: ~160/218 trails "outside Madrid", including unambiguously-Madrid ones). **The owner supplied a real boundary directly** (OpenStreetMap relation 349055, 6 294 vertices, fetched from their own network) — validated against known landmarks (La Pedriza in / Valsaín out), a minor topology defect repaired (`buffer(0)`, area Δ 0.015%), and B-01's plan regenerated with `--boundary-authoritative`: **no longer PROVISIONAL**. See `clean_assets/field_validation/reference/README.md`.

### A-5 · GPS positions with recorded accuracy

| Field | Value |
|---|---|
| Source | Field GNSS / smartphone, ≥ 60 s averaging |
| Spatial unit | Point, with accuracy in metres |
| **Target or proxy?** | **Target** for plot location |
| Limitations | Consumer GNSS under montane canopy is typically 3–10 m — a substantial fraction of a 20 m cell. This is why accuracy is recorded per plot and why > 5 m is an exclusion |
| Current state | **MISSING** — no accuracy column exists in the current schema |
| Blocking | Yes (Backlog B-02 adds the column) |

---

## Band B — USEFUL SECONDARY DATA

### B-1 · Real multi-scale SCM / SIG zones for H4

Sampling frame is now the 218 OAPN trails (Contract §F, frozen 2026-08-09), so the relevant path is the **Universe-B operational SCM**, not the Universe-A GEE zone export. `run_scm_operational.py` performs genuine real zonal NDVI extraction (core/near/landscape ring buffers) — but against `spring_raster.tif`/`summer_raster.tif`, the same disqualified 2025-08-10/2026-04-10 pair as `delta_ehs` (`SATELLITE_FIELD_MATCHING_PLAN.md` §1). **Proxy** — zonal NDVI is a spatial contrast, not a causal measure (`SCM_REFRAMING.md`). Current state: real extraction exists but is temporally unusable for H4 as-is; a **fresh** extraction against the campaign-matched composite is needed (Backlog B-14) — no new data source, reuses the composite already required for `satellite_stress`. Needed for **H4 only**. If not completed, **H4 is not tested** — it is *not* tested with the temporally mismatched existing values. (The separate Universe-A GEE zone export path, `src/spatial_causality/zones/<asset_id>.json` via `scripts/gee_scm_zones_pnsg.js`, is now out of scope — it targets the wrong asset universe under F-1.)

### B-2 · Direct visitor counts during the campaign

Source: manual tally by the field team at the plot, during the observation. Spatial unit: the plot. Temporal: the observation window (minutes). **Target** for "people present at this plot at this moment" — and **not a proxy for anything else**. A 30-minute tally does not estimate daily, seasonal or annual use. Its only legitimate use in Paper 1 is as a descriptive covariate showing the sites were in active use. Current state: MISSING; column exists (`visitor_count`), never populated. **Not blocking.** If collected, the manuscript must state the observation duration alongside every count.

### B-3 · Trail-use type and management attributes

Source: OAPN `UsoPublico_visor` + PRUG zonification (already integrated: `prug_zone`, `prug_protection_weight` on all 218 trails). Authority: OAPN. **Target** for management category. Useful as a descriptive covariate and for reporting how the sample spans management zones. Current state: ✅ available.

### B-4 · Weather / antecedent precipitation

Source: AEMET station data near PNSG. Authority: AEMET (Spain). Licence: AEMET OpenData, attribution required. Spatial unit: point station, interpolated at best. Temporal: daily. **Proxy** — station precipitation is not plot-level soil moisture. Needed only to document that the ≥ 48 h no-rain rule for penetrometer readings was met, and to contextualise NDMI. Current state: MISSING for the campaign window. Not blocking.

### B-5 · Independent-sensor NDVI (MODIS / Landsat)

`src/validation/cross_sensor.py` is implemented and tested. MODIS MOD13Q1 is 250 m — far coarser than a trail corridor, and the module says so. Landsat C2 at 30 m is the usable option. **Not blocking**, and arguably a separate study. Excluded from Paper 1 to keep scope contained.

---

## Band C — FUTURE PAPER / PRODUCT (explicitly not blocking Paper 1)

| Dataset | Why deferred |
|---|---|
| **MITMA mobility snapshot** | `etl_mobility.py` and the zone crosswalk exist; `src/mobility/snapshot/` does not. Spatial unit is the **municipality**; it measures **inbound trips**, which is not trail footfall and never becomes trail footfall. Admissible in Paper 1 at most as a one-sentence contextual statement of regional visitation, with the proxy gap named. Recommended: **omit entirely** to avoid inviting the misreading. |
| **SVI longitudinal history** | Needs ≥ 2 dated snapshots; only `2026-06` exists. Socioeconomic vulnerability is not an ecological outcome. Out of scope. |
| **Visitor-pressure time series / forecasting** | `INSUFFICIENT_EVIDENCE` is the correct and current state and **must be preserved**. Paper 1 does not touch it. Forecasting is a different paper requiring a real counter network. |
| **Automated trail counters** | The right long-term instrument for a use–impact study — and the only path to an honest visitor-pressure claim. Infrastructure investment, multi-year. Paper 2 or 3. |
| **Second park (transferability)** | ADR-003 gates multi-park claims on validation. Paper 1 *is* that gate. |
| **Temporal replication (before–after)** | Requires ≥ 2 campaign rounds. Converts association into change detection. Paper 2. |
| **UAV / sub-metre imagery** | The only way to resolve the tread itself (`SPATIAL_MATCHING_PROTOCOL.md` §7). Genuinely exciting follow-up. Not Paper 1. |
| **Institutional multi-user data (ArcGIS Survey123)** | Capture infrastructure, ready but unauthorised for creation and holding zero real observations. Paper 1's data can be collected on paper + CSV. |

---

## Band D — DO NOT FABRICATE

Substitutions that would each, individually, invalidate the paper. Listed because each is *technically easy* and would produce plausible-looking results.

| Never do this | Why |
|---|---|
| Use NDVI / NDMI / EVI / EHS as a **visitor** measurement | Environmental observations are not observations of people. The forecasting lab already states this; it holds for Paper 1 without exception |
| Use `annual_visitors` from `src/territorial/fixtures.py` | **Synthetic** (owner decision Q-01). Authored backwards from a desired tier distribution |
| Use `visitor_capacity_annual` as observed capacity | A static planning range, never a measured limit |
| Use MITMA municipal inbound trips as trail footfall | Wrong spatial unit, wrong quantity, wrong denominator |
| Use α-decay **simulated** SCM zones in any analysis | Simulated evidence cannot support a finding (ADR-004 gating matrix) |
| Impute a missing field measurement from the satellite value | Circular: it would guarantee the correlation the paper is testing |
| Impute a missing satellite value from a neighbouring cell or an adjacent date | Fabricated evidence with a real-looking provenance record |
| Substitute the 2025-08-10 / 2026-04-10 scenes for a campaign-matched acquisition | Chronologically inverted, cross-year, cross-sensor |
| Fill a blank field cell with 0 | 0 is a measurement (zero cover, zero erosion). Blank is absence. `io.py` already gets this right — keep it right |
| Reuse pilot plots in the main sample after changing the protocol | Different measurement processes silently pooled |
| Report `budget_eur` as an empirical restoration cost | A derived planning estimate; PR #127 already caught a 7× drift in a figure of this kind |
| Promote any `simulated` / `synthetic` / `estimated` value to `observed` | The project's founding non-negotiable |

---

## Critical path

```
✅ Owner: sampling frame resolved (Contract §F → F-1, 218 OAPN trails, 2026-08-09)
        ↓
A-4 strata derived from OAPN vegetation + DEM        ← desk, days
        ↓
Site selection stratified by stratum × EHS tercile   ← desk, days
        ↓
A-3 ✅ + plot centroids snapped to 20 m grid (B-04)  ← desk, days
        ↓
🔲 PNSG research authorisation                        ← WEEKS. Start now.
        ↓
A-2 acquisition window defined and manifest committed ← desk, days
        ↓
A-1 PILOT (1–2 days)  ────►  σ, effect range, timing
        ↓
Sample size frozen; SAP frozen; Contract amended
        ↓
A-1 MAIN CAMPAIGN  ──►  A-5 GPS  ──►  QA  ──►  frozen CSV
        ↓
A-2 extraction at plot cells
        ↓
Locked statistical analysis
```

**The two long-lead items are the research authorisation and the seasonal acquisition window.** Both are calendar-bound, neither is under the project's control, and both should be started before any code is written. Everything else on this path is desk work measured in days.

## Open items requiring owner input

| # | Item |
|---|---|
| ✅ | ~~Sampling frame~~ — **resolved 2026-08-09: F-1, 218 OAPN trails** (Contract §F) |
| 🔲 1 | **OAPN data licence terms** — confirm and record the exact reuse conditions for A-3 and A-4 |
| 🔲 2 | **PNSG research authorisation** — drafting started (`PNSG_RESEARCH_AUTHORIZATION_REQUEST.md`); territorial scope resolved (Madrid-only, 2026-08-09); blocked on applicant identity fields and the go-ahead to file |
| 🔲 3 | **Field team composition** — two observers are required for the repeatability protocol |
| ~~4~~ | ~~Target field season~~ — **resolved 2026-08-09: summer 2027 (~20 Jun – 31 Jul), 2028 fallback** (`SATELLITE_FIELD_MATCHING_PLAN.md` §2) |
| 🔲 5 | **Instrument availability** — penetrometer model, gridded quadrat frame, GNSS |
