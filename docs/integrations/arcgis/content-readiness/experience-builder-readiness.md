# Disposición de Experience Builder (preliminar → anónima → esquema autenticado → existencia)

## Existencia GOBERNANTE (2026-08-01, Fase 4)

> **Experience Builder — existencia: `DOES_NOT_EXIST — OWNER_UI_VERIFIED`.** El
> propietario verificó ArcGIS Online Content y confirmó que **no existe** app de
> Experience Builder ni Web Experience / Experiencia web para esta demo SNTO.
> **Decisión:** `CREATE_NEW_EXPERIENCE_BUILDER_APP`. **La creación NO está
> autorizada aún** (tras A0c + aprobación explícita de mutación).
>
> Esto **reemplaza** el `UNKNOWN` previo sobre la existencia. El plan de
> construcción operado por el propietario está en
> [`../experience-builder-build/README.md`](../experience-builder-build/README.md).

## A0c COMPLETADA (2026-08-01, Fase 4B)

> **`A0c_PERMISSION_VERIFICATION: COMPLETED_FOR_OWNER_OPERATED_BUILD`** ·
> global `READY_FOR_OWNER_OPERATED_EXPERIENCE_BUILDER_CREATION_WITH_APPROVED_HARDENING`.
> El owner verificó los permisos/compartición de los 7 items
> (`../experience-builder-build/a0c-verification-results.md`). **Ninguna
> mutación autorizada aún**; plan en 3 lotes (A/B/C, puertas separadas) en
> `../experience-builder-build/mutation-plan.md`. **Pendiente:** QA multiusuario
> (grupo con 1 miembro) y continuidad de cuenta.

## Veredicto GOBERNANTE (2026-08-01)

> **`READY_FOR_OWNER_OPERATED_EXPERIENCE_BUILDER_BUILD_WITH_CONFIGURATION`** —
> la construcción/mutación **aún no está autorizada**.

Con la evidencia de esquema autenticada:

- **Fuentes de datos listas (esquema) para el MVP académico:** `pilot_assets`
  (capa 0) y el servicio Survey123 con sus vistas están
  `OWNER_AUTHENTICATED_SCHEMA_VERIFIED`. La **results view** es la fuente de
  evidencia read-oriented preferida.
- **El Web Map requiere configuración** (filtros + refinamiento de popups) antes
  de servir de base a las páginas — ver `webmap-readiness.md`.
- **El item de Experience Builder sigue `UNKNOWN`** (no aportado); no se crea en
  esta tarea.

### Prerrequisitos de construcción de Experience Builder

1. Verificación de permisos a nivel de item (compartición/edición efectiva) —
   **pendiente**.
2. Configuración del Web Map (filtros + popups) — **pendiente, no ejecutar aún**.
3. Confirmar existencia del item de Experience Builder o decidir crearlo (fuera
   de esta tarea).
4. Autorización explícita de mutación/build del propietario.

| Página | Fuente | Esquema | Config previa |
|---|---|---|---|
| Decidir | `pilot_assets` | OWNER_AUTHENTICATED_SCHEMA_VERIFIED | popups/filtros |
| Diagnosticar | `pilot_assets` (+ PRUG diferido) | verificado | filtros Web Map |
| Evidenciar | Survey123 **results view** | verificado | popups + adjuntos |
| Gobernar | contenido en Git | N/A | — |
| Asset Detail | pilot_assets + observaciones (unión por `asset_id`) | verificado | sin relación formal (unión lógica) |

---

> **Histórico (estado previo).** Debajo, el análisis anónimo (2026-07-31).

## Suplemento de verificación anónima (2026-07-31)

- **Item de Experience Builder:** existencia **UNKNOWN**; estado
  **AUTHENTICATED_READ_REQUIRED**. El propietario **no** lo aportó y el endpoint
  de contenidos del grupo devuelve `403` anónimo. **No se afirma que exista ni
  que no exista.**
- **Fuentes de datos de las páginas:** los dos FeatureServer (activos y
  Survey123) **resuelven** (ANONYMOUS_REST_VERIFIED) y sus items están
  OWNER_UI_VERIFIED — esto **retira** el bloqueo previo de "el feature service
  de Survey123 podría no existir" en la página *Evidenciar*. Sin embargo, sus
  **esquemas** siguen `AUTHENTICATED_READ_REQUIRED`, así que la disposición de
  fuente de datos para EB **sigue sin poder determinarse**.
- **Clasificación global (sin cambio):** **`PRELIMINARY_REPOSITORY_READY`** +
  **`LIVE_ARCGIS_READINESS_UNKNOWN`**. La existencia de las fuentes está
  verificada; su idoneidad de esquema y la config del Web Map no.

