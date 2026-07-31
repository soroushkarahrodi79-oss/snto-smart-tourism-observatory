# Comparación de esquemas — contrato Git vs estado ArcGIS (preliminar)

> **Sin inspección en vivo, no existe ninguna comparación real posible en el
> lado ArcGIS.** Este documento describe con precisión el contrato Git (lado
> conocido) y marca el lado ArcGIS como `UNKNOWN` en todos los casos. Los
> riesgos de deriva se etiquetan explícitamente `DERIVED_RISK` — una hipótesis
> plausible por cronología, **no** una comparación de esquemas reales.

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
