# Claude Code Handoff 2026

## 1. Purpose of This Handoff

This file transfers the important conclusions from a long Codex strategic, scientific, product, technical, repository-safety, and documentation review conversation into durable context for Claude Code. It is not a new audit and not a new review. Its purpose is to let Claude Code understand the current state of SNTO without access to the original chat.

## 2. Project Identity

SNTO means Smart Natural Tourism Observatory. It is a scientific-product prototype for decision intelligence in protected natural tourism destinations.

The current active case study is Parque Nacional de la Sierra de Guadarrama (PNSG). Sierra del Rincon is archived and should not be treated as the active pilot.

SNTO is currently a Python 3.12 / Streamlit prototype with research credibility, product ambition, and possible SaaS/institutional futures. It should be understood as an advanced scientific-product prototype rather than an enterprise-ready platform.

## 3. Current Repository Assessment

Current assessment scores from the Codex review:

- Repository health: 78/100
- Maintainability: 74/100
- Scalability: 72/100
- Design system consistency: 70/100
- Enterprise readiness: 66/100

Strengths:

- Strong domain modeling.
- Transparent scientific caveats.
- Broad unit coverage.
- Production-minded Streamlit deployment path.
- Healthier analytical core under `src/`.
- Scientific defensibility.
- Score-semantics guardrails.
- Curated data provenance.

Weaknesses:

- `app.py` is a monolith of around 2,890 lines.
- UI, orchestration, copy, state, and product logic are intertwined.
- Deployment workflow appears to have drift from README claims.
- API persistence is partial.
- No observed authentication layer.
- `.env` exists locally.
- Data artifacts are tracked despite a data ignore policy.
- Many branches contain stacked or duplicated future work.

## 4. Architecture Overview

The repository contains two main conceptual pipelines.

Pipeline A is the real geospatial PNSG workflow:

- Sentinel-2 inputs.
- Raster/vector ETL.
- Operational EHS.
- SCM.
- Causal budget.
- Curated dashboard outputs.

Pipeline B is the territorial intelligence demo/governance workflow:

- Calibrated and synthetic assets.
- TPI.
- TIS.
- DCS.
- Executive dashboard.
- Maturity model.
- Stakeholders.
- Reports.

Core module areas include:

- `ingestion`
- `features`
- `geospatial`
- `time_series`
- `risk_engine`
- `spatial_causality`
- `decision_confidence`
- `territorial`
- `intervention`
- `platform`
- `validation`
- `socioeconomic`
- `api`

## 5. Branch Situation

Known branch state from the review:

- `feature/v1.1.0-multiyear-trends`: 7 ahead / 7 behind, 34 files, about +8,080 lines. Adds real PNSG time series, GEE scripts, and satellite trends. Medium risk.
- `feature/v1.2.0-oapn-network-expansion`: 8 ahead / 7 behind, 52 files, about +10,812 lines. Contains v1.1 plus OAPN templates/expansion plan. Medium-high risk.
- `research/statistical-rigor`: 15 ahead / 7 behind, 69 files, about +13,208 lines. Contains v1.1, v1.2, and statistical rigor work including Pettitt tests, confidence intervals, and cross-sensor considerations. High risk but valuable.
- `fix/readme-doi-badge`: 1 ahead / 8 behind. Likely obsolete or should be handled manually.
- `docs/*` branches: mostly already merged or obsolete, except the clean documentation recovery branch described below.
- `hf-space`, `hf-deploy`, `space/main`: divergent Hugging Face packaging. High risk as merge targets.
- `backup-antes-de-purgar`: archive only.

Current clean documentation recovery branch:

- `docs/strategic-knowledge-base-2026-clean` was recreated from latest `main`.
- It was committed and pushed as `305b137 docs: add SNTO strategic knowledge base 2026`.
- It should be used to open a replacement docs-only PR.

## 6. Pull Request Situation

PR #1: `feat: v1.1.0 - capa temporal Sentinel-2 real 2021-2026`

- Functional v1.1.0 PR.
- 34 files changed.
- 8,127 additions / 91 deletions.
- Coherent for v1.1 scope.
- High risk.
- Conflicting.
- No checks reported during review.
- Not safe to merge yet.
- Potentially safe later after conflict resolution, CI, review, generated asset validation, and dependency review.

PR #7: `docs: add SNTO strategic knowledge base 2026`

- Intended as docs-only.
- Actually contaminated.
- 151 files changed.
- 15,975 additions / 95 deletions.
- Includes strategic docs plus v1.1/v1.2/statistical-rigor functional changes.
- Modifies `app.py`, `src/`, `tests/`, `scripts/`, `.github/`, `requirements.txt`, `pyproject.toml`, and `clean_assets/`.
- Not safe to merge as-is.
- Should be kept only as reference or replaced by a clean docs-only PR.

Conflict risk:

- PR #7 overlaps with every file in PR #1.
- 34/34 PR #1 files overlap with PR #7.
- PR #7 appears stacked on PR #1 plus additional future work.
- Merging PR #7 first would accidentally merge functional work.

## 7. Documentation System Created

Codex created a strategic documentation system under `docs/` and `MASTER_STRATEGIC_INDEX.md`.

It includes:

- Architecture docs.
- Methodology docs.
- Product docs.
- UX docs.
- Strategy docs.
- 2026 review archive.
- Roadmap docs.
- ADRs.
- Appendix.

Documentation QA scores:

- Documentation completeness: 96/100.
- Documentation usefulness: 88/100.
- Strategic clarity: 90/100.
- Internal consistency: 92/100.
- Actionability: 86/100.

Added ADRs:

