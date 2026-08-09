# Paper 1 — Scientific Validation Program

Publication-oriented working set for **one** paper: empirical validation of SNTO's Sentinel-2-derived ecological stress indicator against real field observations in Parque Nacional de la Sierra de Guadarrama.

**Start here:** [`PAPER1_MASTER_EXECUTION_PLAN.md`](PAPER1_MASTER_EXECUTION_PLAN.md)

## Documents

| # | Document | Purpose |
|---|---|---|
| 0 | [`PHASE0_REPOSITORY_AUDIT.md`](PHASE0_REPOSITORY_AUDIT.md) | What the code and data actually support, verified against implementation and tests |
| 1 | [`PAPER1_SCIENTIFIC_CONTRACT.md`](PAPER1_SCIENTIFIC_CONTRACT.md) | **Governing document.** Question, hypotheses, evidence rules, stop/go, forbidden claims |
| 2 | [`FIELD_CAMPAIGN_EXECUTION_PLAN.md`](FIELD_CAMPAIGN_EXECUTION_PLAN.md) | Two-stage sampling design + field-day checklist |
| 3 | [`SPATIAL_MATCHING_PROTOCOL.md`](SPATIAL_MATCHING_PROTOCOL.md) | Plot ↔ satellite support; the sub-pixel problem |
| 4 | [`SATELLITE_FIELD_MATCHING_PLAN.md`](SATELLITE_FIELD_MATCHING_PLAN.md) | Acquisition window, quality rules, no-interpolation rule |
| 5 | [`STATISTICAL_ANALYSIS_PLAN.md`](STATISTICAL_ANALYSIS_PLAN.md) | **Freeze before data collection.** Tests, thresholds, sensitivity |
| 6 | [`SCM_REFRAMING.md`](SCM_REFRAMING.md) | Spatial contrast ≠ causal attribution; threshold provenance |
| 7 | [`DATA_ACQUISITION_TRIAGE.md`](DATA_ACQUISITION_TRIAGE.md) | Must / secondary / future / never-fabricate |
| 8 | [`MANUSCRIPT_OUTLINE.md`](MANUSCRIPT_OUTLINE.md) | Skeleton with every absent result marked `[TBD]` |
| 9 | [`FIGURE_PLAN.md`](FIGURE_PLAN.md) | Figures + required source data |
| 10 | [`JOURNAL_STRATEGY.md`](JOURNAL_STRATEGY.md) | Venue fit; decision staged until results exist |
| 11 | [`IMPLEMENTATION_BACKLOG.md`](IMPLEMENTATION_BACKLOG.md) | Minimum code; **nothing implemented pending approval** |
| — | [`PNSG_RESEARCH_AUTHORIZATION_REQUEST.md`](PNSG_RESEARCH_AUTHORIZATION_REQUEST.md) | Draft permit application (gate G2). Technical content complete; applicant identity and territorial scope (Madrid vs. Castilla y León) still open. **Nothing submitted.** |

## Status

**No code has been changed. No scientific threshold has been modified. No field data exists.**

**Sampling frame decided (2026-08-09): the 218 real OAPN trail segments** (`PAPER1_SCIENTIFIC_CONTRACT.md` §F, option F-1). This forfeits nothing the cross-sectional design needed, but it means the existing real SCM/SIG values already computed for those 218 trails are **not** usable for the H4 spatial-contrast analysis as-is — they come from the same disqualified satellite-scene pair as `delta_ehs` and need a fresh extraction against the campaign-matched composite (Backlog B-14).

Remaining blocking owner decisions are marked 🔲 throughout; they are collected in the Master Execution Plan §7.

## Relationship to existing documentation

- **Supersedes for Paper-1 purposes:** `docs/field_validation_protocol.md` (audited and extended in #2), and the validation-readiness prose in `docs/methodology/validation.md`.
- **Builds on, does not duplicate:** `docs/audit/2026-snto-baseline/` (the broader Phase 0 system baseline, PR #143).
- **Does not modify:** `WHITEPAPER_SNTO_Architecture_Blueprint.md`, which tracks the latest *stable* methodological baseline by its own scope rule and must not be rewritten with dev-branch work.
- **Preserves unchanged:** the `INSUFFICIENT_EVIDENCE` state of visitor-pressure forecasting, and every ADR-004 evidence-class rule.

## Non-negotiables carried into every document here

Never fabricate an observation · never promote `SYNTHETIC` / `SIMULATED` / `ESTIMATED` / proxy evidence to `OBSERVED` · never substitute NDVI/NDMI/EHS/capacity/mobility for a visitor measurement · no causal claim without REAL evidence **+** validated method **+** supported attribution **+** independent verification · when evidence is missing, say **MISSING**; when a method is plausible but unvalidated, say **PLAUSIBLE BUT UNVALIDATED**; when a proxy is used, name it **and** name the target it does not measure.
