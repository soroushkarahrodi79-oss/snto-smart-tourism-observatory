# SNTO · Campaña de validación PNSG — DEMO académico

Paquete fuente canónico y reproducible para la futura configuración, operada
por el propietario, de Survey123, Field Maps, Web Map y Experience Builder.
No contiene credenciales, envíos de campo, fotografías ni adjuntos, y no
modifica el núcleo científico de SNTO.

**Base de reconstrucción:** repositorio SNTO `2.1.0.dev0`, commit
`6284091460e9271bb8c1c4dbf7ab9aa31ea48d45`.

**Estado:** paquete fuente de demostración. La capa piloto y el Web Map se
publicaron de forma privada el 2026-07-13; el servicio Survey123 y la app
Experience Builder todavía no están creados/publicados desde este paquete.
Nada aquí constituye sincronización en vivo ni preparación para producción.

## Contenido

- `pilot_assets.geojson`: dos activos prioritarios convertidos a puntos de referencia WGS84 para una única capa ArcGIS.
- `field_observations_seed.csv`: cuatro parcelas previstas, con las columnas canónicas de SNTO y campos adicionales de gobierno.
- `SNTO_DEMO_PNSG_FieldValidation.xlsx`: XLSForm de Survey123 Connect para capturar las cuatro parcelas con controles de rango, GPS, fotografías y trazabilidad DEMO.
- `PROVENANCE.md`: hashes de origen, transformaciones, procedencia, privacidad
  y reproducción.

El XLSForm contiene únicamente las hojas `survey`, `choices` y `settings`.
La documentación se mantiene en este archivo Markdown para evitar que
Survey123 Connect interprete una hoja auxiliar como parte del formulario.

## Advertencias

- Todo elemento que se cree con estos archivos debe llevar el prefijo `SNTO_DEMO_`.
- El GeoJSON es un **snapshot manual**, no un servicio en vivo. Contiene
  tendencia Sentinel-2 real, pero no evidencia de campo ni un veredicto sobre
  la causa de la señal.
- Las filas del CSV están en estado `planned` y evidencia `missing`; no son observaciones de campo.
- Las coordenadas del CSV son marcadores provisionales de demostración:
  `missing` no significa cero y `planned` no significa observado. La posición
  real debe capturarse con GPS a la distancia definida y dentro del mismo
  hábitat comparable.
- En el GeoJSON, El Nevero conserva el punto oficial de la fuente. El punto de
  Maliciosa–Porrones es una referencia aproximada dentro de la huella
  poligonal oficial; no sustituye esa geometría.
- `synthetic` identifica una prueba; nunca se convierte automáticamente en
  `real`.
- No cambiar los nombres de las primeras catorce columnas: son el contrato de importación de `src.validation.io`.
- No compartir públicamente las capas durante el desarrollo.
- No afirmar validación de campo completada ni acuerdo satélite↔campo.

## Documentación relacionada

- [Hoja de ruta operativa de captura](../../../docs/arcgis/field-validation-demo-roadmap.md)
- [Arquitectura Experience Builder de Fase 2A](../../../docs/integrations/arcgis/experience-builder/README.md)

## Orden de publicación previsto

1. Crear el grupo privado `SNTO — Validación de campo DEMO`.
2. Publicar `pilot_assets.geojson` como `SNTO_DEMO_PNSG_Assets`.
3. Comprobar que se publican exactamente dos puntos.
4. Mantener la capa de activos como solo lectura.
5. Crear la capa de observaciones desde Survey123 Connect en la Fase 3; el CSV funciona como diccionario y semilla, no como sustituto del formulario.

## Comprobaciones del GeoJSON

| Activo | Tendencia NDVI | p | Pendiente de Sen | Lectura prudente |
|---|---:|---:|---:|---|
| Maliciosa–Porrones | decreciente | 0.0000 | -0.000371 | candidato prioritario a inspección |
| El Nevero | creciente | 0.0113 | 0.000775 | contraste favorable; mantener seguimiento |

Ambas tendencias son significativas y sus intervalos de confianza excluyen cero. El año 2026 es parcial y no debe interpretarse como un año completo.

Los valores proceden del snapshot preparado el 2026-07-13 sobre observaciones
mensuales 2021-01-01–2026-06-01. La inspección de campo sigue pendiente.

## Estado permitido de la evidencia

| Estado | Uso |
|---|---|
| `missing` | parcela prevista, sin medición |
| `synthetic` | prueba de escritorio o móvil sin campaña real |
| `real` | medición efectivamente recogida en campo |

Nunca cambiar automáticamente `synthetic` a `real`.
