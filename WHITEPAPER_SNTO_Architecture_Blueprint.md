# System Architecture & Methodological Blueprint
## Smart Natural Tourism Observatory (SNTO)
### *Whitepaper — Source of Truth Document*

**Project:** Gobernanza Inteligente y Transición Regenerativa en Espacios Naturales Protegidos. Territorio principal: **Parque Nacional Sierra de Guadarrama** (Red de Parques Nacionales — OAPN). Marco de gobernanza de referencia: Carta Europea de Turismo Sostenible (CETS / EUROPARC), empleada como metodología. Piloto de calibración: Reserva de la Biosfera Sierra del Rincón.

**Version:** 2.0.0 | **Date:** July 2026 | **Author:** Smart Natural Tourism Observatory Research Team

> **Document scope:** this whitepaper tracks the latest stable methodological baseline (`v2.0.0`). The repository `main` branch may contain later development work that is not yet part of a stable release. Note: v2.0.0 is a modular-architecture, backend and role-based-UI release; the methodology described here is unchanged from the v1.3.0 statistical-rigor baseline.

---

# 1. Executive Summary

The **Smart Natural Tourism Observatory (SNTO)** is an open, spatially explicit, data-driven platform designed to transition natural tourism destination management from a reactive maintenance paradigm to a proactive, scientifically grounded **Regenerative Tourism** model. Developed primarily for the **Sierra de Guadarrama National Park (PNSG)** — the first site of the Spanish National Parks Network (OAPN) integrated into the observatory — and methodologically grounded in the **European Charter for Sustainable Tourism (CETS / EUROPARC)** governance framework, the SNTO operationalises the core regenerative principle that tourism infrastructure must actively restore the ecological carrying capacity it consumes. The method was initially calibrated on the Sierra del Rincón Biosphere Reserve, retained as a methodological calibration pilot.

The platform ingests multitemporal **ESA Sentinel-2 Level-2A** satellite imagery to derive spatially explicit **vegetation stress and canopy moisture indices** along hiking trail corridors. These raw spectral signals are transformed through a validated algorithmic pipeline into an **Environmental Health Score (EHS)** — a normalised degradation index (0–100) that quantifies the cumulative biophysical impact of recreational trampling, soil compaction, and associated water stress on trail-adjacent ecosystems. The EHS feeds directly into a **financial model calibrated against TRAGSA official restoration rates**, generating dynamic, trail-specific restoration budgets that are surfaced to decision-makers through an interactive **Streamlit geospatial dashboard**.

Beyond immediate operational utility, the SNTO embeds a family of advanced analytical modules — the **Spatial Causality Module (SCM)**, the **Territorial Priority Index (TPI)**, the **Decision Confidence Score (DCS)**, and the **Tourism Impact Score (TIS)** — that collectively elevate destination management from reactive indicator monitoring to anticipatory, evidence-based governance aligned with CETS Phase I accountability requirements and the broader **Sustainable Development Goals (SDGs)**, particularly SDGs 11, 13, and 15.

---

# 2. Theoretical Framework: CETS Phase I & the Regenerative Transition

## 2.1 The European Charter for Sustainable Tourism

The **European Charter for Sustainable Tourism in Protected Areas (CETS)**, administered by the European Charter Foundation under the Europarc Federation, provides a voluntary accreditation framework structured around participatory governance, continuous monitoring, and measurable sustainability commitments. **Phase I** of the accreditation process requires candidate territories to demonstrate:

1. A **shared five-year action plan** developed through a multi-stakeholder forum.
2. A **monitoring system** capable of objectively tracking environmental and socio-economic performance indicators over time.
3. Evidence of **commitment to minimising the ecological footprint** of tourism activities within protected area boundaries.

The SNTO directly addresses requirements 2 and 3 by providing the quantitative monitoring infrastructure that transforms qualitative commitments into auditable, satellite-validated evidence.

## 2.2 From Sustainable to Regenerative Tourism

The conventional **Sustainable Tourism** framework operates on the principle of *minimising harm* — a defensive, steady-state logic that seeks to preserve existing conditions. The **Regenerative Tourism** paradigm, increasingly prominent in post-pandemic tourism governance literature (Duxbury et al., 2021; Sheldon, 2020), advances a more ambitious ontological claim: that tourism, when properly governed, can function as a *positive ecological driver* — actively restoring degraded habitats, recharging soil hydrology, and rebuilding ecosystem service provision.

The SNTO implements regenerative logic through three operational mechanisms:

- **Degradation Detection:** Satellite-derived indices identify statistically significant vegetation stress in trail corridors before irreversible threshold effects occur.
- **Ecological Accounting:** Restoration budgets are dynamically computed and directly indexed to observed stress levels, making the financial cost of regeneration explicit and proportional to ecological debt.
- **Proactive Intervention:** The TIS Engine routes restoration investment to the trails where the ecological dividend per euro is maximised, rather than applying uniform maintenance schedules.

## 2.3 Scientific Grounding: Trampling Ecology

The methodological link between hiking trail use and vegetation degradation is well-established in the ecological literature. Studies in Mediterranean montane ecosystems demonstrate that **soil compaction** from recreational trampling reduces macro-porosity by 15–40%, directly suppressing root-zone moisture availability and inducing physiological drought stress in surface vegetation independently of climatological conditions (Roovers et al., 2004; Pickering & Mount, 2010). This process creates a measurable spectral signature:

