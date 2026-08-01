# Map Inventory

Four map/geospatial visualizations exist in the product. Three render in the
dashboard (all inside one tab, *Diagnosticar → Diagnóstico espacial*); one is an
export. There are no other `st.pydeck_chart` / `st.map` / Folium call sites
(`grep` over `src/` returns only `tab_diagnostic.py:173` and `:353`).

Common to all rendered maps: **basemap** = CARTO `dark-matter-gl-style` over
WebGL/Deck.gl; **CRS** = EPSG:4326 (WGS-84) throughout, with **no reprojection
anywhere** — the Pipeline A GeoJSON is already WGS-84 and the GeoPackage export
sets `crs="EPSG:4326"` explicitly (`gis_export.py:161`). No CRS bug found.

---

## M-01 · Territorial asset map — "Vista de Gestión (Tiers)"

| Field | Value |
|---|---|
| Code | `src/platform/map_layers.py::build_pydeck_deck` (426-522); rendered `src/ui/tabs/tab_diagnostic.py:172-173` |
| Layers | 1 × `GeoJsonLayer` (LineString for TRAIL/CYCLING_ROUTE, Point otherwise) |
| Source data | 8 PNSG assets from `src/territorial/fixtures.py::build_pnsg_territory()`, ranked by `territorial/tpi.rank_assets` |
| Geometry | **Real trace where the asset matches a Pipeline A trail** (`calibration.asset_trail_geometries`); otherwise **synthesised**: municipality centroid from a 13-entry hard-coded table (`map_layers.py:49-65`) + hash jitter (`_jitter`, ±~350 m) + a sinusoidal pseudo-trail polyline (`_trail_path`, 11 vertices, amplitude 10–18 % of length) |
| Spatial resolution | Not applicable to the synthetic features; the colour they carry derives (where overridden) from Sentinel-2 10–20 m bands aggregated over a 50 m trail buffer |
| Temporal resolution | Two scenes (2025-08-10, 2026-04-10) where satellite-derived; otherwise the fixture is undated |
| CRS | EPSG:4326, no reprojection |
| Analytical transformation | `tier` from TPI classification → indigo→slate 4-step palette (`TIER_COLORS`) |
| Legend / units | Sidebar + in-tab: "TIER I–IV, prioridad de inversión". Deliberately **non-traffic-light** — a good, explicit design decision (`map_layers.py:76-78`) |
| Management question | "Where should investment be prioritised?" |
| Evidence status | **MIXED** — attribute colour is CALIBRATED (fixture TPI), geometry is REAL for the matched subset and **SYNTHETIC** for the rest |
| Uncertainty communication | Per-feature tooltip carries `geom_note` ("≈ Posición aproximada (centroide municipal)" vs "📍 Traza cartográfica real"); a caption states the real/approx split (`tab_diagnostic.py:157-162`, `:240-244`) |
| Classification | **Operational-looking, partly illustrative. Candidate for redesign, not removal.** |

### Flags

- 🔴 **Non-reproducible geometry.** `_jitter`, `_heading_from_id` and
  `_trail_path` all key on Python's built-in `hash()` of a string, which is
  **salted per process** (PYTHONHASHSEED is unset; verified — two interpreter
  runs returned `-7366547649286595343` and `1041257594381499767` for the same
  `asset_id`). The docstrings claim the opposite: *"the same asset always
  appears at the same location across page reloads"* (`map_layers.py:135`) and
  *"deterministic curved path (same trace on every reload)"* (`map_layers.py:183`).
  Within one Streamlit process this holds; **across restarts, redeploys or
  replicas the synthetic assets move.** Two users can see the same asset in two
  places.
- 🟠 **Fabricated shape realism.** `_trail_path` deliberately generates
  switchback-like curves because *"a straight 2-point segment misleads the
  territorial analyst"* (`map_layers.py:184-186`). The remedy increases apparent
  cartographic fidelity of a feature that has none. The tooltip disclaimer is
  correct but is one hover away from a shape that reads as surveyed.
- 🟠 **Stale default view state.** `_MAP_LATITUDE/_MAP_LONGITUDE/_MAP_ZOOM`
  default to Sierra del Rincón (41.130, −3.490), the **archived** territory
  (`map_layers.py:70-73`). Live calls pass PNSG explicitly, so no user-visible
  bug — but any new caller that omits the centre lands on the wrong park.
- 🟡 **Centroid table covers 13 municipalities only**; anything else falls back
  to `_DEFAULT_CENTROID`, again Sierra del Rincón.

