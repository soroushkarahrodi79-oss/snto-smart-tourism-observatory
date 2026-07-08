# Deployment

## Purpose
Document deployment maturity and release-governance risks.

## Background
SNTO has Docker and Azure Container Apps deployment mechanics, but the reviews found production-governance gaps.

## Current State
The deployment is suitable for demos or controlled pilots, not enterprise rollout. A documented mismatch was identified between CI-gated deployment claims and observed deploy behavior.

## Evidence
The repository audit and CTO review both called out deployment governance risk, lack of staged promotion, rollback playbooks, observability, and production readiness controls.

## Recommendations
Treat deployment as non-enterprise until CI gates, environment promotion, rollback, monitoring, and release approvals are formalized.

## Next Steps
Create separate dev, staging, and production release policies before onboarding institutional users.

## Related Documents
- [Technical Debt](technical-debt.md)
- [Enterprise Readiness](../strategy/enterprise-readiness.md)

