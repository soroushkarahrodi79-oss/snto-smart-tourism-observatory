# Satellite–Field Temporal Matching Plan

**Status:** DRAFT for owner approval · **Date:** 2026-08-09 · **Phase 4 deliverable**

Governs which imagery Paper 1's field observations are compared against, and what happens when that imagery is not available.

---

## 1. Why the existing imagery cannot be used

The two scenes behind every `ehs_spring` / `ehs_summer` / `delta_ehs` value on the 218 PNSG trails are:

- `S2A_MSIL2A_20250810T110701_…_T30TVL` — labelled **"summer"**
- `S2B_MSIL2A_20260410T110619_…_T30TVL` — labelled **"spring"**

Four independent disqualifications for validation use:

1. **Chronological inversion.** `delta_ehs = EHS_summer − EHS_spring` subtracts the 2026-04-10 observation from the 2025-08-10 one. The scene labelled "later in the season" is **eight months earlier in time**. Every "primavera → verano" narrative in the repository (`docs/dossier_institucional_OAPN.md:44`, `docs/informe_tecnico_limites.md:16`) describes the reverse of the computation.
2. **Cross-year confounding.** An 8-month, two-calendar-year gap confounds seasonal phenology with inter-annual variability — including the 2022 drought recovery visible in the Universe-A annual means.
3. **Cross-sensor.** S2A vs S2B. The offset is small but uncorrected and undocumented.
4. **Non-comparable baselines.** EHS is anchored to **per-scene** P90/P10 percentiles. `EHS_spring` and `EHS_summer` are each expressed relative to their own scene's distribution, so their difference is not a difference in a fixed unit. Even with the chronology fixed, the subtraction is not a well-defined change measurement.

**Conclusion: `delta_ehs` in its current form is not a publishable quantity, and neither scene is temporally relevant to a 2026-or-later field campaign.** This is not a bug to patch; it is an input that must be acquired.

Separately: the operational product's use of these scenes is a *product* question, already flagged in `docs/audit/2026-snto-baseline/KPI_INVENTORY.md`. Paper 1 does not change the product. It declines to validate against it.

## 2. Acquisition strategy for Paper 1

### Preferred window

**A single-season, single-year composite centred on the field campaign.**

| Parameter | Specification | Rationale |
|---|---|---|
| **Target window** | Peak growing season, ± 3 weeks around the campaign midpoint | Maximum vegetation signal; NDVI/NDMI most sensitive to condition |
| **PNSG phenological peak** | ~mid-June to mid-August above 1 500 m | Montane Mediterranean; snowmelt-constrained at S4 |
| **Composite type** | Median of all qualifying acquisitions in the window | Robust to residual cloud; standard in S2 practice |
| **Minimum scenes in composite** | **3** | Below this the median is not robust; declare and use single-scene with the caveat, or abandon |
| **Sensor** | S2A + S2B both admitted **within one composite**, but the sensor mix is recorded | Harmonised L2A; mixing within a composite is standard, mixing across a *difference* is not |
| **Processing level** | L2A (Sen2Cor) — the same level the pipeline already consumes | Continuity with existing processing |
| **Tile** | T30TVL (the tile already used for PNSG) | Continuity |

### Maximum acceptable temporal offset 🔒

| Offset (field date → nearest qualifying acquisition) | Handling |
|---|---|
| ≤ 15 days | **Primary** — plot included, no flag |
| 16–30 days | **Included, flagged**; sensitivity analysis excluding these plots is mandatory |
| > 30 days | **Excluded** (Contract L-5) |
| Field date outside the composite window entirely | **Excluded** |

Thirty days is the outer bound at which montane vegetation condition can be treated as approximately stationary in peak season. It is a judgement, it is declared here in advance, and the sensitivity analysis at 15 days tests whether the conclusion depends on it.

### Cloud and quality rules 🔒

| Rule | Threshold | Action on failure |
|---|---|---|
| Scene-level cloud cover (metadata) | ≤ 20 % | Scene excluded from the composite |
| SCL masking | Exclude classes {3 shadow, 5 bare/rock, 6 water, 8 cloud-med, 9 cloud-high, 10 cirrus} | Mandatory |
| **SCL availability** | **Mandatory** | **Hard failure.** The current pipeline prints a warning and proceeds unmasked when SCL is absent — unacceptable for publication. See Backlog B-05. |
| Snow (SCL 11) | Excluded | Mandatory at S4; snow contamination is the main risk above 2 100 m |
| Valid-pixel coverage per plot cell | ≥ 70 % after masking | Plot excluded (Contract L-4) |
| Valid-pixel coverage per plot cell | 70–90 % | Included, flagged; sensitivity analysis mandatory |

Note on SCL class 5 (bare soil / rock): excluding it is correct for establishing a *healthy vegetation baseline*, but it also means genuinely bare, severely degraded ground is masked out of the reference distribution. For plot-level extraction this matters — a fully degraded plot could be dominated by SCL-5 pixels and fail the 70 % coverage rule, **removing exactly the most degraded plots from the analysis.** This is a real selection risk. Mitigation: for plot extraction, SCL 5 is **retained** (it is signal, not noise, at a trail plot) while remaining excluded from the scene-level baseline computation. This asymmetry is deliberate, is declared here, and must be stated in the manuscript.

### Cross-sensor handling 🔒

