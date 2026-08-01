# Mapeo de fuentes de datos

> `pilot_assets` = contexto analítico del activo · Survey123 **results view** =
> visualización de evidencia · Survey123 **form item** = solo enlace/botón de
> captura externa · **Web Map** = fuente de mapa principal. El **form view** NO
> es la fuente de visualización de evidencia por defecto.

| Página | Widget | Fuente de datos | Capa/vista | Filtro/interacción | Rol lectura/escritura |
|---|---|---|---|---|---|
| Decidir | Map | Web Map | Web Map (ambas capas) | filtros globales | lectura |
| Decidir | List / Indicators | pilot_assets | capa 0 | filtro `evidence_class`/`trend` | lectura |
| Decidir | Text | pilot_assets | capa 0 | `decision_caveat` del seleccionado | lectura |
| Diagnosticar | Map / Feature Info | Web Map / pilot_assets | capa 0 | selección | lectura |
| Diagnosticar | Table | pilot_assets | capa 0 | filtro | lectura |
| Evidenciar | Map / List / Feature Info | Survey123 **results view** | capa 0 | `asset_id`/`plot_id`/`evidence_class`/`qa_status`/`observed_at` | **lectura** (read-oriented) |
| Evidenciar | Attachment | Survey123 **results view** | capa 0 | por observación seleccionada | lectura |
| Evidenciar | Button «Registrar» | Survey123 **form item** | form item (enlace externo) | prefill `asset_id`/`stratum`/`is_control` | escritura (fuera de la app) |
| Gobernar | Text / Button | contenido en Git + items enlazados | — | — | lectura |
| Asset Detail | Map / Feature Info | pilot_assets | capa 0 | activo seleccionado | lectura |
| Asset Detail | Observaciones relacionadas | Survey123 **results view** | capa 0 | filtro lógico por `asset_id` | lectura |
| Asset Detail | Attachment | Survey123 **results view** | capa 0 | por observación | lectura |

## Reglas

- **No** usar el form view para visualizar evidencia (es para captura); la
  captura ocurre **fuera** de la app EB, en Survey123, vía enlace prefilled.
- **No** duplicar capas alojadas: todas las fuentes son las existentes.
- La unión activo↔observación es **lógica por `asset_id` string** (ver
  `interaction-matrix.md`), no una relationship class.
