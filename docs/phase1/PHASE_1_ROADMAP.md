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
  `src/persistence/models/intervention.py` (spec, not applied). Minimum field set:
  intervention id · asset · spatial footprint · decision date · implementation
  start/end · intervention type · authorized by · target pressure/state · intended
  mechanism · **planned cost** · **actual cost** · completion state · monitoring
  window · evidence links · triggering recommendation.
- **Deliverable / DoD:** reviewed contract; migration deferred to a data WP.
- **Code required:** spec only (no migration). **Owner work:** confirm the field
  set matches OAPN practice (real-world fact → may need owner input).
- **Blocked-by:** WP-1. **Unlocks:** L6 once real records + before/after exist.

## WP-4 — Visitor-pressure: ingest MITMA as macro-context (does NOT lift the target gate)
- **Objective:** generate `src/mobility/snapshot/mobility.json` via the committed
  MITMA path (`etl_mobility.py`); surface the municipal figure as **macro-context
  only**; re-run `resolve_signals()`; update the docs claim in the same PR.
- **Why / honest scope:** this moves MITMA from MISSING to an L4 **context**
  signal — it does **NOT** change visitor-pressure `ReadinessStatus`, because a
  municipal inbound-trip count is **not** the pressure *target variable* (trail/
  park footfall). Calibrating municipal mobility → park pressure is an open
  research problem, not a wiring task. The `INSUFFICIENT_EVIDENCE` *target* gate
  stays honest.
- **Prerequisite:** WP-1. **Evidence:** real MITMA export (macro context only).
- **Files:** `src/mobility/snapshot/mobility.json` (generated), doc claim update.
- **Deliverable / DoD:** MITMA shown as labelled macro-context, never trail
  footfall; pressure-target readiness explicitly unchanged.
- **Code required:** run existing ETL. **Owner work:** authorize the feed.
- **Blocked-by:** WP-1; data availability. **Unlocks:** L4 macro-context only.
- **⚠ Do NOT** build forecasting/ML on MITMA, and do **not** claim it upgrades the
  pressure target (contract §F Pillar 1, §I gate 2). A separate future WP is
  needed for a real *asset-level* counter series.

## HARD GATE — #26 Field Validation Campaign (INDEPENDENT — can start now, owner/manual)
- **Objective:** collect real ground-truth (compaction/cover/erosion) on PNSG
  priority plots per `docs/field_validation_protocol.md`.
- **Why:** the only path to L6/L7; blocks all validated/causal/regenerative claims.
- **Status:** tooling, protocol, agreement runner all merged; **field data not
  collected.** Manual field work — **no repository prerequisite**; it does **not**
  depend on WP-2/3/4 and should begin as early as the owner can mobilise it.
- **Unlocks:** WP-5 (satellite↔field agreement), then L6/L7 evaluation.
- **Do not close, weaken, or simulate.**

## WP-5 — Satellite↔field agreement (only after #26)
- **Objective:** run `src/validation/agreement.py` on real plots; report the
  agreement statistics **against the approved pre-registration** (not a threshold
  invented here); emit the L3/L6/L7 verdict honestly.
- **Prerequisite:** #26 data ingested. **Blocked-by:** #26.
- **Deliverable / DoD:** agreement report; claim level updated per result. No
  numeric pass threshold is adopted from the uncommitted `paper1/` draft until the
  owner commits and approves it.

---

### Dependency graph (reality, not narrative order)
```
WP-1 (this PR) ──unlocks──> { WP-2 , WP-3 , WP-4 }   (mutually independent)
#26 field campaign ─────── independent; startable NOW; no code prerequisite
WP-5 ── depends on ──> #26
```
- WP-2 does **not** need WP-3 or WP-4; #26 does **not** wait for any WP.
- Management-response (WP-3) is **not** required before MITMA context (WP-4).
- Only WP-5 is truly gated (on #26).

## WP-C10 — Re-verify the TIS euro-efficiency UI text (corrective, small)
- **Objective:** confirm the live intervention/TIS UI does not present SIMULATED
  scenario coefficients (register item **C-10**, Q-05 illustrative-only) as
  observed or forecast effect; correct the text if it does.
- **Why:** the one **RED-RISK** surface in the audit; a runtime-text issue, so it
  is out of scope for the docs-only WP-1 but must not be forgotten.
- **Prerequisite:** none (independent). **Files:** `src/ui/tabs/tab_diagnostic.py`
  or the TIS reporter text; a claims-register cross-check.
- **Code required:** yes (text/label only). **Blocked-by:** none.
- **Deliverable / DoD:** C-10 surface verified/fixed; register updated.

## WP-C11 — LAC/ROS capacity-at-standard: attribution precondition (corrective, small) — ✅ DONE (PR #158)
- **Objective:** stop emitting `capacity_at_standard` for assets whose attribution
  does not support it, and gate the surface that renders it.
- **Why:** the **second RED-RISK** surface (see `EVIDENCE_DECISION_MATRIX.md` §2).
  `capacity_at_standard` (`src/platform/lac_ros.py:107`) computes
  `P_std = P·(100−standard)/(100−EHS)`; the denominator is the *entire* health
  deficit, so the formula attributes **all** degradation to visitor use — while the
  system's own SCM classifies **165 of 218** real PNSG trails `LANDSCAPE_DRIVEN`.
  For those, a climate/landscape deficit is converted into a visitor threshold. It
  is rendered per asset (`src/ui/tabs/tab_portfolio.py:219`) from **SYNTHETIC**
  fixture inputs **with no `supports()` gate**, producing a quota-shaped number
  under an L5a ceiling that forbids restrictive recommendations.
- **Prerequisite:** none (independent, like WP-C10).
- **Files:** `src/platform/lac_ros.py`, `src/platform/pressure_capacity.py`,
  `src/ui/tabs/tab_portfolio.py`, a test module beside the existing LAC/ROS tests.
- **Approach:** return `None` when attribution is not `LOCALIZED_IMPACT` — the
  function **already** returns `None` for the near-pristine case, so absence is an
  established, honest output here. Apply the canonical `supports()` gate. State the
  attribution precondition in the docstring and the UI caption.
- **Deliverable / DoD:** no capacity figure shown for an asset whose attribution
  does not support it; surface re-audited from RED to GREEN; ladder ceiling
  unchanged at L5a; no new index, enum, threshold or dependency.
- **Stop condition:** if the fix would require inventing a dose-response or a
  non-visitor deficit share, **stop and escalate**. The correct output is absence,
  not a fabricated decomposition.
- **Code required:** yes. **Blocked-by:** none.

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
