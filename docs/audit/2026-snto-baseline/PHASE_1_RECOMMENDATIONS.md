# Phase 1 Recommendations

**Nothing here has been implemented.** This is a proposed scope for a separately
approved phase, following the stated rule: every implementation phase needs an
approved audit, explicit acceptance criteria, tests, and a small reviewable PR.

## Sequencing principle

Phase 1 should be **claims and reproducibility only** — no data re-rooting, no
architecture change, no removals. Rationale:

1. The Tier-1 scientific findings are text and one-line defects. They are cheap
   to fix, they are the highest-severity items in the audit, and fixing them
   does not change a single number.
2. Re-rooting the decision layer on real trails (`REMOVAL_CANDIDATES.md` R-08)
   changes every headline figure at once. It must not share a PR with anything
   else, and it needs a published before/after comparison.
3. Fixing reproducibility first means the numbers Phase 2 compares are stable.

## Proposed Phase 1 scope — five small PRs

### PR 1.1 · Remove unsupported causal language

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
  colour encodes EHS (which may be calibrated), not a spectral measurement.

**Acceptance criteria**

- No KPI narrative string contains "caused by", "confirmed", "measurable damage",
  or an equivalent, for any indicator whose resolved `EvidenceClass` is not
  `REAL`.
- No claim string in `src/` names a specific climatic event that is not read
  from data.
- Numbers unchanged: existing KPI value assertions pass untouched.

**Tests**

- A new claims-lint test that walks the KPI registry and asserts a forbidden-verb
  list against `EvidenceClass`, mirroring the pattern already used by
  `tests/unit/test_pilot_package.py` (which regex-asserts no currency figure
  exists in a document). This makes the rule enforceable, not advisory.

**Risk:** Low. Text-only.

---

### PR 1.2 · Make provenance degrade honestly

**Changes**

- `src/platform/provenance.py::snapshot_provenance` — return
  `DataStatus.MISSING` (and `n_scenes = 0`) when `detect_scene_dates()` is empty,
  instead of `DataStatus.REAL` with an assumed `n_scenes = 2`.
- Surface the actual acquisition dates wherever ΔEHS is presented
  (`tab_diagnostic.py`, `prug_monitoring`, the PRUG/CETS reports), and state the
  sensor of each scene.

**Acceptance criteria**

- With `data/raw_assets/raster_data/` absent, no "🛰️ Dato satelital real" badge
  renders anywhere.
- The ΔEHS surfaces display both acquisition dates and both sensor IDs.
- Existing behaviour is unchanged when the rasters are present.

**Tests**

- Parametrised test over `snapshot_provenance` with and without a scene folder,
  asserting the status transition (currently untested — see `TEST_BASELINE.md` T-3).

**Risk:** Low–Medium. Changes what a fresh clone displays — which is the point.

---

### PR 1.3 · Fix map geometry reproducibility

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
whether it should exist at all (`REMOVAL_CANDIDATES.md` R-03, question Q-03).
That decision belongs to a later phase.

---

### PR 1.4 · Fix test isolation

**Changes**

- Move `load_dotenv()` inside `main()` / `if __name__ == "__main__":` in the
  eight root scripts listed in `REMOVAL_CANDIDATES.md` R-06.

**Acceptance criteria**

- `python -m pytest -q` passes on a developer machine that has a populated
  `.env`. Currently it does not.
- Running each script directly still loads `.env` — verified by an explicit test
  or a documented manual check.
- No credential value can appear in test output.

**Tests**

- Keep `tests/persistence/test_settings_database_url.py` unchanged; it becomes a
  genuine regression test once the leak is closed.

**Risk:** Very low.

---

### PR 1.5 · Relabel the fixtures (docs-only, pending Q-01)

**Blocked on the owner answering Q-01** (`CALIBRATED` vs `SYNTHETIC`).

**Changes**

- Correct the `fixtures.py` docstrings so they no longer describe the assets as
  "reales", and state plainly that the numeric fields are authored to exercise
  the TPI engine.
- Add a provenance note recording who authored them, when, and on what basis.

**Acceptance criteria**

- No docstring or comment in `src/` describes fixture data as real.
- The chosen evidence class is stated once, in `fixtures.py`, and referenced from
  `docs/methodology/evidence-classes.md`.

**Risk:** None (comments only). **Must not be mixed with functional changes**
per the project's non-negotiables.

---

## Explicitly deferred beyond Phase 1

| Item | Why deferred |
|---|---|
| Re-rooting the decision layer on the 218 real trails (R-08) | Changes every headline number; needs its own phase, its own audit of the before/after delta, and an owner decision on the three fields real data cannot supply (Q-08). |
| Consolidating or removing the spectral map (R-02) | Requires promoting the real-trail map first. |
| Ingesting the three v2.2 feeds (mobility, SCM zones, SVI history) | Zero-code-change data work, but it *upgrades evidence classes* — it should follow the claims layer (PR 1.1), so the labels are correct when the data lands. Highest-value non-code work available. |
| Field validation campaign (#26) | The hard gate for every validation claim. Manual field work; nothing in software unblocks it. |
| `platform/` package decomposition (B-2) | Structural; needs a target architecture, which Phase 0 deliberately did not invent. |
| Removing legacy v1 routers, phase-report scripts | Blocked on Q-17, Q-18. |
| Applying the PostGIS migration to production | Blocked on Q-12/Q-13; nothing consumes it. |

## What Phase 1 explicitly does not change

- Any KPI value, tier, budget figure, or ranking.
- Any data source, ingestion path, or schema.
- Any dependency.
- Any file location or name.
- The navigation contract (4 layers × 14 modules).

## Suggested definition of done for Phase 1

1. All five PRs merged, each reviewed independently, none mixing docs with code.
2. `python -m pytest -q` green on a developer machine with a populated `.env`.
3. Coverage still ≥ 80 %.
4. A re-run of `SCIENTIFIC_CLAIMS_REGISTER.md` shows zero claims classified
   **Misleading** or **Contradicted by implementation** in Tier 1.
5. `docs/audit/2026-snto-baseline/` updated with a short "Phase 1 delta" note
   rather than rewritten — the baseline stays a historical record.
