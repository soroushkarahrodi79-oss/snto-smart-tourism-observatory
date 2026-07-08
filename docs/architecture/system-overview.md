# System Overview

## Purpose
Summarize SNTO's current software system from an architecture perspective.

## Background
SNTO combines Earth observation analysis, ecological indicators, territorial prioritization, and dashboard presentation.

## Current State
The system is best understood as a Python analytical application with:
- domain modules under `src`;
- Streamlit as the primary product surface;
- FastAPI as a secondary analytical API;
- ETL/reporting scripts;
- Docker and Azure Container Apps deployment;
- GitHub Actions CI/deploy workflows.

## Evidence
The repository audit identified two analytical pipelines: real geospatial PNSG processing and broader territorial-intelligence demonstration. The CTO review found this architecture insufficient for enterprise SaaS because it lacks auth, tenancy, audit, durable workflow state, and operational observability.

## Recommendations
Treat the current system as a pilot architecture. Do not position it as enterprise SaaS until a product backend, identity model, audit model, and workflow layer exist.

## Next Steps
Define the future platform boundary around assets, observations, indicators, recommendations, interventions, users, territories, and audit events.

## Related Documents
- [Repository Architecture](repository-architecture.md)
- [Future Architecture](future-architecture.md)
- [Enterprise CTO Review](../reviews/2026/04-enterprise-cto.md)

