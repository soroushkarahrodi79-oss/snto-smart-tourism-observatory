# Phase 0.5 Recommendations — Integrity Stabilization

**Nothing here has been implemented.**

## Governance note — phase sequencing correction

This document was originally titled "Phase 1 Recommendations." Following owner
review of the Phase 0 baseline, the implementation work described below is
**re-governed as Phase 0.5 — Integrity Stabilization**, not Phase 1. The
filename (`PHASE_1_RECOMMENDATIONS.md`) is left unchanged to preserve the
original required Phase 0 audit deliverable name; the content below is the
Phase 0.5 plan.

The distinction matters and is not cosmetic:

- **Phase 0.5 — Integrity Stabilization** is correctness, reproducibility and
  claim-safety work. It touches no scientific model, changes no headline
  number, and requires no new methodological decision — every item below is a
  defect the audit already characterised in full.
- **Phase 1** is reserved for a later, separately scoped phase that defines the
  **scientific/product contract** SNTO operates under, across four pillars:
  **Visitor Pressure**, **Ecosystem State**, **Management Response**, and
  **Regenerative Outcome**. Phase 1 begins **only after** Phase 0.5 lands and
  is verified. It is scoped at the end of this document — scope only, not
  implemented, not designed.

Every implementation phase still needs an approved audit, explicit acceptance
criteria, tests, and a small reviewable PR, per the project's standing rule.

## Sequencing principle

Phase 0.5 should be **claims and reproducibility only** — no data re-rooting,
no architecture change, no removals. Rationale:

1. The Tier-1 scientific findings are text and one-line defects. They are cheap
   to fix, they are the highest-severity items in the audit, and fixing them
   does not change a single number.
2. Re-rooting the decision layer on real trails (`REMOVAL_CANDIDATES.md` R-08)
   changes every headline figure at once. It must not share a PR with anything
   else, needs a published before/after comparison, and — per the pillars
   above — is Phase 1 (Ecosystem State) territory, not Phase 0.5.
3. Fixing reproducibility first means the numbers any later phase compares are
   stable.

## Proposed Phase 0.5 scope — five corrective PRs + four integrity items

### PR 0.5.1 · Remove unsupported causal language

**Changes**

- `src/platform/dashboard.py::_kpi_human_pressure_alerts` — replace "measurable
  environmental damage **caused by** visitor pressure" and "**confirmed**
  visitor-driven environmental damage" with hypothesis-framed wording; replace
  the GREEN-branch "driven by natural climate variability" with an explicit
  statement of absence of evidence.
- `src/decision_confidence/assessor.py:467-471` — delete the hard-coded
  "(driven by the 2022 drought)" attribution.
- `src/ui/tabs/tab_diagnostic.py:440` — qualify "sin datos sintéticos" to exclude
  the SCM column.
- `src/platform/map_layers.py:733` and `tab_diagnostic.py:144` — state that the
  colour encodes EHS (which may be calibrated or synthetic), not a spectral
  measurement.
- No restrictive management action (seasonal closure, visitor quota, guided-only
  access, or equivalent) may be emitted from evidence that is `SIMULATED`,
  `SYNTHETIC`, unvalidated, or attribution-unsupported — i.e. the same four-part
  gate below applies to *actions*, not only to causal *language*. Concretely:
  `SIMULATED`/`SYNTHETIC` evidence never qualifies; `CALIBRATED` evidence never
  qualifies without an explicit uncertainty caveat attached at the point of
  emission; and `REAL` evidence only qualifies once it also has a validated
  method and a supported, independently-verified attribution — not on its
  `EvidenceClass` label alone. This closes the specific failure mode in
  `SCIENTIFIC_CLAIMS_REGISTER.md` C-01, where a fixture-derived classification
  currently recommends restricting public access to a national park.

**Owner decision applied (Q-02):** suspend this language **immediately** — do
not wait for real SCM zones to be ingested. This PR is not conditional on any
data-ingestion work landing first.

