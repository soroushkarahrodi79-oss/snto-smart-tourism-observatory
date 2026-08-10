# Paper 1 — Master Execution Plan

**Status:** DRAFT for owner review · **Date:** 2026-08-09 · **Branch:** `claude/snto-validation-audit-8vzv6u`
**Audited state:** `main` @ `c1661e1`

The executive synthesis of Phases 0–11. Everything asserted here is traceable to the phase document that established it, and every phase document is traceable to code, data or a test — not to repository prose.

---

## 1. The one-paragraph summary

SNTO has more software than it has evidence. It holds genuinely publication-grade inputs — 218 real OAPN trail segments covering 1 035 km, real Sentinel-2 L2A processing, a transparent and reproducible stress indicator, a rigorous machine-enforced evidence-provenance framework, and correct agreement mathematics with a green test suite. It holds **zero field observations**. Every scientific claim about the indicator's validity therefore rests on nothing, and the project's own non-negotiables already say so. The path to a defensible paper is short and almost entirely non-code: decide what is being sampled, acquire imagery matched to a field window, walk the park, and analyse under a plan frozen beforehand. The bottleneck is a field campaign and a research permit, not a feature.

---

## 2. Factual current state

**Verified REAL and usable:**
218 OAPN trail segments, 1 035.1 km, official cartography with PRUG management zones · Sentinel-2 L2A → NDVI (10 m) / NDMI (20 m native) processing · a transparent EHS formulation with per-scene percentile anchoring · real multi-scale zonal extraction on real rasters for the 218 trails (24 LOCALIZED / 29 MIXED / 165 LANDSCAPE) · a 2021–2026 monthly Sentinel-2 record for 21 curated sites with harmonic-deseasonalised Mann-Kendall trends · the ADR-004 evidence-class framework with a machine-readable gating matrix · Spearman, Cliff's δ, confusion matrix and Cohen's κ implemented correctly (48 tests green).

**Verified MISSING:**
**All field observations** · a temporally coherent satellite acquisition matched to any field window · plot-level satellite↔field pairing · empirical calibration of any threshold · independent verification.

**Three structural problems, one resolved by owner decision, two that no amount of further development fixes:**

1. **Two disjoint asset universes — RESOLVED 2026-08-09.** The 21 curated assets carry the defensible time series but are crags, launch sites and reserves — the two originally seeded field-validation targets were a climbing polygon and a paragliding point, neither a trail. **The owner selected the sampling frame: the 218 real OAPN trails (Contract §F, option F-1).** Consequence, propagated through the Scientific Contract, the Field Campaign Plan, the Satellite Matching Plan, `SCM_REFRAMING.md` and the Backlog: the 2021–2026 Mann-Kendall record does not apply to the sampled trails (the design was cross-sectional regardless), and the *existing* real SCM/SIG values already computed for all 218 trails are **not** usable for H4 as-is — they come from the same disqualified scene pair as `delta_ehs` (problem 2) and require a fresh extraction against the campaign-matched composite (Backlog B-14).
2. **The existing satellite pair is not usable for validation.** `delta_ehs` subtracts a 2026-04-10 scene from a 2025-08-10 scene — **the delta runs backwards in time**, across two years, across two satellites, with per-scene baselines that make the difference dimensionless in an uncontrolled way. This also disqualifies the existing SCM/SIG values (see problem 1).
3. **Sub-pixel treads.** PNSG trails are 1–3 m wide; Sentinel-2 resolves 10 m and 20 m. The indicator describes the **corridor's vegetation matrix**, of which the tread is a minority component. This is physics, not a defect, and the field design must match it rather than pretend otherwise.

---

## 3. Scientific contribution

**One question:** do Sentinel-2 stress values covary with field-measured trail degradation at co-located plots in a Mediterranean protected mountain landscape?

**Four contributions:** a transparent indicator applied to a complete real network · a support-matched stratified control–impact field validation · an explicit error-structure characterisation (FP/FN) of the indicator as a management trigger · an evidence-provenance framework that mechanically prevents real and simulated evidence from being conflated.

**One deliberately absent contribution:** causation. No visitor measurement exists, no manipulation was performed, no counterfactual is available. The paper is an association study and says so in its title.

---

## 4. Critical evidence gaps

