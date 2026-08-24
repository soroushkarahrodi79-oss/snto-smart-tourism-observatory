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

### Two orthogonal axes (do not conflate)

Provenance is **not** the same as epistemic operation. A datum has *both*:

- **Axis 1 — Source / provenance** (the table above): REAL / CALIBRATED /
  SIMULATED / SYNTHETIC / MISSING. Implemented as `EvidenceClass`.
- **Axis 2 — Epistemic transformation:** OBSERVED / DERIVED / MODELLED /
  HYPOTHESIZED. Partly implemented as `DataType`
  (Observed/Calculated/Estimated/Simulated); `DataStatus` is the temporal trust
  tier. **No new enum is added by Phase 1** — this is a documentation-level
  clarification; wiring is out of scope.

**Critical consequence: `REAL` does not mean "observed."** Sentinel-2 L2A
surface reflectance and official cartography are REAL **and** OBSERVED. NDVI /
NDMI / **EHS** are REAL-provenance but **DERIVED** (a documented transform of
observations). SCM output is SIMULATED **and** MODELLED/HYPOTHESIZED. This
matters for the ladder: an OBSERVED value may support L1; a DERIVED value enters
at **L2**, never L1; a MODELLED/HYPOTHESIZED value is capped at an L2 *hypothesis*
display. A **Calculated/derived** value inherits the *source class* of its inputs
and is never collapsed to a single class.

---

## D. Claim ladder

Authoritative table lives in ADR-016 and machine-readable form in
[`claim_ladder.json`](claim_ladder.json). Summary:

- **L0 Availability** → any class. Authorizes nothing.
- **L1 Observation** → REAL **and OBSERVED** (Sentinel L2A reflectance, official
  cartography). Derived indices are **not** L1.