**The conceptual gate — corrected**

The original draft of this PR proposed gating causal language on
`EvidenceClass != REAL`. **That criterion was wrong and is corrected here:**
`EvidenceClass.REAL` is a *provenance* tier — it states a value came from a
direct Sentinel-2 observation — not a *causal-attribution* license. Real
satellite data can sit behind an unvalidated method, an unsupported
attribution, or a signal nobody has independently verified, and none of
SNTO's current indicators clear that bar today (including the ones already
resolved to REAL, such as the SCM classification once real zones exist).

The required conceptual gate for any causal or confirmatory term ("caused by",
"confirmed driver", "attributable to", "visitor-driven damage", or an
equivalent) is:

```text
REAL evidence
+ validated method
+ supported attribution
+ independent verification
```

All four conditions must hold, not just the first. Today, **no SNTO indicator
clears this gate**, so no causal or confirmatory term may currently be emitted
by any indicator regardless of its `EvidenceClass`.

**Acceptance criteria**

- No KPI narrative string contains "caused by", "confirmed", "measurable
  damage", "confirmed driver", "attributable to", "visitor-driven damage", or
  an equivalent causal/confirmatory term — for **any** indicator, regardless of
  its resolved `EvidenceClass`, until the four-part gate above is met and
  documented for that specific indicator.
- No restrictive management action is recommended from `SIMULATED` or
  `SYNTHETIC` evidence, from unverified `CALIBRATED` evidence, or from `REAL`
  evidence that has not cleared the four-part gate (validated method +
  supported attribution + independent verification).
- No claim string in `src/` names a specific climatic event that is not read
  from data.
- Numbers unchanged: existing KPI value assertions pass untouched.

**Future machine-readable fields (documentation-only proposal, not implemented
in this PR)**

A later phase may want to carry the four-part gate as data rather than prose,
via fields such as `validation_status`, `attribution_status`, and
`claim_strength` attached to each indicator or claim. Their types, defaults,
storage location and wiring into `evidence.supports()` are **not designed
here** — this paragraph records the idea so it is not lost, not a spec.

**Tests**

- A new claims-lint test that walks the KPI registry and asserts that no
  causal/confirmatory term is emitted unless the four-part gate is satisfied
  and recorded for that indicator (today: assert it never is), mirroring the
  pattern already used by `tests/unit/test_pilot_package.py` (which
  regex-asserts no currency figure exists in a document). This makes the rule
  enforceable, not advisory.

**Risk:** Low. Text-only.

---

### PR 0.5.2 · Make provenance degrade honestly

**The original recommendation was wrong and is corrected here.** It proposed
collapsing the entire satellite-evidence surface to `DataStatus.MISSING`
whenever the raw `.SAFE` products are absent locally. That conflates four
distinct things the current code (and the original PR draft) treats as one:

1. **Derived output availability** — does `data/outputs/pnsg/pipeline_a_results.geojson`
   exist? This file is **committed to git** and can be genuinely present and
   REAL-derived regardless of whether the raw rasters are on disk.
2. **Raw-source availability** — are the `.SAFE` products present in this
   environment? Today: no, on any fresh clone (rasters are git-ignored, ~900 MB).
3. **Provenance completeness** — can the specific acquisition dates and sensors
   be re-derived from the raw source? Today: no, without the rasters, because
   `detect_scene_dates()` parses `.SAFE` filenames.
4. **Reproducibility** — could a fresh clone regenerate the derived output from
   scratch? Today: no, the pipeline needs the raw rasters.

A committed derived GeoJSON remaining available while its raw source cannot be
locally inspected is a **normal, honest state** for a versioned research
artifact — it is not the same as having no evidence at all. Recommending
`MISSING` would misstate a real, git-tracked artifact as absent.

**Changes**

