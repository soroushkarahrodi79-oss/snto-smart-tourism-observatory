# Repository Separation Assessment

## Purpose
Assess whether SNTO's strategic knowledge base should remain in the main repository or move to a separate repository.

## Background
The documentation QA brief asked for a separation assessment without performing migration.

## Current State
The strategic knowledge base currently lives under `docs/` in the main code repository.

## Evidence
The knowledge base now includes architecture, methodology, product, UX, strategy, reviews, roadmap, ADRs, and appendix material. Some of this is code-coupled; some is strategic, commercial, institutional, or potentially confidential.

## Option A: Keep Documentation Inside Main Repository
Advantages:
- Strong connection between code and strategic rationale.
- Simple navigation for developers.
- ADRs and architecture docs stay close to implementation.
- No cross-repository synchronization overhead.

Disadvantages:
- Strategic and commercial material can clutter the engineering repository.
- Confidential reviews may be harder to share selectively.
- Non-technical collaborators may avoid the code repository.
- Long-term documentation growth can make `docs/` noisy.

## Option B: Create Separate `snto-knowledge-base` Repository
Advantages:
- Cleaner code repository.
- Easier sharing with supervisors, institutions, advisors, and partners.
- Better separation between engineering documentation and strategic knowledge.
- Can support different confidentiality and access rules.
- Better long-term home for reviews, product strategy, commercialization, and institutional adoption.

Disadvantages:
- Cross-repository links can drift.
- ADRs that affect implementation may be missed by developers.
- More Git workflow overhead.
- Requires explicit ownership and synchronization.

## Recommendation
Use a hybrid approach.

Keep in the code repository:
- code-coupled architecture docs;
- technical ADRs that guide implementation;
- methodology docs directly tied to algorithms;
- developer-facing README and index links;
- API, deployment, and operational documentation.

Move to `snto-knowledge-base` when approved:
- strategic reviews;
- product positioning;
- commercialization;
- institutional adoption;
- internationalization;
- market/competitor analysis;
- long-term strategic roadmap;
- sensitive consensus documents.

## Proposed Repository Name
`snto-knowledge-base`

## Proposed Knowledge-Base Structure
- `README.md`
- `strategy/`
- `product/`
- `reviews/`
- `roadmap/`
- `methodology/`
- `decisions/`
- `appendix/`

## Migration Plan
1. Keep current docs in main repo until human approval.
2. Create `snto-knowledge-base`.
3. Move strategic/product/review documents first.
4. Leave stubs in main repo linking to the knowledge base.
5. Keep technical ADRs mirrored or referenced from the main repository.
6. Define an owner for cross-repo link maintenance.

## Recommendations
Do not split immediately if the project is still solo-developed. Split when collaboration, confidentiality, or documentation scale becomes a real operating constraint.

## Next Steps
Human decision required: keep all docs in main repo, split fully, or adopt the recommended hybrid model.

## Related Documents
- [ADR-010](../decisions/ADR-010.md)
- [Master Strategic Index](../../MASTER_STRATEGIC_INDEX.md)

