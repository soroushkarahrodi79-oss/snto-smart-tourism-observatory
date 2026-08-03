# Contradictions and Open Questions

Where documentation and code disagree, **both readings are recorded and neither
is declared correct.** Resolution is an owner decision.

---

## Part 1 — Documentation ↔ implementation contradictions

### X-01 · `docs/ai-context/CLAUDE_CODE_HANDOFF_2026.md` is comprehensively stale

| Handoff says | Reality |
|---|---|
| "`app.py` is a monolith of around 2 890 lines" (§3) | `app.py` is **346 lines**, composition-only. Modularization shipped in v1.5.0. |
| "PR #1 … Not safe to merge yet"; "Do not merge PR #7" (§6, §13) | Both resolved long ago; `gh pr list` is the current source of truth. |
| "Do not start design/v2-exploration implementation yet" (§13.11) | Fase 6 UI evolution is complete and shipped in v2.0.0. |
| "API persistence is partial" (§3) | Fase 5 persistence is complete; production Postgres cutover executed 2026-07-18. |
| Roadmap v3.0 "Authentication, roles, permissions" as future | Shipped in code (PRs #109–#113), dormant pending real `User` rows. |

The document is explicitly framed as a point-in-time transfer, so this is not a
defect — but it is listed **second** in the Phase 0 grounding instructions, and a
new contributor following that order would form a materially wrong picture.
**Question:** should it be dated and marked historical, or retired in favour of
`CLAUDE.md` + `MASTER_STRATEGIC_INDEX.md`?

### X-02 · `docs/roadmap/README.md` contradicts `CLAUDE.md` on release state

- `docs/roadmap/README.md:12`: *"The `v2.0.0` tag + GitHub Release are **pending the owner**; `v1.5.0` (2026-07-18) is the last pushed stable tag."*
- `CLAUDE.md`: *"The `v2.0.0` tag + GitHub Release are **LIVE** (published 2026-07-21)."*

`CLAUDE.md` is almost certainly current (it also records the post-release dev-marker
bump to `2.1.0.dev0`, which `pyproject.toml:7` confirms). The roadmap README was
not updated. **Not resolved here.**

### X-03 · `fixtures.py` calls authored demo data "reales"

- `src/territorial/fixtures.py:20`: *"20 activos **reales** de la Reserva de la Biosfera Sierra del Rincón"*
- Same docstring, 4 lines later: *"Distribución de tiers **calibrada contra el motor TPI**"*, with per-asset comments `# TPI ≈ 95 | CU=40(CRITICAL) + ES=20.5 + SV=19.3 + CC=15` and `# Activadores garantizados`.
- ADR-004 and `CLAUDE.md` both forbid blurring real/calibrated/synthetic.

The place names and ecological narratives are genuine; the numeric fields are
authored to hit target tiers. **Question (as posed at audit time):** which class
does the owner intend — `CALIBRATED` (expert elicitation) or `SYNTHETIC` (demo)?
The answer changes what `evidence.supports()` permits these assets to back.

✅ **Resolved after audit: `SYNTHETIC`** (Q-01). Initially classified as
CALIBRATED during the audit; owner decision after audit: SYNTHETIC. That
decision governs Phase 0.5 and later work, and has been propagated through the
feature, map, KPI, claims, data-source and removal-candidate inventories. See
"Owner decisions after audit" below.

### X-04 · Map determinism docstrings vs `hash()` behaviour

- `map_layers.py:135`: *"the same asset always appears at the same location across page reloads"*
- `map_layers.py:183`: *"deterministic curved path (same trace on every reload, keyed on asset_id)"*
- Python salts `str` hashing per process; `PYTHONHASHSEED` is unset in `Dockerfile` and the deploy workflow. Verified: two runs, two different hashes.

True within a process, false across restarts/replicas. **This is a defect, not
an ambiguity** — but whether the fix is a stable hash or removal of the synthetic
geometry entirely is an owner decision (`REMOVAL_CANDIDATES.md` R-03).

### X-05 · `snapshot_provenance` always reports REAL

- `docs/methodology/evidence-classes.md` and ADR-004 require honest degradation.
- `src/platform/provenance.py:129`: `n_scenes = len(scene_dates) if scene_dates else 2`
- `:153`: `status=DataStatus.REAL` — unconditional.

Every other gate in the system (`mobility_snapshot_exists`, `real_zones_exist`,
`svi_history_available`, `get_park_boundary`, `_load_gis_feature_collection`,
`build_prug_monitoring`) degrades honestly. This one does not.

### X-06 · "Sin datos sintéticos" beside a simulated column

- `tab_diagnostic.py:440`: *"Salida real, sin datos sintéticos."*
- The same table's `Causa (SCM)` column and the map tooltip's `Causa:` field come from the α-decay **simulation** (`src/spatial_causality/zones/` absent).

### X-07 · `docs/reviews/2026/09-risk-register.md` shows all 10 risks "Open"

R02 (no enterprise auth/audit) and R06 (deployment governance) have both been
substantially addressed in code — identity/tenancy/audit shipped (PRs #109–#113),
CI-gated deploy shipped (ADR-009, #95). The register has not been reviewed since
authoring, despite its own instruction to *"review this register quarterly"*.

### X-08 · `pyproject.toml` declares no dependencies

`pyproject.toml:9`: `dependencies = []`, while `requirements.txt` carries 25
production pins. `pip install -e .` yields an unusable package. Intentional (the
project is deployed as an image, not a wheel) or an oversight?

### X-09 · `mypy` strict globally, enforced nowhere

`pyproject.toml:27` sets `strict = true`; `ci.yml:118` runs it
`continue-on-error: true` over three packages with ~110 known errors. Any new
module inherits a failing baseline that nothing enforces.

### X-10 · Two territory registries

`src/config/territories.py` (raster folder names) and
`src/ui/layout.py:310 _TERRITORY_CONFIG` (name, budget, map centre, report date),
plus a third read-only view via `platform/territory_registry.py` surfaced in
*Gobernar → Configuración territorial*. No single source of truth for "what is a
territory".

### X-11 · Default map centre is the archived territory

`map_layers.py:70-73` defaults to Sierra del Rincón (41.130, −3.490, zoom 11);
`_DEFAULT_CENTROID` likewise. PNSG is the active park. Live callers pass PNSG
explicitly so nothing is visibly broken — a latent bug for any new caller.

### X-12 · `README.md` synced, whitepaper deliberately not

`CLAUDE.md` states the whitepaper intentionally tracks the last *stable*
methodological baseline (v2.0.0) and must not be advanced with dev-branch
milestones. This is a **deliberate, documented policy**, recorded here so a
future audit does not mistake it for drift.

---

## Part 2 — Internal inconsistencies within the code

| # | Inconsistency | Locations |
|---|---|---|
| Y-01 | Two different EHS formulas under one brand and one 0–100 scale | `risk_engine/ehs.py` (5-component multi-year composite) vs `calculate_delta_ehs._trail_stress_score` (2-scene percentile deficit) |
| Y-02 | Two Sentinel-2 records presented as one | 2 local rasters (ΔEHS) vs the GEE 2021–2026 export (Mann-Kendall trends) |
| Y-03 | Three EHS band labellings | `tab_diagnostic.py:184-190`, `:358-364`, `real_trails.PRIORITY_BANDS` |
| Y-04 | Two alert-threshold implementations | `alerts/engine.py` and `platform/enrichment.py:50` |
| Y-05 | Four provenance vocabularies | `EvidenceClass`, `DataStatus`, `DataType`, `provenance.StatusBadge` — reconciled by `evidence.py` but all four remain in circulation, with `_STATUS_BADGE` duplicating `_DESCRIPTORS` strings verbatim |
| Y-06 | `visitor_capacity_annual` used as both capacity and current pressure | defined as capacity in `territorial/models.py`; consumed as `annual_pressure_proxy` in `pressure_capacity.py:127` and as a visitor count in KPI 3 |
| Y-07 | Sign convention inverted between pipeline and dashboard | handled correctly and in exactly one place (`metrics/semantics`, `real_trails._summary_to_health`) — but it is a standing trap, called out in the tab's own methodological note |

---

## Owner decisions after audit

Following review of the Phase 0 baseline, the owner has settled five of the
scientific open questions below (Q-01 through Q-05). These decisions are
binding for Phase 0.5 planning (`PHASE_1_RECOMMENDATIONS.md`). They are
recorded here as a distinct section — additive to the original findings —
rather than silently edited into Part 1/2 above, so the baseline continues to
show what was genuinely uncertain *at audit time*, with this section showing
what changed after review.

| Question | Decision | Where it is applied |
|---|---|---|
| **Q-01** — fixture evidence class | The `fixtures.py` assets are **`SYNTHETIC`**, not `CALIBRATED`. | `DATA_SOURCE_INVENTORY.md` D-07; `REMOVAL_CANDIDATES.md` R-08; `PHASE_1_RECOMMENDATIONS.md` PR 0.5.5. Under `platform/evidence.py`'s gating matrix, `SYNTHETIC` authorizes **no** decision use (monitoring, prioritization, intervention, or public reporting) — a stricter consequence than `CALIBRATED` would have carried. |
| **Q-02** — KPI 7 causal language | **Suspend immediately.** Do not wait for real SCM zones to be ingested. | `KPI_INVENTORY.md` K-14; `SCIENTIFIC_CLAIMS_REGISTER.md` C-01/C-02; `REMOVAL_CANDIDATES.md` R-01; `PHASE_1_RECOMMENDATIONS.md` PR 0.5.1. This is Phase 0.5 work, not deferred pending data. |
| **Q-03** — Aug-2025/Apr-2026 scene pair | The pair **cannot support** seasonal, trend, recovery, deterioration, or causal claims of any kind. | `SYSTEM_BASELINE.md` §3; `MAP_INVENTORY.md` M-03; `KPI_INVENTORY.md` K-02; `SCIENTIFIC_CLAIMS_REGISTER.md` C-12. Every surface presenting ΔEHS must describe it only as a dated two-scene comparison. |
| **Q-04** — SCM decision thresholds | Classified as **`EXPERIMENTAL_HEURISTIC`** — an operating rule the system runs on today, locally unvalidated, until its basis is documented and tested. Not `arbitrary`: the repository does not demonstrate deliberate, methodless value selection, only the absence of a citation. | `KPI_INVENTORY.md` K-03 and its Reading Key vocabulary. |
| **Q-05** — TIS visitor-uplift coefficients | **Illustrative scenario assumptions only.** May not be presented as observed efficiency or as a forecast effect. | `KPI_INVENTORY.md` K-06, K-15; `SCIENTIFIC_CLAIMS_REGISTER.md` C-10. |

Q-06 through Q-21 (and Y-01 through Y-07) remain open below, unchanged by this
review.

---

## Part 3 — Open questions for the owner

**Scientific**

1. **Q-01** What is the intended evidence class of the `fixtures.py` assets — `CALIBRATED` or `SYNTHETIC`? (Determines what `evidence.supports()` lets them back.) — ✅ **RESOLVED after audit: `SYNTHETIC`.** See "Owner decisions after audit" above.
2. **Q-02** Should KPI 7's causal language be suspended now, or held until real SCM zones are ingested? A `zones/` export is a documented, zero-code-change path. — ✅ **RESOLVED after audit: suspend immediately.** See "Owner decisions after audit" above.
3. **Q-03** Are the two Sentinel-2 scenes (Aug 2025 / Apr 2026) an acceptable basis for any "seasonal deterioration" claim, given the year gap and the S2A/S2B change? Should `src/validation/cross_sensor.py` be wired into the ΔEHS path? — ✅ **RESOLVED after audit: no, the pair cannot support any seasonal/trend/recovery/causal claim.** Whether `cross_sensor.py` gets wired in remains open — see "Owner decisions after audit" above.
4. **Q-04** Where do the SCM decision thresholds (0.07 / 0.15 / 0.85 / 0.70) come from? The α coefficients are cited; these are not. — ✅ **RESOLVED after audit: classified `EXPERIMENTAL_HEURISTIC`, locally unvalidated.** See "Owner decisions after audit" above.
5. **Q-05** What is the source of the TIS visitor-uplift coefficients (25 % / 15 % / 8 % / 5 %)? — ✅ **RESOLVED after audit: illustrative scenario assumptions only, not an observed or forecast effect.** See "Owner decisions after audit" above.
6. **Q-06** Should `capacity_at_standard` be restricted to assets the SCM classifies as LOCALIZED_IMPACT, given that it attributes all EHS deficit to visitors?
7. **Q-07** What is the source of the "340 % sobre la capacidad de carga" claim for Laguna de Peñalara?

**Product**

8. **Q-08** Should the decision layer be re-rooted on the 218 real trails? Three fields have no real equivalent (`economic_importance`, `accessibility_score`, `visitor_capacity_annual`) — should they be `MISSING`, or retained as declared policy inputs?
9. **Q-09** Should the default view remain **Tribunal/Auditoría** (`app.py:97`)? A first-time institutional visitor currently lands in the methodological-review view.
10. **Q-10** Should the 60-second autorefresh and "live" pulse be kept over a manually-refreshed dataset?
11. **Q-11** Is the ArcGIS Experience Builder Batch C intended to proceed? It remains prepared, unauthorized, unexecuted.

**Engineering / ops**

12. **Q-12** Apply the PostGIS migration `b2c3d4e5f6a7` to production `snto-db`, or defer until a consumer exists?
13. **Q-13** Should anything in `src/` populate `managed_assets`? Without it, PostGIS, tenancy, audit, `/api/v2` and the mobile client have nothing to serve.
14. **Q-14** What is the disposition of the 12 untracked OAPN GEE CSVs and `downgrade_preview.sql` — commit, ignore, or delete?
14b. **Q-14b** Should the 46 tracked `.pyc` files be removed from version control and `__pycache__/` added to `.gitignore`? Running the test suite currently modifies tracked files, so no contributor can produce a clean `git status` after testing. (This audit restored them with `git checkout -- "*.pyc"` after the baseline test run.)
15. **Q-15** Is `pyproject.toml`'s empty `dependencies` list intentional?
16. **Q-16** Should `docs/ai-context/CLAUDE_CODE_HANDOFF_2026.md` be dated as historical?
17. **Q-17** Are the root `run_phase*_report.py` scripts still used?
18. **Q-18** Does anything external call the legacy v1 API routers?

**Legal / commercial**

19. **Q-19** Do OSM's ODbL share-alike terms constrain the GeoJSON/GeoPackage export feature? No document addresses this.
20. **Q-20** What are OAPN's redistribution terms for the trail cartography and PRUG zonification embedded in the exports?
21. **Q-21** The seven `🔲` commercial decisions in `docs/product/pilot-package.md` remain open (`grep -n "🔲" docs/product/pilot-package.md`).
