# Security

## Purpose
Record the security posture identified by the enterprise software review.

## Background
Security was the lowest-scoring engineering dimension.

## Current State
Critical gaps:
- no visible authentication;
- no role-based authorization;
- no tenant isolation;
- no audit trail;
- no API rate limiting;
- no enterprise secrets governance;
- no security testing evidence;
- Streamlit protections were identified as disabled in the deployment command.

## Evidence
The CTO review assigned security 25/100 and treated auth, authorization, audit, and tenant isolation as hard blockers.

## Recommendations
SNTO should not be approved for enterprise customers until security foundations exist.

## Next Steps
Create ADRs and implementation plans for identity provider integration, role model, audit events, tenant boundaries, and security testing.

## Related Documents
- [Enterprise Readiness](../strategy/enterprise-readiness.md)
- [ADR-001](../decisions/ADR-001.md)

