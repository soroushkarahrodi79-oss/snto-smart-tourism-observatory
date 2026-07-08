# Risk Register

## Purpose
Maintain a professional register of strategic, scientific, product, and engineering risks.

## Background
Risks were identified across all independent reviews.

## Current State
The most severe risks are validation, enterprise security, product focus, and institutional trust.

## Evidence
The risk table consolidates repeated risks from the reviews.

| ID | Description | Probability | Impact | Severity | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|---|
| R01 | Scientific claims outrun field validation | High | High | Critical | Execute validation and reduce claim strength | Science Lead | Open |
| R02 | No enterprise auth/authorization/audit | High | High | Critical | Build identity, roles, audit model | Engineering Lead | Open |
| R03 | Product remains too broad and academic | High | High | Critical | Adopt ADR-001 and simplify workflows | Product Lead | Open |
| R04 | Causal attribution is overclaimed | Medium | High | High | Use causal-hypothesis language and validate | Science Lead | Open |
| R05 | Institutional buyers distrust satellite-only inference | Medium | High | High | Add field verification and evidence reports | Product/Science | Open |
| R06 | Deployment governance blocks enterprise use | Medium | High | High | Add staged release and CI gates | DevOps Lead | Open |
| R07 | GIS incumbents make SNTO look redundant | Medium | Medium | Medium | Position as decision layer and integrate | Product Lead | Open |
| R08 | Public-sector procurement lacks clear package | Medium | Medium | Medium | Create paid pilot package | Commercial Lead | Open |
| R09 | Generalizability across habitats fails | Medium | High | High | Multi-territory validation | Science Lead | Open |
| R10 | Monolithic product surface slows evolution | High | Medium | High | Platform architecture roadmap | Engineering Lead | Open |

## Recommendations
Review this register quarterly during active roadmap execution.

## Next Steps
Assign named owners before pilot commercialization.

## Related Documents
- [Technical Debt](../../architecture/technical-debt.md)
- [Validation](../../methodology/validation.md)

