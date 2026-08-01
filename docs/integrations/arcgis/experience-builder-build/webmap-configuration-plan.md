# Plan de configuración del Web Map (preparado — NO ejecutar)

> Ninguna edición del Web Map se realiza en esta tarea. Este plan se ejecuta solo
> tras A0c + aprobación explícita de mutación.

## Principio

- Mantener el Web Map **ampliamente reutilizable**.
- Implementar **la mayor parte del filtrado interactivo en Experience Builder**
  (widget Filter + interacciones por selección), no como restricciones
  permanentes del mapa.
- Usar **definition expressions** solo donde se necesite una restricción de datos
  **permanente** (evitar expresiones destructivas o restrictivas innecesarias).

## Filtros — dónde vive cada uno

| Filtro | Web Map (permanente) | EB Filter widget | Interacción por selección | Página |
|---|---|---|---|---|
| `asset_id` | No | Sí | Sí (asset → observaciones) | Decidir, Diagnosticar, Evidenciar, Asset Detail |
| `evidence_class` | No | Sí | — | Decidir, Evidenciar |
| `qa_status` | No | Sí | — | Evidenciar |
| `observed_at` | No | Sí (rango) | — | Evidenciar |
| `plot_id` (opcional) | No | Opcional | Sí (selección de parcela) | Evidenciar, Asset Detail |

**Definition expressions permanentes:** ninguna requerida para el MVP. Solo se
consideraría una si se necesitara ocultar permanentemente registros (p. ej.
excluir pruebas `synthetic` de una vista pública) — **no** es el caso ahora
(demo privada). Documentar y aprobar caso por caso si surge.

## Popup — `Observaciones de campo · DEMO`

**Mostrar (orden de decisión):** `plot_id`, `asset_id`, `observed_at`,
`evidence_class`, `qa_status`, `soil_compaction_mpa`, `veg_cover_pct`,
`erosion_class`, `trail_width_m`, `visitor_count`, `notes`, **adjuntos**
(«Evidencia fotográfica»).

**Ocultar del popup de usuario:** `objectid`, `globalid`, `Creator`, `Editor`,
`CreationDate`, `EditDate`, y `lat`/`lon` crudos (salvo uso administrativo).

**Reglas:** los campos nulos se muestran «Sin dato» (nunca `0`); `evidence_class`
`synthetic`/`missing` se muestran explícitamente; no promocionar `synthetic` a
`real`.

## Popup — `pilot_assets`

**Mostrar:** `asset_name`, `category`, `stratum`, `trend`, `trend_significant`,
`confidence`, `n_observations`, `tau`, `p_value`, `sens_slope`,
`change_point_date`, `evidence_class`, `demo_status`, `decision_caveat`,
`provenance`.

**Ocultar:** `ObjectId` y campos técnicos no útiles para usuarios de decisión.

**Reglas:** tendencia ≠ causalidad; el punto de un activo con geometría
provisional no es un límite autoritativo; mostrar `decision_caveat` de forma
prominente; sello de fecha/`source_version` visible («snapshot, no en vivo»).

## Simbología (ya existente — conservar)

- `Observaciones de campo · DEMO`: por clase de evidencia (Real / Faltante /
  Sintética / Otro) — combinar con etiqueta/patrón, no solo color (accesibilidad).
- `pilot_assets`: por tendencia (decreasing / increasing / Otro) — ídem.

## Puerta

Revisión visual del propietario de simbología + popups antes de conectar el Web
Map a Experience Builder. No ejecutar hasta A0c + aprobación de mutación.
