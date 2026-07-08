# SNTO Master Strategic Index

## Purpose
This index is the entry point for the SNTO strategic knowledge base. It explains where strategic, scientific, product, UX, architecture, and commercial decisions live.

## Background
The knowledge base consolidates the approved reviews produced in the Codex strategic audit conversation: repository audit, protected-area buyer review, scientific review, SaaS CTO review, CPO review, and international consensus review.

## Current State
SNTO is documented as a promising decision-intelligence platform for protected natural tourism destinations. The consensus position is that SNTO is strong as a concept and methodological framework, but not yet enterprise-ready, scientifically validated, or commercially mature enough to be treated as a global reference platform.

## Evidence
Authoritative summaries are archived in [docs/reviews/2026](docs/reviews/2026/README.md). Scores and repeated findings are normalized in [docs/appendix/scoring-matrix.md](docs/appendix/scoring-matrix.md) and [docs/appendix/recurring-themes.md](docs/appendix/recurring-themes.md).

## Documentation Architecture
- [Architecture](docs/architecture/README.md): software, deployment, security, scalability, technical debt, and future architecture.
- [Methodology](docs/methodology/README.md): scientific positioning, validation, uncertainty, limitations, and scientific review.
- [Product](docs/product/README.md): vision, personas, workflows, commercialization, and roadmap.
- [UX](docs/ux/README.md): information architecture, dashboard critique, accessibility, visualization, and UI evolution.
- [Reviews 2026](docs/reviews/2026/README.md): permanent record of the strategic reviews and consensus.
- [Roadmap](docs/roadmap/README.md): release-oriented plan from v1.1 through long-term vision.
- [Decisions](docs/decisions/README.md): Architecture Decision Records.
- [Strategy](docs/strategy/README.md): market position, differentiation, institutional adoption, competitors, and internationalization.
- [Appendix](docs/appendix/README.md): glossary, scoring, themes, bibliography, and document index.

## How Future Reviews Should Be Added
Add a dated folder under `docs/reviews/YYYY/`. Include an executive summary, full review, consensus analysis, risks, strengths, weaknesses, and roadmap implications. Update [docs/appendix/document-index.md](docs/appendix/document-index.md) and [docs/appendix/recurring-themes.md](docs/appendix/recurring-themes.md).

## How Future ADRs Should Be Written
Copy [docs/decisions/ADR-template.md](docs/decisions/ADR-template.md). Every ADR must include problem, context, options, decision, consequences, status, related documents, and review date. Approved ADRs should be linked from the relevant architecture, product, or methodology document.

## How Roadmap Updates Should Be Managed
Roadmap changes belong in [docs/roadmap](docs/roadmap/README.md). Each change should identify affected release, rationale, dependencies, risks, and impacted ADRs.

## How Strategic Decisions Should Be Documented
Strategic decisions belong in [docs/strategy](docs/strategy/README.md) and, if they affect architecture or delivery, also require an ADR. Repeated recommendations from reviews should be reflected in [docs/reviews/2026/07-consensus-analysis.md](docs/reviews/2026/07-consensus-analysis.md).

## Recommendations
Use this knowledge base as the single source of truth for SNTO's strategic direction. Avoid duplicating canonical definitions; link to the authoritative document instead.

## Next Steps
Future contributors should start with [docs/reviews/2026/00-executive-summary.md](docs/reviews/2026/00-executive-summary.md), then read the domain area relevant to their role.

## Related Documents
- [Document Index](docs/appendix/document-index.md)
- [Scoring Matrix](docs/appendix/scoring-matrix.md)
- [Consensus Analysis](docs/reviews/2026/07-consensus-analysis.md)

