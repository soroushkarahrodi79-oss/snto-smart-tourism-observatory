# Phase 1 — Data Source Inventory Delta

**Status:** Additive. This document does **not** rewrite or replace
`DATA_SOURCE_INVENTORY.md` or any other Phase 0 baseline document — those remain
immutable historical evidence, per the precedent set by `PHASE_0_5_DELTA.md`.
It records sources identified *after* the Phase 0 baseline was published.

**Authority:** `docs/phase1/SCIENTIFIC_PRODUCT_CONTRACT.md` §C (evidence
ontology), §F Pillar 1 (proxy hierarchy), §I (validation gates).

---

## D-10 · OAPN official visitor statistics — *Informe de Visitantes de la Red de Parques Nacionales*

| Field | Value |
|---|---|
| Provider | Organismo Autónomo Parques Nacionales (OAPN) / MITECO |
| Access | Official OAPN publication. **Not accessed, not downloaded, not ingested by this repository.** |
| Geographic coverage | Red de Parques Nacionales, reported **per park**. PNSG is in scope. |
| Spatial resolution | **park-level** (sub-park breakdowns, where published, are to be verified against the report itself — not assumed) |
| Temporal resolution | **annual** (the published report). Any finer underlying cadence is unverified. |
| Measurement method | An **estimation methodology**, heterogeneous across parks. **To be read and recorded from the report's own methodology section before any figure enters this repository.** |
| Update frequency | annual |
| Licence | To be verified. The inventory already notes that licence terms across sources are attributed but never analysed (`DATA_SOURCE_INVENTORY.md`, cross-cutting finding 5). |
| Status | **not ingested** |
| Transformation | none |
| Caching | n/a |
| Provenance retention | n/a — this entry registers a *source*, not a datum |
| Failure behaviour | n/a — nothing consumes it |
| Tracked in git | **no** — no file, no figure |

### Evidence classification (reuses the existing ontology; no new vocabulary)

Two axes, per contract §C:

- **Axis 1 — provenance:** `REAL` (official authority, official publication).
- **Axis 2 — epistemic operation:** **ESTIMATED / MODELLED**, because the figure
  is produced by an estimation method, not a census.

**Consequence: it enters the claim ladder at L2, not L1.** `REAL` does not mean
"observed" — the same rule that places NDVI/EHS at L2 places an official
estimate at L2. It is rank **5** in the Pillar-1 proxy hierarchy.

### Three constraints (stated so no later agent can drift)

1. **Park-level annual ≠ trail-level footfall.** It cannot become ground truth
   for any asset, cannot validate any trail-level claim, and cannot be
   disaggregated to the 218 trails by any method available in this repository.
2. **It does not lift the visitor-pressure target gate.** Only ranks 1–2 of the
   proxy hierarchy can. An annual series additionally fails the depth and
   frequency policy in `src/visitor_pressure/data_validation.py` (an isolated
   annual value is explicitly not longitudinal evidence). `ReadinessStatus`
   stays `INSUFFICIENT_EVIDENCE`.
3. **It is not a MITMA calibration source.** Municipal inbound trips (D-06) and
   park visitor estimates measure different universes. Order-of-magnitude
   agreement is a sanity check, never a calibration.

### Why register it at all

It is the only official, institutionally recognised, cross-park-comparable
visitor evidence for PNSG, and it was entirely absent from D-01…D-09. Registered,
it supplies:

- an **official institutional anchor** to cite in place of the SYNTHETIC
  `visitor_capacity_annual` constant (K-10, mislabelled "visitors/yr"); and
- a **comparability denominator** for `src/benchmarking/oapn_rollup.py`, which
  today rolls up satellite trend with no visitor denominator at all.

Neither use is activated by this entry. Both require the methodology
verification above first.

### Open items (owner)

- [ ] Supply / authorise the report edition to be used.
- [ ] Record its verified spatial resolution, measurement method, and licence
      terms into this entry.
- [ ] Only then decide, as a separate work package, whether any figure is held.

**No visitor figure appears anywhere in this document, and none may be added
until the item above is closed.**
