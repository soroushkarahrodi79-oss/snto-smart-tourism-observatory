# Matriz de interacción (message actions de Experience Builder)

> Todas con widgets/acciones estándar. Ninguna construcción se realiza aún.

| Disparador | Acción (message action) | Objetivo | Página(s) |
|---|---|---|---|
| Selección en List | Map select + zoom | Map | Decidir, Evidenciar, Asset Detail |
| Selección de entidad en Map | Feature Info update | Feature Info | Diagnosticar, Asset Detail |
| Selección de activo | Filtrar lista de observaciones por `asset_id` | List/Table de observaciones | Evidenciar, Asset Detail |
| Filter widget | Filtrar map/list/table/indicadores | Múltiples | Decidir, Diagnosticar, Evidenciar |
| Selección de observación | Mostrar adjuntos | Attachment | Evidenciar, Asset Detail |
| Clear selection | Restaurar el estado por defecto de la página | Todos | Todas |

## Limitaciones documentadas (reglas duras)

- `asset_id` es una **unión lógica**, **no** una relationship class.
- `pilot_assets` **no tiene GlobalID** → no hay clave estable para una relación
  ArcGIS formal.
- **Sin integridad referencial garantizada** entre activos y observaciones.
- Los valores `asset_id` **nulos no** deben tratarse silenciosamente como
  enlazados (mostrar «sin activo asociado», nunca inventar el enlace).
- La evidencia analítica (satélite) y la de campo se muestran **separadas**;
  `planned`/`missing` nunca como `observed`.
