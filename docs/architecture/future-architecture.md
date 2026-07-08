# Future Architecture

## Purpose
Define the architecture direction required for SNTO to become an institutional platform.

## Background
The consensus review concluded that SNTO can become a reference platform only if it shifts from dashboard/prototype to accountable decision system.

## Current State
The current architecture supports analysis and demonstration better than enterprise operations.

## Evidence
The CTO review required auth, tenancy, persistence, audit, API discipline, background jobs, observability, and release governance before enterprise customers.

## Recommendations
Future architecture should include:
- identity and role model;
- organization and territory model;
- asset registry;
- observation and indicator store;
- recommendation and alert resources;
- intervention lifecycle;
- field verification records;
- audit log;
- background job system;
- versioned API;
- GIS integration layer.

## Next Steps
Convert these requirements into ADRs before major v2.0 implementation work.

## Related Documents
- [ADR-001](../decisions/ADR-001.md)
- [ADR-002](../decisions/ADR-002.md)
- [v2.0 Roadmap](../roadmap/v2.0.md)

