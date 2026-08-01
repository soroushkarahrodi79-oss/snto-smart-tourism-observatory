# Matriz de brechas — Fase 3 (preliminar → anónima → esquema autenticado)

## Actualización del suplemento de esquema autenticado (2026-08-01) — GOBERNANTE

La evidencia autenticada del propietario **cierra el BLOCKER de esquema** de la
fase anónima: los esquemas de `pilot_assets`, servicio principal Survey123, form
view, results view y la configuración del Web Map (capas/leyenda/popup) están
`OWNER_AUTHENTICATED_SCHEMA_VERIFIED`. Persisten brechas de **configuración** y
de **permisos**, no de esquema.

| Item/dominio | Estado previo | Ahora (2026-08-01) | Severidad | Acción |
|---|---|---|---|---|
| Esquema `pilot_assets` | BLOCKER (esquema) | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** — apto demo | MEDIUM | Config demo; migrar/recrear antes de producción |
| Esquema Survey123 (servicio + vistas) | BLOCKER (esquema) | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** | LOW-MEDIUM | Config (dominios faltantes) |
| Config Web Map (capas/leyenda/popup) | HIGH/UNKNOWN | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** (parcial) | MEDIUM | Filtros + refinamiento de popups (no ejecutar) |
| Dominios `stratum`/`is_control`/`qa_status` | UNKNOWN | **AUSENTES (confirmado)** | LOW | Añadir dominios en fase de config |
| GlobalID / relación pilot_assets↔obs | UNKNOWN | pilot_assets **sin GlobalID**; **sin relación formal** | MEDIUM | Unión lógica por `asset_id`; formalizar en producción |
| CRS pilot_assets | DERIVED_RISK | **Web Mercator (confirmado)**, no WGS84 canónico | MEDIUM | Migrar/recrear antes de producción |
| Compartición exacta / permisos de grupo / edición efectiva | UNKNOWN | **AUTHENTICATED_READ_REQUIRED** (aún) | HIGH | Verificación de permisos a nivel de item |
| Filtros ocultos / definition expressions | UNKNOWN | no observados en Map Viewer; JSON no aportado | MEDIUM | Revisar item/data JSON |
| Bookmarks / basemap | UNKNOWN | no aportados | LOW | Aportar si relevante |
| Existencia de Experience Builder | UNKNOWN | **UNKNOWN** (sin cambio) | HIGH | Aportar Item ID o confirmar ausencia |
| Continuidad de cuenta | UNKNOWN | **UNKNOWN** (sin cambio) | HIGH | §A0 (owner) |

**Enunciado gobernante:** *"Esquema verificado por evidencia autenticada del
propietario; las brechas restantes son de configuración (filtros, dominios,
popups) y de permisos/compartición, no de esquema. Construcción de Experience
Builder aún no autorizada."*

---

> **Histórico (estado previo).** Debajo, la actualización anónima (2026-07-31).

## Actualización del suplemento de verificación anónima (2026-07-31)

La verificación anónima **cerró parcialmente** la brecha BLOCKER anterior
("no hay metadatos en vivo"): ahora los Item IDs/URLs están aportados
(OWNER_UI_VERIFIED) y la **existencia** de la organización y de los dos
FeatureServer está `ANONYMOUS_REST_VERIFIED`. Sin embargo, **surge un nuevo
bloqueo de esquema**: los servicios bloquean el acceso anónimo y la lectura de
su esquema requiere autenticación.

| Item/dominio | Antes | Ahora (2026-07-31) | Severidad | Acción |
|---|---|---|---|---|
| Disponibilidad de Item IDs/URLs | BLOCKER (ausencia total) | **Resuelto** — aportados y registrados (local) | INFORMATIONAL | — |
| Existencia de org + 2 FeatureServer | UNKNOWN | **ANONYMOUS_REST_VERIFIED** | INFORMATIONAL | — |
| Existencia de items (Web Map, Survey123, pilot_assets) | UNKNOWN | **OWNER_UI_VERIFIED** | INFORMATIONAL | — |
| Acceso anónimo a endpoints probados | UNKNOWN | **ANONYMOUS_ACCESS_BLOCKED** (positivo, solo esas rutas) | INFORMATIONAL | — |
| Alcance de compartición exacto / pertenencia al grupo / permisos | UNKNOWN | AUTHENTICATED_READ_REQUIRED (no inferible de `403`/`499`) | HIGH | §A0b |
| Esquema real de capas/tablas | HIGH/DERIVED_RISK | **AUTHENTICATED_READ_REQUIRED** (nuevo bloqueo) | **BLOCKER** (esquema) | §A0b: export REST autenticado read-only |
| Config Web Map (capas/popups) | HIGH/VERIFICATION_REQUIRED | AUTHENTICATED_READ_REQUIRED | HIGH | §A0b |
| Existencia de Experience Builder | HIGH/VERIFICATION_REQUIRED | UNKNOWN / AUTHENTICATED_READ_REQUIRED (no aportado; grupo→403) | HIGH | §A0b o aportar Item ID |
| Continuidad de cuenta educativa | HIGH/VERIFICATION_REQUIRED | UNKNOWN (sin cambio) | HIGH | §A0 (owner) |

