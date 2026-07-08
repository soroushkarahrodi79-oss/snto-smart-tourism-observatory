# Architecture Documentation

## Purpose
Document SNTO's software architecture, operational risks, and future technical direction.

## Background
The approved CTO and repository reviews found that SNTO is a strong analytical prototype but not yet enterprise SaaS.

## Current State
The repository contains structured analytical modules, a large Streamlit application surface, FastAPI endpoints, Docker packaging, GitHub Actions, and Azure Container Apps deployment.

## Evidence
See [../reviews/2026/01-repository-audit.md](../reviews/2026/01-repository-audit.md) and [../reviews/2026/04-enterprise-cto.md](../reviews/2026/04-enterprise-cto.md).

## Contents
- [System Overview](system-overview.md)
- [Repository Architecture](repository-architecture.md)
- [Technical Debt](technical-debt.md)
- [Scalability](scalability.md)
- [Security](security.md)
- [Performance](performance.md)
- [Deployment](deployment.md)
- [Future Architecture](future-architecture.md)

## Recommendations
Use this section to guide enterprise hardening, not scientific or product positioning.

## Next Steps
Prioritize security, deployment governance, persistence, observability, and modular product architecture.

## Related Documents
- [ADR-001](../decisions/ADR-001.md)
- [Enterprise Readiness](../strategy/enterprise-readiness.md)

