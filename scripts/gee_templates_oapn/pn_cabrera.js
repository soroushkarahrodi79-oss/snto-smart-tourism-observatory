// ============================================================================
// SNTO — Extracción NDVI/NDMI/EVI mensual 2021–2026 · Parque Nacional Marítimo-Terrestre del Archipiélago de Cabrera
// GENERADO por scripts/build_gee_oapn_templates.py — pegar en
// code.earthengine.google.com (replica el modelo validado del PNSG, v1.1.0).
// ----------------------------------------------------------------------------
// 10 assets reales = itinerarios (senderismo) + rutas bici (ciclismo)
// de la cartografía oficial OAPN (GeoServer SIGRED).
// Ventana: ene-2021 .. jun-2026 (2026 parcial; el análisis lo trata aparte).
// Tesela(s) Sentinel-2 orientativa(s): 31SDD (el script usa filterBounds,
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
  ee.Feature(ee.Geometry.LineString([[2.93417, 39.15129], [2.93475, 39.15059], [2.93593, 39.15016], [2.93602, 39.14958], [2.93688, 39.14865], [2.93608, 39.14787], [2.93593, 39.14742], [2.93642, 39.1467], [2.93749, 39.14586], [2.9373, 39.14542], [2.93737, 39.14421], [2.93988, 39.14101], [2.94056, 39.14056], [2.94138, 39.1404], [2.94182, 39.13994]]), {"asset_id": "pn_cabrera_senderismo_un_paseo_por_la_historia_de_cabrera_000", "nombre": "Un paseo por la historia de Cabrera", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93417, 39.15129], [2.93475, 39.15059], [2.93593, 39.15016], [2.93602, 39.14958], [2.93688, 39.14865], [2.9361, 39.14789], [2.93593, 39.14747], [2.93642, 39.1467], [2.93751, 39.1458], [2.9373, 39.14542], [2.93737, 39.14421], [2.937, 39.14387], [2.93637, 39.1438], [2.93515, 39.14423], [2.93285, 39.14438], [2.93208, 39.14403], [2.93179, 39.1432], [2.93047, 39.14304], [2.92933, 39.14215], [2.92906, 39.14219], [2.92878, 39.14232], [2.92892, 39.1429], [2.92869, 39.14339], [2.92814, 39.1437], [2.92834, 39.14405], [2.92796, 39.14521], [2.92658, 39.14551], [2.92573, 39.14495], [2.92504, 39.14501], [2.92473, 39.14553], [2.92367, 39.14622], [2.92287, 39.1454], [2.92405, 39.14446], [2.92298, 39.1445], [2.92236, 39.14361], [2.9222, 39.14281], [2.92179, 39.14252], [2.91954, 39.14249], [2.91936, 39.14288], [2.91942, 39.14409], [2.91903, 39.14412], [2.91894, 39.14389]]), {"asset_id": "pn_cabrera_senderismo_na_picamosques_001", "nombre": "Na Picamosques", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93133, 39.14321], [2.93179, 39.1432], [2.93209, 39.14404], [2.93287, 39.14439], [2.93515, 39.14423], [2.93639, 39.1438], [2.937, 39.14387], [2.93737, 39.14421], [2.9373, 39.14542], [2.93749, 39.14586], [2.93642, 39.1467], [2.93593, 39.14742], [2.93608, 39.14787], [2.93688, 39.14865], [2.93602, 39.14958], [2.93593, 39.15016], [2.93475, 39.15059], [2.93417, 39.15129]]), {"asset_id": "pn_cabrera_senderismo_visita_arqueologica_002", "nombre": "Visita arqueológica", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93417, 39.15129], [2.93475, 39.15059], [2.93593, 39.15016], [2.93602, 39.14958], [2.93688, 39.14865], [2.93608, 39.14787], [2.93593, 39.14742], [2.93642, 39.1467], [2.93749, 39.14586], [2.9373, 39.14542], [2.93737, 39.14421], [2.937, 39.14387], [2.93639, 39.1438], [2.93515, 39.14423], [2.93285, 39.14438], [2.93208, 39.14403], [2.93179, 39.1432], [2.93047, 39.14304], [2.92946, 39.14229], [2.92902, 39.14158], [2.92881, 39.14013], [2.93032, 39.13813], [2.92967, 39.13814], [2.9299, 39.13804], [2.92878, 39.13755], [2.92896, 39.13724], [2.92944, 39.13733], [2.92887, 39.13678], [2.92941, 39.13689], [2.92871, 39.13624], [2.92857, 39.1358], [2.92745, 39.13512], [2.92728, 39.13485], [2.92768, 39.13507], [2.92835, 39.13492], [2.92751, 39.13309], [2.92739, 39.13351], [2.92698, 39.13287], [2.92729, 39.13239], [2.92677, 39.13239], [2.928, 39.1319], [2.92695, 39.13162], [2.92657, 39.13111], [2.92613, 39.13127], [2.92515, 39.13111], [2.92472, 39.13078], [2.9245, 39.12998], [2.92402, 39.12994], [2.92366, 39.13028], [2.92376, 39.12979], [2.92416, 39.12949], [2.92367, 39.12965], [2.92331, 39.13002], [2.92348, 39.12958], [2.92315, 39.13005], [2.92351, 39.12929], [2.92288, 39.12988], [2.92297, 39.12963], [2.92273, 39.12987], [2.92287, 39.12964], [2.92253, 39.12982], [2.92298, 39.12926], [2.92204, 39.1296], [2.92259, 39.1291], [2.92183, 39.12936]]), {"asset_id": "pn_cabrera_senderismo_el_faro_de_l_enciola_003", "nombre": "El Faro de L'Enciola", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93417, 39.15129], [2.93475, 39.15059], [2.93593, 39.15016], [2.93602, 39.14958], [2.93686, 39.14868], [2.93602, 39.14778], [2.93596, 39.14733], [2.93642, 39.1467], [2.93749, 39.14586], [2.9373, 39.14542], [2.93737, 39.14421], [2.9401, 39.14083], [2.94068, 39.14055], [2.9408, 39.14083], [2.94202, 39.14117], [2.94237, 39.14095], [2.94244, 39.14056], [2.94296, 39.14104], [2.94246, 39.14171], [2.94118, 39.14187], [2.94075, 39.14248], [2.94087, 39.14265], [2.94124, 39.14244], [2.94251, 39.1426], [2.94424, 39.14196], [2.94538, 39.14189], [2.94528, 39.14424]]), {"asset_id": "pn_cabrera_senderismo_la_miranda_004", "nombre": "La Miranda", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93357, 39.15144], [2.93314, 39.15131], [2.93307, 39.15178], [2.93276, 39.15176], [2.93292, 39.15226], [2.93268, 39.15231], [2.93301, 39.15283], [2.93267, 39.15283], [2.93277, 39.15305], [2.93246, 39.15333]]), {"asset_id": "pn_cabrera_senderismo_el_castillo_de_cabrera_005", "nombre": "El Castillo de Cabrera", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93417, 39.15129], [2.93475, 39.15059], [2.93593, 39.15016], [2.93602, 39.14958], [2.93686, 39.14868], [2.93602, 39.14778], [2.93596, 39.14733], [2.93642, 39.1467], [2.93749, 39.14586], [2.9373, 39.14542], [2.93737, 39.14421], [2.94009, 39.14084], [2.94068, 39.14055], [2.9408, 39.14083], [2.94202, 39.14117], [2.94236, 39.14096], [2.94249, 39.14059], [2.94296, 39.14106], [2.94249, 39.14168], [2.94122, 39.14184], [2.94075, 39.14249], [2.94088, 39.14265], [2.94124, 39.14244], [2.94253, 39.14259], [2.94424, 39.14196], [2.9455, 39.14189], [2.94776, 39.14041], [2.9484, 39.13954], [2.95054, 39.13881], [2.95095, 39.13808], [2.951, 39.13748], [2.9516, 39.13652], [2.95234, 39.13338], [2.95229, 39.13241], [2.95114, 39.13184], [2.94924, 39.13238], [2.94708, 39.13237], [2.9459, 39.13261], [2.94405, 39.1324], [2.94312, 39.13207], [2.94091, 39.13265], [2.93993, 39.13252], [2.939, 39.13303], [2.93904, 39.1334], [2.94023, 39.13356], [2.9416, 39.13471], [2.93987, 39.13672], [2.939, 39.13811], [2.93871, 39.1395], [2.93903, 39.1403], [2.93984, 39.14106], [2.93737, 39.14421], [2.9373, 39.14542], [2.93749, 39.14586], [2.93641, 39.1467], [2.93593, 39.14742], [2.93608, 39.14787], [2.93688, 39.14865], [2.93602, 39.14958], [2.93593, 39.15016], [2.93474, 39.15059], [2.93417, 39.15129]]), {"asset_id": "pn_cabrera_senderismo_serra_del_canal_de_ses_figueres_006", "nombre": "Serra del Canal de ses Figueres", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93417, 39.15129], [2.93475, 39.15059], [2.93593, 39.15016], [2.93602, 39.14958], [2.93686, 39.14868], [2.93602, 39.14778], [2.93596, 39.14733], [2.93642, 39.1467], [2.93749, 39.14586], [2.9373, 39.14542], [2.93737, 39.14421], [2.94009, 39.14084], [2.94068, 39.14055], [2.9408, 39.14083], [2.94202, 39.14117], [2.94237, 39.14095], [2.94244, 39.14056], [2.94296, 39.14104], [2.94246, 39.14171], [2.94118, 39.14187], [2.94075, 39.14248], [2.94089, 39.14265], [2.94124, 39.14244], [2.94253, 39.14259], [2.94463, 39.14188], [2.94537, 39.142], [2.94733, 39.14145], [2.94901, 39.14067], [2.94959, 39.14119], [2.94995, 39.14211], [2.95079, 39.14289], [2.9506, 39.14353], [2.95114, 39.14393], [2.95106, 39.14463], [2.95124, 39.14502], [2.95238, 39.14595], [2.95322, 39.14706], [2.95351, 39.1483], [2.9544, 39.14824], [2.95537, 39.14894], [2.95546, 39.1492], [2.95525, 39.14986], [2.95539, 39.15028], [2.95641, 39.15108], [2.95736, 39.15279], [2.95697, 39.15397], [2.9569, 39.15505], [2.95593, 39.1537], [2.95508, 39.15295], [2.95388, 39.15239], [2.95361, 39.15204], [2.95166, 39.15189], [2.9518, 39.15151], [2.9509, 39.15059], [2.95064, 39.14979], [2.95008, 39.14935], [2.94981, 39.14831], [2.94908, 39.1479], [2.94728, 39.14798], [2.94647, 39.14778], [2.94502, 39.14731], [2.94474, 39.14687], [2.94341, 39.14685], [2.94177, 39.14608], [2.94132, 39.14679], [2.94211, 39.14815], [2.94118, 39.14925], [2.93911, 39.14908], [2.93829, 39.14942], [2.93681, 39.14959], [2.93588, 39.1502], [2.93475, 39.15059], [2.93417, 39.15129]]), {"asset_id": "pn_cabrera_senderismo_ses_sitges_007", "nombre": "Ses Sitges", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.93606, 39.14438], [2.9348, 39.14481]]), {"asset_id": "pn_cabrera_senderismo_fondo_marino_cabrera_008", "nombre": "Fondo marino Cabrera", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[2.92735, 39.13475], [2.92738, 39.13506], [2.92857, 39.1358], [2.92871, 39.13624], [2.92941, 39.13689], [2.92887, 39.13678], [2.92944, 39.13733], [2.92896, 39.13724], [2.92878, 39.13755], [2.9299, 39.13804], [2.92967, 39.13814], [2.93032, 39.13813], [2.92881, 39.14013], [2.92902, 39.14158], [2.92946, 39.14229], [2.93047, 39.14304], [2.93179, 39.1432], [2.93208, 39.14403], [2.93285, 39.14438], [2.93515, 39.14423], [2.93639, 39.1438], [2.937, 39.14387], [2.93737, 39.14421], [2.9373, 39.14542], [2.93749, 39.14586], [2.93642, 39.1467], [2.93593, 39.14742], [2.93608, 39.14787], [2.93689, 39.14862], [2.93602, 39.14958], [2.93594, 39.15014], [2.93475, 39.15059], [2.93421, 39.15129], [2.93353, 39.15127], [2.93334, 39.15113], [2.93328, 39.15068]]), {"asset_id": "pn_cabrera_senderismo_es_coll_roig_un_balcon_hacia_enciola_009", "nombre": "Es Coll Roig, un balcón hacia Enciola", "geom_type": "LINESTRING", "category": "senderismo"}),
]);

// Buffer según tipo de geometría (puntos y líneas) server-side
var assets = rawAssets.map(function(f) {
  var gt = ee.String(f.get('geom_type'));
  var isLine = gt.equals('LINESTRING').or(gt.equals('MULTILINESTRING'));
  var geom = ee.Geometry(ee.Algorithms.If(
    gt.equals('POINT'), f.geometry().buffer(POINT_BUFFER_M),
    ee.Algorithms.If(isLine, f.geometry().buffer(LINE_BUFFER_M), f.geometry())
  ));
  return f.setGeometry(geom);
});

print('Assets cargados:', assets.size());
Map.centerObject(assets, 11);
Map.addLayer(assets, {color: 'red'}, 'Parque Nacional Marítimo-Terrestre del Archipiélago de Cabrera assets');

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
  description: 'pn_cabrera_indices_multiyear',
  folder: 'SNTO_exports',
  fileNamePrefix: 'pn_cabrera_gee_timeseries',
  fileFormat: 'CSV',
  selectors: [
    'asset_id', 'nombre', 'category', 'year', 'month', 'date',
    'ndvi', 'ndmi', 'evi',
    'ndvi_p25', 'ndvi_p75', 'ndvi_stdDev',
    'data_source'
  ]
});
