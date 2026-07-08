# Technical Debt

## Purpose
Define the major technical debt categories identified by the reviews.

## Background
The CTO and repository reviews found that SNTO's debt is not primarily analytical; it is product-platform debt.

## Current State
Highest-severity debt:
- monolithic Streamlit product surface;
- no enterprise auth or authorization;
- no tenancy model;
- no audit trail;
- incomplete API resource model;
- in-memory API stores;
- deployment governance mismatch;
- mixed research/demo/production concerns;
- fragmented branch strategy.

## Evidence
The CTO review scored technical maturity 42/100, architecture 45/100, security 25/100, DevOps 48/100, and enterprise readiness 28/100.

## Recommendations
Do not treat technical debt as cleanup. Treat it as adoption risk. Enterprise customers should not be onboarded until critical platform debt is resolved.

## Next Steps
Use [../reviews/2026/08-priority-roadmap.md](../reviews/2026/08-priority-roadmap.md) to sequence technical debt by release.

## Related Documents
- [Risk Register](../reviews/2026/09-risk-register.md)
- [Security](security.md)
- [Deployment](deployment.md)

