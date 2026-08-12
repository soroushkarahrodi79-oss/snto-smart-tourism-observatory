# SNTO Phase 1.0 — Scientific & Product Contract

**Status:** Canonical (documentation-level). Defines what SNTO is *scientifically
allowed to observe, infer, recommend, evaluate and claim*, and under exactly
which evidence conditions. It tightens claims; it adds no feature and changes no
public claim.
**Authority:** ADR-016 (claim ladder & gates), ADR-004 (evidence classes),
ADR-003 (validation gate #26).
**Date:** 2026-08-12 · **Deciders:** Owner (pending review).
**Source of truth this document must not outrank:** current `main` →
data/artifacts → tests → ADRs → this contract. If code and this contract
disagree, **code wins and this document is wrong** — fix the document.

Companion documents: [`EVIDENCE_DECISION_MATRIX.md`](EVIDENCE_DECISION_MATRIX.md),
[`PHASE_1_ROADMAP.md`](PHASE_1_ROADMAP.md), [`claim_ladder.json`](claim_ladder.json).

---

## A. Product purpose

**What SNTO is.** A *decision-intelligence layer* for protected natural tourism
destinations. It observes ecosystem state from satellite evidence, organises it
by official cartography and management geography, and — **only within the
evidence conditions defined here** — flags where managers should look, prioritise
investigation, and (conservatively) what non-restrictive action to consider.

**What SNTO is not.** It is not a GIS, an Earth-observation platform, or a BI
tool, and does not try to replace ArcGIS / GEE / Sentinel Hub / Tableau / Power
BI — it sits above them. It is **not** a validated ecological-impact system, a
causal-attribution engine, a visitor-counting system, or a regenerative-outcome
evaluator. It does not issue closures, quotas, or enforcement. It never presents
model output or simulation as measurement.

---

## B. Unit of analysis (resolved)

The repository mixes "asset", "managed asset", "trail", "territory" and
"observation". Phase 1 fixes the hierarchy:

| Role | Entity | Where |
|---|---|---|
| **Observed unit** | **Asset** = a trail/segment (218 official PNSG trails) | curated layer, Sentinel-2 footprint |
| **Persisted product entity** | **managed_asset** | `src/persistence/models/managed_asset.py` |
| **Aggregation unit** | **Territory** (park / OAPN management zone) | `src/persistence/models/territory.py` |
| **Validation unit** | **Plot** co-located with an asset | field campaign (#26) |
| **Atomic evidence** | **Observation** (timestamped, class-tagged) | `observation.py`, `visitor_pressure/contracts.py` |

**Rule:** a claim inherits the *weakest* support in its chain. A territory-level
statement may not assert asset-level specificity; an asset-level statement may
not assert plot-level (field) confirmation.

---

## C. Evidence ontology

Canonical and already implemented in `src/platform/evidence.py`
(`EvidenceClass`). This contract **reuses it verbatim** — no new vocabulary.

| Class | Meaning | Decision ceiling |
|---|---|---|
| **REAL** | Direct Sentinel-2 L2A / official cartography / official field observation | up to L5; L6–L7 only with #26 + management record |
| **CALIBRATED** | Literature/expert reconstruction (e.g. AEMET-Copernicus anomalies) | context & prioritization (L4) |
| **SIMULATED** | Scenario / counterfactual (α-decay SCM, forecasts, TIS) | nothing above L0 |
| **SYNTHETIC** | Authored demo/fixture data | nothing above L0 (demo only) |
| **MISSING** | Expected datum absent — declared `null`, never filled | nothing; records absence |

Two related axes remain distinct on purpose: `DataType` (epistemic operation:
Observed/Calculated/Estimated/Simulated) and `DataStatus` (temporal trust tier).
A **Calculated** value inherits the class of its inputs and is never collapsed to
a single class.

---

## D. Claim ladder

Authoritative table lives in ADR-016 and machine-readable form in
[`claim_ladder.json`](claim_ladder.json). Summary:

- **L0 Availability** → any class.
- **L1 Observation / L2 Derived / L3 Association** → **REAL** inputs; L3 needs
  ≥2 REAL series and declared statistics. No causal language below L7.
- **L4 Decision-support signal** (flag / prioritize investigation) → REAL, or
  CALIBRATED strictly as labelled context.
- **L5 Management recommendation** → REAL state + explicit uncertainty;
  **non-restrictive actions only** (monitor/inspect/maintain). Restrictive
  actions (closure/quota/access limit) are **not** authorized here.
- **L6 Effectiveness assessment** → REAL before/after **+ a complete management
  record** (§F pillar 3) **+ field validation**. **Blocked today.**
- **L7 Causal attribution / evaluated regenerative outcome** → BACI field
  validation (#26 pre-registration: Cliff's δ ≥ 0.474 p<0.01; Spearman ρ ≥ 0.60).
  **Blocked today.**

**SNTO operates at L1–L4 today; L5 for non-restrictive recommendations only.**

---

## E. Decision-use gates

The class×use gate in `evidence.py` (`supports(evidence, use)`) is the runtime
enforcement point; the *combination* gate is in
[`EVIDENCE_DECISION_MATRIX.md`](EVIDENCE_DECISION_MATRIX.md). Authorizations:

| Use | Minimum evidence | Ladder |
|---|---|---|
| Monitor / contextualise | REAL or CALIBRATED (labelled) | L1–L2 |
| Flag / prioritize investigation / field inspection | REAL (CALIBRATED as context) | L4 |
| Recommend non-restrictive action | REAL state + uncertainty | L5 |
| Recommend restrictive action | **not authorized** (needs ≥L6 + owner policy) | — |
| Public / institutional reporting | REAL only, with caveats; never "validated" | ≤ L4/L5 |
| Evaluate effectiveness | REAL before/after + complete mgmt record + field | L6 (blocked) |
| Claim causality / regeneration | BACI + field (#26) | L7 (blocked) |
| Any use of SIMULATED/SYNTHETIC | demo/scenario exploration only | L0 |

---

## F. Four-pillar contract

### Pillar 1 — Visitor Pressure
- **Minimum data:** a traceable, real, time-stamped pressure series (counts /
  vehicles / reservations / trail entries) passing the temporal policy in
  `src/visitor_pressure/data_validation.py`.
- **Current status:** `INSUFFICIENT_EVIDENCE` ("Decision C"). Only a curated
  annual capacity *proxy* exists; the MITMA crosswalk is committed but the
  snapshot has never been generated (`mobility_real=False`).
- **Target status:** ≥ `PARTIALLY_READY` on one real feed → enables L4 pressure
  context (never trail footfall from municipal data).
- **Validation requirement:** none to *hold* data; a real series to *use* it.
- **Permitted outputs:** with no real data → none beyond declaring the gap. With
  MITMA → macro-territorial context only.

### Pillar 2 — Ecosystem State
- **Minimum data:** Sentinel-2 L2A observation with valid-pixel accounting.
- **Current status:** **REAL and operational** for PNSG / Monfragüe / Tablas
  (Mann-Kendall trends, EHS). SCM causal layer is **SIMULATED** (α-decay); SCM
  real zones = 0.
- **Target status:** hold REAL at L1–L4; SCM stays a labelled *hypothesis* until
  real multi-scale zones are exported.
- **Validation requirement:** #26 for any field-confirmed condition claim.
- **Permitted outputs:** observe, derive condition, associate, flag, prioritize;
  causal *hypothesis* display only.

### Pillar 3 — Management Response
- **Minimum data (recording contract, currently missing):** per intervention —
  *what, where (asset/geometry), when, who authorized, cost, duration, target,
  intended effect, completion status*, linked to the triggering recommendation
  and to the asset.
- **Current status:** `interventions` table is a **thin stub** (asset_id,
  status, budget_eur, started_at, resolved_at) and unpopulated; the required
  fields above are absent. No scientifically usable management record exists.
- **Target status:** a defined recording contract (schema spec — WP-3) so that
  L6 becomes *possible* once real records + real before/after exist.
- **Validation requirement:** completeness of the record itself; field for L6.
- **Permitted outputs:** none as evidence today; TIS/scenarios remain SIMULATED
  projections.

### Pillar 4 — Regenerative Outcome
- **Minimum data:** the full chain `pressure → state → intervention →
  post-intervention REAL change → attribution/confidence`, with field BACI.
- **Current status:** **no chain exists.** "Improved NDVI" is **not** treated as
  regenerative. "Economía Regenerativa" appears only as a *socioeconomic framing*
  label in one tab, not as an evaluated outcome.
- **Target status:** aspiration only in Phase 1; unlocking requires pillars 1&3
  **and** #26.
- **Validation requirement:** L7 (BACI, pre-registered thresholds).
- **Permitted outputs:** none. The term "regenerative outcome" may not be used as
  an evaluated result until L7 conditions are met.

---

## G. Missing-data behaviour

- **Null ≠ zero.** A missing count is `null`/`MISSING`, never `0`.
- **Missing ≠ safe.** Absence of a stress signal is not evidence of health.
- **Synthetic ≠ observed / Model output ≠ measurement.** SIMULATED and SYNTHETIC
  never render as REAL and authorize no real decision.
- Enforced today by `resolve_signals()` (no evidence inheritance) and the
  visitor-pressure contract (`MISSING` requires explicit `null` + `MISSING`
  quality flag). Any new surface must preserve this.

---

## H. Uncertainty

Every claim at L1+ must carry, proportionate to its level: (a) its evidence
class label; (b) its ladder level; (c) a stated limitation or confidence (trend
p-value, valid-pixel %, calibration caveat, or "hypothesis — not measured"). A
claim without an uncertainty statement is a contract violation. Public/reporting
surfaces must additionally state the #26 gate explicitly.

---

## I. Validation gates (hard)

1. **Field validation (#26)** — the only open Issue. Blocks L6–L7, all
   satellite↔field agreement claims, and any "validated"/"regenerative
   outcome"/causal language. **Not to be closed, weakened, or worked around.**
2. **Visitor-pressure readiness** — `INSUFFICIENT_EVIDENCE` until one real,
   traceable series passes the temporal policy. No forecasting/ML before then.
3. **Management-response completeness** — L6 blocked until the recording contract
   exists and real, complete records are captured.
4. **Regenerative-outcome** — L7 blocked until 1–3 and BACI are satisfied.

---

## J. Phase 1 exit criteria (Definition of Done)

Phase 1.0 is **done** when:
1. This contract, the evidence→decision matrix, and ADR-016 are merged on `main`.
2. The claim ladder exists in machine-readable form (`claim_ladder.json`).
3. The Phase-1 product audit (§F above + `EVIDENCE_DECISION_MATRIX.md`) records
   no RED surface (no product surface implies more than its authorized level);
   any AMBER has a tracked follow-up.
4. Canonical multi-agent guidance (`CLAUDE.md`) points to this contract as the
   current phase authority.
5. #26 remains the sole open hard gate; no fabricated data, invented threshold,
   or unrelated feature entered the branch.

Phase 1.0 explicitly does **not** include: forecasting/ML, PostGIS production
migration, API deployment, Experience Builder Batch C, visitor-pressure
ingestion, management-record migration, regenerative evaluation, or multi-park
expansion. Those are sequenced in `PHASE_1_ROADMAP.md`.
