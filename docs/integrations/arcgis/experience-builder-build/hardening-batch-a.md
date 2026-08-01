# BATCH A — Hardening de bajo riesgo (preparado — NO ejecutar)

> Puerta de aprobación: **`APPROVE ARCGIS HARDENING BATCH A`**. Ninguna mutación
> se ejecuta hasta esa aprobación explícita. Toggles de gobernanza reversibles.

## Convenciones de ruta UI

`Content → <item> → Settings` para protección de borrado, export, Save As,
búsqueda y aprobación de compartición pública editable. Compartición en el panel
`Share`. Rutas exactas pueden variar según la versión del visor; verificar en la
UI.

## Mutaciones

| # | Item | Estado actual | Estado propuesto | Ruta UI · toggle | Resultado esperado | Riesgo | Rollback | Coste/crédito | Evidencia | Bloq/Opc |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Grupo | protección borrado off | **on** | Group → Settings → Delete protection | grupo no borrable por accidente | ninguno | desactivar toggle | ninguno | captura de Settings | Opcional (recomendado) |
| A2 | pilot_assets | protección on | **sin cambio** | — | — | — | — | ninguno | — | N/A |
| A3 | survey123_main | protección off | **on** | Item → Settings → Delete protection | servicio no borrable | ninguno | desactivar | ninguno | captura | Recomendado |
| A4 | results_view | protección off | **on** | Item → Settings → Delete protection | vista no borrable | ninguno | desactivar | ninguno | captura | Recomendado |
| A5 | **results_view** | export por otros **on** | **off** (default MVP) | Item → Settings → Export data | reduce riesgo de extracción de observador/notas/coords/adjuntos | funcional bajo (viewers no exportan) | reactivar export | ninguno | captura Settings | **Bloqueante (gobernanza)** |
| A6 | form_view | protección off + **aprobación pública editable on** | protección **on**; aprobación pública editable **off** | Item → Settings | evita compartición pública accidental | bajo (no se usa encuesta abierta) | reactivar aprobación | ninguno | captura | **Bloqueante (gobernanza)** |
| A7 | form_item | protección off | **on** | Item → Settings → Delete protection | form no borrable | ninguno | desactivar | ninguno | captura | Recomendado |
| A8 | Web Map | protección off | **on** | Item → Settings → Delete protection | mapa no borrable | ninguno | desactivar | ninguno | captura | Recomendado |
| A9 | Web Map | Save As **on** | **off** (default gobernanza) | Item → Settings → Save As | evita copias no controladas | bajo | reactivar | ninguno | captura | Opcional |
| A10 | Web Map | búsqueda por dirección **on** | **off** (default) | Item → Settings → Search / address | evita dependencia de locator/créditos; demo usa activos conocidos | ninguno funcional para el MVP | reactivar | **evita posible consumo de créditos de geocoding** | captura | Opcional |

## Notas

- **A5 y A6 son las decisiones de gobernanza clave** (bloqueantes): reducen
  exposición de datos sensibles y riesgo de compartición pública accidental.
- Ninguna mutación de A altera esquemas, campos, dominios ni datos.
- Ninguna afirmación de coste cero; A10 puede evitar consumo de créditos de
  geocoding pero la política real es de la organización.
