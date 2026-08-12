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
| L1 | Observation ("we observed X") | REAL |
| L2 | Derived condition | REAL inputs + declared method |
| L3 | Association | ≥2 REAL series + declared statistics |
| L4 | Decision-support signal (flag / prioritize investigation) | REAL, or CALIBRATED as context |
| L5 | Management recommendation (non-restrictive) | REAL state + explicit uncertainty |
| L6 | Effectiveness assessment | REAL before/after **+ complete management record** |
| L7 | Causal attribution | BACI field validation (#26 pre-registration: Cliff's δ ≥ 0.474, p<0.01) |

**Invariants:**

1. SIMULATED, SYNTHETIC, and MISSING authorize **nothing above L0**.
2. **REAL is the ceiling for un-validated claims** — REAL provenance alone never
   authorizes L6 or L7. Field validation (#26) is a hard gate for L7.
3. **Restrictive** management recommendations (closures, quotas, access
   limits) are **not** authorized at L5; they require at least L6-grade evidence
   plus explicit owner policy sign-off.
4. Municipal MITMA mobility is macro-territorial **context only** and never
   authorizes a trail-footfall or pressure claim on its own.
5. The unit of analysis is fixed (see contract §B): the observed unit is the
   **asset (trail/segment)**; the persisted product entity is the
   **managed_asset**; the aggregation unit is the **territory**; field
   validation operates on **plots** co-located with assets.

## Consequences

- **Positive:** one authority; product surfaces auditable against it; future
  agents cannot silently drift upward; the ladder is ready to become executable
  policy (WP-2) that extends `evidence.py`.
- **Cost:** WP-2 must reconcile the ladder JSON with `evidence.py`'s existing
  `DecisionUse` gate and add tests; until then the ladder is advisory doc.
- **Neutral:** no current SNTO surface is knowingly above its authorized level
  (see the Phase-1 product audit in the contract §F); this ADR mostly makes the
  existing conservative posture explicit and testable.

## Review date

Re-review when WP-2 lands (ladder enforced in code) or when #26 field data is
ingested (unlocks L6/L7 evaluation), whichever first.
