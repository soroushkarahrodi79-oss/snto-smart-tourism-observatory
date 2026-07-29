# Integración Survey123

> Fase 2A · documentación únicamente. **No se modifica el XLSForm existente ni
> ningún item de ArcGIS en esta fase.**

## 1. Estado conocido (Verificado)

Fuente: `docs/arcgis/field-validation-demo-roadmap.md` (Fase 3, progreso
2026-07-13) y `arcgis/demo/pnsg/`.

- Survey123 Connect **instalado**.
- XLSForm generado: `arcgis/demo/pnsg/SNTO_DEMO_PNSG_FieldValidation.xlsx`
  (solo hojas `survey`, `choices`, `settings`), con 4 parcelas controladas,
  coordenadas y `gps_accuracy_m` calculadas, rangos de calidad, fotografías y
  clasificación explícita de evidencia.
- Esquema alineado con las **14 columnas canónicas** de `src.validation.io`.
- Semilla de datos: `arcgis/demo/pnsg/field_observations_seed.csv` — 4 parcelas
  en estado `qa_status = planned`, `evidence_class = missing` (**no** son
  observaciones).
- **Pendiente (Verificado):** importar en Connect, analizar la encuesta, probar
  una captura sintética y publicar el feature service **solo** en el grupo
  privado.

## 2. Metadato de ArcGIS desconocido (Requiere input humano)

No está en el repositorio y solo el propietario puede aportarlo (placeholders en
`item-registry.example.yaml`):

- `field_survey_item_id` (Item ID del formulario),
- `field_service_item_id`, `field_service_url`, `field_layer_index` (feature
  service publicado),
- configuración real de adjuntos/fotos,
- dominios/alias efectivos tras publicar,
- ajustes de editor tracking,
- ID del grupo privado y owner.

## 3. Concepto de URL prefill (Propuesto)

Al abrir Survey123 desde **Asset Detail** o desde la página **Evidenciar**, se
puede prellenar contexto mediante parámetros de URL de Survey123:

- **Prellenar (contexto):** `asset_id` (string), `stratum`, `is_control`
  (según se registre impacto o control). Estos son campos de **contexto**, no
  mediciones.

### Valores que NUNCA se prellenan como observaciones (regla dura)

**[Verificado por política]** (`arcgis/demo/pnsg/README.md`): jamás prellenar ni
autocompletar como si fueran datos observados:

- `soil_compaction_mpa`, `veg_cover_pct`, `erosion_class`, `trail_width_m`,
  `visitor_count` — se **miden en campo**; en la semilla son `null`, nunca 0.
- `lat`/`lon` definitivos — se capturan por **GPS en campo**; las coordenadas de
  la semilla son «marcadores provisionales».
- `evidence_class` **nunca** se prellena como `real`; una prueba de escritorio es
  `synthetic`. «Nunca cambiar automáticamente `synthetic` a `real`».

## 4. Adjuntos y privacidad GPS/fotos

**[Propuesto]**

- Fotos y adjuntos → mecanismo nativo de adjuntos de la Hosted Feature Layer
  (relación por `GlobalID`/`parentglobalid`, ver `data-contract.md` §7).
- **Privacidad:** ubicación, fotografías, adjuntos y registros de observación
  son sensibles. Compartición **solo con el grupo privado**; **nunca** público
  durante el desarrollo ni antes de una revisión de compartición explícita y
  documentada (roadmap §1.2, Fase 7). Los binarios de fotos **no** se exportan a
  Git.
- El binario permanece en ArcGIS; `photo_ref` es solo una referencia textual.

## 5. Diseño de la relación observación ↔ activo

**[Propuesto]** Unión lógica por **`asset_id` string**, no por `OBJECTID`:

```
Activo (SNTO_DEMO_PNSG_Assets.asset_id)  1 ── N  Observación (Survey123.asset_id)
Observación (GlobalID)                   1 ── N  Adjunto/foto (parentglobalid)
```

`plot_id` es la clave de negocio de la parcela (deduplicación en la importación).

## 6. Brecha de esquema con persistencia (Verificado)

Ver `data-contract.md` §6. Resumen:

- Survey123/GIS usan `asset_id` **string** + esquema de 14 columnas de
  `FieldObservation`.
- `src/persistence/models/field_verification.py` usa `asset_id` **int** (FK a
  `managed_assets.id`) y **carece** de `plot_id`, `lat`/`lon`, `is_control` y de
  las mediciones granulares.

**[Propuesto]** La conciliación es responsabilidad del futuro
`scripts/import_arcgis_field_observations.py` (roadmap Fase 6), **no** de un
cambio de modelo en esta fase. Esa brecha se documenta, no se «arregla» aquí.

## 7. Límite de no-cambio en Fase 2A

**[Verificado por instrucción]** Durante la Fase 2A **no** se toca:

- el XLSForm `SNTO_DEMO_PNSG_FieldValidation.xlsx`,
- ningún item ni servicio de ArcGIS Online,
- el cargador canónico `src.validation.io`.

Cualquier cambio de formulario se decide y ejecuta en la fase de build,
gobernado por el roadmap Fase 3, con su propia puerta de aprobación.