---

## M-02 · Territorial asset map — "Vista de Diagnóstico Espectral (NDVI/NDMI)"

| Field | Value |
|---|---|
| Code | `src/platform/map_layers.py::build_pydeck_deck_spectral` (689-783) + `_assets_to_geojson_spectral` (662) |
| Layers | 1 × `GeoJsonLayer`, identical geometry to M-01 |
| Source data | Same 8 fixture assets |
| Geometry | **Identical to M-01** — same real/synthetic mix |
| Analytical transformation | `asset.ehs` → continuous RdYlGn ramp (`_SPECTRAL_RAMP`, ColorBrewer 5-class, 6 anchors) |
| Legend / units | In-tab 6-band legend, EHS 0–100 |
| Management question | "Which assets are in worst ecological condition?" |
| Evidence status | **MIXED**, skewed CALIBRATED — EHS is the fixture literal unless the conservative satellite override fired |
| Uncertainty communication | Same `geom_note` tooltip; caption explains the ramp |
| Classification | **Misleading in its current labelling. Candidate for redesign.** |

### Flags

- 🔴 **Overstates spectral provenance.** The tooltip states
  *"Color = gradiente espectral NDVI/NDMI"* (`map_layers.py:733`) and the tab
  caption says the view *"Reproduce el contraste espectral NDVI/NDMI a lo largo
  del corredor del sendero"* (`tab_diagnostic.py:144`). For any asset whose EHS
  was **not** overridden by the satellite, the colour encodes a hand-written
  constant, not a spectral measurement. The module's own docstring is more
  honest — *"simulating the NDVI/NDMI spectral signature"* (`map_layers.py:666`)
  — and the UI drops the word "simulating".
- 🔴 **Pixel-level implication.** Colouring a synthetic 11-vertex polyline with a
  continuous spectral ramp implies a per-metre reading along a corridor that does
  not exist on the ground.
- 🟠 **Duplicates M-01.** Identical geometry, identical layer configuration, one
  attribute swap. Two maps, one dataset, one tab.
- 🟠 **Inconsistent band labels versus M-03**: here `EHS 75-85 Bueno / >85
  Óptimo` (`tab_diagnostic.py:189-190`), there `≥75 Saludable`
  (`tab_diagnostic.py:359`). Same underlying ramp anchors.

---

## M-03 · Real-trail map (Pipeline A)

| Field | Value |
|---|---|
| Code | `src/platform/map_layers.py::build_real_trails_deck` (527-620); GeoJSON built by `src/platform/real_trails.py::build_real_trails_geojson`; rendered `tab_diagnostic.py:347-353` |
| Layers | 2 — park boundary (`get_park_boundary`, OAPN official limit) beneath; 218 real trail LineStrings above |
| Source data | `data/outputs/pnsg/pipeline_a_results.geojson` (**tracked in git**) + `data/raw_assets/vector_data/oapn/oapn_limite_pn.geojson` |
| Geometry | **Real OAPN / OSM cartography.** No synthesis. |
| Spatial resolution | Sentinel-2 10 m (B04/B08) and 20 m (B11), zonally aggregated over a 50 m trail buffer; scene percentiles P90/P10 as the healthy/degraded anchors |
| Temporal resolution | **2 scenes**: S2A 2025-08-10 ("verano") and S2B 2026-04-10 ("primavera") |
| CRS | EPSG:4326 |
| Analytical transformation | stress → health (`metrics.semantics.stress_to_health`, health = 100 − stress) → RdYlGn ramp (`real_trails._health_to_rgba`) |
| Legend / units | In-tab 6-band EHS legend + "Sin dato" grey; tooltip carries EHS verano, ΔEHS, SCM cause, PRUG zone, budget |
| Management question | "Which real trails are degrading, and where, weighted by protection level?" |
| Evidence status | **REAL** |
| Uncertainty communication | Strongest in the product: evidence badge, scene dates, trend-gate statement ("Mann-Kendall NO aplicable"), coverage fraction, and a view-modulated confidence caveat ("señal de alerta temprana, no veredicto de intervención formal") |
| Classification | **Operational and analytical. Retain and promote.** |

### Flags