- ADR-004: Separate Real, Calibrated, Synthetic, and Simulated Evidence.
- ADR-005: Require Authentication, Authorization, and Audit Before Enterprise Adoption.
- ADR-006: Introduce Persistent Backend Resources Before Operational Workflows.
- ADR-007: Keep UI Evolution Separate From v1.0 Stability.
- ADR-008: Use Existing GIS and EO Platforms as Integration Surfaces.
- ADR-009: Formalize Deployment Governance Before Institutional Rollout.
- ADR-010: Use a Hybrid Documentation Repository Strategy.

## 8. Repository Separation Decision

The final recommendation is a hybrid approach.

Keep in the main repository for now:

- Code-coupled architecture docs.
- Technical ADRs.
- Deployment/security/API docs.
- Methodology docs tightly coupled to algorithms.
- Compact strategic index.

Move later to a separate repository if collaboration or confidentiality grows:

- Strategic reviews.
- Product positioning.
- Commercialization.
- Institutional adoption.
- Competitor analysis.
- Long-term strategy.
- Sensitive consensus documents.

Suggested future repository name: `snto-knowledge-base`.

Do not migrate yet. Review this decision after v1.1 stabilization or before external sharing.

## 9. Strategic Product Conclusions

SNTO is not yet an international reference product. It is a strong scientific-product prototype above typical academic level, but it is below leading platforms in SaaS maturity, UX, information architecture, institutional trust, and operational scalability.

SNTO should not compete directly with ArcGIS, Google Earth Engine, Sentinel Hub, Tableau, Power BI, or Palantir. It should position as: "Decision Intelligence for Protected Natural Tourism Destinations."

Brutal summary: "SNTO has the brain of a reference product but the body of an advanced academic prototype."

Core differentiation:

- Vertical tourism-natural-area domain.
- Translation from ecological stress to management, investment, and conservation decisions.
- Scientific transparency.
- Causal decision chain: ecological state -> probable cause -> confidence -> priority -> budget.

## 10. Main Product Risks

- Too many ambitions at once.
- Dashboard demonstrates capability rather than guiding decisions.
- Cognitive density.
- Weak multi-territory product shape.
- No enterprise-grade authentication, governance, or audit yet.
- Uncertainty is documented but not central enough in the UX.
- Real, synthetic, calibrated, and simulated evidence separation must never regress.
- Scientific claims need validation before institutional overclaiming.

## 11. Recommended Product Direction

SNTO should become the best platform for translating ecological stress in protected natural tourism destinations into defensible management, investment, and conservation decisions.

It should evolve:

- From dashboard to decision system.
- From one case to repeatable territory model.
- From methodology to institutional trust.
- From academic prototype to operational decision platform.

## 12. Roadmap

v1.1:

- Integration.
- Stabilization.
- Real Sentinel-2 time series.
- Evidence clarity.
- Deployment gating correction.
- PR #1 conflict resolution.
- CI/checks.
- Generated asset validation.

v1.2:

- Controlled OAPN expansion.
- Pilot readiness.
- Additional park templates.
- Validation structure.
- Avoid overclaiming multi-park maturity before real validation.

v2.0:

- `app.py` modularization.
- UI evolution.
- Page-like dashboard structure.
- Persistent backend/API resources.
- Design system formalization.
- Evidence separation in UX.
- Modular product architecture.

v3.0:

- Enterprise readiness.
- Authentication, roles, and permissions.
- Audit logging.
- Multi-territory architecture.
- Institutional governance.
- Observability.
- Integration with GIS/EO platforms.

## 13. Immediate Next Actions

1. Do not merge PR #7.
2. Open a new clean documentation-only PR from `docs/strategic-knowledge-base-2026-clean`.
3. Verify that the new PR includes only documentation/context files.
4. Close contaminated PR #7 only after the clean PR is verified.
5. Keep PR #1 open.
6. Resolve PR #1 conflicts.
7. Run checks/CI.
8. Review `app.py`, requirements, `pyproject.toml`, workflows, and generated assets in PR #1.
9. Convert v1.1 action items into tickets.
10. Modularize `app.py` before any major design evolution.
11. Do not start design/v2-exploration implementation yet.

Note: the clean branch already exists and has been pushed. The remaining human action is to open and verify the replacement PR.

## 14. Rules for Future AI Agents

Any future AI agent working on SNTO must:

- Preserve v1.0 stability.
- Not modify `main` directly.
- Not merge PRs without human approval.
- Not mix docs and functional changes.
- Not introduce v2 UI work into v1.1/v1.2.
- Not weaken evidence labeling.
- Not remove methodological caveats.
- Not overstate scientific validity.
- Not treat synthetic/calibrated data as observed data.
- Not assume SaaS enterprise readiness exists.
- Not attempt to replace GIS/EO platforms.
- Use branches for all changes.
- Produce clean PRs with narrow scope.

## 15. Open Decisions

- Whether to keep all docs in the main repo for now or later split into `snto-knowledge-base`.
- When to close PR #7.
- When to merge the clean docs-only PR.
- Whether PR #1 needs splitting before merge.
- Whether v1.2 should wait until v1.1 stabilization.
- When to begin `app.py` modularization.
- When to begin UI/design evolution.
- What validation threshold is required before institutional claims.

## 16. How Claude Code Should Use This File

Claude Code should read repository-level `CLAUDE.md` first. Then it should read this handoff. After that, it should read `MASTER_STRATEGIC_INDEX.md` and `docs/` only if needed.

Before making changes, Claude Code should identify the intended release target:

- docs-only
- v1.1
- v1.2
- v2.0
- research
- infrastructure

Claude Code should warn or refuse if a requested change mixes scopes in a way that risks contaminating a PR.

