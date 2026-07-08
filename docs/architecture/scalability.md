# Scalability

## Purpose
Document scalability limitations and future scaling requirements.

## Background
The reviews distinguished between running a demo dashboard and operating a multi-park SaaS platform.

## Current State
SNTO may scale for a small number of dashboard users. It does not yet demonstrate scalability for multi-tenant institutional use, many protected areas, long-running geospatial jobs, or large asset inventories.

## Evidence
The CTO review identified missing background jobs, persistence, multi-tenant architecture, observability, and performance budgets.

## Recommendations
Scale the product around institutional workflows, not dashboard rendering. Long-running analysis should become asynchronous. Customer data should be modeled explicitly.

## Next Steps
Define target scale assumptions for v2.0: number of territories, assets, users, observations, reports, and concurrent jobs.

## Related Documents
- [Future Architecture](future-architecture.md)
- [Performance](performance.md)

