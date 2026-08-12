# SNTO Phase 1.0 — Scientific & Product Contract

**Current phase.** Phase 1.0 defines *what SNTO is scientifically allowed to
observe, infer, recommend, evaluate and claim, and under exactly which evidence
conditions* — before adding any capability. It codifies (does not invent) the
conservative posture already implemented across `src/platform/evidence.py`,
`resolve_signals()`, the visitor-pressure contract, and CETS readiness.

## Read these in order
1. [`SCIENTIFIC_PRODUCT_CONTRACT.md`](SCIENTIFIC_PRODUCT_CONTRACT.md) — purpose,
   unit of analysis, evidence ontology, claim ladder, four-pillar contract,
   missing-data/uncertainty rules, hard gates, exit criteria.
2. [`EVIDENCE_DECISION_MATRIX.md`](EVIDENCE_DECISION_MATRIX.md) — evidence
   combination → authorized use, plus the current product-surface audit.
3. [`PHASE_1_ROADMAP.md`](PHASE_1_ROADMAP.md) — ordered work packages (WP-1…WP-5).
4. [`claim_ladder.json`](claim_ladder.json) — machine-readable ladder (WP-2 wires
   it into code).
5. [ADR-016](../decisions/ADR-016-claim-ladder-and-decision-gates.md) — the
   governing decision.

## Answers in under five minutes (multi-agent operating contract)
- **What phase are we in?** Phase 1.0 — Scientific & Product Contract.
- **What is allowed?** L1–L4 today (L5 for *non-restrictive* recommendations
  only). See the matrix.
- **What is blocked?** Effectiveness (L6), causality/regeneration (L7),
  restrictive recommendations, "validated"/"regenerative outcome" language —
  gated on #26 field validation and Pillars 1 & 3.
- **What should I work on next?** **WP-2** (enforce the ladder in code) once WP-1
  is merged. The only open hard gate is **#26** (manual field campaign).
- **Prohibited shortcuts:** fabricating field/pressure data, promoting
  SIMULATED/SYNTHETIC to REAL, inventing thresholds, closing/weakening #26,
  forecasting without a real asset-level pressure series.
- **Source-of-truth order:** `main` → data/artifacts → tests → ADRs → these docs
  → roadmap → merged PRs → issues → handoffs → any AI statement.

## Not part of Phase 1.0
The uncommitted `docs/paper1/` and `.agents/` material (Track-B *publication*
contract from another agent) is complementary but **not canonical** and not
merged here. See the WP-1 PR description for the reconciliation flag.
