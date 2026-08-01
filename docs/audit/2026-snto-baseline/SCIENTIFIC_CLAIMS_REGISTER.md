# Scientific Claims Register

Claims extracted from UI strings, docstrings, comments, report generators,
tooltips, legends and variable names. Classification:

- **Supported** — the implementation and data back the claim as stated.
- **Plausible but unvalidated** — methodologically reasonable, no empirical validation.
- **Proxy-based** — the claim describes a proxy as if it were the target quantity.
- **Overstated** — stronger than the evidence, but directionally defensible.
- **Misleading** — a reader would form a materially false belief.
- **Contradicted by implementation** — the code does not do what the text says.
- **Needs external evidence review** — requires literature/expert review beyond Phase 0 scope.

No internet literature review was performed. Only what the repository claims and
what it cites was audited.

---

## Tier 1 — Highest risk

### C-01 · "Sites experiencing measurable environmental damage **caused by visitor pressure**" / "**confirmed** visitor-driven environmental damage"

- **Where:** `src/platform/dashboard.py:392-402` (KPI 7 "Human Pressure Alerts"), rendered in *Decidir → Panorama ejecutivo*.
- **Backing:** `scm_classification == "LOCALIZED_IMPACT"` — a hard-coded fixture string on the live path; and where computed, an α-decay **simulation** (`src/spatial_causality/zones/` does not exist, `scm_real_zones == 0`).
- **What is actually measured:** nothing about visitors. No counter, no MITMA snapshot, no field observation exists in the system.
- **Consequence:** the KPI recommends *"seasonal closures"* and *"visitor quotas or guided-only access"*.
- **Classification: MISLEADING.** The words "measurable" and "confirmed" are unsupported at every link in the chain.

### C-02 · "No sites are currently flagged for visitor-driven damage. Environmental changes appear to be **driven by natural climate variability**."

- **Where:** `src/platform/dashboard.py:406-409` (KPI 7, GREEN branch).
- **Backing:** the *absence* of a LOCALIZED_IMPACT classification among Tier 1/2 assets.
- **Classification: MISLEADING.** Absence of a simulated localized signal is asserted as positive evidence of climatic causation. This is an argument from ignorance presented to a director.

### C-03 · "Significant inter-annual variability (**driven by the 2022 drought**)"

- **Where:** `src/decision_confidence/assessor.py:467-471`, emitted whenever `model_stability < 8`.
- **Backing:** none. The sentence is a literal, independent of the asset, the years covered, or whether 2022 is in the series at all.
- **Classification: CONTRADICTED BY IMPLEMENTATION.** A fabricated causal attribution presented as a data-derived uncertainty factor. This is a one-line fix and should be Phase 1 work.

### C-04 · "20 activos **reales** de la Reserva de la Biosfera Sierra del Rincón"

- **Where:** `src/territorial/fixtures.py:20`; the PNSG twin at `:429` says "8 activos representativos".
- **Backing:** the same docstrings state *"Distribución de tiers calibrada contra el motor TPI"* and annotate each asset with the TPI arithmetic that produces its target tier (`# TPI ≈ 95 | CU=40(CRITICAL) + ES=20.5 …`, `# Activadores garantizados`).
- **Classification: CONTRADICTED BY IMPLEMENTATION.** The numeric fields are authored backwards from a desired output distribution. Calling them "reales" is precisely the blurring ADR-004 forbids, inside the module that feeds every headline KPI.

### C-05 · "Color = gradiente espectral **NDVI/NDMI**"

- **Where:** map tooltip `src/platform/map_layers.py:733`; tab caption `src/ui/tabs/tab_diagnostic.py:144` ("Reproduce el contraste espectral NDVI/NDMI a lo largo del corredor del sendero").
- **Backing:** the colour encodes `asset.ehs`, which for non-overridden fixture assets is a hand-written constant. The module's own docstring says "**simulating** the NDVI/NDMI spectral signature" (`map_layers.py:666`) — the UI drops "simulating".
- **Classification: MISLEADING.** Presents a calibrated constant as a spectral measurement, along a synthetic corridor.

---

## Tier 2 — Substantive risk

### C-06 · "the same asset always appears at the same location across page reloads" / "deterministic curved path (same trace on every reload, keyed on asset_id)"

- **Where:** `src/platform/map_layers.py:135-137`, `:183-186`.
- **Backing:** `hash()` on a `str` is salted per interpreter process (verified: two runs gave different values for the same `asset_id`; `PYTHONHASHSEED` is unset in `Dockerfile` and the deploy workflow).
- **Classification: CONTRADICTED BY IMPLEMENTATION.** True within one Streamlit process; false across restarts, redeploys and replicas.

