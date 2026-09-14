# SNTO — PNSG Public-Use Decision Evidence Brief 2026/27

> **Perspective.** This brief is written from a *tourism destination planning and
> management* standpoint (public-use planning), **not** from that of an ecologist,
> physical geographer, or trail-condition specialist. Its purpose is to turn the
> heterogeneous, incomplete evidence currently held in this repository into a
> *transparent, proportionate* planning recommendation — including the legitimate
> outcome of concluding that the evidence is **insufficient to prioritise** an
> intervention.
>
> **Governing rules applied throughout.**
> 1. *Spatial resolution of claim ≤ spatial resolution of evidence.* No statement
>    is attributed to an individual trail/asset when the supporting evidence exists
>    only at a coarser unit.
> 2. *Environmental change ≠ tourism impact* unless attribution is supported by
>    evidence. A Sentinel-2 / NDVI / NDMI signal is described as an **observed
>    remote-sensing change**, never as tourism pressure or tourism impact.
> 3. **No field validation was performed by the author** (see §5). Nothing here
>    claims ecological, trail-condition, erosion, biodiversity, or anomaly
>    verification on the ground.
>
> Date: 2026-09-14 · Status: decision-support brief · Evidence ceiling: claim
> ladder **L5a** (recommend monitoring / inspection) per
> [`docs/phase1/SCIENTIFIC_PRODUCT_CONTRACT.md`](phase1/SCIENTIFIC_PRODUCT_CONTRACT.md).

---

## 1. Decision question

> *With the evidence currently ingested in SNTO, which public-use units of the
> Parque Nacional de la Sierra de Guadarrama (PNSG) — if any — justify a
> **priority management review / monitoring** of public use for the 2027 planning
> cycle, and where is the existing evidence **insufficient** to establish such a
> priority?*

The question deliberately admits three answers per unit (§4/Gate 4), including
*"insufficient evidence to prioritise"*. It does **not** ask where to close,
restrict, or fund restoration — those decisions are out of scope of the current
evidence (see §5, §13).

## 2. Decision owner

**PNSG public-use / destination-management team** (Organismo Autónomo Parques
Nacionales — PNSG unit and its public-use technical staff). No individual person
is named or assumed. SNTO is a decision-support layer *above* the owner's existing
GIS/EO/BI tools, not a substitute for the owner's technical judgement.

## 3. Why this decision matters

Public-use planning for a national park allocates scarce staff attention:
where to send field technicians, where to install counters, where to commission a
condition survey, where to re-examine management before the next planning cycle.
The failure mode this brief guards against is **misallocation driven by a
misread signal** — treating a remote-sensing vegetation change as if it were
proven visitor pressure, or attributing a sector-scale figure to a single trail.
A defensible "we do not yet have enough evidence to prioritise here" protects the
owner from spending attention on the wrong place, and names exactly what to
measure to change that.

## 4. Evidence available

Verified by direct inspection of the repository on 2026-09-14 (not assumed).

| Group | What it is | Class | Spatial unit | Temporal |
|---|---|---|---|---|
| **21 GEE-campaign assets** — `clean_assets/pnsg_assets.geojson` + `clean_assets/timeseries/pnsg_gee_timeseries.csv` + `.../analysis/mk_trends_pnsg.json` | Real monthly Sentinel-2 (S2_SR_HARMONIZED) NDVI/NDMI/EVI + Mann-Kendall/Sen trend per asset | **REAL** (environmental/context signal) | Per-asset footprint (mixed geometry: 3 points, 12 polygons, 6 linestrings) | 66 months, 2021-01 → 2026-06 |
| **218 OAPN trails** — `data/outputs/pnsg/pipeline_a_results.geojson` | Official OAPN trail cartography × two-scene S2 → EHS/ΔEHS, PRUG zone, priority index (and a derived per-trail `budget_eur`) | REAL cartography × REAL S2 signal; **budget/priority are derived, not observed** | Per-trail (real geometry) | Two-scene ΔEHS (seasonal), not a time series |
| **PRUG management zoning** — embedded in the 218-trail layer (`prug_zone`, `prug_protection_weight`) | Official OAPN protection zoning (Uso Restringido / Moderado / Especial / fuera) | Official / management evidence | Management zone | Static |
| **MITMA mobility crosswalk** — `src/mobility/reference/pnsg_mobility_zones.json` | Municipal zone ↔ PNSG municipality crosswalk (6 municipalities, 4 resolved) | Reference only — **snapshot NOT generated** (`src/mobility/snapshot/` absent) | Municipality | — |
| **Socioeconomic snapshot** — `src/socioeconomic/snapshot/municipalities.json` | Single dated municipal socioeconomic snapshot | REAL but single point | Municipality | 1 snapshot (no trend) |