- `src/platform/provenance.py::snapshot_provenance` — when
  `detect_scene_dates()` finds no local `.SAFE` products but the derived
  GeoJSON exists, do not report the current unconditional
  `"🛰️ Dato satelital real. Observación directa."` badge, and do not collapse to
  `DataStatus.MISSING` either. Report an explicitly degraded state distinguishing
  the four items above, for example:

  ```text
  Derived from real Sentinel-2 observations;
  raw source scenes unavailable in this environment;
  provenance incomplete and not locally reproducible.
  ```

  Reserve `DataStatus.MISSING` for the case where the derived output itself is
  also absent.
- Surface the actual acquisition dates and sensor IDs wherever ΔEHS is
  presented (`tab_diagnostic.py`, `prug_monitoring`, the PRUG/CETS reports)
  when they are derivable; state explicitly when they are not.

**Acceptance criteria**

- With `data/raw_assets/raster_data/` absent but the derived GeoJSON present,
  the UI shows the degraded-but-honest four-way state above — neither the
  current unconditional REAL badge nor an unqualified `MISSING`/"Sin dato"
  state.
- With neither the derived GeoJSON nor the raw rasters present, the surface
  degrades to `DataStatus.MISSING` as today.
- The ΔEHS surfaces display both acquisition dates and both sensor IDs when
  derivable.
- Existing behaviour is unchanged when the raw rasters are present.

**Tests**

- A three-way parametrised test over `snapshot_provenance` — (a) raw rasters
  present, (b) raw rasters absent / derived output present, (c) both absent —
  asserting the three distinct status outcomes (currently untested — see
  `TEST_BASELINE.md` T-3, which only anticipated the two-way case).

**Risk:** Low–Medium. Changes what a fresh clone displays — which is the point.

---

### PR 0.5.3 · Fix map geometry reproducibility

**Changes**

- Replace `hash()` with a stable digest (`hashlib.blake2b(asset_id.encode())`) in
  `_jitter`, `_heading_from_id`, `_trail_path`.
- Correct the SNR-defaulting `_MAP_LATITUDE` / `_MAP_LONGITUDE` / `_MAP_ZOOM` /
  `_DEFAULT_CENTROID` constants (`map_layers.py:68-73`), or make the parameters
  required.
- Correct the two docstrings to state precisely what is guaranteed.

**Acceptance criteria**

- The same `asset_id` produces byte-identical synthetic geometry across separate
  interpreter processes.
- No map builder can be called without an explicit map centre.

**Tests**

- Determinism test that runs the generator in a subprocess and compares
  coordinates (the class of test whose absence let this defect ship — T-2).

**Risk:** Low. Synthetic asset positions will shift once, at deploy.

**Note:** this makes the synthetic geometry *reproducible*; it does not resolve
whether it should exist at all (`REMOVAL_CANDIDATES.md` R-03). That decision
belongs to a later phase.

---

### PR 0.5.4 · Fix test isolation and prevent credential exposure

**Changes**

- Move `load_dotenv()` inside `main()` / `if __name__ == "__main__":` in the
  eight root scripts listed in `REMOVAL_CANDIDATES.md` R-06.

**Acceptance criteria**

- `python -m pytest -q` passes on a developer machine that has a populated
  `.env`. Currently it does not.
- Running each script directly still loads `.env` — verified by an explicit test
  or a documented manual check.
- **No credential value or database connection string/URL (host, user,
  password, port, or any combination such as `postgresql+psycopg2://user:pass@host:port/db`,
  API key, or service-account path) can appear in test output, assertion
  diffs, or CI logs**, on any developer machine regardless of local `.env`
  contents. This is the specific failure this audit observed
  (`TEST_BASELINE.md` §3, where a full connection string was printed into an
  assertion diff) and is a required, independently-checked acceptance
  criterion, not a side effect of the isolation fix.

**Tests**

- Keep `tests/persistence/test_settings_database_url.py` unchanged; it becomes a
  genuine regression test once the leak is closed.

**Risk:** Very low.

---

