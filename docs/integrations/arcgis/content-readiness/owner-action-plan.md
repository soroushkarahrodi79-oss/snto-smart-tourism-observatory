# Plan de acción operado por el propietario — Fase 3 (preliminar → anónima → esquema autenticado)

> Ninguna acción de mutación se ejecuta. Estado de las puertas previas:
> **A0 ✅ (metadatos), A0b ✅ (esquema autenticado)**. Nueva puerta pendiente:
> **A0c (permisos/compartición)**.

## Estado de progreso de puertas (2026-08-01)

- **A0 — Recolectar metadatos ArcGIS no-secretos: ✅ COMPLETADA (2026-07-31).**
- **A0b — Aportar lectura autenticada del esquema: ✅ COMPLETADA (2026-08-01).**
  El propietario inspeccionó la REST autenticada (pilot_assets, servicio
  Survey123, form/results views) y el Map Viewer, y aportó los esquemas exactos
  (`OWNER_AUTHENTICATED_SCHEMA_VERIFIED`). Registrado en el registro local.
- **Experience Builder — existencia (Fase 4, 2026-08-01): `DOES_NOT_EXIST —
  OWNER_UI_VERIFIED`.** El propietario verificó ArcGIS Online Content: no existe
  app EB/Web Experience para esta demo. **Decisión:
  `CREATE_NEW_EXPERIENCE_BUILDER_APP`** (creación **no autorizada** aún). Plan
  operado por el propietario en `../experience-builder-build/`.
- **A0c — Verificar permisos/compartición a nivel de item: ✅ COMPLETADA
  (2026-08-01).** El owner verificó los 7 items (`OWNER_UI_VERIFIED`): todos
  compartidos solo con owner + grupo privado (no org-wide, no público). Estado:
  `COMPLETED_FOR_OWNER_OPERATED_BUILD` · global
  `READY_FOR_OWNER_OPERATED_EXPERIENCE_BUILDER_CREATION_WITH_APPROVED_HARDENING`.
  Brechas de hardening (protección de borrado off en varios items; export activo
  en results view; aprobación pública editable en form view) → plan en 3 lotes
  (A/B/C, puertas separadas) en `../experience-builder-build/mutation-plan.md`.
  **Pendiente:** QA multiusuario (grupo con 1 miembro) y continuidad de cuenta.
  Resultados: `../experience-builder-build/a0c-verification-results.md`.
- **Batch A — Hardening de bajo riesgo: ✅ `OWNER_EXECUTED_AND_VERIFIED`
  (2026-08-01).** Ejecutado por el propietario en su sesión autenticada
  (`OWNER_MANUAL_UI`); `CLAUDE_DIRECT_ARCGIS_MUTATION: NONE`. A1–A6 protección de
  borrado ON; A7 export de results view OFF; A8 aprobación pública del form view
  OFF; A9 Save As OFF; A10 búsqueda por dirección OFF. Invariantes confirmados
  (edición off, form privado/add-only, búsqueda por capa off, compartición y
  pilot_assets sin cambios). Registro:
  `../experience-builder-build/batch-a-execution-record.md`.
- **Batch B — Configuración del Web Map: ✅ `OWNER_EXECUTED_AND_VERIFIED`
  (2026-08-01).** Ejecutado por el propietario (`OWNER_MANUAL_UI`);
  `CLAUDE_DIRECT_ARCGIS_MUTATION: NONE`. Backup privado del Web Map creado
  (referencia solo en el registro local ignorado); popups B1 (observaciones) y
  B2 (pilot_assets) configurados y guardados con campos técnicos ocultos y nulos
  no como 0, sin Arcade; B3 sin filtros restrictivos; B4 orden/visibilidad/
  simbología preservados. Invariantes: original privado, compartición sin
  cambios, capas alojadas sin duplicar, esquema/datos sin cambios. Registro:
  `../experience-builder-build/batch-b-execution-record.md`.
- **Batch C: pendiente** de `APPROVE EXPERIENCE BUILDER CREATION BATCH C`
  (no autorizado).

Ninguna construcción de Experience
Builder (Batch C) se ejecuta sin su aprobación explícita separada.

---

> **Histórico (estado previo).** Debajo, el plan preliminar/anónimo.

## (Histórico) Plan preliminar

> Ninguna acción se ejecuta en Fase 3. **Toda acción de las categorías A, B y
> C está condicionada a completar primero A0.** No se prescribe ninguna
> edición de capa, publicación de formulario o creación de item como acción
> decidida antes de esa verificación.

