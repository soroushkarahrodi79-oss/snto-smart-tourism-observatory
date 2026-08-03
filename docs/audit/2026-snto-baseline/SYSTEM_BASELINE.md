# System Baseline

## 1. Identity and state

| Property | Value | Evidence |
|---|---|---|
| Name | Smart Natural Tourism Observatory (SNTO) | `CLAUDE.md`, `README.md` |
| Active case study | Parque Nacional Sierra de Guadarrama (PNSG) | `src/ui/layout.py:336` (`_VISIBLE_TERRITORIES = ["pnsg"]`) |
| Archived pilot | Reserva de la Biosfera Sierra del Rincón (SNR) | code + fixtures retained, hidden from selector |
| Runtime | Python 3.12, Streamlit | `pyproject.toml:8`, `requirements.txt:31` |
| Version marker | `2.1.0.dev0` | `pyproject.toml:7` |
| Last stable tag | `v2.0.0` | `CLAUDE.md` |
| Branch audited | `audit/2026-baseline-phase0` from `docs/v3-status-sync-rebuild` @ `ed25d0a` | `git log` |
| Published via | [PR #143](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/pull/143) on `audit/2026-baseline-phase0-pr`, a clean branch cut from `main` and rebased onto `main` after publication began — a different commit SHA than `ed25d0a`, same document content. The audit itself was performed once, at `ed25d0a`; it was not re-run against the rebased commit. | `gh pr view 143` |
| Test result | 1083 passed, 1 failed, 8 skipped | local run, see `TEST_BASELINE.md` |
| Coverage | 84 % of `src` (gate: 80 %) | `pytest --cov=src`, `.github/workflows/ci.yml:90` |

## 2. What actually runs

### 2.1 The deployed surface

**One** deployed artifact: the Streamlit dashboard (`app.py`) in an Azure
Container App, consuming persistence **in-process** via `src/ui/services/`.

**Not deployed:** the FastAPI `/api/v2` HTTP surface. This is a deliberate,
documented decision (ADR-012), not an omission. Consequence for the
modernization: the mobile client's `MobileHttpRepository` (ADR-014) and the
published OpenAPI contract (`docs/api/openapi.json`) describe an interface with
**no live endpoint**.

**Database:** Azure Postgres `snto-db` since the 2026-07-18 cutover. The v3.0
PostGIS migration `b2c3d4e5f6a7` is merged in code but **not applied to
production**; `managed_assets.geom` therefore does not exist in the production
schema, nothing populates `managed_assets` from `src/`, and no UI/API/report
consumer calls the spatial queries. The PostGIS work is currently inert
infrastructure.

### 2.2 The two pipelines, and why this matters most

The handoff document describes "Pipeline A" (real geospatial) and "Pipeline B"
(territorial intelligence demo). **That split is still live, and it is the
central structural fact of the system.**

| | Pipeline A (**real geospatial/spectral core, mixed derived outputs**) | Pipeline B (curated/demo — **SYNTHETIC**, Q-01) |
|---|---|---|
| Unit of analysis | 218 real OAPN trails | 8 hand-written PNSG assets |
| Source | `data/outputs/pnsg/pipeline_a_results.geojson` (tracked in git) | `src/territorial/fixtures.py:427` `build_pnsg_territory()` |
| Geometry | true OAPN cartography — **real** | municipality centroid + hash jitter, unless matched to a real trail — **synthetic** |
| EHS | computed from Sentinel-2 NDVI/NDMI percentiles — **real-derived** | hard-coded literal (e.g. `ehs=35.0`) — **synthetic** |
| SCM | **SIMULATED** (α-decay fallback; `zones/` absent) | hard-coded literal (`scm_confidence="HIGH"`) — **synthetic** |
| DCS / trend | not computed on this path | hard-coded literal (`dcs=79.0`, `mk_p_value=0.006`) — **synthetic** |
| Budget | **derived / modelled**, not observed | derived from synthetic inputs |
| Where it surfaces | lower half of *Diagnosticar → Diagnóstico espacial*; PRUG report; GIS export | **the entire Decidir layer**: 10 KPIs, tiers, budget, alerts, simulator, socio-economic |

**Pipeline A is not uniformly real.** Its geospatial and spectral core is
genuinely real-derived; its causal attribution is simulated and its budget is
modelled. Describing the whole pipeline as "the real one" — as the handoff
document and parts of the UI do — overstates two of its four output families.

The bridge between them is `src/platform/enrichment.py::enrich_assets_with_satellite`,
a deliberately **one-directional, conservative override**: real satellite EHS
replaces the curated EHS *only* when the satellite reads *more degraded*
(`flag == "mas_degradado"`), never when it reads healthier. The reasoning
(granite/quartzite summits have low NDVI from geology, not trampling) is sound
and documented. The consequence is not: the headline decision layer is
predominantly curated judgement, upgraded in a minority of cases, and the
proportion is only visible in a caption.

**Outputs of the Pipeline A layer, by component evidence class**
(`data/outputs/pnsg/pipeline_a_summary.json`, converted to health convention by
`real_trails._summary_to_health`). These are **not uniformly measurements** —
the block below was originally headed "Measured reality of the real layer,"
which incorrectly placed a simulated distribution and a modelled budget under a
measurement heading:

| Component | Value | Evidence class |
|---|---|---|
| Trails and geometry | 218 trails, 1 035.1 km | **Real cartography** (official OAPN) |
| Health at the second scene | mean **88.5 / 100** (range 28.0 – 100.0) | **Real-derived** from Sentinel-2 |
| Two-date health difference | mean **+5.2** points; 46 trails negative | **Real-derived, but temporally non-comparable** — the Aug-2025/Apr-2026 pair spans two years and two sensors, so this is *not* interpretable as seasonal, longitudinal, deterioration or recovery (Q-03) |
| SCM distribution | 165 landscape-driven, 29 mixed, 24 localized | **SIMULATED** — a property of the α-decay fallback, not a measured finding about the park (`src/spatial_causality/zones/` absent) |
| Indicative budget | € 1 435 721 | **Derived / modelled**, not observed — `length × cost/m × EHS × SCM factor`, and its SCM factor inherits the simulation above |

The curated portfolio, by contrast, is authored to a target tier distribution:
"*Distribución de tiers calibrada contra el motor TPI*", "*Activadores
garantizados*" (`src/territorial/fixtures.py:24-33`).

**Correction — these two means are not directly comparable, and their gap is
not evidence of a factual disagreement.** The fixture-portfolio mean (≈ 55
across the 8 curated assets, `KPI_INVENTORY.md` K-08) and the real-trail mean
above differ on every axis that would make a comparison valid: unit of
analysis (8 curated assets vs. 218 real trails), formula (the multi-year
5-component composite risk model vs. the 2-scene percentile-deficit model,
`KPI_INVENTORY.md` K-01), and temporal record. The correct statement is: **two
non-equivalent metrics share the same EHS name and scale, creating semantic
incompatibility in the product** — not "the datasets disagree," which implies
two comparable measurements of the same thing producing different answers.

## 3. Satellite evidence depth — the hard constraint

Probed, not assumed (`src/platform/provenance.py::detect_scene_dates('pnsg')`):

```
scene_dates(pnsg) = ['2025-08-10', '2026-04-10']
n_scenes = 2 | mann_kendall_justified = False
```

The two Sentinel-2 L2A products under `data/raw_assets/raster_data/PNSG/` are:

- `S2A_MSIL2A_20250810T110701_..._T30TVL_...` — labelled *summer*
- `S2B_MSIL2A_20260410T110619_..._T30TVL_...` — labelled *spring*

Three consequences the system does not currently state:

1. The "seasonal ΔEHS" compares **April 2026 against August 2025** — 8 months
   apart, in the wrong chronological order relative to the "spring → summer"
   framing, and **across two different calendar years**.
2. It compares **two different satellites** (S2A vs S2B). The repository already
   owns cross-sensor tooling (`src/validation/cross_sensor.py`) but the
   Pipeline A ΔEHS path does not use it.
3. The trend gate correctly refuses Mann-Kendall on 2 scenes and the UI says so.
   That gate works.

**Owner decision (Q-03):** this scene pair cannot support any seasonal, trend,
recovery, deterioration, or causal claim. The only defensible description of
the resulting figure is a **mean two-date health difference under the current
sign convention** — every UI and report surface presenting it should say so,
with both dates and both sensor IDs on screen, and drop the spring/summer
framing entirely until same-year, same-sensor paired scenes exist.

Separately, the multi-year Mann-Kendall series shown in *Evidencia satelital*
comes from a **different** source — a GEE Code Editor export under
`clean_assets/timeseries/` — not from these two rasters.
`data/outputs/pnsg/run_context.json` records the time-series pipeline last ran
with `"mode": "dry-run"` and `"git_dirty": true`.

## 4. The three un-ingested real-data feeds

Probed via `src/reporting/cets_readiness.py::resolve_signals('pnsg')`:

```
{'satellite_real': True, 'mobility_real': False, 'socioeconomic_series': False,
 'field_measured_plots': 0, 'scm_real_zones': 0}
```

| Feed | Gate | Directory | State |
|---|---|---|---|
| MITMA mobility | `mobility_snapshot_exists()` | `src/mobility/snapshot/` | **does not exist** — capacity falls back to the curated proxy |
| SCM real zones | `real_zones_exist()` | `src/spatial_causality/zones/` | **does not exist** — α-decay simulation is what runs |
| SVI time series | `svi_history_available()` | `src/socioeconomic/snapshot/history/` | **does not exist** — only one dated snapshot ships |
| Field validation (#26) | measured columns non-empty | `clean_assets/field_validation/pnsg_field_observations_template.csv` | **all measurement columns empty** (4 plot rows, no readings) |

Each gate degrades honestly to a labelled fallback. **The gates are correct
engineering.** What is missing is the data, and consequently *no satellite↔field
validation exists*.

## 5. Positioning versus implementation

The strategic material (`MASTER_STRATEGIC_INDEX.md`, `docs/reviews/2026/`) is
consistent and states the correct posture: narrow to protected-area decision
intelligence, validate before claiming, integrate with GIS rather than replace
it, never blur evidence classes. Scores recorded there: overall 61/100, software
quality 42/100, enterprise readiness 28/100.

The implementation partly honours this and partly does not:

- **Honoured:** the canonical evidence vocabulary and gating matrix
  (`src/platform/evidence.py`); the forecast evidence guard that makes
  `EvidenceClass.REAL` unconstructible on a projection
  (`src/forecasting/projection.py:104`); GIS export rather than GIS replacement;
  LAC/ROS labelled as planning estimates; CETS/PRUG reports resolved from live
  repository probes.
- **Not honoured:** the KPI narrative layer (`src/platform/dashboard.py`), which
  emits confident causal and quantitative statements about visitor damage and
  visitor numbers from curated constants; the synthetic map geometry; and the
  fixture docstring that calls hand-authored demo assets "activos reales".

## 6. Known bottlenecks

1. **Fixture-rooted decision layer** — the highest-leverage architectural issue
   (§2.2).
2. **`hash()`-derived synthetic geometry** — non-reproducible across processes
   (see `MAP_INVENTORY.md` M-01).
3. **Global cache keyed only on territory** — `@st.cache_data load_dashboard`
   (`src/ui/layout.py:341`) plus a hard-coded `REPORT_DATE = "2026-06-12"`
   (`src/ui/layout.py:306`) means "fecha de informe" is a constant, not a
   computed data date.
4. **60-second autorefresh over a static dataset** — `st_autorefresh(60_000)`
   (`app.py:180`) with a "live" pulsing indicator, over data that changes only
   when a pipeline is re-run offline.
5. **Test-order-dependent failure** from `load_dotenv()` at import in root
   scripts (see `TEST_BASELINE.md`).
6. **Root-directory sprawl** — 25 `.py` scripts at repository root mixing ETL,
   report runners, and one-off utilities, with no package boundary.