- **Reduced NDVI** (Normalised Difference Vegetation Index): As photosynthetic tissue collapses under combined mechanical and water stress, the red-edge reflectance contrast diminishes, reducing NDVI.
- **Reduced NDMI** (Normalised Difference Moisture Index): Soil compaction limits capillary water transport, producing characteristic SWIR reflectance increases that depress NDMI values in affected canopy zones.

The SNTO exploits precisely these spectral responses to non-invasively quantify trail-induced ecosystem degradation at landscape scale.

---

# 3. Methodological Architecture: Remote Sensing & Spectral Indices

## 3.1 Data Source: ESA Sentinel-2 Level-2A

The SNTO ingests imagery from the **ESA Copernicus Sentinel-2** constellation (satellites A and B), processed to **Level-2A (L2A)** — bottom-of-atmosphere surface reflectance. Key mission parameters relevant to this application are:

| Parameter | Value |
|-----------|-------|
| **Revisit frequency** | 5 days (A+B combined) |
| **Spatial resolution** | 10 m (Bands B4, B8); 20 m (Band B11) |
| **Radiometric resolution** | 12-bit (0–4095 DN) |
| **Surface reflectance scaling** | Raw DN ÷ 10,000 → unitless [0, 1] |
| **Processing level** | L2A (Bottom-of-Atmosphere, atmospherically corrected) |
| **UTM tile** | T30TVL (covers both PN Sierra de Guadarrama and Sierra del Rincón) |

**Band selection rationale:**

- **Band 4 (B4 — Red, 665 nm, 10 m):** Chlorophyll absorption maximum. Sensitive to photosynthetically active biomass density and vegetation health.
- **Band 8 (B8 — NIR, 842 nm, 10 m):** Near-infrared plateau. Highly sensitive to leaf mesophyll structure and canopy biomass; the primary signal channel for vegetation vitality.
- **Band 11 (B11 — SWIR1, 1610 nm, 20 m):** Shortwave infrared. Sensitive to liquid water content in both vegetation canopy and surface soil layers; resampled to 10 m resolution via bilinear interpolation to maintain pixel grid alignment with B4/B8.

**Cloud masking:** The Scene Classification Layer (SCL) is used to exclude pixels classified as cloud shadow (class 3), medium-probability cloud (class 8), high-probability cloud (class 9), thin cirrus (class 10), and snow/ice (class 11). Monthly median compositing across 5–10 valid A+B scenes provides robust cloud-free time steps (minimum 30% valid pixel coverage required for composite acceptance).

## 3.2 Spatial Domain: Trail Buffer Geometry

Spectral signals are spatially aggregated within **50-metre geometric buffers** generated around digitised hiking trail centrelines. This buffer radius is operationally justified on three grounds:

1. **Ecological:** Soil compaction effects from repeated trail use propagate laterally 10–30 m from the trail centreline, with measurable vegetation stress extending to 40–50 m in heavily-used corridors (Cole & Monz, 2002).
2. **Radiometric:** The 50 m buffer ensures a minimum pixel count sufficient for statistically stable zonal statistics at 10 m resolution (≥ 250 pixels per 1 km trail segment).
3. **Cadastral:** 50 m corresponds to standard Spanish natural park management zone widths for linear infrastructure corridors (PORN buffer classes under Spanish Law 42/2007).

**Coordinate Reference System:** All spatial operations are performed in **EPSG:25830 (ETRS89 / UTM Zone 30N)** — the official reference system for Peninsular Spain, ensuring metric accuracy in length and area calculations.

Trail vector geometries are sourced from OpenStreetMap, cleaned through the `etl_vector_cleaner.py` pipeline, validated for topological integrity, and stored with PostGIS spatial indexing (GIST index on `geometry` column).

**Observación vs. acción — escala de intervención:** El buffer de 50 m es la unidad de observación satelital: captura la señal NDVI/NDMI del entorno del sendero para detectar estrés vegetal difuso. La unidad de acción de restauración es la traza del sendero (1–2 m de ancho), sobre la que se aplican las intervenciones físicas (descompactación, fajinas transversales, revegetación). El coste unitario de 15,50 €/m lineal corresponde a esta escala de actuación.

## 3.3 Spectral Index Formulation

### 3.3.1 NDVI — Normalised Difference Vegetation Index

$$\text{NDVI} = \frac{\rho_{NIR} - \rho_{Red}}{\rho_{NIR} + \rho_{Red}}$$

Where $\rho_{NIR}$ and $\rho_{Red}$ are surface reflectance values in Bands B8 and B4 respectively. NDVI ranges theoretically from −1 to +1, with healthy Mediterranean scrubland exhibiting typical peak-growing-season values of **0.45–0.65**. Bare soil returns values of approximately 0.10–0.20. A zero-guard term ($\varepsilon = 10^{-8}$) prevents division-by-zero artefacts in dark pixels or no-data regions.

**Ecological interpretation in the SNTO context:** NDVI is the primary proxy for **photosynthetic capacity and aerial biomass density**. Sustained NDVI depression below the established regional healthy baseline (**NDVI_baseline = 0.55** for Mediterranean scrubland, derived from a 5-year climatological reference dataset) constitutes evidence of trampling-induced phytomass loss.

### 3.3.2 NDMI — Normalised Difference Moisture Index