### C-07 · Trail geometry realism — "a straight 2-point segment misleads the territorial analyst" therefore generate switchbacks

- **Where:** `src/platform/map_layers.py:177-223`.
- **Classification: MISLEADING (by construction).** The stated remedy for a misleading simplification is to increase apparent cartographic fidelity of a feature that has no survey basis. Disclosed only in a hover tooltip.

### C-08 · "Presión de visitantes **340 % sobre la capacidad de carga** en verano"

- **Where:** `src/territorial/fixtures.py:455-456` (Laguna de Peñalara description), rendered in asset cards and tooltips.
- **Backing:** none in the repository. No carrying-capacity study, no visitor count, no citation.
- **Classification: OVERSTATED / needs external evidence review.** The claim may well be true of Peñalara in the real world; nothing in SNTO establishes it, and it renders as a system output.

### C-09 · "X,XXX **visitors/yr**" (KPI 3, Visitor Capacity at Risk)

- **Where:** `src/platform/dashboard.py:218-252`; narrative *"X annual visitors … are visiting sites in deteriorating condition"*.
- **Backing:** `visitor_capacity_annual`, a fixture constant whose *name* says capacity.
- **Classification: PROXY-BASED, mislabelled.** A capacity estimate is rendered with the unit and grammar of a measured visitor count.

### C-10 · TIS as euro efficiency — "every euro invested delivers strong territorial benefit", "EXCELLENT EFFICIENCY"

- **Where:** `src/platform/dashboard.py:428-436` (KPI 8); model in `src/intervention/impact.py`.
- **Backing:** modelled intervention effects with uncited coefficients, notably "excellent assets attract **25 % more** visitors with promotion" (`impact.py:252`).
- **Classification: OVERSTATED.** A benefit-per-euro verdict derived from unsourced elasticity constants.

### C-11 · `capacity_at_standard` — the visitor quota implied by a linear EHS model

- **Where:** `src/platform/lac_ros.py:107-137`.
- **Backing:** `P_std = P·(100 − standard)/(100 − EHS)`, i.e. **all** EHS deficit below 100 is attributed to visitor pressure.
- **Tension:** the SCM classifies **165 of 218** real trails as LANDSCAPE_DRIVEN, and the enrichment module explicitly warns that low NDVI on quartzite summits is geology, not tourism.
- **Classification: OVERSTATED.** The docstring's "planning estimate, not a fitted dose-response" caveat is honest about *precision* but not about the embedded *causal* assumption.

### C-12 · "ΔEHS negativo = deterioro estival" / "Sendas en deterioro"

- **Where:** `src/ui/tabs/tab_diagnostic.py:102-103`, `:332-334`; `prug_monitoring`.
- **Backing:** two scenes, **2025-08-10** and **2026-04-10** — 8 months apart, two calendar years, **two different satellites** (S2A/S2B), in the reverse of the implied spring→summer order.
- **Classification: OVERSTATED / needs methodological review.** A defensible two-date difference is framed as a within-season deterioration signal, with no acquisition dates on screen and no cross-sensor control (despite `src/validation/cross_sensor.py` existing).

### C-13 · "🛰️ Dato satelital real. Observación directa Sentinel-2 L2A."

- **Where:** `src/platform/provenance.py:59-62`, rendered on the evidence card.
- **Backing:** `snapshot_provenance` sets `status=DataStatus.REAL` **unconditionally** and falls back to `n_scenes = 2` when no `.SAFE` products are found (`provenance.py:129,153`).
- **Classification: CONTRADICTED BY IMPLEMENTATION** in the fallback case — on any environment without the git-ignored rasters, the badge asserts direct observation that cannot be verified.

### C-14 · The "live" affordance

- **Where:** `app.py:180` `st_autorefresh(interval=60_000)`; `src/ui/layout.py:141-146` pulsing green dot CSS; `render_widgets._render_live_alerts` refresh timestamp; comment *"simula polling de datos en vivo"*.
- **Backing:** the underlying data changes only when an offline pipeline is re-run manually.
- **Classification: MISLEADING.** The code comment is honest ("simula"); the interface is not. A 60-second refresh with a pulsing indicator asserts a live feed.

---

## Tier 3 — Lower risk, worth correcting

### C-15 · "Fecha de informe: 2026-06-12"

- **Where:** `src/ui/layout.py:306` `REPORT_DATE`, surfaced in the sidebar, the executive brief filename, the CETS and PRUG reports.
- **Classification: MISLEADING (minor).** A hard-coded literal presented as the report's data date. It also does not match either satellite acquisition date.