| Gap | Severity | Substitutable? |
|---|---|---|
| Real field observations | 🔴 **BLOCKING** | **No.** Nothing substitutes for ground truth |
| Campaign-matched Sentinel-2 acquisition | 🔴 **BLOCKING** | No — but free and acquirable within a defined window |
| Ecological strata derived from cartography | 🟠 High | No — needed before site selection |
| Plot↔pixel matching machinery | 🟠 High | No — but it is desk work (B-04) |
| GPS accuracy recording | 🟡 Medium | No — one schema column (B-02) |
| Real SCM zones for H4 | 🟢 Low | No — if absent, **H4 is simply not tested** |
| Independent-sensor NDVI | 🟢 Low | Out of scope |
| Visitor counts | 🟢 Low | Band D — **never** substituted |

---

## 5. Plan by phase

| Phase | Deliverable | State |
|---|---|---|
| 0 | `PHASE0_REPOSITORY_AUDIT.md` | ✅ Complete — implementation- and data-verified |
| 1 | `PAPER1_SCIENTIFIC_CONTRACT.md` | ✅ §F frozen to F-1 (218 OAPN trails, 2026-08-09); remainder freezes after the pilot fixes sample size |
| 2 | `FIELD_CAMPAIGN_EXECUTION_PLAN.md` | ✅ Drafted — two-stage design, field-ready checklist |
| 3 | `SPATIAL_MATCHING_PROTOCOL.md` | ✅ Drafted — 20 m support, 5-subplot aggregation, dilution quantified |
| 4 | `SATELLITE_FIELD_MATCHING_PLAN.md` | ✅ Drafted — campaign-matched composite, no interpolation |
| 5 | `STATISTICAL_ANALYSIS_PLAN.md` | ✅ Drafted — **must be frozen before the first observation** |
| 6 | `SCM_REFRAMING.md` | ✅ Drafted — contrast ≠ causation; threshold provenance classified |
| 7 | `DATA_ACQUISITION_TRIAGE.md` | ✅ Drafted — A/B/C/D bands, critical path |
| 8 | `MANUSCRIPT_OUTLINE.md` | ✅ Drafted — every absent result marked `[TBD]`, no invented numbers |
| 9 | `FIGURE_PLAN.md` | ✅ Drafted — 3 items drawable today, rest gated on data |
| 10 | `JOURNAL_STRATEGY.md` | ✅ Drafted — RSASE primary, decision staged until results exist |
| 11 | `IMPLEMENTATION_BACKLOG.md` | ✅ Drafted — 14 items; **no code written pending approval** |

**Scope removed, deliberately:** independent frontend · public portal · Entra SSO · Key Vault migration · FastAPI deployment · further mobile work · Experience Builder productization · commercial pilot packaging · ML visitor forecasting · SVI trends · CETS accreditation claims · LAC/ROS carrying capacity · OAPN cross-park benchmarking · PostGIS spatial queries. All remain valid engineering; none is a Paper-1 contribution.

---

## 6. STOP / GO gates

| Gate | Condition to pass | Consequence of failure |
|---|---|---|
| **G0 — Frame** | Owner resolves Contract §F | ✅ **PASSED 2026-08-09** — F-1, 218 OAPN trails |
| **G1 — Contract frozen** | Contract and SAP frozen with commit hashes | **STOP.** Post-hoc analysis choices are unfalsifiable |
| **G2 — Permit** | PNSG research authorisation obtained | **STOP.** No fieldwork without it. Drafting started, `PNSG_RESEARCH_AUTHORIZATION_REQUEST.md` — territorial scope resolved (Madrid-only, 2026-08-09); blocked on applicant identity and the explicit go-ahead to file |
| **G3 — Window** | Acquisition manifest committed; field days inside the window | **STOP.** No temporal matching is possible otherwise |
| **G4 — Pilot** | ≥ 6 valid plot pairs; σ estimated; timing measured | **STOP.** Sample size cannot be justified |
| **G5 — Sample size** | Main n fixed from pilot σ; Contract amended | **STOP.** Reverts to asserting "15–20" without basis |
| **G6 — QA** | Field CSV passes QA; frozen with a checksum | **STOP.** Unverified data must not be analysed |
| **G7 — Match** | ≥ 30 valid plots after all exclusions | Downgrade to **pilot / data note** (§Journal §5) |
| **G8 — Analysis** | Run once, under the frozen SAP | Any deviation is a dated amendment, reported |
| **G9 — Claim audit** | Every claim passes Contract §P/§R | **STOP.** Fix the claims, not the data |
| **G10 — Reproducibility** | End-to-end rerun on a clean checkout | **STOP.** Not submittable |

