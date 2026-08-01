# BATCH B — Configuración del Web Map

> **✅ EJECUTADO POR EL PROPIETARIO Y VERIFICADO (2026-08-01).**
> `BATCH_B_STATUS: OWNER_EXECUTED_AND_VERIFIED` · EXECUTOR `OWNER_MANUAL_UI` ·
> AUTHORIZATION `APPROVE WEB MAP CONFIGURATION BATCH B` · `CLAUDE_DIRECT_ARCGIS_MUTATION: NONE`.
> Backup privado del Web Map creado; B1/B2 popups configurados y guardados; B3
> sin filtros restrictivos; B4 orden/visibilidad/simbología preservados.
> Detalle en [`batch-b-execution-record.md`](batch-b-execution-record.md). La
> tabla de abajo se conserva como el plan aprobado que se ejecutó.

## Mutaciones

| # | Item | Estado actual | Estado propuesto | Ruta UI | Resultado | Riesgo | Rollback | Coste | Evidencia | Bloq/Opc |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | Web Map · popup observaciones | popup con lista de campos + adjuntos | popup refinado: mostrar `plot_id`,`asset_id`,`observed_at`,`evidence_class`,`qa_status`,`soil_compaction_mpa`,`veg_cover_pct`,`erosion_class`,`trail_width_m`,`visitor_count`,`notes`,adjuntos; **ocultar** `objectid`,`globalid`,`Creator`,`Editor`,`CreationDate`,`EditDate`,lat/lon crudos | Map Viewer → capa → Configure pop-ups | popup honesto (null→«Sin dato») | bajo | restaurar popup previo | ninguno | captura popup | Opcional |
| B2 | Web Map · popup pilot_assets | popup por defecto | mostrar `asset_name`,`category`,`stratum`,`trend`,`trend_significant`,`confidence`,`n_observations`,`tau`,`p_value`,`sens_slope`,`change_point_date`,`evidence_class`,`demo_status`,`decision_caveat`,`provenance`; **ocultar** `ObjectId`/técnicos | Map Viewer → capa → Configure pop-ups | popup de decisión | bajo | restaurar | ninguno | captura | Opcional |
| B3 | Web Map · filtros | sin filtro de usuario | **no** añadir definition expressions restrictivas permanentes (el filtrado interactivo vive en Experience Builder, Batch C) | — | Web Map ampliamente reutilizable | ninguno | — | ninguno | nota | N/A |
| B4 | Web Map · visibilidad/orden | 2 capas (Observaciones, pilot_assets) | conservar orden y visibilidad; simbología por evidencia/tendencia con etiqueta/patrón | Map Viewer | legibilidad accesible | bajo | restaurar | ninguno | captura leyenda | Opcional |

## Reglas

- **Sin definition expressions restrictivas permanentes** salvo justificación
  documentada y aprobada (no requerida para el MVP privado).
- Todo cambio es de **presentación**; no altera esquemas, campos, dominios ni
  datos.
- Los campos nulos se muestran «Sin dato» (nunca `0`); `synthetic`/`missing`
  explícitos; no promocionar `synthetic` a `real`.
