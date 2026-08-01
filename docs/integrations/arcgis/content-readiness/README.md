# Fase 3 — Readiness de contenido ArcGIS (preliminar → anónima → esquema autenticado)

> **Título de estado (actual, gobernante):** *"Verificación de esquema y Web Map
> autenticada por evidencia del propietario (2026-08-01)"*.
> Documentación únicamente. **Ninguna** mutación en ArcGIS Online se realizó.

## 0. Categorías de evidencia

- **OWNER_UI_VERIFIED** — el propietario identificó el item en su interfaz
  autenticada de ArcGIS Online o aportó su página de item exacta.
- **ANONYMOUS_REST_VERIFIED** — el endpoint REST exacto resolvió y devolvió una
  respuesta ArcGIS con sentido (p. ej. `499 Token Required`), no `400 Invalid URL`.
- **ANONYMOUS_ACCESS_BLOCKED** — el endpoint aportado no permite acceso anónimo
  a metadatos/datos.
- **AUTHENTICATED_READ_REQUIRED** — se requiere sesión autenticada de solo
  lectura o JSON exportado por el propietario para inspeccionar configuración o
  esquema.
- **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** *(categoría gobernante de esta fase)* —
  el propietario inspeccionó la REST autenticada o la interfaz autenticada de
  ArcGIS Online y aportó los metadatos exactos de capa/servicio o capturas. Se
  usa **solo** para los campos/configuración directamente respaldados por esa
  evidencia.
- **LIVE_SCHEMA_VERIFIED** — reservado para inspección autenticada realizada
  **por este flujo** (no por el propietario). Sigue sin calificar nada.

## 0.0 Suplemento de esquema autenticado (2026-08-01) — resumen gobernante

El propietario inspeccionó las páginas REST autenticadas (pilot_assets, servicio
principal Survey123, form view, results view) y el Web Map Viewer, y aportó los
metadatos exactos. Marco temporal aplicado en todo el paquete: **estado previo →
evidencia autenticada del propietario recibida → disposición gobernante actual**.

- **pilot_assets (capa 0 `pilot_assets_points`):** OWNER_AUTHENTICATED_SCHEMA_VERIFIED.
  Punto, WKID 102100 (Web Mercator), sin GlobalID, sin adjuntos, `asset_id`
  nullable, strings de 4000, sin dominios visibles. Conserva el set de campos de
  negocio canónico. → `REUSE_WITH_CONFIGURATION_FOR_DEMO`;
  `MIGRATE_OR_RECREATE_BEFORE_PRODUCTION` (no recrear ahora).
- **Servicio principal Survey123 (capa 0):** OWNER_AUTHENTICATED_SCHEMA_VERIFIED.
  Punto, EPSG 4326, `globalid`, adjuntos, editor tracking, dominios en
  `plot_id`/`erosion_class`/`evidence_class`; sin dominios en
  `stratum`/`is_control`/`qa_status`; sin tablas relacionadas ni relación formal
  con pilot_assets. → `REUSE_WITH_CONFIGURATION`.
- **Form view:** `REUSE_AS_IS_FOR_SURVEY123_CAPTURE`.
- **Results view:** `REUSE_AS_IS_FOR_READ_ONLY_EVIDENCE` (fuente de evidencia
  preferida para Experience Builder; ops de capa orientadas a consulta; el root
  reporta *Is Updatable View* → **no** se afirma solo-lectura absoluta para todo
  usuario; permisos efectivos PENDIENTES).
- **Web Map:** OWNER_AUTHENTICATED_SCHEMA_VERIFIED para capas operacionales,
  leyenda y popup de observaciones. → `REUSE_WITH_CONFIGURATION` (faltan filtros
  y refinamiento final de popups para el MVP).
- **Experience Builder:** existencia **UNKNOWN** (no aportado).
- **Veredicto global:** `READY_FOR_OWNER_OPERATED_EXPERIENCE_BUILDER_BUILD_WITH_CONFIGURATION`
  — la construcción/mutación **aún no está autorizada**.

**Sigue PENDIENTE (AUTHENTICATED_READ_REQUIRED / UNKNOWN):** compartición exacta
de items, pertenencia/permisos del grupo, filtros ocultos o definition
expressions, bookmarks y basemap, existencia de Experience Builder, continuidad
de cuenta, y permisos de edición efectivos por usuario.

Los Item IDs reales, las URLs exactas de servicio y los metadatos locales
detallados permanecen únicamente en el registro local ignorado
`arcgis/demo/pnsg/item-registry.local.yaml`. La documentación versionada
conserva los hallazgos de esquema respaldados por evidencia, sus limitaciones y
las decisiones gobernantes, sin incluir esos identificadores ni URLs reales.

---

