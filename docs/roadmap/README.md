# Roadmap

## Purpose
Translate strategic conclusions into release-level direction.

## Background
The reviews identified a path from current prototype to reference platform.

## Current State
SNTO should prioritize focus and validation before enterprise expansion.

Releases `v1.3.0` and `v1.4.0` are complete. `main` is now `v1.5.0.dev0`. Phase 4 (`app.py` modularization, #27) and the audience-views rescue (#28) are both complete. **Fase 5 (v2.0 persistent-backend foundations, ADR-011) is complete in code** — all steps 5.0–5.9 merged (#61–#70): persistence layer, `/api/v2`, lifecycle state machines, audit trail, minimal write-auth, and the first UI consumer. The only Fase 5 item left is the explicit owner-executed Postgres cutover (§4bis); no cloud resource is provisioned by any PR.

## Evidence
The consensus review defined a three-year roadmap: narrowing, operationalization, institutional scaling.

## Contents
- [v1.1](v1.1.md)
- [v1.2](v1.2.md)
- [Plan de fases post-v1.2.0](plan_fases_post_v1.2.md) — hoja de ruta operativa: cierre v1.2.0, auditoría de ramas y fases hacia v1.3/v1.4/v2.0
- [Fase 5 — Fundamentos de v2.0](plan_fase5_v2_foundations.md) — backend persistente (ADR-011): esquema de recursos y plan de PRs **✅ completado (5.0–5.9, #61–#70)**; solo queda el cutover manual a Postgres del propietario (§4bis)
- [v2.0](v2.0.md)
- [v3.0](v3.0.md)
- [Long-Term Vision](long-term-vision.md)

## Recommendations
Use releases as maturity gates, not feature buckets.

## Next Steps
Align implementation planning with [../reviews/2026/08-priority-roadmap.md](../reviews/2026/08-priority-roadmap.md).

## Related Documents
- [Product Roadmap](../product/product-roadmap.md)