$$\text{NDMI} = \frac{\rho_{NIR} - \rho_{SWIR1}}{\rho_{NIR} + \rho_{SWIR1}}$$

Where $\rho_{SWIR1}$ is surface reflectance in Band B11 (resampled to 10 m). NDMI ranges from −1 to +1, with values above 0.20 indicating well-hydrated canopy conditions in the study region. The index is particularly sensitive to **canopy water content and soil moisture availability in the root zone**.

**Ecological interpretation in the SNTO context:** NDMI provides a complementary and partially independent stress signal to NDVI. While NDVI tracks above-ground biomass degradation, NDMI captures the **hydrological pathway of soil compaction stress** — mechanically compacted soils reduce macropore connectivity, restrict capillary water rise, and induce sub-canopy moisture deficits that manifest as SWIR reflectance increases even before visible biomass loss occurs. The combined use of NDVI and NDMI therefore captures stress at two complementary points in the ecological degradation cascade.

---

# 4. The Environmental Health Score (EHS): Operational Formula

## 4.1 Conceptual Design

> **Normative note — two canonical score directions.** SNTO works with two
> 0–100 score directions that must never be conflated. The canonical conversion
> `health = 100 − stress` is centralised in `src/metrics/semantics.py`.
>
> | Direction | 0 means | 100 means | Where it lives |
> |---|---|---|---|
> | **Stress / Degradation Score** | no stress | maximal degradation | `calculate_delta_ehs.py` (Pipeline A) and the legacy DB columns `ehs_spring`, `ehs_summer`, `delta_ehs` |
> | **Health Score** | critical | healthy | dashboard, TPI, tiers, `src/risk_engine/ehs.py` (§4.3), executive communication |
>
> **Delta convention:** `DeltaStress > 0` ⇒ condition worsens; the equivalent
> `DeltaHealth = −DeltaStress < 0` ⇒ health falls. The live dashboard ingests
> the Pipeline A stress output and converts it to health on load
> (`src/platform/real_trails.py`), so every figure the user sees is health.

The **Environmental Health Score (EHS)** is the SNTO's principal operational indicator. The operational Pipeline A formula below (§4.2) computes the **stress direction** — a **degradation index scaled from 0 to 100**, where:

- **0** = no deviation from healthy baseline (optimal state)
- **100** = maximal stress / complete degradation

This stress direction is deliberately adopted *inside Pipeline A* to align with financial logic: a **higher stress score directly implies a higher restoration budget requirement**, making the ecological-financial relationship intuitively transparent. It is converted to the health direction (high = good) before reaching the dashboard, so the "EHS" the user reads is always a Health Score. The research-grade engine (§4.3) emits the health direction natively.

## 4.2 Core EHS Formula (Operational Dashboard Implementation)

The operational EHS formula implemented in the `calculate_delta_ehs.py` pipeline uses a **scene-specific percentile-anchored deficit formulation** that normalises each observation against the actual healthy and degraded pixel distributions of the same scene:

$$D = \text{clamp}\!\left(\frac{B_{percentile} - X}{B_{percentile} - Floor_{percentile}},\ 0,\ 1\right)$$

$$\boxed{\text{EHS} = 100 \times \left(W_{NDVI} \cdot D_{NDVI} + W_{NDMI} \cdot D_{NDMI}\right)}$$

Where:
- $X$ is the mean NDVI (or NDMI) value extracted via zonal statistics within the 50 m trail buffer.
- $B_{percentile}$ is the healthy reference level — the P90 percentile of valid vegetation pixels (SCL class 4) in the scene, excluding trail buffers.
- $Floor_{percentile}$ is the degraded floor — the P10 percentile of the same pixel distribution.
- $D_{NDVI}$, $D_{NDMI}$ are per-index deficit fractions, each clamped to [0, 1].
- $W_{NDVI} = W_{NDMI} = 0.5$ (equal weighting, configurable in `src/config/constants.py`).

**Operational parameters** (`src/config/constants.py`): `EHS_P_BASE = 90`, `EHS_P_FLOOR = 10`, `EHS_W_NDVI = 0.5`, `EHS_W_NDMI = 0.5`.

**Algebraic interpretation:** The formula computes a scene-specific deficit of each index relative to the observed healthy range in the same image. A trail at the P90 reference level yields $D = 0$ (no deficit, EHS contribution = 0). A trail at or below the P10 floor yields $D = 1$ (maximum deficit, full EHS contribution). This approach normalises against the actual ecological conditions of each acquisition, making EHS robust to inter-seasonal and inter-annual radiometric variability.

## 4.3 Research-Grade EHS Engine (Full Statistical Implementation)

The research-grade EHS engine (`src/risk_engine/ehs.py`) extends the operational formula with a multi-component, statistically grounded composite risk model for longitudinal analysis:

$$\text{EHS}_{research} = 100 \times \left(1 - r_{composite}\right)$$

$$r_{composite} = 0.30 \cdot r_{baseline} + 0.25 \cdot r_{trend} + 0.25 \cdot r_{anomaly} + 0.10 \cdot r_{recovery} + 0.10 \cdot r_{stability}$$

| Risk Component | Weight | Definition |
|---|---|---|
| **Baseline risk** | 30% | NDVI distance below healthy regional baseline (0.55) |
| **Trend risk** | 25% | Magnitude of statistically significant declining Mann-Kendall slope (p < 0.05) |
| **Anomaly risk** | 25% | Fraction of months with severe NDVI anomaly (|z| ≥ 1.5 σ) |
| **Recovery risk** | 10% | Post-drought NDVI recovery ratio (failure to recover to pre-drought levels) |
| **Stability risk** | 10% | Inter-annual residual variability relative to mean NDVI |

