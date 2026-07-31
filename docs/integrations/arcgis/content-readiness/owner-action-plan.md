# Plan de acción operado por el propietario — Fase 3 (preliminar)

> Ninguna acción se ejecuta en Fase 3. **Toda acción de las categorías A, B y
> C está condicionada a completar primero A0.** No se prescribe ninguna
> edición de capa, publicación de formulario o creación de item como acción
> decidida antes de esa verificación.

## A0 — Recolectar metadatos ArcGIS no-secretos (acción previa obligatoria)

Esta es la **primera y única acción no condicionada** de este plan. Ninguna
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
