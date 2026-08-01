# Contrato de datos ArcGIS ↔ SNTO

> Fase 2A · documentación únicamente. **No se modifica el modelo de persistencia
> ni ningún esquema en esta fase.** Este documento define el contrato que la
> implementación futura deberá respetar.

## 0. Principios transversales

- **[Verificado] CRS:** todo es **WGS84 / EPSG:4326** (`arcgis/demo/pnsg/pilot_assets.geojson`
  `metadata.crs = "EPSG:4326"`; `src/reporting/gis_export.py` escribe
  `crs="EPSG:4326"`).
- **[Verificado] El ensamblador conserva las propiedades de entrada.**
  `build_feature_collection` (`src/reporting/gis_export.py`) añade propiedades
  de tendencia escalares, pero no aplana ni valida las propiedades originales.
  **[Propuesto]** La fuente que se publique debe pasar una comprobación
  scalar-only antes de crear el Hosted Feature Layer.
- **[Verificado] Null ≠ cero.** Un activo sin tendencia obtiene campos `null` y
  `has_trend=false`, **nunca** un valor fabricado (`_trend_properties(None)`).
  Un `degradation_index` sin componentes devuelve `None`
  (`src/validation/field.py`), que el consumidor debe tratar como «sin dato»,
  no como 0.
- **[Propuesto] Regla de presentación:** en ArcGIS, los campos numéricos nulos
  se muestran como «—» o «Sin dato», nunca como 0. Los popups usan expresiones
  Arcade que distinguen `null` de `0`.
- **[Propuesto] Semántica de ausencia:** `unknown` no equivale a `false`; no
  tener observación no equivale a tendencia `no trend`/«estable»; no tener
  registro de campo no equivale a `field_verified`; y un dato
  `synthetic`/`simulated` nunca pasa automáticamente a `real`.

## 1. Capa de activos (`SNTO_DEMO_PNSG_Assets`)

Fuente canónica de geometría: **[Verificado]** `clean_assets/pnsg_assets.geojson`
(21 activos; geometrías `Point`, `LineString` y `Polygon`; propiedades mínimas
`asset_id`, `name`, `category`, `geom_type`). `build_feature_collection`
preserva cada geometría y añade tendencia + EHS + evidencia. La capa piloto ya
publicada (`arcgis/demo/pnsg/pilot_assets.geojson`, 2 activos) es un
**subconjunto enriquecido manualmente y convertido a dos puntos de referencia**.

| Campo | Tipo ArcGIS | Nulable | Alias sugerido | Dominio / regla | Origen |
|---|---|---|---|---|---|
| `asset_id` | Text(128) | No | Identificador de activo | clave estable string | `pnsg_assets.geojson` |
| `asset_name` / `name` | Text(200) | No | Nombre | — | `pnsg_assets.geojson` |
| `category` | Text(64) | Sí | Categoría | p. ej. `escalada`, `vuelo_libre` | `pnsg_assets.geojson` |
| `stratum` | Text(64) | Sí | Estrato | dominio de hábitat | pilot geojson |
| `original_geom_type` | Text(32) | Sí | Geometría original | `POINT`/`POLYGON` | pilot geojson |
| `trend` | Text(16) | Sí | Tendencia | `increasing`/`decreasing`/`no trend`/null; null se presenta «Sin serie», nunca «Estable» | `satellite_trends` |
| `trend_significant` | Integer (0/1) | Sí | ¿Significativa? | booleano ArcGIS-safe | `AssetTrend.significant` |
| `is_degrading` | Integer (0/1) | Sí | ¿Degradando? | `AssetTrend.is_alert` | `_trend_properties` |
| `tau` | Double | Sí | Tau de Kendall | redondeo 4 | `_trend_properties` |
| `p_value` | Double | Sí | p | redondeo 4 | `_trend_properties` |
| `sens_slope` | Double | Sí | Pendiente de Sen | — | `_trend_properties` |
| `sens_slope_ci_low` | Double | Sí | IC inf. | — | `AssetTrend.sens_slope_ci[0]` |
| `sens_slope_ci_high` | Double | Sí | IC sup. | — | `AssetTrend.sens_slope_ci[1]` |
| `n_observations` | Integer | Sí | Nº observaciones | — | `_trend_properties` |
| `has_trend` | Integer (0/1) | No | ¿Tiene tendencia? | 0 = sin serie | `_trend_properties` |
| `ehs` | Double | Sí | EHS | null si falta | `ehs_by_id` |
| `confidence` | Text(16) | Sí | Confianza | dominio `high`/`medium`/`low` | pilot geojson |
| `change_point_date` | Date | Sí | Punto de cambio | ISO | pilot geojson |
| `partial_years` | Text(32) | Sí | Años parciales | p. ej. `2026` | pilot geojson |
| `evidence_level` / `evidence_class` | Text(16) | No | Nivel de evidencia | dominio (ver §5) | `DataStatus` |
| `demo_status` | Text(8) | No | Estado demo | siempre `DEMO` | pilot geojson |
| `source_version` | Text(16) | No | Versión SNTO | `src._version.__version__` | pilot geojson; el exportador actual solo la incluye como `metadata.version` top-level |
| `calculated_at` | Date | Sí | Calculado el | sello de snapshot | **[Propuesto]** añadir en export |
| `provenance` | Text(500) | No | Proveniencia | texto | `_DEFAULT_PROVENANCE` |
| `decision_caveat` | Text(500) | Sí | Cautela de decisión | texto | pilot geojson |