This formulation captures both **chronic degradation** (baseline and trend) and **episodic stress events** (anomaly and recovery) while penalising high temporal instability — all key dimensions of the Sierra del Rincón's fire-drought-tourism stress complex.

## 4.4 EHS Classification Scale

| EHS Range | Class | Management Implication |
|---|---|---|
| 0–39 | **Excellent** | Vegetation above regional baseline; active promotion eligible |
| 40–59 | **Good** | Moderate seasonal stress; stable long-term; routine monitoring |
| 60–74 | **Moderate** | Noticeable chronic stress; annual monitoring recommended |
| 75–89 | **Poor** | Persistent degradation; preventive intervention triggered |
| 90–100 | **Critical** | Severe degradation; immediate restoration mandated |

## 4.5 Temporal Dynamics: Delta EHS as Early Warning Signal

A critical analytical dimension of the SNTO is the **seasonal Delta EHS** ($\Delta\text{EHS}$):

$$\Delta\text{EHS} = \text{EHS}_{Summer} - \text{EHS}_{Spring}$$

This metric computes the EHS differential between the late-growing season (Spring, May–June) and the peak-stress season (Summer, July–August). Under natural Mediterranean phenology, summer drought produces moderate EHS increases; however, trail corridors subject to high recreational pressure exhibit **accelerated EHS escalation** beyond the climatological baseline — a pattern distinguishable from background climate variability.

**Interpretation:**
- **ΔEHS positive (and above seasonal baseline):** Anthropogenic stress is compounding seasonal drought stress — an **early warning signal** requiring increased monitoring intensity.
- **ΔEHS near zero or negative:** Trail ecosystem recovering seasonally, consistent with climatological norms.

The Delta EHS is computed by `calculate_delta_ehs.py`, which reads multitemporal raster stacks and outputs per-trail seasonal stress differentials stored in the PostGIS `production_hiking_trails` table.

---

# 5. Technical Data Pipeline: From Satellite to Dashboard

## 5.1 Architecture Overview

The SNTO data pipeline is structured as a four-stage **Extract-Transform-Load-Serve (ETLS)** workflow:

```
[STAGE 1: INGEST]         Raw Sentinel-2 L2A (.SAFE / ZIP) Archive
         ↓
[STAGE 2: PROCESS]        Band Extraction → Spectral Index Computation → GeoTIFF
         ↓
[STAGE 3: INTEGRATE]      Zonal Statistics → PostGIS → TIS Engine → Budget Scores
         ↓
[STAGE 4: SERVE]          Streamlit Dashboard → Interactive Map + KPI Cards
```

## 5.2 Stage 1 — Raster Ingestion (`etl_raster_processor.py`)

The ingestion pipeline processes raw Sentinel-2 L2A products in **SAFE format** (distributed as ZIP archives of ~250 MB per scene). The `etl_raster_processor.py` script:

1. **Locates** the target SAFE ZIP in `data/raw_assets/raster_data/` using `glob` pattern matching.
2. **Selectively extracts** only the three required JP2 band files (B04, B08, B11) from the ZIP archive, avoiding full decompression of the ~1 GB SAFE bundle.
3. **Clips** each extracted band to the Sierra del Rincón study area bounding box (WGS84: −3.65°E to −3.30°E, 41.05°N to 41.20°N) using `rasterio.mask`.
4. **Reprojects** all bands to **EPSG:25830** (metric coordinate system) using `rasterio.warp.reproject`.
5. **Resamples** Band B11 from its native 20 m resolution to the 10 m reference grid (defined by B4) using **bilinear interpolation** (`Resampling.bilinear`), ensuring pixel-perfect spatial alignment across all index bands.
6. **Computes** NDVI and NDMI index rasters as `float32` arrays with epsilon zero-guard.
7. **Writes** five production GeoTIFFs to `data/clean_assets/` with LZW lossless compression and NoData value = −9999.0:
   - `clean_S2_B04_red.tif`
   - `clean_S2_B08_nir.tif`
   - `clean_S2_B11_swir.tif`
   - `clean_S2_NDVI.tif`
   - `clean_S2_NDMI.tif`

**Key Python libraries:** `rasterio`, `rasterio.mask`, `rasterio.warp`, `numpy`, `os`, `glob`.

## 5.3 Stage 2 — Zonal Statistics (`etl_raster_intersection.py`)

Trail-level index values are extracted by intersecting the NDVI and NDMI GeoTIFFs with buffered trail geometries:

1. Trail geometries are loaded from PostGIS (`production_hiking_trails` table) using `geopandas.read_postgis()`.
2. Geometries are reprojected to EPSG:25830 to match the raster CRS.
3. **50 m buffers** are generated around each trail centreline using `geopandas.GeoDataFrame.buffer(50)` in metric coordinates.
4. **Zonal statistics** (mean pixel value within each buffer polygon) are computed using `rasterstats.zonal_stats()` for both NDVI and NDMI rasters.
5. Extracted mean values are written back to the `production_hiking_trails` table as `avg_ndvi` and `avg_ndmi` columns.

## 5.4 Stage 3 — Scoring & Budget Allocation (`tis_engine.py`)

