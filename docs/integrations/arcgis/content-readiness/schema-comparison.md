# Comparación de esquemas — contrato Git vs estado ArcGIS

> **Estado gobernante (2026-08-01): DESBLOQUEADA por evidencia autenticada del
> propietario.** El propietario inspeccionó la REST autenticada y aportó los
> esquemas exactos; esta sección los compara con el contrato Git. Categoría:
> `OWNER_AUTHENTICATED_SCHEMA_VERIFIED`. El estado previo anónimo (BLOQUEADA) se
> conserva más abajo como histórico.

## A. Comparación autenticada — `pilot_assets` (capa 0 `pilot_assets_points`)

**Coincidencias confirmadas (`OWNER_AUTHENTICATED_SCHEMA_VERIFIED`):** capa de
puntos; el set analítico de negocio del contrato Git está presente y preservado
(`asset_id`, `asset_name`, `category`, `stratum`, `original_geom_type`, `trend`,
`trend_significant`, `n_observations`, `tau`, `p_value`, `sens_slope`,
`sens_slope_ci_low/high`, `confidence`, `change_point_date`, `partial_years`,
`evidence_class`, `demo_status`, `source_version`, `provenance`,
`decision_caveat`). Uso apto para la demo académica.

**Debilidades confirmadas (esquema de importación genérico, frágil para un
contrato de producción duradero):**

| Aspecto | Contrato Git deseado | ArcGIS real verificado |
|---|---|---|
| CRS | EPSG:4326 (canónico) | **WKID 102100 / EPSG 3857 (Web Mercator)** |
| Clave `asset_id` | estable/única | **nullable, sin restricción de unicidad** |
| `GlobalID` | presente (relaciones/adjuntos) | **ausente** |
| Adjuntos | — | **false** |
| Longitud de strings | acotada por campo | **genérica 4000 en todos** |
| Dominios categóricos | dominios en campos gobernados | **ninguno visible** |
| OID | — | `ObjectId` (OID, no editable) |

`editable=true` a nivel de campo **no** prueba que todo usuario pueda editar; la
compartición e ítem-permisos exactos son una cuestión separada (pendiente).

## B. Comparación autenticada — Survey123 (servicio principal, capa 0)

**Coincidencias/fortalezas confirmadas (`OWNER_AUTHENTICATED_SCHEMA_VERIFIED`):**
capa 0 `SNTO_DEMO_PNSG_FieldValidation`, geometría punto, **EPSG 4326**,
`objectid` (OID) + **`globalid` (GlobalID)**, **adjuntos habilitados**, **editor
tracking** (`CreationDate`/`Creator`/`EditDate`/`Editor`), `has views: true`. Los
campos del flujo de validación documentado están presentes (`plot_id`,
`asset_id`, `stratum`, `is_control`, `observed_at`, `observer`,
`distance_to_trail_m`, `lat`, `lon`, `gps_accuracy_m`, `soil_compaction_mpa`,
`veg_cover_pct`, `erosion_class`, `trail_width_m`, `visitor_count`, `notes`,
`photo_ref`, `evidence_class`, `qa_status`, `survey_version`). **Dominios de
valores codificados** presentes en `plot_id`, `erosion_class`, `evidence_class`.

**Debilidades/brechas de configuración confirmadas:**

- campos de negocio nullable a nivel de servicio;
- **sin dominios visibles** para `stratum`, `is_control`, `qa_status`;
- **sin tablas relacionadas** enumeradas; **sin relación formal** con
  `pilot_assets` (la unión sigue siendo lógica por `asset_id` string, según
  `data-contract.md` §6);
- compartición exacta de item y permisos efectivos de edición: **pendientes**.

## C. Vistas Survey123

- **Form view** (capa 0, `Is View: true`, `Is Updatable View: true`, punto, EPSG
  4326, adjuntos): rol de captura/actualización Survey123 →
  `REUSE_AS_IS_FOR_SURVEY123_CAPTURE`. No usar como fuente de evidencia
  read-only por defecto.