**[Propuesto] Deriva a corregir:** `pnsg_assets.geojson` (fuente de 21 activos)
solo trae 4 propiedades; para preparar una capa completa hay que ejecutar
`scripts/export_gis.py` y usar su salida enriquecida, no el GeoJSON mínimo.
**[Verificado]** Esa salida actual todavía no lleva `source_version`,
`calculated_at` ni `demo_status` en cada feature (la versión solo aparece en la
metadata top-level), por lo que no debe publicarse como conforme a este contrato
sin una preparación/revisión separada. `source_version` del pilot geojson dice
`1.5.0.dev0` y debe regenerarse a la versión actual.

## 2. Atributos satélite / tendencia

**[Verificado]** Modelados como columnas de la propia capa de activos (join 1:1
por `asset_id`), no como tabla separada — así lo hace `build_feature_collection`.
Semántica de evidencia: la tendencia real proviene de Sentinel-2
(`src/platform/satellite_trends.py`). **[Verificado]** El repositorio actual
contiene tendencias para los **21** IDs de `pnsg_assets.geojson`; la capa piloto
publicada contiene solo **2** de esos activos. Para cualquier activo sin serie
coincidente, el exportador usa `has_trend=false` + campos null.

## 3. Atributos de evidencia / proveniencia

Ver §5 para el vocabulario. Campos: `evidence_level`, `provenance`,
`source_version`, `calculated_at`, `demo_status`, `decision_caveat`. **Regla:**
`evidence_level` es de **estado de dato**, no de workflow ni de validación (esas
son dimensiones separadas, §5).

## 4. Observaciones de campo (Survey123 `SNTO_DEMO_PNSG_FieldObservations`)

**[Verificado]** Las **14 columnas canónicas** deben conservar su nombre para que
`src.validation.io` pueda importarlas (roadmap §2.2; `arcgis/demo/pnsg/README.md`
línea 21: «No cambiar los nombres de las primeras catorce columnas»).

| Campo canónico | Tipo | Nulable | Dominio / regla | Origen |
|---|---|---|---|---|
| `plot_id` | Text | No | único por parcela | `FieldObservation.plot_id` |
| `asset_id` | Text | Sí* | **string**, FK lógica al activo | `FieldObservation.asset_id` |
| `lat` | Double | No | WGS84 | — |
| `lon` | Double | No | WGS84 | — |
| `distance_to_trail_m` | Double | No | ≥ 0 | — |
| `is_control` | Integer (0/1) | No | impacto/control (BACI) | — |
| `soil_compaction_mpa` | Double | Sí | ≥ 0 (penetrómetro) | null si no medido |
| `veg_cover_pct` | Double | Sí | 0–100 | null si no medido |
| `erosion_class` | Integer | Sí | 0/1/2/3 (`ErosionClass`) | null si no medido |
| `trail_width_m` | Double | Sí | ≥ 0 | null si no medido |
| `visitor_count` | Integer | Sí | ≥ 0 | null si no medido |
| `photo_ref` | Text | Sí | referencia a adjunto | ver §7 |
| `stratum` | Text | Sí | hábitat / banda altitudinal | — |
| `observed_at` | Date | Sí | ISO | obligatorio en captura real |

\* `asset_id` es opcional en el esquema `FieldObservation`, pero **obligatorio en
el formulario Survey123** para poder unir la observación al activo.

**Campos de gobierno adicionales [Verificado] (ignorados por el cargador actual;
roadmap §2.2):** `observer`, `gps_accuracy_m`, `qa_status`
(`draft`/`submitted`/`reviewed`/`rejected`), `evidence_class`
(`synthetic` por defecto en pruebas), `notes`, más editor/fecha de ArcGIS.

## 5. Vocabulario de evidencia — TRES dimensiones separadas

**[Verificado] deriva de vocabulario** (informe Fase 1 §11). **[Propuesto]** No
colapsar en un solo campo. Tres columnas distintas:

### 5.1 Estado del dato de origen (`evidence_level` / `evidence_class`)

