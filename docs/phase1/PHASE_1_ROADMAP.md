# SNTO Phase 1.0 — Executable Roadmap

Ordered work packages that move SNTO from its current baseline toward
**empirically defensible decision intelligence**. Small, one focused PR each. No
giant multi-feature phase. Authority: [`SCIENTIFIC_PRODUCT_CONTRACT.md`](SCIENTIFIC_PRODUCT_CONTRACT.md),
ADR-016.

**Principle:** technical availability ≠ priority. Work is sequenced by what
raises defensible evidence, not by what the codebase *could* do.

---

## WP-1 — Scientific & Product Contract (THIS PR)
- **Objective:** one canonical contract + evidence→decision matrix + claim ladder
  + ADR-016; point `CLAUDE.md` at it.
- **Why:** Phase 1 defines what maturity means before adding any capability.
- **Prerequisite:** none. **Evidence:** existing repo only.
- **Files:** `docs/phase1/*`, `docs/decisions/ADR-016*`, `CLAUDE.md`,
  `docs/decisions/README.md`.
- **Deliverable / DoD:** merged docs; no RED surface; #26 still sole open issue.
- **Code required:** no. **Owner work:** review + merge.
- **Blocked-by:** none. **Unlocks:** WP-2, WP-3.

## WP-2 — Enforce the claim ladder in code
- **Objective:** turn `claim_ladder.json` into executable policy that extends
  `src/platform/evidence.py`'s `DecisionUse` gate; add a test asserting the
  JSON, ADR-016, and `evidence.py` agree.
- **Why:** a machine-checked contract prevents silent upward drift by any agent.
- **Prerequisite:** WP-1 merged. **Evidence:** none new (logic + tests).
- **Files:** `src/platform/evidence.py` (or a new `src/platform/claim_ladder.py`),
  `tests/unit/test_claim_ladder.py`, `docs/phase1/claim_ladder.json`.
- **Deliverable / DoD:** ladder loaded and enforced; CI test green; no behaviour
  change to existing surfaces (they already comply).
- **Code required:** yes. **Owner work:** review.
- **Blocked-by:** WP-1. **Unlocks:** auditable enforcement for all later WPs.

## WP-3 — Management-Response recording contract (schema spec only)
- **Objective:** specify the complete intervention record (what/where/when/
  who-authorized/cost/duration/target/intended-effect/completion) as a documented
  contract + an *additive, unmigrated* schema proposal; do **not** migrate prod.
- **Why:** L6 effectiveness is impossible without a usable management record;
  today's `interventions` table is a thin stub.
- **Prerequisite:** WP-1. **Evidence:** none (design).
- **Files:** `docs/phase1/management_response_contract.md`, proposed fields for
  `src/persistence/models/intervention.py` (spec, not applied).
- **Deliverable / DoD:** reviewed contract; migration deferred to a data WP.
- **Code required:** spec only (no migration). **Owner work:** confirm the field
  set matches OAPN practice (real-world fact → may need owner input).
- **Blocked-by:** WP-1. **Unlocks:** L6 once real records + before/after exist.

## WP-4 — Visitor-pressure: ingest one real feed (data, un-gated)
- **Objective:** generate `src/mobility/snapshot/mobility.json` via the committed
  MITMA path (`etl_mobility.py`), OR onboard one real asset-level counter series;
  re-run the readiness audit and `resolve_signals()`; update the docs claim in the
  same PR.
- **Why:** upgrades Pillar 1 from `INSUFFICIENT_EVIDENCE` toward `PARTIALLY_READY`
  with **zero code change** — the gate and fallback already exist.
- **Prerequisite:** WP-1. **Evidence:** real MITMA export (macro context only) or
  a real counter feed.
- **Files:** `src/mobility/snapshot/mobility.json` (generated), doc claim update.
- **Deliverable / DoD:** readiness ≠ `INSUFFICIENT_EVIDENCE` for the ingested
  feed; MITMA labelled macro-territorial context, never trail footfall.
- **Code required:** run existing ETL. **Owner work:** provide/authorize the feed.
- **Blocked-by:** WP-1; data availability. **Unlocks:** L4 pressure context.
- **⚠ Do NOT** build forecasting/ML on this until a real *asset-level* series
  exists (contract §I gate 2).

## HARD GATE — #26 Field Validation Campaign (unchanged, owner/manual)
- **Objective:** collect real ground-truth (compaction/cover/erosion) on PNSG
  priority plots per `docs/field_validation_protocol.md`.
- **Why:** the only path to L6/L7; blocks all validated/causal/regenerative claims.
- **Status:** tooling, protocol, agreement runner all merged; **field data not
  collected.** This is manual field work, not a code task.
- **Unlocks:** WP-5 (satellite↔field agreement), then L7 evaluation.
- **Do not close, weaken, or simulate.**

## WP-5 — Satellite↔field agreement (only after #26)
- **Objective:** run `src/validation/agreement.py` on real plots; report ρ/δ/κ
  against the pre-registered thresholds; emit the L3/L7 verdict honestly.
- **Prerequisite:** #26 data ingested. **Blocked-by:** #26.
- **Deliverable / DoD:** agreement report; claim level updated per result.

---

### Sequence
`WP-1 → WP-2 ; WP-3 ; WP-4` (parallelisable after WP-1) → **#26 (hard gate)** →
`WP-5`.

### Deliberately excluded from Phase 1 (see contract §J)
Forecasting/ML · PostGIS prod migration · API deployment · Experience Builder
Batch C · management-record *migration* · regenerative-outcome evaluation surface
· multi-park expansion · Alpine · new indices · new visualizations · mobile
changes · BI integrations. Each is technically available and each is postponed
because it does not raise defensible evidence at this phase.

### Issue policy
No new GitHub issues are opened by WP-1. **#26 remains the sole open issue.** A
work package graduates to a GitHub issue only when it is genuinely ready
(prerequisite merged, unblocked) — the next candidate is **WP-2** once WP-1 is
merged.
