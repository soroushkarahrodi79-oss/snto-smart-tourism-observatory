# Repository Architecture

## Purpose
Record the repository-level architecture observed during the audit.

## Background
The repository includes a large application entrypoint, many domain modules, scripts, tests, docs, deployment files, and multiple feature branches.

## Current State
The analytical modules are better separated than the product shell. Major domains include ingestion, geospatial processing, time series, risk scoring, spatial causality, decision confidence, territorial prioritization, intervention modeling, platform/dashboard logic, validation, socioeconomic modeling, and API routers.

## Evidence
The original audit found a large `app.py` around 2,890 lines. Phase 4 has reduced it to approximately 2,072 lines by extracting territorial fixtures, shared render helpers/widgets and the first dashboard tabs, but the target of fewer than 300 composition-only lines is not yet met. The FastAPI layer exists but is not a mature SaaS API.

## Recommendations
Preserve analytical domain boundaries. Treat the Streamlit application shell as a pilot interface. Avoid letting UI orchestration become the canonical product architecture.

## Next Steps
Move future architectural decisions into ADRs and avoid adding new strategic responsibilities to the monolithic app surface.

## Related Documents
- [Technical Debt](technical-debt.md)
- [Future Architecture](future-architecture.md)