- 🔴 **Temporal comparability of ΔEHS is not stated.** The "seasonal" delta is
  `health_spring − health_summer` where spring = **April 2026** and summer =
  **August 2025**. The two scenes are 8 months apart, span **two calendar
  years**, and are ordered opposite to the "spring → summer deterioration"
  narrative used throughout the UI (`tab_diagnostic.py:102-103`, the
  `n_degrading` KPI help text, `prug_monitoring`). Nothing in the UI discloses
  the acquisition years.
- 🔴 **Cross-sensor comparison is not controlled.** S2**A** vs S2**B** are
  different instruments. The repository owns `src/validation/cross_sensor.py`;
  the Pipeline A ΔEHS path does not use it.
- 🟠 **No climatic control.** A spring-vs-summer vegetation-index difference in
  a Mediterranean mountain system is dominated by phenology and interannual
  precipitation. The SCM tries to separate landscape from localized forcing —
  and in fact classifies **165 of 218 trails as LANDSCAPE_DRIVEN** — but the map
  colour itself carries no climatic normalisation.
- 🟡 **Legend caption slightly overstates.** *"Color = NDVI/NDMI real del píxel
  sobre el buffer de 50 m"* (`tab_diagnostic.py:373`) — the colour encodes a
  derived composite index anchored on scene percentiles, not a pixel value.
- 🟢 The layer *"NO usa datos curados"* claim (`tab_diagnostic.py:250`) is
  **accurate and verified**.

---

## M-04 · GIS export layer (GeoJSON / GeoPackage)

| Field | Value |
|---|---|
| Code | `src/reporting/gis_export.py`; UI `tab_reports.py:139-183`; CLI `scripts/export_gis.py` |
| Layers | 1 (`snto_assets`) |
| Source data | `clean_assets/pnsg_assets.geojson` (official OAPN geometry) joined to `mk_trends_pnsg.json` |
| Geometry | Real, preserved verbatim |
| Temporal resolution | Multi-year GEE series (2021–2026) — a **different** record from M-03's two rasters |
| CRS | EPSG:4326, declared explicitly on GeoPackage write |
| Attributes | `has_trend`, `tau`, `p_value`, `trend_significant`, `is_degrading`, `sens_slope` + 95 % CI, `n_observations`, `ehs`, `evidence_level`, `provenance`, `park` |
| Management question | "Give me SNTO's conclusions inside QGIS/ArcGIS" |
| Evidence status | **REAL**, and the tier travels with the data |
| Uncertainty communication | Per-feature `evidence_level` + `provenance` string; missing trends become explicit nulls with `has_trend=false`, never fabricated |
| Classification | **Operational. Retain.** This is the correct ADR-008 integration posture. |

### Flags

- 🟡 **Fragile default.** `build_feature_collection(..., evidence_level=DataStatus.REAL)`
  defaults to REAL (`gis_export.py:84`). Correct for today's single caller, but
  a future caller that forgets the argument silently stamps "real" on whatever
  it exports. A required argument would be safer.

---

## Cross-cutting map findings

### Does any map imply Sentinel-2 measures tourists or visitor pressure?

**No map layer does directly.** No heatmap of visitors exists anywhere; there is
no visitor-density surface. This is a genuine strength.

However, **M-03's tooltip carries `Causa: {scm}`**, which renders
*"Impacto localizado (uso del sendero)"* — a causal attribution to trail use,
displayed on a Sentinel-2-coloured line. For the 24 trails so classified, that
attribution rests on the α-decay **simulation** (`src/spatial_causality/zones/`
does not exist), not on observed multi-scale zones. The map presents a simulated
causal inference beside real measurements with no visual distinction between the
two. **This is the map-level expression of the product's highest-risk claim**
(see `SCIENTIFIC_CLAIMS_REGISTER.md` C-01).

### Heatmaps without traceable evidence

None. No `HeatmapLayer`, `HexagonLayer`, or kernel-density surface exists.

### Simulated or fallback data presented as observed

- M-02's *"gradiente espectral NDVI/NDMI"* tooltip over calibrated EHS — **yes**.
- M-01/M-02 synthetic geometry — disclosed in tooltip, **but only in tooltip**.
- M-03's SCM cause label over simulated zones — **yes**, undisclosed at the map.

### Duplication

M-01 and M-02 are the same map twice. M-01/M-02 and M-03 answer overlapping
questions ("where is degradation?") over two different asset universes in the
same tab.

### Maps that do not support a clear user decision

M-02 (spectral view) has no decision attached that M-03 does not serve better
with real geometry and real spectra. It is the strongest candidate for
consolidation — see `REMOVAL_CANDIDATES.md` R-02.