### C-16 · "Sin datos sintéticos" (real-trails section)

- **Where:** `src/ui/tabs/tab_diagnostic.py:440`.
- **Backing:** the geometry, EHS and ΔEHS are real. But the `Causa (SCM)` column in the same table, and the tooltip `Causa:` field, come from the α-decay **simulation**.
- **Classification: OVERSTATED.** Accurate for most columns; one column contradicts it.

### C-17 · "Corazón científico del observatorio" (the territorial map)

- **Where:** `src/ui/tabs/tab_diagnostic.py:50-53`.
- **Classification: OVERSTATED.** Applied to a tab whose upper map is fixture-driven with partly synthetic geometry; the real evidence is below the fold.

### C-18 · Evidence-class gating matrix

- **Where:** `src/platform/evidence.py:73-110`.
- **Classification: SUPPORTED.** REAL supports all four decision uses; CALIBRATED supports only monitoring/prioritisation; SIMULATED and SYNTHETIC support **nothing**. Conservative, documented as a proposed policy open to owner review, and consistent with ADR-004.

### C-19 · Forecast evidence guard

- **Where:** `src/forecasting/projection.py:101-108` — `Forecast.__post_init__` raises if `evidence_class is REAL`.
- **Classification: SUPPORTED.** The claim "a projection can back no decision" is enforced in code and pinned by a test. Best-practice example in the repository.

### C-20 · Human-pressure proxy self-critique

- **Where:** `src/risk_engine/human_pressure.py:6-94`.
- **Classification: SUPPORTED.** States why the previous NDVI-volatility proxy was invalid, lists five limitations including "does not capture seasonality" and "visitor counts should be used instead where available", and cites its sources.

### C-21 · Dense-canopy NDVI saturation handling

- **Where:** `src/risk_engine/ehs.py:56-72`, threshold 0.80 cited to Myneni et al. 1995.
- **Classification: PLAUSIBLE BUT UNVALIDATED / needs external evidence review.** The mechanism is standard; the specific 0.80 cut and the 0.10 weight shift are not validated for Guadarrama.

### C-22 · SCM scientific basis

- **Where:** `src/spatial_causality/analyzer.py:12-31`, citing Marion & Leung 2001, Pickering et al. 2011, Sims et al. 2014.
- **Classification: PLAUSIBLE BUT UNVALIDATED.** The *principle* (climate acts uniformly, trampling produces a spatial gradient) is sound and properly cited. What is unvalidated is (a) the decision thresholds 0.07/0.15/0.85/0.70, which carry no citation, and (b) the simulation standing in for observed zones.

### C-23 · CETS readiness and PRUG monitoring framing

- **Where:** `src/reporting/cets_readiness.py`, `src/reporting/prug_monitoring.py`, `tab_reports.py:206-212`, `:288-293`.
- **Classification: SUPPORTED.** Explicitly "not a candidacy dossier", "does not accredit compliance", "early warning, not a plan-compliance verdict", with a live warning that #26 has not run. The separation of *Coverage* (editorial) from *DataStatus* (computed) is the correct pattern.

### C-24 · "SNTO should not replace ArcGIS / GEE / Sentinel Hub / Tableau"

- **Where:** `CLAUDE.md`, `docs/decisions/ADR-008.md`, the About menu (`src/ui/layout.py:32-34`).
- **Classification: SUPPORTED.** The GIS export (M-04) and the published OpenAPI contract are the correct expression of this posture.

---

## Claims by classification

| Classification | IDs |
|---|---|
| Supported | C-18, C-19, C-20, C-23, C-24 |
| Plausible but unvalidated | C-21, C-22 |
| Proxy-based | C-09 |
| Overstated | C-08, C-10, C-11, C-12, C-16, C-17 |
| Misleading | C-01, C-02, C-05, C-07, C-14, C-15 |
| Contradicted by implementation | C-03, C-04, C-06, C-13 |
| Needs external evidence review | C-08, C-12, C-21 |

## Structural observation

The repository's **documentation layer is more scientifically careful than its
UI layer**. `docs/methodology/limitations.md`, the module docstrings for
`human_pressure`, `lac_ros`, `projection`, `evidence` and `zone_loader`, and the
CETS/PRUG report framing all state limits accurately. The overclaims cluster in
one place: **the management-facing narrative strings compiled into
`src/platform/dashboard.py` and the map tooltips in `src/platform/map_layers.py`**.

That is a tractable target. Extracting those strings into a reviewable,
evidence-class-aware claim layer — rather than leaving them interleaved with
arithmetic — would address the majority of Tier 1 and Tier 2 findings without
touching the analytical core.