**A weak or null result passes every one of these gates.** The gates guard integrity, not outcome. This must stay true under pressure — the moment a gate is relaxed because the result is disappointing, the entire framework is decorative.

---

## 7. Immediate next actions

**Owner (blocking, and not code):**

1. ✅ ~~Decide the sampling frame~~ — **resolved 2026-08-09: F-1, 218 OAPN trails.**
2. 🟡 **PNSG research authorisation — drafting started, territorial scope resolved.** `PNSG_RESEARCH_AUTHORIZATION_REQUEST.md` has the full technical case (memoria) ready, sourced from the park's own published requirements. Territorial scope decided 2026-08-09: **Madrid only** — one application, not two (propagated into Contract §F and Backlog B-01, which now filters the 218-trail pool to the Madrid-administered sector before site selection). Still blocked on: applicant identity, contact and scientific-endorsement/CV — cannot be fabricated — and the explicit go-ahead to file. Nothing has been submitted.
3. 🔲 **Fix the target field season** — this sets the satellite window and the whole schedule.
4. 🔲 **Confirm the field team** — two observers are required for the repeatability protocol.
5. 🔲 **Confirm OAPN data licence terms** for trail and vegetation layers.
6. 🔲 **Approve the Implementation Backlog**, in particular the two 🔴 items (B-02, B-05).

**Engineering (safe, unblocked, small):** B-01 site/plot generation can now proceed once B-04 (grid snapping) exists · B-08 (SCM docstrings) · ✅ **B-06 (acquisition manifest) — done 2026-08-09**, `clean_assets/paper1/acquisition_manifest.json` committed at `status=planned`, 25 tests, full suite green (1459 passed) · B-09 partial (Figure 1b, Figure 2, Table T2 from committed data) · B-14 (fresh SIG extraction for H4) once the manifest advances past `planned`.

**Flagged to the owner as separate, non-Paper-1 issues:**
- `delta_ehs` chronological inversion (Phase 0 §3) — a real product defect affecting the dossier and the technical report.
- `CLAUDE.md` is stale by ten PRs (#143–#152).
- In-code literature citations should be verified against their sources before any publication.

---

## 8. Dependency graph

```
                    Repository audited  ✅ (Phase 0)
                            │
              ✅ OWNER: sampling frame decided (F-1)   ◄── G0 PASSED
                            │
                 Scientific contract frozen           ◄── G1
                  Statistical analysis plan frozen
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
  🔲 Research          Strata derived      B-04 / B-06 / B-08
    permit  ◄── G2      from cartography     (desk, days)
        │                   │                   │
        └───────────────────┴─────────┬─────────┘
                                      │
                       Plot plan generated (B-01)
                       pairs pass SM-1…SM-5
                                      │
                       Acquisition window fixed   ◄── G3
                                      │
                             FIELD PILOT          ◄── G4
                                      │
                  σ, effect range, timing measured
                                      │
                 Sample size finalised, contract amended  ◄── G5
                                      │
                            FIELD CAMPAIGN
                                      │
                        QA → frozen CSV + checksum  ◄── G6
                                      │
                  Matched satellite extraction (B-04)  ◄── G7
                                      │
                   Locked statistical analysis (B-10)  ◄── G8
                                      │
                                  RESULTS
                                      │
                        Claim audit (B-13)           ◄── G9
                                      │
                          Manuscript written
                                      │
                    Journal selected BY OUTCOME (§Journal §5)
                                      │
                        Reproducibility rerun        ◄── G10
                                      │
                               SUBMISSION
```

Note the shape: the only parallelism is early and cheap. **Everything after the pilot is strictly serial**, and two of the three longest-lead items — the permit and the seasonal window — are calendar-bound and outside the project's control. Starting them late is the single most likely cause of a lost year.

---

## 9. Success criterion

> A skeptical external reviewer can trace every major scientific statement from raw evidence → method → result → claim, and can reproduce the analysis without relying on fabricated or mislabeled data.

Concretely, this framework delivers that when: every plot traces to a GPS position, a support cell, a scene ID and a temporal offset (B-11) · every constant is labelled literature-backed / expert-defined / heuristic / locally-validated (Table T2) · the SAP freeze predates the first observation and its hash is in the Methods · every exclusion is counted in the flow diagram · every claim passes the causal gate · the analysis reruns end-to-end on a clean checkout.

**Not "more features". Not "better numbers". Traceability, and the willingness to publish whatever the ground says.**