## A0 — Recolectar metadatos ArcGIS no-secretos — ✅ COMPLETADA (2026-07-31)

El propietario aportó los Item IDs/URLs de los 8 items (registrados en el
archivo ignorado `arcgis/demo/pnsg/item-registry.local.yaml`). La verificación
**anónima de solo lectura** confirmó **existencia** (OWNER_UI_VERIFIED /
ANONYMOUS_REST_VERIFIED) y **bloqueo de acceso anónimo** de la org y los dos
FeatureServer. **No** verificó el alcance de compartición exacto ni la
pertenencia al grupo. **Item de Experience Builder no aportado** (pendiente, A0b).

## A0b — Aportar lectura autenticada del esquema (NUEVA acción previa obligatoria)

La verificación anónima de solo lectura **no puede leer el esquema** porque los
endpoints bloquean el acceso anónimo (`499 Token Required`) y este flujo no usa
credenciales.
Para desbloquear la comparación de esquemas y las decisiones formales, el
propietario debe, **desde su propia sesión ya autenticada** (sin compartir
tokens ni cookies con este flujo), realizar **una de estas dos opciones**:

- **Opción 1 (recomendada, no-mutante):** abrir en su navegador y guardar como
  archivo local (fuera de Git, o en el registro local) el JSON REST read-only
  de cada recurso:
  - `…/pilot_assets/FeatureServer?f=json` y `…/FeatureServer/0?f=json` (y cada
    índice de capa/tabla que aparezca);
  - `…/<survey123-feature-service>/FeatureServer?f=json` y cada `…/FeatureServer/<n>?f=json`;
  - el `item/data` del Web Map (`?f=json`).
  Luego facilitar esos JSON para su lectura. **No cambia compartición ni datos.**
- **Opción 2:** habilitar una sesión de solo lectura supervisada para
  inspección de metadatos (sin edición). El propietario decide.

**No se recomienda cambiar la compartición a pública** para facilitar la
lectura — eso reduciría el control de acceso actual (los endpoints probados hoy
bloquean el acceso anónimo) y contradiría el objetivo de mantener la demo
restringida.

Esta es ahora la **acción previa obligatoria**. Ninguna fila de A/B/C se ejecuta
antes de completar A0b.

---

> Texto histórico de A0 (preliminar) conservado abajo por trazabilidad.

## A0 (histórico) — Recolectar metadatos ArcGIS no-secretos

Esta era la primera acción no condicionada del plan preliminar. Ninguna
otra fila de este documento puede ejecutarse antes de completarla.

**Requerido del propietario (sin contraseñas, tokens ni cookies):**

1. URL de la organización;
2. URL del item/grupo privado;
3. URL del item de la Hosted Feature Layer de activos;
4. URL del item del Web Map;
5. URL del item del formulario Survey123;
6. URL del item del Feature Service de Survey123, **si existe**;
7. URL del item de Experience Builder, **si existe**.

**Cómo se usa:** cada URL/Item ID recibido se registra en
`arcgis/demo/pnsg/item-registry.local.yaml` (ignorado por Git). A partir de
ahí, una inspección de solo lectura (metadatos REST, propiedades del item)
puede cerrar los `UNKNOWN` de `item-inventory.md`, `schema-comparison.md`,
`gap-matrix.md`, `reuse-decision.md`, `webmap-readiness.md` y
`experience-builder-readiness.md`.

**Sin completar A0, ninguna fila de las categorías A/B/C siguientes puede
ejecutarse** — todas están marcadas *"Condicional a A0"*.

---

## A. Cambios de configuración sin riesgo (todos condicionales a A0)

| Acción | Item afectado | Razón exacta | Efecto esperado | Rollback | Aprobación | Riesgo de privacidad | Riesgo de integridad de evidencia | Condición |
|---|---|---|---|---|---|---|---|---|
| Ajustar texto de popup del Web Map | Web Map | Alinear con `design-system.md` §6, **si la inspección confirma que no lo está** | Popups honestos y consistentes | Revertir a popup anterior | Sí (revisión visual) | Ninguno | Reduce riesgo | **Condicional a A0** + confirmación de que el popup actual no cumple la regla |
| Ajustar simbología a patrón+etiqueta | Web Map | Accesibilidad, **si la inspección confirma que falta** | Estados legibles sin color | Revertir simbología | Sí | Ninguno | Ninguno | **Condicional a A0** |
| Añadir bookmarks / extent | Web Map | Usabilidad | Navegación más rápida | Eliminar bookmark | No | Ninguno | Ninguno | **Condicional a A0** |
| Etiquetas de capa | Web Map | Claridad | — | Revertir etiqueta | No | Ninguno | Ninguno | **Condicional a A0** |

