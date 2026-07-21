# Roadmap

## Purpose
Translate strategic conclusions into release-level direction.

## Background
The reviews identified a path from current prototype to reference platform.

## Current State
SNTO should prioritize focus and validation before enterprise expansion.

**The whole v2.0 vision is code-complete on `main` (`2.0.0`).** Fase 4 (`app.py` modularization, #27), the audience-views rescue (#28), **Fase 5** (v2.0 persistent-backend foundations, ADR-011 — persistence layer, `/api/v2`, lifecycle state machines, audit trail, minimal write-auth; production Postgres cutover executed 2026-07-18), and **Fase 6** (role-based UI evolution — 4 IA layers, persona homes, asset-as-a-page, alert triage, and all six 6.7x modules) are merged. The `v2.0.0` tag + GitHub Release are pending the owner; `v1.5.0` (2026-07-18) is the last pushed stable tag. **Next: v3.0** — the post-v2.0 frontier is scoped in [`plan_v3_roadmap.md`](plan_v3_roadmap.md) (v2.1 activation/governance → v2.2 forecasting & real pressure → v2.5 validation gate → v3.0 enterprise/network).

## Evidence
The consensus review defined a three-year roadmap: narrowing, operationalization, institutional scaling.

## Contents
- [v1.1](v1.1.md)
- [v1.2](v1.2.md)
- [Plan de fases post-v1.2.0](plan_fases_post_v1.2.md) — hoja de ruta operativa: cierre v1.2.0, auditoría de ramas y fases hacia v1.3/v1.4/v2.0
- [Fase 5 — Fundamentos de v2.0](plan_fase5_v2_foundations.md) — backend persistente (ADR-011): esquema de recursos y plan de PRs **✅ completado (5.0–5.9, #61–#70)**; cutover a Postgres del propietario **✅ ejecutado (2026-07-18)**
- [Fase 6 — Evolución de UI por roles v2.0](plan_fase6_v2_ui_evolution.md) — plan de implementación de `docs/ux/ui-evolution-v2-spec.md` sobre el backend de Fase 5 **✅ completado (6.0–6.7f, PRs #75–#89)**
- [v2.0](v2.0.md)
- [v3.0](v3.0.md) — visión de alto nivel (el *qué*)
- [**Plan: Roadmap v2.1 → v3.0 (and beyond)**](plan_v3_roadmap.md) — plan de ejecución del frontier post-v2.0 (el *cómo*): fases, acciones, ficheros y criterios de salida, con la puerta dura de validación de campo
- [Long-Term Vision](long-term-vision.md)

## Recommendations
Use releases as maturity gates, not feature buckets.

## Next Steps
Align implementation planning with [../reviews/2026/08-priority-roadmap.md](../reviews/2026/08-priority-roadmap.md).

## Related Documents
- [Product Roadmap](../product/product-roadmap.md)