**[Verificado]** `src/temporal/manifest.DataStatus` implementa `real` ·
`calibrated` · `synthetic` · `missing`. **[Propuesto]** El contrato de
presentación ArcGIS conserva además `estimated` y `simulated` como etiquetas
explícitas cuando procedan; no se degradan silenciosamente a `calibrated` ni se
promocionan a `real`. `simulated` y `synthetic` pertenecen a la misma familia de
no-observación, pero se mantienen distinguibles para preservar su procedencia.

### 5.2 Estado de QA / workflow (`qa_status`)
`planned` (semilla) · `draft` · `submitted` · `reviewed` · `rejected`.
**[Verificado]** en `field_observations_seed.csv` (`planned`) y roadmap §2.2.

### 5.3 Estado de validación (`validation_status`) — **[Propuesto]**
Derivado, no almacenado en origen: `unvalidated` (sin parcela de campo) ·
`in_campaign` (parcelas en curso) · `field_verified` (medición real recogida).
**Nunca** se calcula automáticamente desde datos `synthetic`.

El resultado de concordancia se guarda aparte como `agreement_status`/métricas:
`not_assessed` · `insufficient_sample` · `assessed`. Solo puede contener un
veredicto de acuerdo después de una comparación legítima satélite↔campo con
muestra suficiente; `field_verified` por sí solo no implica acuerdo.

| Dimensión | Campo | Valores | No confundir con |
|---|---|---|---|
| Dato de origen | `evidence_level` / `evidence_class` | real/calibrated/estimated/simulated/synthetic/missing | QA |
| QA/workflow | `qa_status` | planned/draft/submitted/reviewed/rejected | validación |
| Validación | `validation_status` | unvalidated/in_campaign/field_verified | dato de origen |
| Concordancia | `agreement_status` + métricas | not_assessed/insufficient_sample/assessed | mera existencia de un registro de campo |

## 6. Identificadores: string `asset_id` vs FK numérica de persistencia

**[Verificado] Brecha real de esquema:**

- **GIS / Survey123 / GeoJSON** usan `asset_id` **string** (p. ej.
  `pnsg_escalada_maliciosa_porrones`). Es la clave del contrato de exportación e
  importación (`src.validation.io`, `pilot_assets.geojson`).
- **Persistencia** (`src/persistence/models/field_verification.py`) usa
  `asset_id` **entero**, FK a `managed_assets.id`. `ManagedAsset` guarda el
  string en `external_asset_id` (Text(128), index).

**[Propuesto] Capa de mapeo obligatoria (sin cambiar persistencia en Fase 2A):**

```
external_asset_id (string, GIS/Survey123)  ⇄  managed_assets.id (int, DB)
```

El futuro `scripts/import_arcgis_field_observations.py` (roadmap Fase 6) debe
resolver este mapeo al ingerir, **no** el modelo ArcGIS. En ArcGIS solo vive el
`asset_id` string; la FK numérica es interna a SNTO y no se expone.

## 7. Identificadores de ArcGIS y adjuntos

| Identificador | Rol | Uso en el contrato |
|---|---|---|
| `OBJECTID` | PK autogenerada de ArcGIS por entidad | Interno de ArcGIS; **no** es clave de negocio. No usar para unir a SNTO. |
| `GlobalID` | UUID estable de ArcGIS por entidad | Clave para relacionar adjuntos y registros hijos. |
| `parentglobalid` | FK de un registro hijo/adjunto a su `GlobalID` padre | Relación 1:N observación→fotos. |
| `plot_id` | Clave de negocio SNTO de la parcela | Unión lógica y deduplicación en la importación. |
| `asset_id` (string) | FK lógica observación→activo | Unión Asset Detail ↔ observaciones. |

**[Propuesto] Adjuntos/fotos:** se gestionan con el mecanismo nativo de adjuntos
de la Hosted Feature Layer (relación por `GlobalID`/`parentglobalid`).
`photo_ref` es una referencia textual; el binario vive como adjunto de ArcGIS,
**no** se exporta a Git. Privacidad: solo dentro del grupo privado (ver
`survey123-integration.md`).

## 8. Metadatos de snapshot / actualización

**[Propuesto]** Cada capa de snapshot expone:

- `source_version` (versión SNTO que generó el snapshot),
- `calculated_at` / `prepared_at` (fecha del snapshot),
- `demo_status = DEMO`,
- una nota de capa: «Snapshot regenerado manualmente; no es un feed en vivo».

La metadata top-level del `FeatureCollection` (`system`, `version`, `park`,
`evidence_level`, `feature_count`, `features_with_trend`) la produce
`build_feature_collection` **[Verificado]** y se traslada a la descripción del
item ArcGIS (GeoPackage la descarta, por eso vive en el GeoJSON hermano).
