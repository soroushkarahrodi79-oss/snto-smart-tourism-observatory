# Roadmap

## Purpose
Translate strategic conclusions into release-level direction.

## Background
The reviews identified a path from current prototype to reference platform.

## Current State
SNTO should prioritize focus and validation before enterprise expansion.

**`v1.5.0` is released** (tag + GitHub Release, 2026-07-18); `main` is now `v1.6.0.dev0`. Phase 4 (`app.py` modularization, #27), the audience-views rescue (#28), and **Fase 5 (v2.0 persistent-backend foundations, ADR-011)** are all complete — persistence layer, `/api/v2`, lifecycle state machines, audit trail, minimal write-auth, and the first UI consumer, all merged and tagged into v1.5.0. The production Postgres cutover (§4bis) was executed by the owner on 2026-07-18. **Fase 6 (v2.0 role-based UI evolution)** is next — plan drafted, awaiting owner sign-off on the open navigation/persona decisions (`plan_fase6_v2_ui_evolution.md` §2) before implementation PRs begin.

## Evidence
The consensus review defined a three-year roadmap: narrowing, operationalization, institutional scaling.

## Contents
- [v1.1](v1.1.md)
- [v1.2](v1.2.md)
- [Plan de fases post-v1.2.0](plan_fases_post_v1.2.md) — hoja de ruta operativa: cierre v1.2.0, auditoría de ramas y fases hacia v1.3/v1.4/v2.0
- [Fase 5 — Fundamentos de v2.0](plan_fase5_v2_foundations.md) — backend persistente (ADR-011): esquema de recursos y plan de PRs **✅ completado (5.0–5.9, #61–#70)**; cutover a Postgres del propietario **✅ ejecutado (2026-07-18)**
- [Fase 6 — Evolución de UI por roles v2.0](plan_fase6_v2_ui_evolution.md) — plan de implementación de `docs/ux/ui-evolution-v2-spec.md` sobre el backend de Fase 5; decisiones de navegación/persona abiertas para el propietario antes de implementar
- [v2.0](v2.0.md)
- [v3.0](v3.0.md)
- [Long-Term Vision](long-term-vision.md)

## Recommendations
Use releases as maturity gates, not feature buckets.

## Next Steps
Align implementation planning with [../reviews/2026/08-priority-roadmap.md](../reviews/2026/08-priority-roadmap.md).

## Related Documents
- [Product Roadmap](../product/product-roadmap.md)

