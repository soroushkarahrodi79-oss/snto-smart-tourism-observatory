# Plan de reversión (rollback)

> Ninguna reversión se ejecuta ni se crean copias en esta tarea. Como el item de
> Experience Builder **no existe**, el rollback es simple: lo único creado nuevo
> sería la app, que puede despublicarse o eliminarse.

## Estrategia preferida

- **Antes** de cualquier configuración: guardar una **copia** del Web Map
  existente si la UI de ArcGIS lo permite, y registrar los ajustes originales con
  capturas (simbología, popups, compartición, extent).
- **No** alterar esquemas alojados (campos/dominios/tipos).
- **No** eliminar items existentes.
- Reversión de la app: **despublicar o eliminar únicamente el item de Experience
  Builder recién creado**.
- Reversión del Web Map: restaurar desde los ajustes documentados o desde la
  copia guardada.

## Rollback por tipo de cambio

| Cambio | Reversión |
|---|---|
| Creación de la app EB | Eliminar/despublicar el item nuevo (no afecta a nada más) |
| Configuración del Web Map (popups/filtros/simbología) | Restaurar desde ajustes documentados o copia previa |
| Cambios de compartición | Revertir cada item al alcance previo registrado |
| Cambios de popup | Restaurar la configuración de popup documentada |
| Filtros (EB) | Eliminar el widget Filter / definition expression |
| Cambios de fuente de datos | Reconectar a la fuente original (Web Map/results view) |

## Garantías

- El **núcleo SNTO** funciona sin dependencia de ArcGIS.
- Los **datos de producción** y `main` no se ven afectados por ninguna acción de
  ArcGIS.
- El backup externo del material fuente
  (`SNTO_BACKUPS/arcgis-field-validation-demo-2026-07-29/`) permanece disponible.
- Ninguna acción destructiva sobre items existentes forma parte del plan.
