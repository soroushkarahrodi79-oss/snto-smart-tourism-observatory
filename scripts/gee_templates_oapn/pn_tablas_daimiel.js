// ============================================================================
// SNTO — Extracción NDVI/NDMI/EVI mensual 2021–2026 · Parque Nacional de las Tablas de Daimiel
// GENERADO por scripts/build_gee_oapn_templates.py — pegar en
// code.earthengine.google.com (replica el modelo validado del PNSG, v1.1.0).
// ----------------------------------------------------------------------------
// 5 assets reales = itinerarios (senderismo) + rutas bici (ciclismo)
// de la cartografía oficial OAPN (GeoServer SIGRED).
// Ventana: ene-2021 .. jun-2026 (2026 parcial; el análisis lo trata aparte).
// Tesela(s) Sentinel-2 orientativa(s): 30SVJ (el script usa filterBounds,
// así que NO necesita la tesela exacta y soporta parques multi-tesela).
// Exporta un CSV a Google Drive → carpeta "SNTO_exports".
// ============================================================================

// ── Configuración ───────────────────────────────────────────────────────────
var START = ee.Date.fromYMD(2021, 1, 1);
var N_MONTHS = 66;            // 2021-01 .. 2026-06 (2026 parcial)
var POINT_BUFFER_M = 50;
var LINE_BUFFER_M  = 30;
var SCALE_M = 10;

// ── Assets (embebidos desde cartografía oficial OAPN, simplificados ~12 m) ───
var rawAssets = ee.FeatureCollection([
  ee.Feature(ee.Geometry.LineString([[-3.69751, 39.13797], [-3.69747, 39.13867], [-3.69621, 39.14118], [-3.69557, 39.14074], [-3.6943, 39.14084], [-3.69473, 39.14193], [-3.6943, 39.14084], [-3.69288, 39.14118], [-3.69267, 39.14101], [-3.69227, 39.14106], [-3.69203, 39.1412], [-3.69225, 39.14168], [-3.69203, 39.1412], [-3.69109, 39.14162], [-3.69008, 39.14239], [-3.68939, 39.14364], [-3.68975, 39.14375], [-3.68939, 39.14364], [-3.68839, 39.14419], [-3.68823, 39.14481], [-3.68888, 39.14505], [-3.68823, 39.14481], [-3.68808, 39.1453], [-3.68758, 39.14564], [-3.68679, 39.14721]]), {"asset_id": "pn_tablas_daimiel_senderismo_la_torre_de_prado_ancho_000", "nombre": "La Torre de Prado Ancho", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-3.69752, 39.13797], [-3.69751, 39.1378], [-3.69798, 39.13758], [-3.6995, 39.13759], [-3.69995, 39.13734], [-3.69969, 39.13698], [-3.69995, 39.13734], [-3.70095, 39.13716], [-3.70092, 39.13702], [-3.70119, 39.13722], [-3.70296, 39.13718], [-3.70301, 39.13681], [-3.70296, 39.13718], [-3.70507, 39.1374], [-3.70569, 39.13712], [-3.70587, 39.13649], [-3.70571, 39.13637], [-3.70637, 39.13569], [-3.70553, 39.13507], [-3.70446, 39.13644], [-3.70474, 39.13702], [-3.70436, 39.13739], [-3.70361, 39.13733], [-3.70368, 39.13681], [-3.70321, 39.13599], [-3.70309, 39.13527], [-3.70349, 39.13517], [-3.70309, 39.13527], [-3.70289, 39.13496], [-3.70189, 39.13477], [-3.70136, 39.13537], [-3.7002, 39.13576], [-3.70029, 39.13589], [-3.7002, 39.13576], [-3.69861, 39.13618], [-3.69833, 39.13707], [-3.6975, 39.1378], [-3.6975, 39.13797]]), {"asset_id": "pn_tablas_daimiel_senderismo_la_isla_del_pan_001", "nombre": "La Isla del Pan", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-3.69753, 39.13798], [-3.69772, 39.1385], [-3.69823, 39.13848], [-3.699, 39.13889], [-3.69918, 39.13948], [-3.69907, 39.13967], [-3.69918, 39.13948], [-3.69942, 39.13958], [-3.69918, 39.13948], [-3.69901, 39.13889], [-3.6993, 39.13834], [-3.69938, 39.13767]]), {"asset_id": "pn_tablas_daimiel_senderismo_la_laguna_de_aclimatacion_002", "nombre": "La Laguna de Aclimatación", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-3.69749, 39.13797], [-3.69749, 39.13779], [-3.69831, 39.13708], [-3.6986, 39.13618], [-3.69778, 39.13515], [-3.69776, 39.13446], [-3.69818, 39.13374], [-3.69764, 39.13277], [-3.69759, 39.13215], [-3.69775, 39.13205], [-3.69759, 39.13214], [-3.69738, 39.13148], [-3.6977, 39.13102]]), {"asset_id": "pn_tablas_daimiel_senderismo_la_laguna_permanente_003", "nombre": "La Laguna Permanente", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-3.69212, 39.13208], [-3.69321, 39.13147], [-3.69348, 39.13071], [-3.69273, 39.13006], [-3.69145, 39.13011], [-3.69105, 39.12987], [-3.69155, 39.12901]]), {"asset_id": "pn_tablas_daimiel_senderismo_molino_de_molemocho_004", "nombre": "Molino de Molemocho", "geom_type": "LINESTRING", "category": "senderismo"}),
]);

