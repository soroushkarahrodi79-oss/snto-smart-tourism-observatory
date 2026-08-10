# Phase 0.5 Integrity Stabilization — Final Delta

**Status:** VERIFIED — closure becomes effective when this document is merged to `main`.

This is an **additive** delta/closeout record. It does **not** rewrite or replace any
Phase 0 baseline document (`SYSTEM_BASELINE.md`, `SCIENTIFIC_CLAIMS_REGISTER.md`,
`PHASE_1_RECOMMENDATIONS.md`, `CONTRADICTIONS_AND_OPEN_QUESTIONS.md`,
`MAP_INVENTORY.md`, …). The Phase 0 baseline remains immutable historical evidence.

`82848dbf265d80bc44ac4cc264a572d820320620` is the Phase 0.5 **implementation and
verification baseline**. Formal Phase 0.5 closure becomes effective when this closeout
document is merged to `main`; that merge commit is the formal closure boundary. The
future merge SHA is not invented here — it is recorded after the closeout PR merges.

---

## 1. Baselines

| Boundary | Commit | Meaning |
|---|---|---|
| Phase 0 audit input | `ed25d0a` | Repository state actually audited on the original audit branch |
| Phase 0 audit publication | `4ed35c08aa9ee4526f416eaa8ae7b00f043684ff` | PR #143 publication of the historical baseline documents |
| Phase 0.5 implementation verification | `82848dbf265d80bc44ac4cc264a572d820320620` | Current `main` after all ten corrective items |

- `ed25d0a` is the repository snapshot the Phase 0 audit was actually performed against
  (as `SYSTEM_BASELINE.md` / the audit `README.md` record).
- PR #143 published the same audit documents later, after a rebase onto an advanced
  `main`; the rebase moved the branch's parent commit but did not re-run or rewrite the
  audit findings.
- `4ed35c08…` is therefore the **publication boundary**, not the original audit input.
  The three concepts are distinct and are not conflated.

---

## 2. Ten corrective items closed

Ten Phase 0.5 items were delivered through **eight** PRs, because two PRs each paired an
intrinsically-related pair of items (`#147` paired PR 0.5.4 + I-1; `#151` paired
PR 0.5.5 + I-5). Each PR was reviewed independently.

| Item | Purpose | PR | Merge SHA | Closeout |
|---|---|---|---|---|
| PR 0.5.1 | Unsupported causal language | #148 | `cad6ac9137ee5340564ea5d38999e877c1fac48d` | PASS |
| PR 0.5.2 | Honest provenance degradation | #149 | `674d666286eb7393f7fe7d450b1ab44e19b9e253` | PASS |
| PR 0.5.3 | Map geometry reproducibility | #150 | `d8b0d362e28f99ac9e3084b6302a2fcc03897c9a` | PASS |
| PR 0.5.4 | Test isolation / credential exposure | #147 | `3ec809a34767159e6f5d37419ff12b191abe1c5b` | PASS |
| PR 0.5.5 | Fixture reclassification | #151 | `b2bb15e193be4edc10ba474352008fd8c3829306` | PASS |
| I-1 | Repository hygiene | #147 | `3ec809a34767159e6f5d37419ff12b191abe1c5b` | PASS |
| I-2 | Stale AI handoff | #152 | `c1661e155579a30200f3fa1215b60d23599fc400` | PASS |
| I-3 | Truthful freshness / fake-live removal | #153 | `6665c57f71b46ef89617f84ae3003d7e1bd25c45` | PASS |
| I-4 | SCM attribution separated from observation at display | #154 | `82848dbf265d80bc44ac4cc264a572d820320620` | PASS |
| I-5 | Machine-readable fixture evidence + decision/display gates | #151 | `b2bb15e193be4edc10ba474352008fd8c3829306` | PASS |

---

## 3. Scientific-claim delta (Tier 1)

| Claim | Phase 0 classification | Phase 0.5 closeout state |
|---|---|---|
| C-01 | MISLEADING | ACCURATELY QUALIFIED |
| C-02 | MISLEADING | ACCURATELY QUALIFIED |
| C-03 | CONTRADICTED BY IMPLEMENTATION | ACCURATELY QUALIFIED / NO LONGER ASSERTED |
| C-04 | CONTRADICTED BY IMPLEMENTATION | ACCURATELY QUALIFIED |
| C-05 | MISLEADING | ACCURATELY QUALIFIED |

**Tier-1 Misleading: 0. Tier-1 Contradicted by implementation: 0.**

- Causal assertions ("caused by visitor pressure", "confirmed") became explicit **working
  hypotheses** that require independent field verification (KPI 7).
