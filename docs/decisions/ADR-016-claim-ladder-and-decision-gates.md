# ADR-016 — SNTO Claim Ladder & Evidence→Decision Gates (Phase 1.0)

- **Status:** Accepted (documentation-level). The ladder is defined and
  machine-readable (`docs/phase1/claim_ladder.json`) but **not yet enforced in
  code** — enforcement is Phase-1 work package WP-2. No code, schema, or public
  claim changes with this ADR.
- **Date:** 2026-08-12
- **Deciders:** Owner (pending review)
- **Related:** ADR-003 (validation gate before authoritative claims, #26),
  ADR-004 (evidence classes; `src/platform/evidence.py`), ADR-011 (persistence),
  the visitor-pressure data contract (`src/visitor_pressure/`), and
  `docs/phase1/SCIENTIFIC_PRODUCT_CONTRACT.md`.
- **Supersedes / conflicts:** none. It *formalises and unifies* rules already
  implemented piecewise in `evidence.py` (the class×use gating matrix),
  `cets_readiness.py` (REAL as the hard ceiling), and the visitor-pressure audit
  (`INSUFFICIENT_EVIDENCE`). It does not relax any of them.

## Context

SNTO already separates evidence classes (REAL / CALIBRATED / SIMULATED /
SYNTHETIC / MISSING) and gates four decision uses (monitoring, prioritization,
intervention, public reporting) in `src/platform/evidence.py`. It also refuses
to inherit evidence via `resolve_signals()` live probes, and holds visitor
pressure at `INSUFFICIENT_EVIDENCE`. But these rules were scattered across
modules and docs, expressed at different granularities, and there was **no
single ordered statement** of *what SNTO may claim, under exactly what evidence
conditions* — the thing a future agent, reviewer, or institution needs to read
in five minutes.

Phase 1.0 requires one canonical, ordered, machine-translatable **Claim Ladder**
and one **Evidence→Decision Matrix**, so that every product surface and future
work package can be checked against a single authority.

## Decision

Adopt an **8-level Claim Ladder (L0–L7)** as the canonical statement of SNTO's
epistemic altitude, and an **Evidence→Decision Matrix** mapping evidence
*combinations* to authorized *uses*. Both are defined in `docs/phase1/` and the
ladder is mirrored in `docs/phase1/claim_ladder.json` for later enforcement.

Ladder (full conditions in the contract):

| Level | Claim | Ceiling condition |
|---|---|---|
| L0 | Availability ("we hold data") | any class, incl. MISSING |
| L1 | Observation ("we observed X") | REAL **and OBSERVED** (reflectance, cartography) — not derived indices |
| L2 | Derived condition | REAL-provenance **DERIVED** (NDVI/EHS) + declared transform + quality metadata; MODELLED/HYPOTHESIZED (SCM) capped here |
| L3 | Association | ≥2 **measured** variables + alignment + explicit statistic + uncertainty |
| L4 | Decision-support signal (flag / prioritize investigation & inspection) | REAL, or CALIBRATED as context — **not** prioritize intervention/budget/restriction |
| L5a | Observational recommendation (monitor / inspect / verify) | REAL state + explicit uncertainty |
| L5b | Committing recommendation (resource-committing **or** restrictive) | **blocked**: ≥L6 evidence; restrictive also needs owner policy |
| L6 | Effectiveness assessment | complete management record + pre/post REAL + **comparator/counterfactual** + confounder discussion + field |
| L7 | Causal attribution (high-confidence, BACI-supported) | L6 + control/impact design + stated assumptions + **approved field-validation pre-registration** — no mechanical p-rule |

**Invariants:**

1. SIMULATED, SYNTHETIC, and MISSING authorize **nothing above L0**.
2. **REAL is the ceiling for un-validated claims** — REAL provenance alone never
   authorizes L6 or L7. Field validation (#26) is a hard gate for L7.
3. **`REAL` ≠ observed:** a REAL-provenance *derived* value (EHS/NDVI) enters at
   L2, never L1; a MODELLED/HYPOTHESIZED value (SCM) is capped at an L2 hypothesis.
4. **No numeric agreement threshold (ρ, κ, p, DI) is product policy.** L6/L7
   require satisfying the *approved, tracked* field-validation protocol and
   pre-registration; the numbers live there, not in the ladder. (Provenance:
   only Cliff's δ = 0.474 is tracked — `agreement.py`, Romano et al. 2006 — and
   only as an effect-size label, not a causal gate; ρ≥0.60 / κ≥0.60 / p<0.01 /
   DI≥50 have **no tracked source** and are **not** canonized.)
5. **Restrictive** recommendations (closures, quotas, access limits) live at
   **L5b** and are **not** authorized on REAL alone; they need ≥L6 evidence plus
   explicit owner policy sign-off. Resource-committing (non-restrictive)
   interventions are also L5b.
6. Municipal MITMA mobility is macro-territorial **context only**; it does not
   satisfy the visitor-pressure *target-variable* gate.
7. The unit of analysis is fixed (see contract §B): observed unit = **asset
   (trail/segment)**; persisted entity = **managed_asset**; aggregation =
   **territory**; validation = **plots** co-located with assets.
8. **Regenerative Outcome is an evaluation layer, not an evidence pillar**, and is
   out of scope for Phase 1.

## Consequences

- **Positive:** one authority; product surfaces auditable against it; future
  agents cannot silently drift upward; the ladder is ready to become executable
  policy (WP-2) that extends `evidence.py`.
- **Cost:** WP-2 must reconcile the ladder JSON with `evidence.py` — including
  **splitting the coarse `DecisionUse.INTERVENTION`** into order-inspection
  (L4/L5a) vs commit-resources (L5b), since this ladder is deliberately stricter
  than the current code on resource-committing recommendations — and add tests;
  until then the ladder is advisory doc.
- **Watch item (not a clean GREEN):** the TIS euro-efficiency verdict is a known
  `OVERSTATED` claims-register item (**C-10**); its live UI text must not present
  SIMULATED scenario coefficients as observed/forecast effect. Verifying/fixing
  that surface is tracked in the audit, not fixed by this docs PR.
- **Otherwise:** no current surface is knowingly above its authorized level; this
  ADR makes the existing conservative posture explicit and testable.

## Review date

Re-review when WP-2 lands (ladder enforced in code) or when #26 field data is
ingested (unlocks L6/L7 evaluation), whichever first.