**Categories of evidence (Gate 1).**
- **A. Visitor / public-use evidence:** *effectively none at asset or trail scale.*
  No counters, no access-control records, no parking occupancy, no surveys, no
  ingested mobility. The only visitor-related asset is a **municipal** MITMA
  crosswalk whose snapshot has never been generated.
- **B. Management / governance evidence:** PRUG protection zoning (real, per
  trail) — the strongest *localised* layer available.
- **C. Environmental / context evidence:** Sentinel-2 NDVI/NDMI, real, per-asset
  and per-trail. Describes vegetation state and its change, **not** its cause.
- **D. Unknown / unsupported:** cause of any observed change; visitor volume at
  any asset; trail physical condition; ecological state.

## 5. Evidence limitations

**No ecological or trail-condition field validation was conducted by the author.**
The author works in tourism destination planning / management / data analysis and
did **not** perform, and does **not** claim, any expert on-the-ground observation
of:

- soil compaction / erosion,
- vegetation cover or biodiversity condition,
- trail degradation or widening,
- ecological anomalies,
- visitor-caused physical impacts.

The field-validation campaign (Issue #26) has **not run even once**:
`clean_assets/field_validation/pnsg_field_observations_template.csv` still has
empty measurement columns. Therefore **no satellite↔field agreement is claimed**.

Further limitations:
- **No causal attribution.** A change in NDVI can arise from climate, drought,
  phenology, fire, management, succession, or cloud/scene artefacts — the system
  cannot, today, separate tourism from these.
- **Spatial-fit ceiling.** For point (paragliding) and linestring (cycling)
  assets, an NDVI footprint is a coarse and heterogeneous proxy for the actual
  used surface; for climbing polygons the index is dominated by surrounding
  vegetation, not the climbing approach itself.
- **No visitor-use denominator.** Without any counts or ingested mobility, "how
  much use" is unknown at every asset.

## 6. Legitimate spatial unit

> **LEGITIMATE_DECISION_UNIT** = *for an environmental change signal:* the
> **per-asset / per-trail footprint** (REAL, context only). *For a tourism /
> public-use pressure decision:* **no unit below the municipality is supportable,
> and even the municipality is unavailable today** (mobility snapshot not
> generated). Consequently, **tourism-pressure prioritisation cannot be resolved
> at trail or asset scale with current evidence.**

Rationale: the finest *real* evidence is per-asset Sentinel-2 — but that measures
vegetation, not use. The finest *visitor-use* evidence that even exists as a path
is municipal, and it is not ingested. The rule *claim ≤ evidence* therefore
forbids any per-trail tourism-pressure statement. The 21 assets are **not** 21
comparable trails: they are 3 paragliding points, 7 climbing areas, 6 cycling
routes and **5 conservation reserves** (reserve zones are not public-use assets
and are excluded from any public-use prioritisation).

## 7. Evidence matrix

Units are shown **only at the scale the evidence supports**. "Env. signal" is a
remote-sensing observation, **not** an impact verdict.

| Unit | Visitor-use evidence | Management sensitivity (PRUG) | Environmental / context signal (S2) | Spatial fit | Uncertainty | Decision status |
|---|---|---|---|---|---|---|
| **Maliciosa-Porrones (climbing area)** | none | high-sensitivity terrain | **NDVI ↓ significant** (τ=−0.37, p≈0, change-pt 2025-03) **but NDMI ↑** (τ=+0.22, p=0.01) — internally contradictory | polygon over rocky area (coarse) | LOW–MODERATE | **MONITOR / DATA GAP** |
| Paragliding points (El Nevero, La Nevera, El Espartal) | none | point launch sites | NDVI ↑ / no trend (greening or stable) | point footprint (weak) | INSUFFICIENT for use | **INSUFFICIENT EVIDENCE TO PRIORITISE** |
| Climbing areas (6 others) | none | mixed | 3 greening / 3 no-trend | polygon (coarse) | INSUFFICIENT for use | **INSUFFICIENT EVIDENCE TO PRIORITISE** |
| Cycling routes (6) | none | mixed | 1 greening / 5 no-trend | linestring buffer (coarse) | INSUFFICIENT for use | **INSUFFICIENT EVIDENCE TO PRIORITISE** |
| Conservation reserves (5) | n/a — not public-use | conservation | mostly no-trend | polygon | out of public-use scope | **EXCLUDED (not a public-use unit)** |
| 218 OAPN trails (aggregate) | none | PRUG zone per trail | 165 improving / 46 worsening (ΔEHS, two-scene) | per-trail cartography, but no time series | MODERATE (no visitor denominator) | **MONITOR / DATA GAP (aggregate)** |
| Any tourism-pressure ranking | — | — | — | — | — | **NOT SUPPORTED at trail/asset scale** |

Whole-park reading: across the 21 assets with a real time series, **6 show
significant greening, 14 no trend, 1 significant decline**. The dominant signal
is stability or recovery — not degradation.

## 8. Priority cases

Under the honest reading, **there are zero cases that qualify for
`PRIORITY FOR MANAGEMENT REVIEW` on public-use grounds**, because no visitor-use
evidence exists at any resolvable unit. The strongest available case rises only to
**MONITOR / DATA GAP**:

### Evidence Card — Escalada Maliciosa-Porrones (MONITOR / DATA GAP)

- **Unit:** climbing area (polygon), `pnsg_escalada_maliciosa_porrones`.
- **Decision question:** does this area warrant a second look before 2027?
- **Evidence supporting review:** the only asset with a *significant declining*
  NDVI trend (τ=−0.37, p≈0, n=65), with a significant change-point at 2025-03 and
  annual-mean NDVI drifting 0.234→0.213.
- **Contradictory / missing evidence:** NDMI (moisture) is *rising* significantly
  (τ=+0.22) — inconsistent with a simple trampling/desiccation story; **no
  visitor data**; no field observation; NDVI baseline here is low (~0.22, rocky),
  so absolute change is small and scene/cloud sensitivity is higher.
- **Uncertainty:** LOW–MODERATE evidence confidence (strong temporal signal, poor
  spatial fit, zero attribution evidence).
- **Legitimate conclusion:** *A remote-sensing vegetation-change signal is present
  and merits monitoring / a targeted look.* It is a candidate for the #26 field
  protocol.
- **What cannot be concluded:** that tourism, climbing, or any visitor activity
  caused it; that the area is "degraded"; that any intervention is warranted.

## 9. Insufficient-evidence cases

**This is the majority outcome and it is a valid result.** Examples:

- **Paragliding points (El Nevero, La Nevera, El Espartal):** El Nevero even shows
  *significant greening* (τ=+0.23). Zero visitor data; point-footprint NDVI is a
  weak proxy. → **INSUFFICIENT EVIDENCE TO PRIORITISE.**
- **All 6 cycling routes and 6 of 7 climbing areas:** no significant adverse
  trend, no visitor data. → **INSUFFICIENT EVIDENCE TO PRIORITISE.**
- **Any trail-by-trail tourism-pressure ranking:** unsupported in principle —
  there is no visitor-use evidence at trail scale to rank on. → **NOT SUPPORTED.**

The reason in every case is the same: *the evidence that would establish a
public-use priority (visitor volume/use at the unit) does not exist at that unit.*

## 10. What we know

- PNSG-wide, the real Sentinel-2 signal (2021–2026) is dominated by **stability
  and greening**; only one campaign asset declines significantly.
- Official PRUG protection zoning is available per trail (a real management layer).
- The system correctly **degrades to "insufficient"** rather than fabricating a
  priority.

## 11. What we do not know

- Visitor volume or use intensity at **any** asset or trail.
- The **cause** of any observed vegetation change (tourism vs climate vs other).
- The **physical / ecological condition** of any trail on the ground.
- Whether the one declining signal (Maliciosa-Porrones) reflects anything a
  visitor did.

## 12. What should be measured next

**Data a tourism planner / data analyst can obtain and analyse without field
ecology expertise:**
- Ingest the already-built **MITMA municipal mobility** feed (run `etl_mobility.py`)
  → municipal-scale visitor context (never trail footfall, but a real denominator
  at municipality level).
- Add a **second dated socioeconomic snapshot** so a real municipal trend exists.
- **Parking-occupancy and access counts** at recreation areas / access points /
  visitor centres (coarser than trail, but real public-use evidence at a unit that
  actually matches the data).
- **Repeated Sentinel-2 observation** of the Maliciosa-Porrones signal (continue
  the series; watch the change-point).

**Data / validation that requires qualified field / technical personnel (not the
author):**
- Pedestrian counters on specific trails.
- Visitor-intercept surveys.
- **Trail-condition assessment by qualified staff** (compaction, cover, erosion,
  width) — the #26 protocol.
- Any ecological or biodiversity condition assessment.
- Ground-truth needed to attribute a remote-sensing signal to a cause.

## 13. Management implications

Proportionate to the evidence, the only defensible recommendations are:

- **Monitor** Maliciosa-Porrones (continue the S2 series; flag for the #26
  protocol). No conclusion of impact.
- **Improve data collection** at the *unit that matches available data*
  (municipality → mobility; access/parking → counts) rather than forcing a
  trail-level story.
- **Maintain current management policy** where the signal is stable/greening
  (the majority) — there is no evidence base to change it.
- **Insufficient evidence to prioritise** any physical intervention, closure,
  quota, or restoration anywhere. Notably, a per-trail restoration `budget_eur`
  (total ≈ €1.44M in the 218-trail Pipeline-A layer) exceeds the current L5a
  ceiling and should be read as an *illustrative planning artefact*, not a
  costed recommendation, until visitor-use and field evidence exist.

No closure, quota, restoration, or budget commitment is recommended. The success
of this brief is a **defensible decision proportionate to the evidence**, not a
ranking.