**Enunciado del BLOCKER actual:** *"Los endpoints resuelven pero bloquean el
acceso anónimo; la comparación de esquemas y la verificación del alcance de
compartición exacto requieren una lectura autenticada (sin credenciales en este
flujo). Las decisiones formales de reutilización siguen UNKNOWN y ningún esquema
se marca LIVE_SCHEMA_VERIFIED."*

---

> Matriz preliminar previa (histórica) conservada abajo. Donde el suplemento
> cambia el estado, prevalece el suplemento.

> Severidades limitadas a lo que el estado de información actual justifica:
> `VERIFICATION_REQUIRED`, `DERIVED_RISK`, `INFORMATIONAL`, y un único
> `BLOCKER` de nivel de proceso (ausencia de metadatos en vivo). **Ningún**
> item recibe `BLOCKER` por el mero hecho de que su existencia sea `UNKNOWN`.

## Brecha de proceso (la única BLOCKER real de esta fase)

| Item/dominio | Contrato Git | Estado ArcGIS real | Coincidencia | Severidad | Decisión | Acción requerida | ¿Mutación? | ¿Aprobación? |
|---|---|---|---|---|---|---|---|---|
| Disponibilidad de metadatos en vivo | N/A | No hay Item IDs, URLs de servicio ni inspección disponibles | No evaluable | **BLOCKER** | N/A | Ejecutar `owner-action-plan.md` §A0 (recolección de metadatos) | No | Sí |

**Enunciado exacto de este BLOCKER:** *"Live ArcGIS metadata unavailable;
reuse and build decisions cannot be finalized."* Este es el único bloqueo de
esta fase — no un bloqueo por item individual.

## Matriz por dominio