The TIS Engine orchestrates the transformation from raw spectral values to actionable intervention budgets:

1. **EHS computation:** `avg_ndvi` and `avg_ndmi` are passed to `_compute_ehs()`, which normalises NDMI to [0, 1] and returns the stress-weighted EHS score per trail.
2. **Traffic normalisation:** Annual visitor counts are min-max normalised across all trails to yield a `traffic_index` ∈ [0, 100].
3. **Priority score:** `priority_score = (EHS × 0.60) + (traffic_index × 0.40)` — weighting ecological urgency (60%) above visitor pressure (40%).
4. **Budget allocation:** Trails with `priority_score > 60` are flagged as requiring intervention. Their restoration budget is computed as:

$$\text{TIS Budget (EUR)} = L_m \times 15.50 \times \frac{\text{priority score}}{100}$$

Where $L_m$ is trail length in metres, computed from PostGIS via `ST_Length(geometry::geography)`.

5. Results are written to four dynamic columns added to `production_hiking_trails`: `ehs_index`, `needs_intervention`, `tis_budget_eur`, `priority_score`.

## 5.5 Stage 4 — Dashboard (`app.py`)

The Streamlit dashboard (`app.py`) provides an interactive geospatial decision-support interface for park managers and CETS evaluators:

- **KPI Summary Cards:** Total trails analysed; critical trails requiring intervention; total restoration budget; maximum recorded tourist volume.
- **Interactive PyDeck (Deck.gl) Map:** Trails colour-coded by health status (green: EHS ≤ 60; red: EHS > 60), centred on Sierra del Rincón (41.14°N, −3.52°E), with pop-up tooltips displaying all diagnostic attributes per trail.
- **Priority Intervention Table:** Top 10 trails sorted by descending priority score, with gradient-coloured EHS column (RdYlGn_r colormap) for rapid visual triage.
- **Temporal Analysis Panel:** Delta EHS visualisation (Summer vs. Spring), identifying trails with accelerated seasonal degradation trajectories.

Data is loaded via `geopandas.read_postgis()` with a 5-minute TTL cache (`@st.cache_data(ttl=300)`) to balance freshness against query latency.

## 5.6 Advanced Analytical Modules

Beyond the core EHS-to-budget pipeline, the SNTO includes three research-grade analytical modules that underpin the platform's scientific credibility:

### Decision Confidence Score (DCS) — `src/decision_confidence/assessor.py`

The DCS (0–100) assesses **recommendation reliability** before any management action is triggered. It penalises decisions based on sparse time series, high cloud contamination, or weak spectral signals. The DCS gates the budget allocation: assets with DCS < 55 are routed to evidence collection protocols rather than full restoration commitment.

| DCS Band | Classification | Action |
|---|---|---|
| 80–100 | Very High Confidence | Full restoration budget allocated |
| 60–79 | High Confidence | Intervention approved |
| 40–59 | Moderate Confidence | Additional monitoring required |
| 0–39 | Low Confidence | Evidence collection only |

### Spatial Causality Module (SCM) — `src/spatial_causality/analyzer.py`

The SCM distinguishes **anthropogenic (localised) degradation** from **climate-driven (landscape) stress** by comparing NDVI dynamics across concentric zones:

- **Core zone** (0–50 m): Direct trail footprint
- **Near zone** (50–200 m): Immediate surroundings
- **Landscape zone** (200–1000 m): Regional background

The **Spatial Impact Gradient (SIG)** = (NDVI_landscape − NDVI_core) / NDVI_landscape:
- SIG > 0.15 → **LOCALIZED_IMPACT** (tourism pressure dominant)
- SIG < 0.07 → **LANDSCAPE_DRIVEN** (climate forcing dominant)
- 0.07–0.15 → **MIXED** signal

This distinction is critical for CETS accountability: only locally-attributable degradation should generate management obligations for the protected area authority.

### Territorial Priority Index (TPI) — `src/territorial/tpi.py`

The TPI (0–100) ranks assets within a territorial portfolio for investment prioritisation:

$$\text{TPI} = U_{condition}\ [0\text{–}40] + S_{evidence}\ [0\text{–}25] + V_{strategic}\ [0\text{–}20] + C_{causality}\ [0\text{–}15]$$

TPI output drives a **four-tier asset classification** — from *Immediate Attention* (Tier 1) through *Routine Monitoring* (Tier 3) to *Promotion Opportunity* (Tier 4) — directly informing the annual CETS management plan priorities.

---

# 6. The Financial-Ecological Model: Budget Calibration

## 6.1 Restoration Cost Basis

The SNTO restoration budget model is anchored to a **unit restoration cost of €15.50 per linear metre of degraded trail**, established through cross-referencing three official Spanish cost frameworks:

| Cost Component | Standard Source | Unit Cost Contribution |
|---|---|---|
| **Soil decompaction** (mechanical scarification) | TRAGSA Price List 2023 (Chapter 15: Forest Work) | €4.20 / linear metre [pendiente de verificar: Tarifas TRAGSA, Resolución oficial, Cap. 15, año 2023] |
| **Erosion control** (fajinas — brushwood check dams; albarradas — stone barriers) | TRAGSA Price List 2023 (Chapter 8: Hydraulic Works) | €6.80 / linear metre [pendiente de verificar: Tarifas TRAGSA, Resolución oficial, Cap. 8, año 2023] |
| **Native revegetation** (autochthonous shrub planting, seed mix for *Quercus*, *Cistus*, *Rosmarinus* assemblage) | Spanish National Plan for Ecological Transition 2021–2025, Unit Price Schedule | €4.50 / linear metre [pendiente de verificar: PNMT 2021–2025, Resolución oficial, año 2021] |
| **Total** | | **€15.50 / linear metre** |