> **Nota histórica.** Debajo se conserva el suplemento de verificación anónima
> (2026-07-31) como *estado previo*. Donde el esquema autenticado (arriba) lo
> actualiza, **prevalece el suplemento de 2026-08-01**.

## 0.1 Suplemento de verificación anónima (2026-07-31) — estado previo (histórico)

El propietario aportó los Item IDs / URLs no-secretos de los 8 items ArcGIS
(organización, grupo, Web Map, formulario Survey123, feature service, results
view, form view, `pilot_assets`). Se realizó una verificación **anónima,
estrictamente read-only y sin credenciales** vía REST/HTTP. Este trabajo **no**
es una inspección autenticada completa: solo comprobó **existencia** (por UI del
propietario y por resolución REST) y **bloqueo de acceso anónimo**.

- **Organización `ucmadrid.maps.arcgis.com`:** existencia **ANONYMOUS_REST_VERIFIED**
  (endpoint `sharing/rest/info`, `isTokenBasedSecurity:true`); configuración
  administrativa **AUTHENTICATED_READ_REQUIRED**.
- **`pilot_assets` y Survey123 FeatureServer:** resolución de endpoint
  **ANONYMOUS_REST_VERIFIED** (URL exacta → `499 Token Required`; inexistente →
  `400 Invalid URL`, calibrado); acceso anónimo **ANONYMOUS_ACCESS_BLOCKED**;
  esquemas/capas/tablas/config **AUTHENTICATED_READ_REQUIRED**.
- **Web Map, formulario Survey123, results view, form view, item de
  pilot_assets:** existencia/título/tipo **OWNER_UI_VERIFIED**; acceso anónimo
  a metadatos de item **ANONYMOUS_ACCESS_BLOCKED**; configuración interna
  **AUTHENTICATED_READ_REQUIRED**.
- **Grupo privado:** existencia **OWNER_UI_VERIFIED**; endpoint anónimo
  **ANONYMOUS_ACCESS_BLOCKED**; owner, miembros, alcance de compartición exacto
  **AUTHENTICATED_READ_REQUIRED**.
- **Experience Builder:** no aportado; contenidos del grupo → `403`. Existencia
  **UNKNOWN**; estado **AUTHENTICATED_READ_REQUIRED** (no se afirma existencia
  ni ausencia).

**Hallazgo de control de acceso (no de privacidad global):** los endpoints
probados **no exponen acceso anónimo**. Es un resultado positivo de control de
acceso **para esas rutas**, pero **no** sustituye la verificación autenticada
del alcance de compartición exacto, la pertenencia al grupo, el control de
acceso basado en propiedad ni los permisos de item. **No** se afirma que todos
los items sean privados a partir de `403`/`499`.

Los Item IDs y URLs REST reales se registran **solo** en el archivo ignorado
`arcgis/demo/pnsg/item-registry.local.yaml`; **no** aparecen en esta
documentación versionada.

**Conclusión del suplemento:** existencia y bloqueo de acceso anónimo quedan
verificados en las categorías anteriores; la comparación de esquemas y la
disposición real siguen requiriendo **una lectura autenticada**
(`owner-action-plan.md` §A0b). Las decisiones formales de reutilización **siguen
`UNKNOWN`** y ningún esquema se marca `LIVE_SCHEMA_VERIFIED`.

---

> Historial: la evaluación preliminar basada en repositorio se fusionó vía PR
> #136 (squash `3c6f9c8`). Lo que sigue conserva ese análisis; el suplemento de
> arriba actualiza lo que la verificación anónima pudo (y no pudo) confirmar.

## 1. Qué es y qué no es este documento

Este paquete **no** es un resultado de inspección en vivo de ArcGIS Online.
Es un análisis preliminar construido enteramente a partir de:

1. lo que `docs/arcgis/field-validation-demo-roadmap.md` documentó como
   verificado por el propietario el **2026-07-13**;
2. la confirmación cualitativa del propietario en esta sesión
   (2026-07-30: *"sigue todo existe"*);
3. inferencias de cronología derivables del propio repositorio (fechas de
   commit, contenido de archivos).

**No sustituye** una inspección real de metadatos ArcGIS. Es el paso previo
que identifica **qué falta verificar** antes de tomar cualquier decisión de
reutilización, reconstrucción o construcción de la app Experience Builder.

## 2. Qué completó y qué NO completó la Fase 3