- **Results view** (capa 0, vista, ops de capa orientadas a consulta —`Query`,
  `Query Pivot/Top Features/Analytic/Bins`, `Query Attachments`— **sin `Add
  Features` a nivel de capa**): fuente de evidencia read-oriented preferida para
  Experience Builder → `REUSE_AS_IS_FOR_READ_ONLY_EVIDENCE`. **Cautela:** el root
  reporta `Is Updatable View` y soporte de `Apply Edits`; **no** se afirma que la
  vista sea solo-lectura garantizada para todo usuario — es preferida por sus
  ops de capa orientadas a consulta; los permisos efectivos y la política de
  edición de la vista requieren verificación de permisos a nivel de item.

## D. Riesgo de deriva resuelto

El `DERIVED_RISK` de deriva de metadata (capa publicada antes de la
normalización de Fase 2B) queda **contextualizado**: la capa real usa Web
Mercator y un esquema de importación genérico; los campos de negocio canónicos
están presentes, pero la representación no coincide con el GeoJSON WGS84 canónico
ni con los metadatos de snapshot enriquecidos de Fase 2B. Esto es un hallazgo de
configuración confirmado, no ya una mera hipótesis.

---

> **Histórico (estado previo).** A continuación se conserva la sección anónima
> (2026-07-31), cuando la comparación estaba BLOQUEADA.

## Comparación anónima (2026-07-31) — histórico

> **Estado tras el suplemento de verificación anónima (2026-07-31): la
> comparación de esquemas seguía BLOQUEADA.** Los dos FeatureServer resuelven
> (ANONYMOUS_REST_VERIFIED) pero bloquean el acceso anónimo
> (ANONYMOUS_ACCESS_BLOCKED, `499 Token Required`), y la regla de "sin
> credenciales" impedía leer el esquema. Por tanto **ninguna** celda "Estado
> ArcGIS real" pudo cerrarse entonces; todas permanecían
> `AUTHENTICATED_READ_REQUIRED`. Los riesgos de deriva se etiquetaban
> `DERIVED_RISK`.

## Nota del suplemento anónimo (2026-07-31)

Lo verificado sin token: **resolución del endpoint y bloqueo de acceso anónimo**
de ambos servicios (ver `item-inventory.md`). Lo NO verificable sin token:
campos, tipos, nulabilidad, dominios, `GlobalID`/`parentglobalid`, geometría,
CRS, índices de capa/tabla, adjuntos, editor tracking, relaciones. En las tablas
siguientes, cada `UNKNOWN` del lado ArcGIS se reclasifica como
**`AUTHENTICATED_READ_REQUIRED`** (el endpoint resuelve pero su esquema requiere
lectura autenticada), salvo donde ya se indica lo contrario.

Para desbloquear: el propietario aporta una **exportación read-only del JSON
REST** de cada servicio/capa (`.../FeatureServer?f=json`, `.../0?f=json`, etc.)
generada desde su sesión ya autenticada, o habilita una sesión de solo lectura
(ver `owner-action-plan.md` §A0b). No se solicita cambiar la compartición.

---

## 1. Capa de activos (`SNTO_DEMO_PNSG_Assets`)

| Campo del contrato (`data-contract.md` §1) | Estado en Git ahora | Estado ArcGIS real |
|---|---|---|
| `asset_id`, `asset_name`, `category`, `stratum` | VERIFIED presentes en `pilot_assets.geojson` | UNKNOWN |
| `trend`, `tau`, `p_value`, `sens_slope`, IC | VERIFIED presentes | UNKNOWN |
| `evidence_level`/`evidence_class`, `demo_status`, `provenance` | VERIFIED presentes | UNKNOWN |
| `source_repository_commit`, `data_observation_period`, `publication_status`, `sync_mode` | VERIFIED — añadidos en la normalización de Fase 2B (commit `78eed77`, 2026-07-29) | UNKNOWN |
| `source_version` = `2.1.0.dev0` | VERIFIED valor actual en `metadata.snto_version` | UNKNOWN |
| `calculated_at` / `prepared_at` | VERIFIED `2026-07-13` (conservado deliberadamente, `PROVENANCE.md` §3) | UNKNOWN |
| Geometría / CRS `EPSG:4326` | VERIFIED | UNKNOWN |
| `editing_enabled` | N/A (no lo controla Git) | UNKNOWN — el roadmap de 2026-07-13 registró `false` en ese momento; el estado **actual** no está reverificado |
| `object_id_field`, `global_id_field`, capabilities, `max_record_count` | N/A (no existen en GeoJSON) | UNKNOWN |