### PR 0.5.5 · Reclassify the fixtures — Q-01 resolved: `SYNTHETIC`

**Owner decision applied (Q-01):** the `fixtures.py` assets are **`SYNTHETIC`**,
not `CALIBRATED`. This PR is no longer blocked on an open question; it is
scoped to implement a settled decision.

**Changes**

- Correct the `fixtures.py` docstrings so they no longer describe the assets as
  "reales", and state plainly that the numeric fields are authored to exercise
  the TPI engine.
- Add a provenance note recording who authored them, when, and on what basis.
- State the resolved evidence class (`SYNTHETIC`) once, in `fixtures.py`, and
  cross-reference `docs/methodology/evidence-classes.md`.

**Acceptance criteria**

- No docstring or comment in `src/` describes fixture data as real.
- The `SYNTHETIC` classification is stated once, in `fixtures.py`, and
  referenced from `docs/methodology/evidence-classes.md`.

**Beyond this PR — not implemented here.** A docstring correction is
necessary but not sufficient: it is not machine-checkable, and nothing stops a
future contributor from reintroducing a real/synthetic conflation by editing
the description without editing the (nonexistent) evidence field. Phase 0.5
should be understood to *point toward* — without designing or implementing
here — attaching machine-readable evidence metadata directly to each fixture
asset, for example:

```yaml
evidence_class: SYNTHETIC
demo_only: true
operational_decision_support: false
scientific_validation_support: false
```

This would let `evidence.supports()` and the PR 0.5.1 claims-lint check the
classification programmatically instead of depending on a comment staying
accurate. The exact schema, its storage (a `TerritorialAsset` field vs. a
sidecar file), and its wiring are implementation design for the PR that
actually does this work — not decided in this document.

**Risk:** Low for the docstring correction (text-only). The metadata-field
extension is out of scope for this PR; its risk is unassessed until proposed.

---

## Phase 0.5 scope — additional integrity items (from audit findings)

These are already-audited, already-characterised defects that belong in Phase
0.5 alongside the five PRs above. They are listed here to keep the plan
complete; none is designed or implemented in this document.

| Item | Audited finding | What Phase 0.5 must correct |
|---|---|---|
| **I-1** · Repository hygiene | `ARCHITECTURE_BASELINE.md` B-8, `TEST_BASELINE.md` P-8 | 46 tracked `.pyc` files make `git status` dirty after every test run. Untrack them and add `__pycache__/`, `*.py[cod]` to `.gitignore`. |
| **I-2** · Stale AI handoff document | `CONTRADICTIONS_AND_OPEN_QUESTIONS.md` X-01, Q-16 | `docs/ai-context/CLAUDE_CODE_HANDOFF_2026.md` describes a `2,890`-line `app.py` that no longer exists and PR states that resolved long ago. Either mark it historical with an unmistakable stale-document warning banner (a dated header a reader cannot miss on opening the file) or retire it in favour of `CLAUDE.md` + `MASTER_STRATEGIC_INDEX.md`. |
| **I-3** · "Live" indicator and report date | `SYSTEM_BASELINE.md` bottlenecks §6.3–4, `SCIENTIFIC_CLAIMS_REGISTER.md` C-14/C-15, Q-10 | The 60-second autorefresh + pulsing "live" indicator asserts a live feed over data that only changes on a manual offline pipeline run; remove it, or qualify it so it cannot be read as a live feed. The hard-coded `REPORT_DATE = "2026-06-12"` should be replaced with a truthful data/publication-date strategy (e.g. the actual pipeline run date, or an explicit "as of" label sourced from `run_context.json`). |
| **I-4** · SCM attribution separated from real measurement at display | `CONTRADICTIONS_AND_OPEN_QUESTIONS.md` X-06, `SCIENTIFIC_CLAIMS_REGISTER.md` C-16, `MAP_INVENTORY.md` M-03 flags | The real-trails table and map tooltip present real EHS/ΔEHS alongside a `Causa (SCM)` value that is currently simulated, with no visual or textual distinction between the two evidence classes at the point of display. **Visually and semantically separate** them — distinct styling *and* distinct wording — so a reader cannot mistake the simulated cause for a measurement of equal standing to the real trail data next to it. |

