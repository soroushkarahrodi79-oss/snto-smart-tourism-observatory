# Plantillas GEE — Red de Parques Nacionales OAPN

Scripts **listos para pegar** en el [GEE Code Editor](https://code.earthengine.google.com)
para extraer series temporales NDVI/NDMI/EVI mensuales (Sentinel-2, 2021–2026)
de cada Parque Nacional de la Red OAPN, replicando el modelo validado con el
**PNSG** en v1.1.0 (`scripts/gee_code_editor_pnsg.js`).

> Generados por `scripts/build_gee_oapn_templates.py`. **Guadarrama no está aquí**:
> ya resuelto en v1.1.0. Estos archivos son material preparado para **futuras
> actualizaciones** de SNTO (incorporación de nuevos territorios OAPN).

## Qué hace cada `.js`

Idéntico al pipeline PNSG, con dos generalizaciones:

1. **Assets = cartografía oficial OAPN** (GeoServer SIGRED, WFS): cada itinerario
   oficial → asset `senderismo`; cada ruta bici → asset `ciclismo`. Geometrías
   simplificadas a ~12 m (Douglas-Peucker) y redondeadas a 5 decimales; luego se
   bufferean ±30 m, así que no se pierde fidelidad útil para muestreo Sentinel-2.
2. **`.filterBounds(assets)` en vez de `MGRS_TILE` fijo** → soporta parques que
   cruzan varias teselas Sentinel-2 (Sierra Nevada, Picos, Ordesa, Doñana…).

Salida: un CSV por parque a Google Drive → carpeta `SNTO_exports`,
columnas `asset_id, nombre, year, month, date, ndvi, ndmi, evi, ndvi_p25,
ndvi_p75, ndvi_stdDev, data_source`.

## Inventario (15 parques)

| Archivo | Parque Nacional | Assets (sender. + bici) | Tesela(s) S2 orientativa | Notas |
|---|---|---:|---|---|
| `pn_aiguestortes.js` | Aigüestortes i Estany de Sant Maurici | 61 (60+1) | 31TCH | Alta montaña, nieve estacional |
| `pn_cabrera.js` | Archipiélago de Cabrera (M-T) | 10 (10+0) | 31SDD | Marítimo-terrestre, mucho mar enmascarado |
| `pn_cabaneros.js` | Cabañeros | 23 (21+2) | 30SUJ / 30SVJ | Bosque mediterráneo |
| `pn_taburiente.js` | Caldera de Taburiente | 24 (22+2) | 28RBS | Canarias (UTM 28N) |
| `pn_donana.js` | Doñana | 38 (31+7) | 29SQA / 29SQB | Marisma, fuerte estacionalidad |
| `pn_garajonay.js` | Garajonay | 23 (20+3) | 28RBS | Canarias, laurisilva, nubosidad alta |
| `pn_islas_atlanticas.js` | Islas Atlánticas de Galicia (M-T) | 19 (19+0) | 29TNG / 29TNH | Islas dispersas, nubosidad atlántica |
| `pn_monfrague.js` | Monfragüe | 21 (13+8) | 29SQD / 30STK | Dehesa mediterránea · ✅ **validado v1.2.0** |
| `pn_ordesa.js` | Ordesa y Monte Perdido | 55 (55+0) | 30TYN / 31TBH | Alta montaña, nieve |
| `pn_picos_europa.js` | Picos de Europa | 47 (47+0) | 30TUN / 30TUP | Multi-tesela, nieve |
| `pn_sierra_nevada.js` | Sierra Nevada | 53 (39+14) | 30SVF/30SWF/30SVG/30SWG | Multi-tesela, archivo grande (~534 KB) |
| `pn_sierra_nieves.js` | Sierra de las Nieves | 11 (11+0) | 30SUF | Parque más reciente |
| `pn_tablas_daimiel.js` | Tablas de Daimiel | 5 (5+0) | 30SVJ | Humedal, NDMI muy informativo · ✅ **validado v1.2.0** |
| `pn_teide.js` | Teide | 54 (54+0) | 28RCS | Canarias, alta cota, roca volcánica |
| `pn_timanfaya.js` | Timanfaya | 7 (7+0) | 28RES / 28RFS | Canarias, malpaís, NDVI bajo natural |

## Flujo de trabajo (igual que PNSG)

1. Abre [code.earthengine.google.com](https://code.earthengine.google.com) y pega
   el contenido del `.js` del parque.
2. **Run** → revisa en consola `Assets cargados` y la muestra de filas.
3. Pestaña **Tasks** → ejecuta el export. El CSV aparece en Drive `SNTO_exports`
   como `<key>_gee_timeseries.csv`.
4. Descarga el CSV e intégralo igual que la serie PNSG:
   `src/platform/satellite_trends.py` + análisis Mann-Kendall
   (`src/time_series/mann_kendall.py`).

## Regenerar / actualizar

```bash
python scripts/build_gee_oapn_templates.py            # todos
python scripts/build_gee_oapn_templates.py donana teide   # subconjunto
```

Descarga las capas de uso público de la red completa desde el WFS de OAPN y
reescribe los `.js`. Si OAPN cambia los nombres de capa o el atributo
`"Nombre Parque"`, ajusta `WFS_*` / `PARKS` en el generador.

## Consideraciones por bioma

- **Canarias / marítimo-terrestres** (Teide, Taburiente, Garajonay, Timanfaya,
  Cabrera, Islas Atlánticas): mayor nubosidad y/o píxeles de agua; la máscara SCL
  ya descarta agua/nube, pero algunos meses quedarán sin dato (se filtran por
  `ndvi` nulo). Timanfaya tiene NDVI naturalmente bajo (malpaís) — no es degradación.
- **Alta montaña** (Aigüestortes, Ordesa, Picos, Sierra Nevada): nieve estacional
  enmascarada como SCL=11; esperar huecos invernales en la serie.
- **Humedales** (Tablas de Daimiel, Doñana): NDMI es el índice más diagnóstico
  del estado hídrico; vigilar inversión estacional.