This unit rate is consistent with published restoration costs for trail rehabilitation in Mediterranean mountain environments (Barros et al., 2013; Spanish MITERD ecological restoration tender baselines, 2022–2024).

## 6.2 Dynamic Budget Formula

The full restoration budget for any trail segment is modulated by the environmental urgency expressed in the priority score:

$$\boxed{B_{restoration} = L_m \times 15.50\ \frac{\text{EUR}}{m} \times \frac{P_{score}}{100}}$$

Where:
- $L_m$ = trail length in metres (computed from PostGIS `ST_Length(geometry::geography)`)
- **15.50** = calibrated unit restoration cost (EUR/m)
- $P_{score}$ = priority score (composite of EHS × 0.60 + traffic_index × 0.40), capped at 100

**Economic rationale:** This proportional scaling embeds **ecological proportionality** into the financial model — a trail at 80% priority receives 80% of its full theoretical restoration budget. This prevents over-allocation to mildly stressed assets while ensuring critical trails receive funding commensurate with their degradation severity. Trails scoring below the intervention threshold (priority_score ≤ 60) receive a €0 allocation; their ecological status is maintained through routine monitoring.

## 6.3 Financial Interpretation at Scale

For a representative Sierra del Rincón network of 20 km of monitored trail:

| Scenario | Mean Priority Score | Total Budget |
|---|---|---|
| Moderate stress year | 65 | €201,500 |
| High stress year (post-drought + peak visitation) | 82 | €254,200 |

> **Nota:** Senderos con priority ≤ 60 no generan presupuesto de intervención; pasan a monitorización anual.

These budget envelopes are fully reproducible from satellite data with no field survey requirement, enabling **annual budget forecasting calibrated to real ecological conditions** — a key CETS Phase I deliverable.

## 6.4 TRAGSA Rate Justification and Regulatory Compliance

The cost basis aligns with the Spanish regulatory framework for publicly contracted ecological restoration:

- **Royal Decree 9/2005** (Contaminated Soils): establishes soil decompaction as eligible restoration action in legally protected natural spaces.
- **Law 26/2007** (Environmental Liability): mandates financial provisioning for restoration of legally protected habitats, providing the legal basis for budget obligation.
- **Law 42/2007** (Natural Heritage and Biodiversity): defines 'favourable conservation status' targets for Natura 2000 habitat types present in Sierra del Rincón (9230, 4030, 5110), against which restoration effectiveness is measured.
- **TRAGSA** (Empresa de Transformación Agraria S.A.): Spain's publicly owned transformation company serving as benchmark price authority for all public ecological restoration tender bids under Spanish procurement law.

---

# 7. Conclusion & Strategic Impact

## 7.1 System Contribution to CETS Phase I

The SNTO directly satisfies the three core evidential requirements of CETS Phase I certification:

1. **Operational monitoring system:** The satellite-derived EHS provides continuous, auditable, spatially explicit environmental performance indicators updated on monthly timescales — exceeding the minimum frequency required by CETS baseline protocols.

2. **Minimising ecological footprint:** The financial-ecological model creates a direct, legally defensible accountability link between tourist visitation, measurable ecological degradation, and mandatory restoration investment — operationalising the CETS commitment to *net-zero ecological impact* within the Biosphere Reserve.

3. **Stakeholder-facing dashboard:** The Streamlit interface translates complex satellite data into accessible KPIs and visual maps intelligible to park managers, municipal stakeholders, and CETS evaluators without specialist remote sensing knowledge.

## 7.2 Contribution to Regenerative Tourism Theory

At a theoretical level, the SNTO makes three contributions to the emerging Regenerative Tourism literature:

- **Operationalisation of ecological debt:** The EHS-to-budget pipeline translates an abstract concept (the ecological cost of recreation) into a concrete, monetised liability — enabling the application of environmental accounting frameworks (e.g., Natural Capital Accounting, ISO 14008) to trail management.
- **Satellite-scale accountability:** By grounding management obligations in satellite data rather than field survey estimates, the SNTO reduces political subjectivity in conservation budget allocation and creates an independent, time-stamped audit trail.
- **Early Warning Architecture:** The Delta EHS metric implements a genuine *leading indicator* — detecting degradation trajectories before they cross irreversible ecological thresholds — consistent with the precautionary principle embedded in EU Biodiversity Strategy 2030 targets.

## 7.3 Scalability and Replicability

The SNTO architecture is designed for geographic scalability. The methodological framework is directly transferable to any:
- European Biosphere Reserve with Sentinel-2 coverage (all of Europe)
- CETS-certified or candidate territory
- Protected natural area with digitised trail infrastructure in OpenStreetMap

The full open-source stack (Python, PostGIS, Streamlit) requires no proprietary licensing, and the Sentinel-2 data source is publicly accessible through the Copernicus Open Access Hub. This positions the SNTO as a replicable **open public good** for the European conservation management community.