---

## Explicitly deferred beyond Phase 0.5

| Item | Why deferred |
|---|---|
| Re-rooting the decision layer on the 218 real trails (R-08) | Changes every headline number; needs its own phase, its own audit of the before/after delta, and an owner decision on the three fields real data cannot supply (Q-08). Falls under the Phase 1 "Ecosystem State" pillar below. |
| Consolidating or removing the spectral map (R-02) | Requires promoting the real-trail map first. |
| Ingesting the three v2.2 feeds (mobility, SCM zones, SVI history) | Zero-code-change data work, but it *upgrades evidence classes* — it should follow the claims layer (PR 0.5.1), so the labels are correct when the data lands. Highest-value non-code work available. |
| Field validation campaign (#26) | The hard gate for every validation claim. Manual field work; nothing in software unblocks it. |
| `platform/` package decomposition (B-2) | Structural; needs a target architecture, which Phase 0 deliberately did not invent. |
| Removing legacy v1 routers, phase-report scripts | Blocked on Q-17, Q-18. |
| Applying the PostGIS migration to production | Blocked on Q-12/Q-13; nothing consumes it. |

## What Phase 0.5 explicitly does not change

- Any KPI value, tier, budget figure, or ranking.
- Any data source, ingestion path, or schema.
- Any dependency.
- Any file location or name.
- The navigation contract (4 layers × 14 modules).

## Suggested definition of done for Phase 0.5

1. All nine Phase 0.5 items (five PRs + four integrity items) merged, each
   reviewed independently, none mixing docs with code.
2. `python -m pytest -q` green on a developer machine with a populated `.env`,
   and no credential value appears in its output.
3. Coverage still ≥ 80 %.
4. A re-run of `SCIENTIFIC_CLAIMS_REGISTER.md` shows zero claims classified
   **Misleading** or **Contradicted by implementation** in Tier 1.
5. `docs/audit/2026-snto-baseline/` updated with a short "Phase 0.5 delta" note
   rather than rewritten — the baseline stays a historical record.

---

## Phase 1 — scientific/product contract (scope only, not started)

Phase 1 begins **only after** Phase 0.5 lands and is verified. Nothing in this
section is designed or implemented; it records the mandate so Phase 0.5 is not
mistaken for the whole of the corrective work.

Phase 1's mandate is to define the scientific/product contract SNTO operates
under, across four pillars:

- **Visitor Pressure** — what SNTO may claim about visitor pressure, from which
  sources (MITMA mobility once ingested, the curated `visitor_capacity_annual`
  proxy, or eventual field counts), and under what evidence class each claim is
  licensed. Directly follows from Q-06 and the D-06 mobility gap.
- **Ecosystem State** — how EHS is computed and represented, resolving the fact
  that two incompatible formulas currently share one name and scale
  (`KPI_INVENTORY.md` K-01), and deciding whether and how the decision layer
  re-roots on the 218 real trails instead of the fixture portfolio
  (`REMOVAL_CANDIDATES.md` R-08, Q-08).
- **Management Response** — which SNTO outputs may drive an actual management
  action (closures, quotas, budget commitments) and under what verification
  standard, formalising in a durable specification the four-part causal gate
  PR 0.5.1 introduces informally.
- **Regenerative Outcome** — how intervention effects (TIS, restoration,
  promotion) are represented once they are more than the illustrative scenario
  assumptions the owner has confirmed they are today (Q-05), if and when a
  validated basis for any of them is established.

This document does not decide the content of that contract. It exists only to
record that Phase 1 is the next phase after Phase 0.5, that it is
methodological and product work rather than integrity/reproducibility work,
and that it has not begun.
