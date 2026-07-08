# Priority Roadmap And Action Matrix

## Purpose
Classify recommendations by priority, impact, complexity, risk, dependencies, effort, and suggested release.

## Background
The documentation brief required every recommendation to become actionable.

## Current State
Recommendations are grouped by release maturity. v1.1 is integration and stabilization; v1.2 is controlled expansion; v2.0 is modular product architecture and UI evolution; v3.0 is enterprise/institutional platform maturity.

## Evidence
The matrix consolidates repeated recommendations from all reviews.

| ID | Recommendation | Rationale | Priority | Impact | Complexity | Risk | Dependencies | Effort | Release |
|---|---|---|---|---|---|---|---|---|---|
| A01 | Narrow positioning to protected-area decision intelligence | Prevents product dilution and aligns all future decisions. | Critical | High | Low | Low | ADR-001 | S | v1.1 |
| A02 | Separate real/calibrated/synthetic/simulated evidence | Prevents overclaiming and protects scientific trust. | Critical | High | Medium | Medium | ADR-004, evidence model | M | v1.1 |
| A03 | Define validation protocol | Establishes the scientific gate for pilots and publication. | Critical | High | Medium | Medium | Scientific partners | M | v1.1 |
| A04 | Create director-grade risk brief prototype | Converts broad observatory content into decision-first framing without destabilizing v1.0. | High | High | Medium | Medium | Product IA, ADR-007 | M | v1.1 |
| A05 | Execute first field validation campaign | Moves SNTO from plausible method to credible evidence. | Critical | High | High | High | Field partners, A03 | L | v1.2 |
| A06 | Add GIS export/integration path | Makes SNTO complementary to agency systems rather than competitive. | High | High | Medium | Medium | ADR-008, GIS requirements | M | v1.2 |
| A07 | Create procurement-ready paid pilot package | Turns strategic interest into a sellable, bounded engagement. | High | High | Medium | Medium | Positioning, validation plan | M | v1.2 |
| A08 | Define asset action-state model | Creates the product backbone for field verification and interventions. | High | High | Medium | Medium | Product workflows, ADR-006 | M | v1.2 |
| A09 | Add field verification workflow | Connects satellite alerts to operational evidence. | High | High | High | Medium | Backend persistence, A08 | L | v2.0 |
| A10 | Add intervention lifecycle | Enables accountable management from detection through resolution. | High | High | High | Medium | Backend persistence, A08 | L | v2.0 |
| A11 | Add auth, roles, tenancy, audit | Required before enterprise or institutional adoption. | Critical | High | High | High | ADR-005, platform architecture | XL | v2.0 |
| A12 | Add observability and release governance | Required for production reliability and public-sector confidence. | Critical | High | High | Medium | ADR-009, DevOps architecture | L | v2.0 |
| A13 | Modularize product architecture and UI surfaces | Separates operational, analyst, audit, and reporting experiences. | High | High | High | Medium | ADR-007, product backend | XL | v2.0 |
| A14 | Validate across multiple protected areas | Tests transferability and international credibility. | Critical | High | High | High | Pilot partners, A05 | XL | v3.0 |
| A15 | Build benchmarking and national rollups | Supports agency-level procurement and reporting. | Medium | High | High | Medium | Multi-park data, A14 | XL | v3.0 |
| A16 | Public transparency portal | Supports public accountability after internal evidence is trustworthy. | Medium | Medium | High | Medium | Institutional adoption, audit model | L | Future |

## Recommendations
Do not promote lower-priority expansion features above validation and platform trust.

## Next Steps
Convert high-priority items into release plans and ADRs where needed. Items requiring product backend, auth, or audit should not be pulled into v1.1 because that would risk v1.0 stability.

## Related Documents
- [Roadmap](../../roadmap/README.md)
- [Risk Register](09-risk-register.md)
