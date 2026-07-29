# Procedencia del paquete ArcGIS PNSG DEMO

## 1. Origen y base de reconstrucción

El paquete se reconstruyó desde el **respaldo externo verificado creado el
2026-07-29**. El respaldo se trató como inmutable y no se versiona dentro del
repositorio.

Base de código y datos usada para la reconciliación:

- commit: `6284091460e9271bb8c1c4dbf7ab9aa31ea48d45`;
- versión del repositorio: `2.1.0.dev0`;
- paquete de arquitectura Experience Builder:
  [`../../../docs/integrations/arcgis/experience-builder/README.md`](../../../docs/integrations/arcgis/experience-builder/README.md).

## 2. Disposición y hashes de origen

| Fuente del respaldo | SHA-256 original | Destino canónico | Acción |
|---|---|---|---|
| `arcgis/demo/pnsg/README.md` | `0ea3f04bb1ca2ffa20c6a3060433d7beb37f3ecceacb0c4bbf29f5e480c6b366` | `arcgis/demo/pnsg/README.md` | Normalizado: límites, coordenadas, versión y enlaces. |
| `arcgis/demo/pnsg/field_observations_seed.csv` | `28ad6ea70e6eb467334af48a524c9df0257762eacdc4c385e90fbb32bf73d14a` | `arcgis/demo/pnsg/field_observations_seed.csv` | Copiado byte-idéntico. |
| `arcgis/demo/pnsg/pilot_assets.geojson` | `f3b74e32f984c838554a07d30b17519e50078096f55617740096f90a18ae1250` | `arcgis/demo/pnsg/pilot_assets.geojson` | Normalizado; valores científicos y coordenadas conservados. |
| `arcgis/demo/pnsg/SNTO_DEMO_PNSG_FieldValidation.xlsx` | `2d3c4ef3c0f5459c73e2ad8b68fdf0d2c45ea67406811f0441679d819d37f7fa` | mismo path | Copiado byte-idéntico; fuente XLSForm única. |
| `docs/arcgis/field-validation-demo-roadmap.md` | `5d1c1854c90e4ae082a9e29352c2a3a07a1d7db30c4b1a58e01ac9f8abc6363e` | mismo path | Reconciliado con Fases 2A/2B y estado real. |
| `outputs/arcgis-field-validation-demo/SNTO_DEMO_PNSG_FieldValidation.xlsx` | `2d3c4ef3c0f5459c73e2ad8b68fdf0d2c45ea67406811f0441679d819d37f7fa` | — | Excluido: duplicado byte-idéntico del XLSForm canónico. |
| `BACKUP_MANIFEST.sha256` y `BACKUP_README.md` | metadatos del respaldo | — | Excluidos; los hashes necesarios se registran aquí. |

## 3. Normalización del GeoJSON

No se recalcularon ni inventaron tendencias. Se verificaron los dos
`asset_id`, geometrías y valores contra:

- `clean_assets/pnsg_assets.geojson`;
- `clean_assets/timeseries/analysis/mk_trends_pnsg.json`;
- `clean_assets/timeseries/pnsg_gee_timeseries.csv`.

La normalización actualizó únicamente metadatos compatibles con el contrato de
Fase 2A:

- `snto_version` y `source_version` → `2.1.0.dev0`;
- commit fuente;
- periodo observado `2021-01-01/2026-06-01`;
- estado de publicación privada;
- declaración explícita de snapshot manual, no vivo;
- `calculated_at = 2026-07-13`, conservando la fecha histórica de preparación.

Fue una normalización documental revisable; no se ejecutó un generador nuevo ni
se modificó `scripts/export_gis.py`.

## 4. Origen y licencia de los datos

- Geometría: cartografía oficial OAPN/PRUG PNSG reproyectada a WGS84 y
  simplificada por el pipeline del repositorio. Condición registrada:
  reutilización institucional con cita. Atribución:
  **«Cartografía oficial OAPN — Parque Nacional Sierra de Guadarrama»**.
- Tendencia: Sentinel-2 L2A (`GEE:S2_SR_HARMONIZED`), 2021-01 a 2026-06,
  procesada mediante NDVI desestacionalizado, Mann-Kendall y pendiente de Sen.
  Atribución: **«Contiene datos Copernicus Sentinel-2 modificados
  (2021–2026)»**.
- La licencia del repositorio no sustituye las condiciones de los proveedores
  de datos.

## 5. Clasificación de coordenadas

| Archivo / campo | Clasificación | Decisión |
|---|---|---|
| GeoJSON · El Nevero | oficial derivada: punto WGS84 de la fuente OAPN | Conservado. |
| GeoJSON · Maliciosa–Porrones | aproximada/provisional: punto representativo dentro del polígono oficial | Conservado para la demo; no sustituye el polígono. |
| CSV · cuatro filas | provisional: marcadores de planificación, no observaciones | Conservados por utilidad; deben sustituirse por GPS de campo. |
| XLSForm | sin coordenadas por defecto; GPS calculado al capturar | Conservado byte-idéntico. |

Las coordenadas corresponden a infraestructura pública del parque y no a
domicilios, lugares de trabajo de observadores ni envíos privados. No se
consideran sensibles en este paquete, pero cualquier captura futura de GPS,
foto o adjunto se clasifica como privada y permanece fuera de Git.

## 6. Madurez de evidencia y privacidad

- GeoJSON: evidencia satelital `real` en un snapshot de demostración; no es
  validación de campo ni prueba de causalidad.
- CSV: cuatro filas `qa_status=planned`, `evidence_class=missing`, sin
  mediciones ni personas identificadas.
- XLSForm: esquema vacío; `synthetic` es el valor de prueba por defecto. No
  contiene hojas de envíos, fotos, adjuntos, GPS capturado ni secretos.
- Clasificación del paquete: demostración académica compartible dentro del
  repositorio; futuras observaciones y adjuntos son privados.

El paquete **no contiene envíos reales de campo**.

## 7. Reproducción y comprobación

1. Usar el commit fuente indicado en §1.
2. Verificar los hashes de las fuentes byte-idénticas con una herramienta
   SHA-256.
3. Comparar los `asset_id` y geometrías del piloto con
   `clean_assets/pnsg_assets.geojson`.
4. Comparar `tau`, `p_value`, pendiente e intervalo de Sen con
   `clean_assets/timeseries/analysis/mk_trends_pnsg.json`.
5. Confirmar que el periodo mensual termina en `2026-06-01` en
   `clean_assets/timeseries/pnsg_gee_timeseries.csv`.
6. Abrir estructuralmente el XLSForm y comprobar que solo existen `survey`,
   `choices` y `settings`.
7. Ejecutar las validaciones focalizadas de CSV, GeoJSON, XLSForm, enlaces y
   seguridad antes de publicar cualquier item.

## 8. Limitaciones conocidas

- Solo hay dos activos y cuatro parcelas planificadas.
- No existe campaña de campo completada ni muestra suficiente.
- No existe concordancia satélite↔campo evaluada.
- El punto de Maliciosa–Porrones es aproximado.
- 2026 es un año parcial.
- El snapshot no se actualiza en vivo.
- La continuidad y transferibilidad de la cuenta educativa requieren
  confirmación del propietario.
- El servicio Survey123 y la app Experience Builder siguen pendientes.