- The fabricated "driven by the 2022 drought" attribution was **removed**.
- The fixture portfolio is explicitly **`SYNTHETIC`** (no longer "20 activos reales").
- The spectral-style fixture visualization is explicitly **not** a direct spectral
  measurement ("gradiente derivado del EHS registrado … no es una medición espectral
  directa").
- Real evidence alone still does **not** license causal/confirmatory language. The
  four-part causal gate remains required in full: **REAL evidence + validated method +
  supported attribution + independent verification.**

---

## 4. Provenance and reproducibility delta

**Sentinel provenance** — three honest states (`src/platform/provenance.py`):

| State | Condition | Result |
|---|---|---|
| A | raw scenes + derived output present | `REAL`, provenance complete, locally reproducible, real `n_scenes` |
| B | derived output only, raw scenes absent | `REAL`-derived, provenance incomplete, not locally reproducible, `n_scenes = None` |
| C | derived output absent | `MISSING` |

`REAL` denotes the **provenance class**, not causal validation. State B never fabricates a
scene count.

**Map determinism** — the Python `hash()`-based fallback was removed; synthetic fallback
geometry is deterministic (BLAKE2b-keyed on `asset_id`); independent interpreter processes
reproduce identical fallback coordinates; an explicit map centre is required (no silent
default); real Pipeline-A geometry is unaffected.

**Test isolation** — `.env` is not loaded as an import-time side effect (`load_dotenv()`
calls are function-scoped); no tracked Python cache artifacts remain; running the suite
leaves the tracked tree clean.

---

## 5. Evidence governance delta

```
Fixture assets verified:
28 / 28 = EvidenceClass.SYNTHETIC
0 = REAL
0 = CALIBRATED
```

For every `SYNTHETIC` fixture asset, the canonical policy

```python
supports(asset.evidence_class, DecisionUse.MONITORING)
supports(asset.evidence_class, DecisionUse.PRIORITIZATION)
supports(asset.evidence_class, DecisionUse.INTERVENTION)
supports(asset.evidence_class, DecisionUse.PUBLIC_REPORTING)
```

all evaluate to **`False`**.

Fixture calculations may be computed and displayed for prototype/scenario purposes, but
they cannot authorize monitoring, prioritization, intervention or public-reporting claims
under the current evidence policy. Runtime gates (`dashboard.py`, `render_widgets.py`,
`territorial_brief.py`) **consume the canonical `supports()` policy** rather than
duplicating authorization rules.

---

## 6. UI integrity delta

**Truthful freshness (I-3):** the 60-second autorefresh, the render-clock `"Actualizado"`
label and cycle counter, the pulsing "live" indicator, and the hard-coded
`REPORT_DATE = "2026-06-12"` were all removed. The generation date uses provenance
metadata when available; an unknown value is `None` machine-readable and `"no registrada"`
in presentation. The application is not described as live or real-time.

**SCM attribution separation (I-4):** EHS/ΔEHS are indicators derived from real Sentinel-2
observations; SCM is presented explicitly as `Atribución SCM` / `MODELO SIG`, a rule-based
attribution classification — **not** a causal measurement, a validated attribution, or a
confirmed cause. The table, map tooltip and PRUG report carry this distinction visually and
semantically.

---

## 7. Audit correction discovered during implementation

The historical baseline correctly detected that SCM attribution was displayed as if it had
the same epistemic standing as environmental measurement. However, its specific **live-path
premise** became stale. The current live chain is:

```
run_pipeline_a_filemode.py
    -> imports SIG helpers from run_scm_operational.py
    -> computes SIG from real Sentinel-2 raster inputs
    -> writes pipeline_a_results.geojson
    -> src/platform/real_trails.py loads RealTrail.scm_class
```

The currently live `RealTrail.scm_class` therefore does **not** come from the separate
α-decay simulator in `src/spatial_causality/` (whose `zones/` directory does not exist).

The historical finding remains valid at the level of evidence-display conflation, but its
specific α-decay-simulation explanation for the live `RealTrail` path was stale. Phase 0.5H
corrected the live presentation without rewriting the historical audit baseline. Real source
pixels do not by themselves establish causal validity.

---

## 8. Verification

| Check | Result |
|---|---|
| Full tracked pytest | 1486 passed / 11 skipped / 0 failed |
| Populated `.env` pytest | 1486 passed / 11 skipped / 0 failed |
| Coverage | 83.99% |
| Coverage gate | 80% |
| Sentinel planted in populated `.env` | 0 stdout/stderr matches |
| Credential / DSN scan | 0 real matches |
| Tier-1 Misleading | 0 |
| Tier-1 Contradicted by implementation | 0 |
| Fixtures | 28/28 SYNTHETIC |
| SYNTHETIC DecisionUse authorization | 0/4 authorized |
| Tracked Python cache artifacts | 0 |

A temporary non-empty `.env` containing a deliberately planted, non-application
secret-shaped sentinel was physically present during the full-suite run. The sentinel was
absent from captured pytest output, and the standard credential/DSN scan found no leaked
values. (The sentinel value itself is not reproduced here.)

---

## 9. Residual risks and explicitly deferred work

Already-approved deferrals (out of Phase 0.5 scope):

- re-rooting the decision layer on the 218 real trails;
- spectral-map consolidation/removal;
- mobility / real SCM-zone / SVI-history ingestion;
- field validation campaign;
- `platform/` package decomposition;
- legacy router / phase-report removal;
- production PostGIS migration.

Non-blocking Phase 1 claim-review note: the aggregate KPI 1 language around "emergency
intervention" remains a strong management-action phrase. Current I-5 authorization gates
prevent synthetic fixture evidence from licensing intervention, so this is not a Phase 0.5
closure blocker; the wording should be reconsidered within the Phase 1 scientific/product
contract. It is deliberately not changed in this PR.

---

## 10. Definition of Done

Criteria 1–5 were verified against `main @ 82848db…`:

| Criterion | State |
|---|---|
| 1 — Ten items merged, independently reviewed | PASS |
| 2 — `pytest` green with populated `.env`, no credential/DSN in output | PASS |
| 3 — Coverage ≥ 80% | PASS |
| 4 — Tier-1 Misleading = 0, Contradicted = 0 | PASS |
| 5 — I-5 machine-readable evidence + decision/display gates | PASS |
| 6 — Short Phase 0.5 delta note added | SATISFIED BY THIS DOCUMENT WHEN MERGED |

Criterion 6 is fulfilled by this additive delta document when the closeout PR is merged
to `main`.

---

## Closure statement

All substantive Phase 0.5 integrity criteria were verified against
`main @ 82848dbf265d80bc44ac4cc264a572d820320620`.

This document is the remaining Definition-of-Done artifact. Phase 0.5 therefore becomes
formally **CLOSED** when this closeout document is merged to `main`.

The merge commit of the closeout PR is the formal Phase 0.5 closure boundary.

Phase 1 has not started.