// Buffer según tipo de geometría (puntos y líneas) server-side
var assets = rawAssets.map(function(f) {
  var gt = ee.String(f.get('geom_type'));
  var isLine = ee.Boolean(gt.equals('LINESTRING')).or(ee.Boolean(gt.equals('MULTILINESTRING')));
  var geom = ee.Geometry(ee.Algorithms.If(
    gt.equals('POINT'), f.geometry().buffer(POINT_BUFFER_M),
    ee.Algorithms.If(isLine, f.geometry().buffer(LINE_BUFFER_M), f.geometry())
  ));
  return f.setGeometry(geom);
});

print('Assets cargados:', assets.size());
Map.centerObject(assets, 11);
Map.addLayer(assets, {color: 'red'}, 'Parque Nacional de las Tablas de Daimiel assets');

// ── Colección Sentinel-2 + máscara SCL + índices ────────────────────────────
function maskAndIndex(image) {
  var scl = image.select('SCL');
  var mask = scl.neq(0).and(scl.neq(1)).and(scl.neq(3))
    .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  var sr = image.select(['B2', 'B4', 'B8', 'B11']).divide(10000);
  var ndvi = sr.normalizedDifference(['B8', 'B4']).rename('ndvi');
  var ndmi = sr.normalizedDifference(['B8', 'B11']).rename('ndmi');
  var evi = sr.expression(
    '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
    {NIR: sr.select('B8'), RED: sr.select('B4'), BLUE: sr.select('B2')}
  ).rename('evi');
  return sr.addBands([ndvi, ndmi, evi]).updateMask(mask)
           .copyProperties(image, ['system:time_start']);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(assets)
  .filterDate(START, START.advance(N_MONTHS, 'month'))
  .map(maskAndIndex);

// ── Estadística mensual por asset (server-side, sin getInfo) ─────────────────
var months = ee.List.sequence(0, N_MONTHS - 1);

var perMonth = months.map(function(m) {
  m = ee.Number(m);
  var start = START.advance(m, 'month');
  var end = start.advance(1, 'month');
  var composite = s2.filterDate(start, end).median();

  var reducer = ee.Reducer.mean()
    .combine({reducer2: ee.Reducer.percentile([25, 75]), sharedInputs: true})
    .combine({reducer2: ee.Reducer.stdDev(), sharedInputs: true});

  var stats = composite.select(['ndvi', 'ndmi', 'evi']).reduceRegions({
    collection: assets,
    reducer: reducer,
    scale: SCALE_M
  });

  return stats.map(function(f) {
    return f.setGeometry(null).set({
      year: start.get('year'),
      month: start.get('month'),
      date: start.format('YYYY-MM-dd'),
      ndvi: f.get('ndvi_mean'),
      ndmi: f.get('ndmi_mean'),
      evi:  f.get('evi_mean'),
      data_source: 'GEE:S2_SR_HARMONIZED'
    });
  });
});

var flat = ee.FeatureCollection(perMonth).flatten();

// Filtrar meses sin datos (NDVI nulo por nubosidad total)
flat = flat.filter(ee.Filter.notNull(['ndvi']));

print('Filas estimadas (puede tardar):', flat.size());
print('Muestra (primeras 5 filas):', flat.limit(5));

// ── Export a Google Drive ────────────────────────────────────────────────────
Export.table.toDrive({
  collection: flat,
  description: 'pn_tablas_daimiel_indices_multiyear',
  folder: 'SNTO_exports',
  fileNamePrefix: 'pn_tablas_daimiel_gee_timeseries',
  fileFormat: 'CSV',
  selectors: [
    'asset_id', 'nombre', 'category', 'year', 'month', 'date',
    'ndvi', 'ndmi', 'evi',
    'ndvi_p25', 'ndvi_p75', 'ndvi_stdDev',
    'data_source'
  ]
});