- Within a composite: S2A and S2B both admitted; the per-plot sensor mix is recorded.
- Across any difference or trend: **prohibited** without an explicit cross-sensor offset correction, which Paper 1 does not perform.
- Since Paper 1's primary analysis uses **one** composite and computes **no** temporal difference, cross-sensor bias does not enter the primary result. This is stated as a design choice, not an oversight.
- `src/validation/cross_sensor.py` (MODIS/Landsat agreement) remains **out of Paper-1 scope** — no independent-sensor series is ingested, and adding one is a separate study.

### Missing-scene fallback 🔒

Ordered, and the order is fixed in advance:

1. **Extend the window symmetrically** to ± 4 weeks, if still within the phenological peak. Record the extension.
2. **Accept a 2-scene composite** with the reduced robustness declared per plot.
3. **Accept a single scene**, declared, with a mandatory sensitivity analysis.
4. **Report the plot as MISSING satellite evidence** and exclude it.

**Never:** interpolate between scenes; borrow a value from an adjacent date outside the window; substitute a prior year's composite; substitute a neighbouring cell's value; fall back to the 2025/2026 scene pair.

> **No interpolation of evidence.** A plot without a qualifying acquisition has no satellite value. It is counted in the flow diagram and excluded. This rule has no exceptions.

## 2b. Manifest mechanism — implemented (Backlog B-06, 2026-08-09)

The acquisition manifest described throughout this document is no longer only a plan: `src/validation/acquisition_manifest.py` implements it, and `clean_assets/paper1/acquisition_manifest.json` is committed at `status="planned"` — the frozen constants above (tile, cloud threshold, composite method, offset limits, valid-pixel thresholds, and the SCL class-5 baseline/plot-extraction asymmetry) are encoded and schema-checked, but `window_start`/`window_end`/`scene_ids` are honestly empty because the target field season is not yet decided (`DATA_ACQUISITION_TRIAGE.md` open item 4). `scripts/paper1/generate_acquisition_manifest.py --validate` checks it; `--check <scenes.json>` will fail loudly the moment a real extraction's scene IDs disagree with what the manifest declares. Advancing the manifest past `planned` (fixing the window, then the scene IDs) is a later, separate step — not part of this commit — gated on the field-season decision.

## 3. Provenance record (mandatory, per plot)

Written into the analysis table for every plot, so any reviewer can trace one plot to one pixel to one scene:

```
plot_id, field_observed_at, composite_window_start, composite_window_end,
n_scenes_in_composite, scene_ids[], sensor_mix, days_offset_nearest_scene,
scl_classes_present, valid_pixel_fraction, cell_id, cell_centre_x, cell_centre_y,
gps_to_cell_centre_m, ndvi, ndmi, ehs, evidence_class
```

`evidence_class` is `real` only when every rule above is satisfied; otherwise `missing`. There is no intermediate state and no promotion path.

## 4. Reproducibility

- The acquisition specification (window, tile, cloud threshold, SCL rules, composite method) is committed as a **machine-readable manifest** before extraction, not written up afterwards. See Backlog **B-06**.
- Scene IDs are committed. The composite is regenerable from the manifest by a third party with a GEE or Copernicus account.
- The existing directory-scan provenance (`src/platform/provenance.py`, which parses `.SAFE` names under a `data/` folder that does not exist in a clean checkout) is **not** the mechanism. Paper-1 provenance is the committed manifest.

## 5. Interaction with the existing product

| Product surface | Paper-1 impact |
|---|---|
| `ehs_spring` / `ehs_summer` / `delta_ehs` on 218 trails | **Unchanged.** Paper 1 does not use them and does not modify them. |
| Two-scene ΔEHS seasonal early-warning framing | **Unchanged by this document**, but Paper 1 cannot cite it, and the chronological inversion (§1) is a product-side finding the owner should address separately. |
| Universe-A 2021–2026 Mann-Kendall trends | **Unchanged.** Out of the primary analysis (single-composite design); available as discussion context for the subset of assets that carries them. |
| `src/config/constants.py` EHS constants | **Unchanged.** The campaign-matched composite is processed with the **existing frozen constants**, so the paper evaluates the system as it is, not a variant tuned for the paper. |

That last row is the important one: **Paper 1 validates the shipped indicator, not a bespoke one.** Any constant change would break the link between the published result and the operational system, and would require owner approval, a before/after comparison and a methodological rationale.

## 6. H4 spatial-contrast extraction (sampling frame = 218 trails, decided 2026-08-09)

With the sampling frame frozen to the 218 OAPN trails (Contract §F, option F-1), the trail-to-landscape spatial contrast (`sig_segment`, H4) is a candidate predictor for every sampled segment. It **cannot** be read from the existing `scm_class` field in `data/outputs/pnsg/pipeline_a_results.geojson`: `run_scm_operational.py:111-112` computes it from `spring_raster.tif`/`summer_raster.tif` — the same 2025-08-10/2026-04-10 pair disqualified in §1. That pair is chronologically inverted, cross-year and cross-sensor whether it feeds `delta_ehs` or SIG.

**Required for H4:** re-run the same real zonal-extraction method (core/near/landscape ring buffers, `SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)`) against the **campaign-matched composite** defined in §2, for the sampled segments only. No new data source — the same composite already being extracted for `satellite_stress` supplies this. Implementation: Backlog **B-14**. If this extraction is not completed before analysis, **H4 is not tested**, per Contract §K and §J — it is not tested with the temporally mismatched existing values.