| Sub-fase | Estado |
|---|---|
| 3A — Preflight | ✅ Completada |
| 3B — Registro local de items | ✅ Completada (archivo ignorado, sin valores reales) |
| 3C — Puerta de input humano | ✅ Alcanzada; **no superada con metadatos reales** — solo confirmación cualitativa |
| 3D — Inspección de solo lectura en ArcGIS | ❌ **No completada** — no hubo sesión ni metadatos reales |
| 3E — Comparación de esquemas reales | ❌ **No completada** — solo análisis de riesgo derivado, sin dato real que comparar |
| 3F — Matriz de brechas | ⚠️ Completada **con severidades limitadas a `VERIFICATION_REQUIRED`/`DERIVED_RISK`**, no brechas confirmadas |
| 3G — Decisión reuse/recreate | ⚠️ Completada, pero **toda decisión formal es `UNKNOWN`**; solo hipótesis preliminares no vinculantes |
| 3H — Disposición del Web Map | ⚠️ Completada como `UNKNOWN — NOT LIVE-VERIFIED` |
| 3I — Disposición de Experience Builder | ⚠️ Completada como `PRELIMINARY_REPOSITORY_READY` / `LIVE_ARCGIS_READINESS_UNKNOWN` |
| 3J — Plan de acción del propietario | ✅ Completada, con **A0 (recolección de metadatos)** como primera acción obligatoria y todo lo demás condicionado a ella |

**Conclusión de alcance:** el paquete de documentación (README + 8 documentos)
es un **entregable válido de Fase 3** en tanto que evaluación preliminar, pero
**ninguna** conclusión sobre existencia, configuración o disposición real de
un item ArcGIS debe tratarse como definitiva. Se requiere una **pasada de
verificación en vivo suplementaria** antes de cualquier mutación en ArcGIS
Online o construcción de Experience Builder.

## 3. Terminología obligatoria usada en todo el paquete

| Término | Significado |
|---|---|
| **HISTORICALLY_VERIFIED** | Respaldado por el roadmap del 2026-07-13 o por el paquete canónico. |
| **QUALITATIVELY_CONFIRMED** | El propietario afirmó que el trabajo/los items siguen existiendo, sin identificar cada item ni aportar metadatos. |
| **LIVE_VERIFIED** | Requiere Item ID, metadatos REST o inspección autenticada de solo lectura. **Ninguno está disponible hoy.** |
| **DERIVED_RISK** | Riesgo plausible inferido de la cronología del repositorio, **no** prueba de deriva real en el estado en vivo. |
| **UNKNOWN** | No puede decidirse sin metadatos ArcGIS. |

## 4. Por qué "sigue todo existe" no resuelve la incertidumbre

La confirmación del propietario es una afirmación **cualitativa y agregada**
("todo existe"), no una identificación item por item con metadatos. No indica:

- qué Item ID tiene cada elemento;
- si el Survey123 feature service se llegó a publicar;
- si existe ya un item de Experience Builder;
- la configuración real (esquema, compartición, capacidades) de ningún item.

Por tanto, este paquete **no afirma** que el feature service de Survey123 o la
app Experience Builder **no** existan — solo que su existencia y estado son
**UNKNOWN** sin metadatos o inspección adicionales.

## 5. Documentos de este paquete

| Documento | Contenido |
|---|---|
| [`item-inventory.md`](item-inventory.md) | Inventario por item, separando estado histórico de estado actual (UNKNOWN salvo confirmación explícita). |
| [`schema-comparison.md`](schema-comparison.md) | Comparación contrato Git vs estado ArcGIS — todo el lado ArcGIS es UNKNOWN; riesgos marcados DERIVED_RISK. |
| [`gap-matrix.md`](gap-matrix.md) | Matriz de brechas con severidades limitadas a `VERIFICATION_REQUIRED`/`DERIVED_RISK`/`INFORMATIONAL`. |
| [`reuse-decision.md`](reuse-decision.md) | Decisión formal `UNKNOWN` en todos los items reales; hipótesis preliminares no vinculantes por separado. |
| [`webmap-readiness.md`](webmap-readiness.md) | Clasificación `UNKNOWN — NOT LIVE-VERIFIED`. |
| [`experience-builder-readiness.md`](experience-builder-readiness.md) | `PRELIMINARY_REPOSITORY_READY` / `LIVE_ARCGIS_READINESS_UNKNOWN` por página. |
| [`owner-action-plan.md`](owner-action-plan.md) | A0 (recolección de metadatos) como acción obligatoria previa; todo lo demás condicionado. |
| [`qa-checklist.md`](qa-checklist.md) | Checklist de validación de esta fase preliminar. |

## 6. Próximo paso obligatorio (fuera de esta fase)

Una pasada de verificación en vivo — el propietario aporta las URLs/Item IDs
de `owner-action-plan.md` §A0, o habilita una inspección de solo lectura — es
**condición previa** para: cerrar cualquier `UNKNOWN` de este paquete, asignar
decisiones formales de reutilización, clasificar el Web Map, o iniciar la
construcción de Experience Builder.