**Empirical replicability pilot (v1.2.0):** the claim above is no longer purely theoretical. The Sentinel-2 → Mann-Kendall trend method validated on PNSG (v1.1.0/v1.1.1) has been replicated on two additional Red de Parques Nacionales (OAPN) territories of contrasting biome — **Tablas de Daimiel** (Manchegan wetland, NDMI-driven, 5 assets) and **Monfragüe** (Mediterranean dehesa, 21 assets) — using the same GEE extraction pipeline and the identical deseasonalized, tie-corrected Mann-Kendall statistics. Rather than deploying to all 15 remaining OAPN parks at once, the rollout was deliberately staged: 15 GEE extraction templates exist for the full network (`scripts/gee_templates_oapn/`), but only the 2 pilot parks passed bioma-specific QA and are exposed in the dashboard. 12 further parks have exported data withheld pending an audit of SCL cloud/water/snow-masking artefacts specific to their biomes (Canarian volcanic badlands, maritime-terrestrial water pixels, high-mountain seasonal snow) — publishing them unaudited would overclaim statistical validity. See `docs/v1.2.0_oapn_expansion_plan.md` for the full QA criteria and staging rationale.

## 7.4 Limitations and Future Research Directions

The SNTO acknowledges the following methodological constraints:

- **Spectral confoundedness:** Drought-induced and trampling-induced NDVI depression produce similar spectral signatures; the SCM module mitigates but cannot fully eliminate this confounding in extreme drought years.
- **Trail width assumption:** The 50 m buffer standardisation may underrepresent impact zones in heavily-used trails or overestimate them in lightly-used corridors; field-calibrated buffer widths would improve precision.
- **Visitor count data quality:** The traffic_index component currently relies on permit or estimation data; integration with automated counting infrastructure (LiDAR or infrared counters) would substantially improve model precision.
- **Temporal depth (updated v1.1.1):** the operational raster-based EHS/ΔEHS pipeline remains a two-scene seasonal snapshot (seasonal ΔEHS only) — unchanged since v1.1.0. Separately, a real 2021–2026 monthly Sentinel-2 series has been ingested via Google Earth Engine for 21 curated PNSG assets (`src/platform/satellite_trends.py`, `clean_assets/timeseries/`), and Mann-Kendall trends are surfaced in the dashboard for real PNSG data. As of **v1.1.1**, the test runs on the harmonically **deseasonalized** series (2-component Fourier decomposition, Julien & Sobrino 2009), with **tie-corrected** variance (Hipel & McLeod 1994) and a **Sen's slope 95% non-parametric confidence interval** (Gilbert 1987). All 7 significant verdicts survive a **Trend-Free Pre-Whitening** robustness check (Yue-Pilon 2002) against lag-1 autocorrelation, with zero direction changes. v1.1.1 also fixed a chronological-ordering bug present in the public v1.1.0 release (`year`/`month` were sorted as strings, placing month "10"/"11" before "2"/"3"), which had corrupted the monthly series feeding the trend test. This layer is architecturally independent of the declarative `src/temporal/` spec and its `trend_gate.py` validity gate (§7.5), which still awaits activation with real data.

Future development priorities include: (1) machine learning classification of degradation typology (trampling vs. drought vs. wildfire); (2) integration of hyperspectral UAV data for validation sub-sampling; (3) extension of the platform to monitor CETS socio-economic indicators alongside ecological ones.

## 7.5 Methodological extensions implemented (F0–F7)

Following an external technical audit, the observatory was repositioned around
the **Sierra de Guadarrama National Park** and extended with the following
layers, each documented and unit-tested. Several are *frameworks* whose full
activation depends on declared data inputs, not on further method design:

| Layer | Module | Status |
|---|---|---|
| Score semantics (health vs stress) | `src/metrics/semantics.py` | ✅ unified across pipeline & dashboard |
| Real Sentinel-2 temporal trends (2021–2026, v1.1.0/v1.1.1) | `src/platform/satellite_trends.py`, `clean_assets/timeseries/` | ✅ real GEE data, 21 PNSG assets; Mann-Kendall **deseasonalized, tie-corrected, Yue-Pilon-verified** (v1.1.1) |
| Red OAPN replicability pilot (v1.2.0) | `scripts/gee_templates_oapn/`, `src/platform/satellite_trends.py` (multi-park) | ✅ 2/15 parks validated and live (Tablas de Daimiel, Monfragüe); 15 GEE templates ready; 12 further CSVs withheld pending bioma-specific mask QA |
| Statistical rigor (v1.3.0) | `src/time_series/changepoint.py`, `src/calibration/ehs_sensitivity.py`, `src/validation/cross_sensor.py` | ✅ Pettitt change points, block-bootstrap EHS confidence intervals, Morris sensitivity and Sentinel-2/MODIS cross-sensor checks |
| Decision integration and evidence governance (v1.4.0) | `src/reporting/risk_brief.py`, `src/reporting/gis_export.py`, `src/platform/evidence.py`, `src/validation/` | ✅ director-grade risk brief, GIS export, canonical evidence classes and decision gates, and field-campaign tooling; completed ground-truth campaign still pending |
| Persistent backend & operational API (v1.5.0, ADR-011) | `src/persistence/`, `src/api/v2/` | ✅ SQLAlchemy 2.0 + Alembic, typed repositories, lifecycle state machines, audit trail, minimal API-key write-auth; `/api/v2` read+write (code + tests, not yet deployed as a service). Production on Azure PostgreSQL since 2026-07-18 |
| Role-based UI evolution (v2.0.0, Fase 6) | `src/ui/navigation.py`, `app.py`, `src/ui/tabs/` | ✅ four IA decision layers (Decidir/Diagnosticar/Evidenciar/Gobernar), per-audience home, asset-as-a-page, alert triage; 14 analytical modules |
| Temporal series scaffolding (declarative, separate) | `src/temporal/` | ✅ spec + Mann-Kendall validity gate + provenance manifest; ingestion into this gate still pending |
| Data provenance & confidence surfacing | `src/platform/provenance.py` | ✅ real/calibrated/synthetic labels in dashboard |
| Stratified baselines | `src/risk_engine/baselines.py` | ✅ framework; per-habitat/altitude needs a DEM |
| Ranking uncertainty & sensitivity | `src/analysis/sensitivity.py` | ✅ weight band, robust-top-N, Monte-Carlo |
| Field validation & pseudo-validation | `src/validation/` | ✅ schema + agreement metrics; field campaign pending |
| Engineering: CI≠deploy, logging, run context | `.github/workflows/ci.yml`, `src/config/` | ✅ CI gates deploy; reproducible run provenance |
| Three-audience dashboard views | `src/platform/views.py` | ✅ técnica / gestor / tribunal with confidence verbosity |

