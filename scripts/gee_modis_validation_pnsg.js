// ============================================================================
// SNTO — Referencia INDEPENDIENTE MODIS para validación cruzada del NDVI (PNSG)
// Fase C · complementa scripts/gee_code_editor_pnsg.js (Sentinel-2).
// ----------------------------------------------------------------------------
// Produce NDVI MENSUAL 2021–2026 de MODIS MOD13Q1 (Terra, 250 m, 16 días) para
// LOS MISMOS 21 activos del PNSG, con asset_id/year/month idénticos, de modo que
// el CSV resultante empareja 1:1 con la serie Sentinel-2 y puede pasarse a
// src/validation/cross_sensor.py (cross_sensor_agreement).
//
// MODIS es un sensor INDEPENDIENTE de Sentinel-2 (Terra/Aqua vs Copernicus), por
// lo que es una verificación real de que la señal S2 no es un artefacto de un
// único instrumento. (Copernicus HR-VPP NO sirve: deriva del propio Sentinel-2.)
//
// CAVEAT DE RESOLUCIÓN (declarado, no oculto): MOD13Q1 es 250 m; varios activos
// son puntos/líneas con buffer de 30–50 m (sub-píxel MODIS). Frente a MODIS la
// validación habla del NIVEL y TENDENCIA del NDVI a escala de vecindario de
// píxel, no del detalle intra-activo. Para concordancia espacial a escala de
// activo, sustituir la colección por Landsat C2 (30 m, también independiente).
//
// USO: pegar en code.earthengine.google.com. En el bloque marcado, PEGAR el
// mismo `rawAssets` de scripts/gee_code_editor_pnsg.js (no se duplica aquí para
// evitar que las geometrías deriven entre ambos scripts).
// ============================================================================

// ── Configuración (idéntica a la de S2 para emparejar) ───────────────────────
var START = ee.Date.fromYMD(2021, 1, 1);
var N_MONTHS = 66;                   // 2021-01 .. 2026-06 (2026 parcial)
var POINT_BUFFER_M = 50;
var LINE_BUFFER_M  = 30;
var SCALE_M = 250;                   // resolución nativa MOD13Q1

// ── Assets PNSG ──────────────────────────────────────────────────────────────
// >>> PEGAR AQUÍ el bloque `var rawAssets = ee.FeatureCollection([...]);` de
// >>> scripts/gee_code_editor_pnsg.js (21 activos con asset_id/geom_type).
// var rawAssets = ee.FeatureCollection([ ... ]);

// Buffer según tipo de geometría (idéntico a S2)
var assets = rawAssets.map(function(f) {
  var gt = ee.String(f.get('geom_type'));
  var isLine = gt.equals('LINESTRING').or(gt.equals('MULTILINESTRING'));
  var geom = ee.Geometry(ee.Algorithms.If(
    gt.equals('POINT'), f.geometry().buffer(POINT_BUFFER_M),
    ee.Algorithms.If(isLine, f.geometry().buffer(LINE_BUFFER_M), f.geometry())
  ));
  return f.setGeometry(geom);
});

// ── MODIS MOD13Q1: NDVI escalado + máscara de calidad ────────────────────────
function prepModis(image) {
  // SummaryQA: 0 = good, 1 = marginal → conservamos 0 y 1, descartamos nube/nieve.
  var qa = image.select('SummaryQA');
  var mask = qa.lte(1);
  var ndvi = image.select('NDVI').multiply(0.0001).rename('ndvi');
  return ndvi.updateMask(mask)
             .copyProperties(image, ['system:time_start']);
}

var modis = ee.ImageCollection('MODIS/061/MOD13Q1')
  .filterBounds(assets)
  .filterDate(START, START.advance(N_MONTHS, 'month'))
  .map(prepModis);

// ── Estadística mensual por activo (server-side) ─────────────────────────────
var months = ee.List.sequence(0, N_MONTHS - 1);

var perMonth = months.map(function(m) {
  m = ee.Number(m);
  var start = START.advance(m, 'month');
  var end = start.advance(1, 'month');
  var composite = modis.filterDate(start, end).mean();   // media de los 16-días del mes

  var stats = composite.select(['ndvi']).reduceRegions({
    collection: assets,
    reducer: ee.Reducer.mean(),
    scale: SCALE_M
  });

  return stats.map(function(f) {
    return f.setGeometry(null).set({
      year: start.get('year'),
      month: start.get('month'),
      date: start.format('YYYY-MM-dd'),
      ndvi_modis: f.get('mean'),
      data_source: 'GEE:MODIS/061/MOD13Q1'
    });
  });
});

var flat = ee.FeatureCollection(perMonth).flatten()
             .filter(ee.Filter.notNull(['ndvi_modis']));

print('Filas MODIS estimadas:', flat.size());
print('Muestra:', flat.limit(5));

// ── Export a Google Drive (empareja con pnsg_gee_timeseries.csv por asset/mes) ─
Export.table.toDrive({
  collection: flat,
  description: 'pnsg_modis_ndvi_validation',
  folder: 'SNTO_exports',
  fileNamePrefix: 'pnsg_modis_ndvi_2021_2026',
  fileFormat: 'CSV',
  selectors: ['asset_id', 'year', 'month', 'date', 'ndvi_modis', 'data_source']
});