### DERIVED_RISK — hipótesis de deriva temporal (no confirmada)

**Hecho verificable sin ArcGIS:** la verificación de publicación de la capa de
activos en el roadmap es del **2026-07-13**. La normalización documental del
contrato Git ocurrió en el commit de Fase 2B, fechado **2026-07-29**
(`78eed77…`) — **16 días después**. Esa normalización añadió campos de
metadata (`source_repository_commit`, `data_observation_period`,
`publication_status`, `sync_mode`, `snto_version` actualizado) al contrato
Git.

**Esto es un `DERIVED_RISK`, no una constatación de deriva real:** es
plausible, por la cronología, que la capa publicada no incluya esos campos
posteriores — pero **no se ha verificado**. La capa pudo haber sido
republicada o actualizada en cualquier momento entre el 2026-07-13 y hoy sin
que quede registro en este repositorio (ArcGIS Online no está versionado en
Git). **No se afirma que la capa real carezca de estos campos.**

## 2. Observaciones de campo (Survey123)

| Campo canónico (`data-contract.md` §4) | Estado en Git ahora | Estado ArcGIS real |
|---|---|---|
| 14 columnas canónicas (`plot_id` … `observed_at`) | VERIFIED en `field_observations_seed.csv` y en el XLSForm | UNKNOWN |
| Campos de gobierno (`observer`, `gps_accuracy_m`, `qa_status`, `evidence_class`, `notes`) | VERIFIED en el XLSForm | UNKNOWN |
| `GlobalID`/`parentglobalid` para adjuntos | Propuesto en `data-contract.md` §7 | UNKNOWN |
| Dominios (`erosion_class` 0-3, etc.) | VERIFIED descritos en `arcgis/demo/pnsg/README.md` | UNKNOWN |

**Estado del feature service:** UNKNOWN (ver `item-inventory.md`). Esta
sección no puede completarse como comparación real hasta que se confirme si
el servicio existe y, de existir, se inspeccione su esquema.

## 3. Identificadores de negocio

| Regla del contrato | Estado |
|---|---|
| `asset_id` string es la clave de unión (no `OBJECTID`) | Regla de diseño VERIFIED en el contrato; su cumplimiento en la capa real es UNKNOWN |
| Brecha `asset_id` string (GIS) vs FK entera (`managed_assets.id`, persistencia) | VERIFIED como hecho de código en `data-contract.md` §6 — no depende de ArcGIS, por tanto no está sujeto a esta incertidumbre |

## 4. Resumen de confianza

| Dominio | Confianza en el contrato Git | Estado ArcGIS real |
|---|---|---|
| Esquema de activos base | Alta (verificado en el archivo) | UNKNOWN |
| Metadata de snapshot (`source_version` etc.) | Alta (verificado en el archivo) | UNKNOWN — DERIVED_RISK de ausencia, no confirmado |
| Esquema de observaciones | Alta (XLSForm verificado) | UNKNOWN — depende de si el servicio existe |
| Reglas de identificador (`asset_id`/`OBJECTID`) | Alta (regla de diseño documentada) | UNKNOWN en la capa real; no aplica a la regla de código interna |

**Conclusión de esta sección:** ninguna celda "Estado ArcGIS real" puede
cerrarse sin una de las dos vías: (a) los metadatos de `owner-action-plan.md`
§A0, o (b) una inspección de solo lectura de las URLs de servicio reales.