Design notes: [`docs/temporal_series_design.md`](docs/temporal_series_design.md),
[`docs/baselines_uncertainty_design.md`](docs/baselines_uncertainty_design.md),
[`docs/field_validation_protocol.md`](docs/field_validation_protocol.md) and the
consolidated assumptions/limits register in
[`docs/informe_tecnico_limites.md`](docs/informe_tecnico_limites.md).

---

## Appendix A — Key Formulas Reference

| Formula | Symbol | Expression |
|---|---|---|
| NDVI | — | (B8 − B4) / (B8 + B4) |
| NDMI | — | (B8 − B11) / (B8 + B11) |
| EHS (Operational) | EHS | 100 × (W_NDVI × D_NDVI + W_NDMI × D_NDMI); D = clamp((B_p90 − X) / (B_p90 − B_p10), 0, 1) |
| Delta EHS (Seasonal) | ΔEHS | EHS_Summer − EHS_Spring |
| Priority Score | P | EHS × 0.60 + traffic_index × 0.40 |
| TIS Budget | B | L_m × 15.50 × (P / 100) |
| SIG (Causality) | SIG | (NDVI_landscape − NDVI_core) / NDVI_landscape |

## Appendix B — Technology Stack

| Layer | Technology | Version | Role |
|---|---|---|---|
| Raster I/O | `rasterio` | ≥ 1.3 | Band extraction, reprojection, GeoTIFF I/O |
| Zonal Statistics | `rasterstats` | ≥ 0.19 | Pixel aggregation within trail buffers |
| Geospatial DataFrames | `geopandas` | ≥ 1.0 | Vector operations, CRS management |
| Spatial Geometry | `shapely` | ≥ 2.0 | Buffer generation, geometry validation |
| Database | PostgreSQL + PostGIS | 16 + 3.4 | Spatial queries, trail geometry storage |
| Database Driver | `psycopg2-binary` | ≥ 2.9 | Python–PostgreSQL interface |
| ORM & migrations | `sqlalchemy` + `alembic` | 2.0 / 1.13 | Persistence layer & schema migrations (Fase 5, ADR-011) |
| Dashboard | `streamlit` | ≥ 1.35 | Interactive decision-support interface |
| Web Map | `pydeck` | ≥ 0.9 | Deck.gl WebGL map rendering (replaces `folium`) |
| REST API | `fastapi` + `uvicorn` | ≥ 0.111 | Programmatic data access endpoints |
| Numerical Computing | `numpy` | ≥ 1.26 | Array operations, index computation |
| Statistical Testing | custom (`src/time_series/`) | — | Mann-Kendall, z-score anomaly, Sen's slope |
| Satellite Data | ESA Copernicus / GEE | L2A | Sentinel-2 surface reflectance |
| CRS (Processing) | EPSG:25830 | — | ETRS89 / UTM Zone 30N (Peninsular Spain) |

## Appendix C — Spatial Reference Systems

| EPSG Code | Name | Usage |
|---|---|---|
| 4326 | WGS 84 (Geographic) | Data storage in PostGIS; source CRS for OSM/GEE data |
| 32630 | WGS84 / UTM Zone 30N | Native Sentinel-2 tile CRS (T30TVL) |
| 25830 | ETRS89 / UTM Zone 30N | All metric operations: buffering, length, area |

---

*This document constitutes the authoritative methodological reference for the SNTO platform as implemented primarily for Sierra de Guadarrama National Park, with the Sierra del Rincón Biosphere Reserve retained as a methodological calibration pilot. All formulas, thresholds, and cost parameters are derived from implemented code (`tis_engine.py`, `src/risk_engine/ehs.py`, `src/spatial_causality/analyzer.py`, `src/decision_confidence/assessor.py`) and validated against the references cited. Any modifications to operational parameters must be reflected in both this document and the codebase to maintain source-of-truth integrity.*

---

**Codebase Repository:** `snto-smart-tourism-observatory`
**Primary Contact:** soroush.karahrodi79@gmail.com
**Platform Version:** 2.0.0 (latest stable) | **Python:** ≥ 3.12 | **License:** Research Use
