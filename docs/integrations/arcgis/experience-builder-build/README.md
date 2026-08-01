# Fase 4 — Preparación del build de Experience Builder (operado por el propietario)

> **Solo planificación y documentación.** Ninguna mutación en ArcGIS Online se
> realiza en esta fase: no se crea la app, no se guarda el Web Map, no se cambian
> compartición/campos/dominios/vistas/permisos, no se envían registros Survey123.

## 1. Estado gobernante (2026-08-01)

- **Experience Builder — existencia:** `DOES_NOT_EXIST — OWNER_UI_VERIFIED`
  (el propietario verificó ArcGIS Online Content y confirmó que no existe app de
  Experience Builder ni Web Experience / Experiencia web para esta demo SNTO).
- **Decisión:** `CREATE_NEW_EXPERIENCE_BUILDER_APP`.
- **Autorización de creación:** **NO otorgada aún.** La creación/mutación queda
  tras la puerta A0c (permisos) y una aprobación explícita de mutación.

## 2. Producto objetivo

**«SNTO · Espacio de decisión PNSG — DEMO académico»** — MVP privado académico.
**No** es un portal público, **no** es despliegue de producción, **no** sustituye
a Streamlit, **no** es un sistema de validación de campo completo, **no** es una
integración de API en vivo.

Páginas planificadas: **Decidir · Diagnosticar · Evidenciar · Gobernar · Asset
Detail**.

## 3. Componentes ArcGIS reutilizables verificados (evidencia autenticada)

| Componente | Estado | Decisión |
|---|---|---|
| `pilot_assets` (capa 0, punto, Web Mercator, campos analíticos preservados) | verificado | `REUSE_WITH_CONFIGURATION_FOR_DEMO` (+ `MIGRATE_OR_RECREATE_BEFORE_PRODUCTION`) |
| Survey123 servicio principal (capa 0, EPSG 4326, GlobalID, adjuntos, editor tracking) | verificado | `REUSE_WITH_CONFIGURATION` |
| Survey123 form view | verificado | `REUSE_AS_IS_FOR_SURVEY123_CAPTURE` |
| Survey123 results view (fuente de evidencia read-oriented preferida) | verificado | `REUSE_AS_IS_FOR_READ_ONLY_EVIDENCE` (permisos efectivos pendientes) |
| Web Map (2 capas operacionales, simbología evidencia/tendencia, popup+adjuntos) | verificado | `REUSE_WITH_CONFIGURATION` |
| Experience Builder | no existe | `CREATE_NEW_EXPERIENCE_BUILDER_APP` (no autorizado) |

## 4. Documentos de este paquete

| Documento | Contenido |
|---|---|
| [`permission-gate-a0c.md`](permission-gate-a0c.md) | Checklist A0c de verificación de permisos por item. |
| [`webmap-configuration-plan.md`](webmap-configuration-plan.md) | Plan exacto de filtros y popups (no ejecutar). |
| [`app-specification.md`](app-specification.md) | Especificación del nuevo item Experience Builder. |
| [`page-architecture.md`](page-architecture.md) | Arquitectura de widgets por página. |
| [`data-source-mapping.md`](data-source-mapping.md) | Mapeo página↔widget↔fuente↔rol. |
| [`interaction-matrix.md`](interaction-matrix.md) | Message actions y reglas de interacción. |
| [`sharing-and-security.md`](sharing-and-security.md) | Modelo de compartición y seguridad. |
| [`rollback-plan.md`](rollback-plan.md) | Plan de reversión. |
| [`credit-and-cost.md`](credit-and-cost.md) | Revisión de créditos y coste. |
| [`owner-ui-checklist.md`](owner-ui-checklist.md) | Checklist de ejecución en la UI (futuro). |
| [`qa-and-acceptance.md`](qa-and-acceptance.md) | QA y criterios de aceptación. |
| [`a0c-verification-results.md`](a0c-verification-results.md) | **A0c** — estados de item verificados (OWNER_UI_VERIFIED). |
| [`mutation-plan.md`](mutation-plan.md) | Plan maestro de mutación (3 lotes, puertas separadas). |
| [`hardening-batch-a.md`](hardening-batch-a.md) | Batch A — hardening de bajo riesgo. |
| [`webmap-batch-b.md`](webmap-batch-b.md) | Batch B — configuración del Web Map. |
| [`experience-builder-batch-c.md`](experience-builder-batch-c.md) | Batch C — creación de la app. |
| [`post-mutation-evidence-checklist.md`](post-mutation-evidence-checklist.md) | Evidencia a capturar tras cada lote. |
| [`multiuser-qa-plan.md`](multiuser-qa-plan.md) | QA multiusuario (pendiente). |

## 4b. Estado A0c (2026-08-01, Fase 4B)

**`A0c_PERMISSION_VERIFICATION: COMPLETED_FOR_OWNER_OPERATED_BUILD`** ·
global `READY_FOR_OWNER_OPERATED_EXPERIENCE_BUILDER_CREATION_WITH_APPROVED_HARDENING`.
**Ninguna mutación autorizada aún.** QA multiusuario y continuidad de cuenta
**pendientes** (grupo con 1 solo miembro: el owner). Puertas separadas:
`APPROVE ARCGIS HARDENING BATCH A` · `APPROVE WEB MAP CONFIGURATION BATCH B` ·
`APPROVE EXPERIENCE BUILDER CREATION BATCH C`.

## 5. Reglas de integridad (heredadas)

- La documentación versionada conserva los hallazgos de esquema y decisiones;
  los **Item IDs reales, URLs exactas de servicio y metadatos locales
  detallados** permanecen únicamente en el registro local ignorado
  `arcgis/demo/pnsg/item-registry.local.yaml`.
- `asset_id` es una **unión lógica**, no una relationship class; `pilot_assets`
  no tiene GlobalID; sin integridad referencial garantizada; `asset_id` nulo
  **no** se trata como enlazado.
- `missing` ≠ `0`; `synthetic` ≠ `real`; tendencia ≠ causalidad; geometría
  provisional ≠ límite autoritativo.
- La creación de la app y cualquier configuración del Web Map requieren **A0c +
  aprobación explícita de mutación**.