## B. Cambios de servicio controlados (todos condicionales a A0)

| Acción | Item afectado | Razón exacta | Efecto esperado | Rollback | Aprobación | Riesgo de privacidad | Riesgo de integridad de evidencia | Condición |
|---|---|---|---|---|---|---|---|---|
| Inspeccionar esquema REST real de la capa de activos | `SNTO_DEMO_PNSG_Assets` | Cerrar el `DERIVED_RISK` de `schema-comparison.md` | Confirmación de campos presentes/ausentes | N/A (solo lectura) | Sí (revisar hallazgo) | Ninguno | Alto valor: evita construir sobre datos desactualizados | **Condicional a A0** (requiere el Item ID/URL de la capa) |
| Actualizar (overwrite) los atributos de la capa con el snapshot normalizado de Fase 2B | `SNTO_DEMO_PNSG_Assets` | **Solo si** la inspección confirma que faltan `source_version`, `sync_mode`, etc. | Esquema real alineado con el contrato Git actual | Mantener copia del esquema anterior antes de overwrite | **Sí, obligatoria** | Ninguno | Reduce riesgo | **Condicional a A0 + hallazgo confirmado**, no a la hipótesis |
| Confirmar/publicar el feature service de Survey123 | Observaciones de campo | **Solo si A0 confirma que no existe todavía**; si ya existe, la acción es inspeccionarlo, no publicarlo de nuevo | Servicio real con las 14 columnas canónicas + gobierno | Despublicar/archivar el servicio si falla la validación | **Sí, obligatoria** | **Alto** — GPS/fotos en juego una vez haya envíos reales | Alto | **Condicional a A0**; la acción exacta (publicar vs. inspeccionar) depende de lo que A0 revele |
| Habilitar/confirmar `GlobalID` y adjuntos | Feature service Survey123 | Requisito del contrato, **si aplica** | Relación foto↔observación funcional | Deshabilitar adjuntos | Sí | Alto (fotos) | Ninguno directo | **Condicional a A0** |
| Confirmar/activar editor tracking | Capa de activos y feature service | Trazabilidad de ediciones | Auditoría de cambios | Desactivar | Sí | Bajo | Ninguno | **Condicional a A0** |
| Crear Hosted Feature Layer View de solo lectura de activos | Capa de activos | Aislar la capa editable base de lo compartido a EB | Vista segura para consumo del grupo | Eliminar la vista | Sí | Ninguno | Ninguno | **Condicional a A0** |

## C. Acciones destructivas / de recreación (todas condicionales a A0 + hallazgo confirmado, nunca a hipótesis)

| Acción | Item afectado | Razón exacta | Efecto esperado | Rollback | Aprobación | Riesgo de privacidad | Riesgo de integridad de evidencia | Condición |
|---|---|---|---|---|---|---|---|---|
| Reemplazar la capa de activos por una incompatible | `SNTO_DEMO_PNSG_Assets` | **Solo si** la inspección REST revela un tipo de geometría/CRS incorrecto (no se espera ni se ha detectado) | Nueva capa con esquema correcto | Restaurar desde `arcgis/demo/pnsg/pilot_assets.geojson` | **Sí, obligatoria + revisión de diff** | Ninguno | Alto si se ejecuta sin revisión | **Condicional a A0 + confirmación positiva de incompatibilidad** — no justificada hoy |
| Recrear el servicio Survey123 con esquema corregido | Feature service | **Solo si** una primera publicación resulta con tipos de campo erróneos | Servicio republicado correctamente | Usar el XLSForm original como fuente de verdad | **Sí, obligatoria** | Alto (si ya hay envíos) | Alto | **Condicional a A0 + confirmación positiva de error** — no justificada hoy |
| Cambiar el tipo de un campo ya publicado | Cualquier capa/servicio | Solo si el tipo real bloquea el contrato | Tipo correcto | Mantener copia de export previa | **Sí, obligatoria** | Depende del campo | Medio | **Condicional a A0 + confirmación positiva** — no justificada hoy |

## Puerta de aprobación única antes de ejecutar cualquier fila

1. Completar A0 (recolección de metadatos) o una inspección real equivalente.
2. Presentar el hallazgo concreto y confirmado al propietario (no una
   hipótesis).
3. Recibir aprobación explícita por acción, no por lote.

**Ninguna fila de A, B o C se ejecuta sin haber completado primero A0.**