- **L2 Derived condition** → REAL-provenance **DERIVED** (NDVI/NDMI/**EHS**);
  requires a documented transform, quality metadata, and valid provenance. A
  MODELLED/HYPOTHESIZED value (SCM) is capped at an L2 *hypothesis* display.
- **L3 Association** → ≥2 *measured* variables, temporal/spatial alignment, an
  explicit statistical method, and uncertainty. (Minimum plot count is the
  *tracked field convention* — ≥3 co-located plots, `field_agreement.py` — cited,
  not invented here.) No causal language.
- **L4 Decision-support signal** → flag / monitor / **prioritize investigation &
  field inspection only**. Explicitly **not**: prioritize a physical
  intervention, allocate budget, or restrict access. REAL, or CALIBRATED strictly
  as labelled context.
- **L5a Observational recommendation** → recommend monitoring / inspection /
  field verification. REAL state + explicit uncertainty. **← current ceiling.**
- **L5b Committing recommendation** → recommend a **resource-committing**
  intervention (restoration/maintenance/redistribution) **or** a **restrictive**
  action (closure/quota/access limit). **Blocked:** needs ≥L6-grade evidence;
  the restrictive sub-type additionally needs explicit owner policy.
- **L6 Effectiveness assessment** → complete management record (§F) + pre/post
  REAL + temporal alignment + a **comparator/counterfactual** + **confounder
  discussion** + field + uncertainty. *A bare before/after change is only L2, not
  L6.* **Blocked today.**
- **L7 Causal attribution (high-confidence, BACI-supported)** →
  quasi-experimental attribution under **stated assumptions**; requires L6 +
  control/impact design + assumption/confounder treatment + the **approved
  field-validation pre-registration** (see §I). Not proof; **no mechanical
  `BACI + p-value = causality` rule.** **Blocked today.**

**No numeric agreement threshold (ρ, κ, p, DI) is canonized as product policy** —
those belong to the field-validation protocol/pre-registration, not the product
contract (see §I and the threshold-provenance note there).

### Current maturity map (do not give the product its strongest component's level)

| Surface | Reached level | Note |
|---|---|---|
| Ecosystem state observation | L1 | REAL+OBSERVED reflectance/cartography |
| EHS / NDVI condition | L2 | REAL-provenance DERIVED |
| Multi-year trend association | L3 | REAL series + Mann-Kendall + p-value |
| Flag / prioritize investigation | L4 | early-warning only |
| Monitoring / inspection recommendation | L5a | **product ceiling today** |
| SCM causal layer | L2 (hypothesis) | SIMULATED+HYPOTHESIZED, labelled |
| Visitor pressure | L0 (L1 context via MITMA) | `INSUFFICIENT_EVIDENCE` target |
| Management response | L0 | schema stub |
| Effectiveness / regeneration | — | blocked (L6/L7) |

**SNTO contains capabilities spanning L1–L4 and L5a; no surface exceeds this, and
several (pressure, management response) are at L0.**

---

## E. Decision-use gates

The class×use gate in `evidence.py` (`supports(evidence, use)`) is the runtime
enforcement point; the *combination* gate is in
[`EVIDENCE_DECISION_MATRIX.md`](EVIDENCE_DECISION_MATRIX.md). Authorizations:

| Use | Minimum evidence | Ladder |
|---|---|---|
| Monitor / contextualise | REAL or CALIBRATED (labelled) | L1–L2 |
| Flag / prioritize investigation / field inspection | REAL (CALIBRATED as context) | L4 |
| Recommend monitoring / inspection | REAL state + uncertainty | L5a |
| Recommend resource-committing intervention | **not authorized** (needs ≥L6) | L5b (blocked) |
| Recommend restrictive action (closure/quota) | **not authorized** (needs ≥L6 + owner policy) | L5b (blocked) |
| Public / institutional reporting | REAL only, with caveats; never "validated" | ≤ L4/L5a |
| Evaluate effectiveness | complete mgmt record + pre/post REAL + comparator + field | L6 (blocked) |
| Claim causality / regeneration | L6 + control/impact + approved pre-registration | L7 (blocked) |
| Any use of SIMULATED/SYNTHETIC | demo/scenario exploration only | L0 |

> **Refinement vs implementation (item to reconcile in WP-2):** `evidence.py`
> currently exposes a single coarse `DecisionUse.INTERVENTION` that REAL
> satisfies — it conflates *"order a field inspection"* (low-regret, L4/L5a) with
> *"commit intervention budget"* (L5b). This contract is deliberately **stricter**
> on the latter: recommending a resource-committing intervention needs ≥L6
> evidence, not REAL satellite alone. WP-2 splits the code's `INTERVENTION` use to
> match. No current surface issues an autonomous budget-commit recommendation, so
> this refinement blocks nothing today.

---

## F. Pillar contract (DPSIR: three evidence pillars + one evaluation layer)

The four "pillars" are **not** four symmetric evidence sources. Three are
evidence pillars; the fourth is an **evaluation layer** computed from them:

```
Visitor Pressure  →  Ecosystem State  →  Management Response   (evidence pillars)
                          └────────────── Regenerative Outcome  (evaluation layer)
```

Regenerative Outcome has **no independent data source** — it is an interpretation
derived from the three pillars plus a comparator, and is **out of scope for Phase
1** (see below).

### Pillar 1 — Visitor Pressure
- **Minimum data:** a traceable, real, time-stamped pressure series (counts /
  vehicles / reservations / trail entries) passing the temporal policy in
  `src/visitor_pressure/data_validation.py`.
- **Current status:** `INSUFFICIENT_EVIDENCE` ("Decision C"). Only a curated
  annual capacity *proxy* exists; the MITMA crosswalk is committed but the
  snapshot has never been generated (`mobility_real=False`).
- **Target status:** the **pressure-target-variable** gate (`ReadinessStatus`)
  changes only with a real, traceable **asset/park-level** count series. **MITMA
  municipal mobility does NOT satisfy this gate** — a municipal inbound-trip
  count is not trail footfall, so ingesting it leaves readiness at
  `INSUFFICIENT_EVIDENCE` for the *target* while adding L4 **macro-context** only.
  A technically-real dataset can be scientifically unsuitable as the target
  variable; calibration from municipal trips to park/trail pressure is an open
  research problem, not a wiring task.
- **Validation requirement:** none to *hold* data; a real asset-level series to
  *use* it as a pressure target.
- **Permitted outputs:** with no real target series → none beyond declaring the
  gap. With MITMA → macro-territorial context only, never a pressure figure.

#### Proxy hierarchy (what may become the pressure *target*, and what may not)

Pressure evidence is not one thing. The weakest-link rule (§B) applies to the
*instrument*, not only to the datum. Ranked from strongest:

| Rank | Source kind | Example | Standing |
|---|---|---|---|
| 1 | **Direct count** | trail counter, turnstile, ticketed entry | candidate pressure **target** |
| 2 | **Instrumented proxy** | parking sensor, reservation system | candidate **target**, with a stated coverage caveat |
| 3 | **Passive mobility proxy** | MITMA municipal inbound trips | **L4 macro-context only** — never the target |
| 4 | **Digital activity proxy** | route/fitness apps (Wikiloc, AllTrails, Strava-like traces) | **not a count.** Self-selected, activity-biased and platform-dependent. Usable only with a documented, validated calibration relationship to a direct or official observation |
| 5 | **Official park-level estimate** | OAPN *Informe de Visitantes de la Red de Parques Nacionales* | REAL-provenance **+ ESTIMATED** ⇒ enters at **L2**; an institutional baseline and cross-park denominator, **never** trail-level |

**Rules.** (a) Only ranks 1–2 can change `ReadinessStatus` for the pressure
*target variable*; ranks 3–5 leave it at `INSUFFICIENT_EVIDENCE` however real
they are. (b) A rank-4 digital trace may **never** be recorded under a person- or
pedestrian-count target — that is the same category error the contract already
forbids for environmental indices (`visitor_pressure/contracts.py` rejects
`ENVIRONMENTAL_OBSERVATION` as a target). (c) A rank-5 official estimate is
produced by an estimation *method*, so its epistemic axis is ESTIMATED even
though its provenance is official — see §C. (d) Ranks 3 and 5 measure different
universes (municipal trips vs. park visitors); an order-of-magnitude agreement
between them is a sanity check, **not** a calibration.

*No such source is ingested today.* This hierarchy is stated so that acquiring
one cannot silently upgrade a claim.

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
- **Minimum data (recording contract, currently missing).** The scientifically
  usable record per intervention (full field set specified in WP-3): intervention
  id; asset; spatial footprint; decision date; implementation start/end;
  intervention type; authorized by; target pressure/state; intended mechanism;
  planned cost; actual cost; completion state; monitoring window; evidence links;
  and the triggering recommendation. *Planned vs actual cost are distinct fields;
  a single `budget_eur` cannot support effectiveness reasoning.*
- **Current status:** `interventions` table is a **thin stub** (asset_id,
  status, budget_eur, started_at, resolved_at) and unpopulated; the fields above
  are absent. No scientifically usable management record exists.
- **Target status:** a defined recording contract (schema spec — WP-3) so that
  L6 becomes *possible* once real records + real before/after exist.
- **Validation requirement:** completeness of the record itself; field for L6.
- **Permitted outputs:** none as evidence today; TIS/scenarios remain SIMULATED
  projections and must never be presented as observed or forecast effect.

### Evaluation layer — Regenerative Outcome (not an independent pillar)
- **What it is NOT.** None of the following, alone, is regeneration: NDVI
  increased; EHS improved; a visitor count decreased; an intervention was
  completed. Each is at most an L2 observation of change.
- **Minimum conceptual chain (all links required):**
  `pressure → ecosystem state → management response → observed post-response
  state → counterfactual/comparator → uncertainty → regenerative interpretation`.
- **Current status:** **no link of the chain past "state" is instrumented.** The
  string "Economía Regenerativa" appears only as a *socioeconomic-vision framing*
  in one tab (SVI/jobs) — not an evaluated ecological outcome (audited AMBER, §
  matrix).
- **Target status:** **out of scope for Phase 1** — it depends on Pillars 1 & 3
  *and* #26, none of which is satisfied. Stated here as a boundary, not a
  deliverable.
- **Permitted outputs:** none. "Regenerative outcome" may not be used as an
  evaluated result. This is a scientific scoping, not a normative definition of
  "regenerative"; any normative definition is deferred to the owner.

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
2. **Visitor-pressure readiness** — `INSUFFICIENT_EVIDENCE` for the pressure
   *target variable* until a real, traceable asset/park-level series passes the
   temporal policy. MITMA context does not lift this. No forecasting/ML before then.
3. **Management-response completeness** — L6 blocked until the recording contract
   exists and real, complete records are captured.
4. **Regenerative-outcome** — blocked until 1–3 and a comparator/counterfactual
   are satisfied.

### Threshold-provenance rule (why no ρ/κ/p/DI number is policy here)

The pass/fail *numbers* for satellite↔field agreement are **field-validation
protocol** parameters, **not product-authorization policy**, and this contract
**does not canonize them**. Provenance audit (2026-08-12):

| Number | Tracked source | Status |
|---|---|---|
| Cliff's δ = 0.474 | `src/validation/agreement.py` (Romano et al. 2006) | tracked *effect-size label* — may be cited, is **not** a causal gate |
| Spearman ρ ≥ 0.60 | none (tracked display gate is ρ≥0.3) | **not canonized** — untracked origin |
| Cohen's κ ≥ 0.60 | none (no kappa in tracked code) | **not canonized** |
| p < 0.01 | none (`agreement.py` computes no p-values) | **not canonized** |
| DI ≥ 50 | none | **not canonized** |

**Gate wording for L6/L7:** *"must satisfy the approved, tracked field-validation
protocol (`docs/field_validation_protocol.md`) and the campaign's pre-registration
when #26 runs."* The pre-registration (an uncommitted `docs/paper1/` draft by
another agent) is **not canonical** until the owner commits and approves it; no
number from it is adopted as policy here.

---

## J. Phase 1 exit criteria (Definition of Done)

Phase 1.0 is **done** when:
1. This contract, the evidence→decision matrix, and ADR-016 are merged on `main`.
2. The claim ladder exists in machine-readable form (`claim_ladder.json`).
3. The Phase-1 product audit (§F above + `EVIDENCE_DECISION_MATRIX.md`) records
   no RED surface (no product surface implies more than its authorized level);
   any AMBER has a tracked follow-up.

   > **Not yet satisfied.** The audit records **two** RED-RISK surfaces: the TIS
   > euro-efficiency verdict (C-10) and the LAC/ROS capacity-at-standard figure.
   > Both are runtime issues, out of scope for the docs-only WP-1, and tracked as
   > **WP-C10** and **WP-C11**. This criterion closes when both land — it is not
   > weakened, and neither surface is downgraded to AMBER to make it close sooner.
4. Canonical multi-agent guidance (`CLAUDE.md`) points to this contract as the
   current phase authority.
5. #26 remains the sole open hard gate; no fabricated data, invented threshold,
   or unrelated feature entered the branch.

Phase 1.0 explicitly does **not** include: forecasting/ML, PostGIS production
migration, API deployment, Experience Builder Batch C, visitor-pressure
ingestion, management-record migration, regenerative evaluation, or multi-park
expansion. Those are sequenced in `PHASE_1_ROADMAP.md`.