| Item/dominio | Contrato Git | Estado ArcGIS real | Coincidencia | Severidad | Decisión | Acción requerida | ¿Mutación? | ¿Aprobación? |
|---|---|---|---|---|---|---|---|---|
| Continuidad de organización | N/A | QUALITATIVELY_CONFIRMED | No evaluable | INFORMATIONAL | UNKNOWN | Confirmar tipo de cuenta/rol | No | No |
| Grupo privado | Nombre esperado conocido | QUALITATIVELY_CONFIRMED; Item ID UNKNOWN | No evaluable | HIGH / VERIFICATION_REQUIRED | UNKNOWN | Obtener Item ID/URL del grupo (§A0) | No | Sí |
| Capa de activos — existencia | Publicada, 2 activos (histórico) | QUALITATIVELY_CONFIRMED | No evaluable | HIGH / VERIFICATION_REQUIRED | UNKNOWN | Obtener Item ID/URL de servicio (§A0) | No | Sí |
| Capa de activos — esquema de metadata Fase 2B | Campos añadidos 2026-07-29 | UNKNOWN | No evaluable | **HIGH / DERIVED_RISK** | UNKNOWN | Inspección REST del esquema real tras §A0 | Posible, condicionada | Sí |
| Capa de activos — edición/compartición | Debía quedar solo lectura, solo grupo (histórico 2026-07-13) | UNKNOWN (estado actual no reverificado) | No evaluable | HIGH / VERIFICATION_REQUIRED | UNKNOWN | Reconfirmar en vivo | No | Sí |
| Web Map — existencia y configuración | Guardado, referencia la capa de activos (histórico) | QUALITATIVELY_CONFIRMED; configuración UNKNOWN | No evaluable | HIGH / VERIFICATION_REQUIRED | UNKNOWN | Ver `webmap-readiness.md` | Posible, condicionada | Sí |
| Survey123 form (XLSForm) | 14 columnas canónicas + gobierno (archivo local VERIFIED) | UNKNOWN si se importó/publicó en Connect | No evaluable | MEDIUM / VERIFICATION_REQUIRED | UNKNOWN | Confirmar estado de publicación (§A0) | Posible | Sí |
| Survey123 feature service | Debe existir para Evidenciar/Asset Detail | **UNKNOWN** (no confirmado ni descartado) | No evaluable | HIGH / VERIFICATION_REQUIRED | UNKNOWN | Obtener Item ID/URL si existe; publicar si no existe (§A0 primero) | Posible | Sí |
| `asset_id` string ↔ FK numérica | Mapeo documentado en `data-contract.md` §6 | N/A — hecho de código, no de ArcGIS | Coincide (documentado) | LOW | N/A (no requiere ArcGIS) | Implementar el script de importación en Fase 6 del roadmap | No (en Fase 3) | No |
| `plot_id` / `GlobalID` / `OBJECTID` | Reglas de uso definidas | UNKNOWN | No evaluable | MEDIUM / VERIFICATION_REQUIRED | UNKNOWN | Verificar tras §A0 | No | Sí |
| GPS / privacidad de adjuntos | Solo grupo privado, nunca público | UNKNOWN | No evaluable | MEDIUM / VERIFICATION_REQUIRED | UNKNOWN | Confirmar alcance de compartición real antes de cualquier campaña | No | Sí |
| Experience Builder app | Requerida para el MVP | **UNKNOWN** (no confirmada ni descartada) | No evaluable | HIGH / VERIFICATION_REQUIRED | UNKNOWN | Obtener Item ID si existe (§A0); si no existe, planificar creación tras cerrar brechas previas | Posible | Sí |
| Cuenta educativa — continuidad/transferibilidad | Debe registrarse (`build-playbook.md` B0.2) | UNKNOWN | No evaluable | HIGH / VERIFICATION_REQUIRED | UNKNOWN | Obtener owner de continuidad y fecha de revisión | No | Sí |
| Snapshot/actualización | Sello `source_version`+fecha obligatorio | UNKNOWN | No evaluable | MEDIUM / VERIFICATION_REQUIRED | UNKNOWN | Confirmar tras §A0 | Posible | Sí |
| Dashboard | Diferido como alcance de producto | UNKNOWN si existe en ArcGIS | No evaluable | INFORMATIONAL | DEFERRED (alcance) / UNKNOWN (existencia) | Ninguna en Fase 3 | No | No |
| StoryMap | Diferido como alcance de producto | UNKNOWN si existe en ArcGIS | No evaluable | INFORMATIONAL | DEFERRED (alcance) / UNKNOWN (existencia) | Ninguna en Fase 3 | No | No |
| Capa PRUG/límite | Condicionada a licencia | UNKNOWN | No evaluable | LOW | DEFERRED | Confirmar licencia antes de considerar | No | Sí |

## Recuento de severidades

| Severidad | Nº de filas |
|---|---|
| BLOCKER (proceso) | 1 |
| HIGH (VERIFICATION_REQUIRED) | 7 |
| HIGH (DERIVED_RISK) | 1 |
| MEDIUM (VERIFICATION_REQUIRED) | 4 |
| LOW | 2 |
| INFORMATIONAL | 3 |

**Nota de corrección:** en la versión anterior de este documento, la ausencia
confirmada del feature service de Survey123 y de la app Experience Builder se
clasificó como `BLOCKER` de contenido. Se corrige aquí: al no haber
confirmación de que esos items **no** existan, su severidad correcta es
`HIGH / VERIFICATION_REQUIRED`, no `BLOCKER`. El único `BLOCKER` real de esta
fase es la **ausencia de metadatos en vivo** que impide evaluar todo lo demás.

## Severidades usadas

- **BLOCKER** — reservado para: ausencia de metadatos que impide una decisión
  de construcción segura (el caso actual); esquema incompatible confirmado;
  problema de privacidad/compartición confirmado; ausencia confirmada de un
  servicio requerido.
- **HIGH** — riesgo real de integridad de datos o de continuidad
  institucional, o verificación pendiente de un ítem central del MVP.
- **MEDIUM** — requiere verificación/configuración antes de confiar en el item.
- **LOW** — riesgo menor o condicional a una decisión futura.
- **INFORMATIONAL** — sin acción requerida ahora.