| Página | Fuente: existencia | Esquema fuente | EB item |
|---|---|---|---|
| Decidir | `pilot_assets` OWNER_UI + endpoint resuelve | AUTHENTICATED_READ_REQUIRED | UNKNOWN / AUTHENTICATED_READ_REQUIRED |
| Diagnosticar | `pilot_assets` ídem | AUTHENTICATED_READ_REQUIRED | ídem |
| Evidenciar | **Survey123 service: endpoint resuelve** | AUTHENTICATED_READ_REQUIRED | ídem |
| Gobernar | Contenido en Git | N/A | ídem |
| Asset Detail | Ambos: existencia verificada | AUTHENTICATED_READ_REQUIRED | ídem |

---

> Análisis preliminar por página (histórico) conservado abajo.

> Basado en `page-blueprints.md` (Fase 2A). Para cada página se separan tres
> ejes: **disposición en Git/contrato de datos** (verificable hoy),
> **disposición del item ArcGIS real** (UNKNOWN salvo confirmación) y
> **dependencia de verificación en vivo** antes de construir.

## Página · Decidir

- **Disposición Git/contrato de datos:** READY IN GIT — el contrato de la
  capa de activos (`data-contract.md` §1) está completo y verificado en el
  archivo.
- **Disposición del item ArcGIS real:** UNKNOWN (capa `SNTO_DEMO_PNSG_Assets`
  — existencia QUALITATIVELY_CONFIRMED, esquema y compartición UNKNOWN).
- **Dependencia de verificación en vivo:** SÍ, antes de construir los KPIs
  sobre valores reales.
- **Bloqueo de proceso:** ninguno específico de esta página más allá del
  BLOCKER general de metadatos (`gap-matrix.md`).

## Página · Diagnosticar

- **Disposición Git/contrato de datos:** READY IN GIT (capa de activos;
  capa PRUG diferida como alcance de producto).
- **Disposición del item ArcGIS real:** UNKNOWN.
- **Dependencia de verificación en vivo:** SÍ.
- **Bloqueo de proceso:** ninguno específico más allá del BLOCKER general.

## Página · Evidenciar

- **Fuente canónica de formulario/esquema:** READY IN GIT — el XLSForm y las
  14 columnas canónicas están verificados en el repositorio
  (`survey123-integration.md` §1).
- **Servicio Survey123 real:** UNKNOWN — no confirmado ni descartado.
- **Disposición de fuente de datos para EB:** CANNOT BE DETERMINED sin
  verificar si el feature service existe y, de existir, su esquema.
- **Verificación requerida antes de construir:** confirmación de existencia
  + Item ID/URL de servicio + esquema real (ver `owner-action-plan.md` §A0).

## Página · Gobernar

- **Disposición Git/contrato de datos:** READY IN GIT — contenido estático
  (metodología, limitaciones, documentación) ya existe en el repositorio.
- **Disposición del item ArcGIS real:** UNKNOWN si hay items de descarga
  específicos ya publicados en ArcGIS.
- **Dependencia de verificación en vivo:** parcial — el contenido textual
  puede prepararse desde ya; los botones de descarga que enlacen a items
  ArcGIS reales requieren sus Item IDs.

## Asset Detail (transversal)

- **Disposición Git/contrato de datos:** READY IN GIT para la mitad "activo"
  (esquema documentado); la mitad "observaciones relacionadas" depende del
  estado UNKNOWN del feature service.
- **Disposición del item ArcGIS real:** UNKNOWN en ambas mitades.
- **Dependencia de verificación en vivo:** SÍ, completa.

## Clasificación global

**PRELIMINARY_REPOSITORY_READY** — el contrato de datos, el diseño de
páginas y las reglas de evidencia están completos y coherentes a nivel de
repositorio para las 4 páginas + Asset Detail.

**LIVE_ARCGIS_READINESS_UNKNOWN** — ninguna página puede considerarse lista
para construirse en ArcGIS Online real sin la verificación en vivo descrita
en `owner-action-plan.md` §A0 y sin cerrar los `VERIFICATION_REQUIRED` de
`gap-matrix.md`.

## Resumen por página

| Página | Git/contrato | Item ArcGIS real | Verificación en vivo requerida |
|---|---|---|---|
| Decidir | READY IN GIT | UNKNOWN | Sí |
| Diagnosticar | READY IN GIT | UNKNOWN | Sí |
| Evidenciar | READY IN GIT (formulario) | UNKNOWN (servicio) | Sí, crítica |
| Gobernar | READY IN GIT | UNKNOWN (items de descarga) | Parcial |
| Asset Detail | READY IN GIT (parcial) | UNKNOWN | Sí, completa |

**Conclusión:** el MVP está **conceptual y documentalmente listo** a nivel de
repositorio (`PRELIMINARY_REPOSITORY_READY`), pero su disposición real en
ArcGIS Online es **`LIVE_ARCGIS_READINESS_UNKNOWN`** en su totalidad hasta
completar la verificación en vivo.
