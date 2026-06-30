// ============================================================================
// SNTO — Extracción NDVI/NDMI/EVI mensual 2021–2026 · Parque Nacional Marítimo-Terrestre de las Islas Atlánticas de Galicia
// GENERADO por scripts/build_gee_oapn_templates.py — pegar en
// code.earthengine.google.com (replica el modelo validado del PNSG, v1.1.0).
// ----------------------------------------------------------------------------
// 19 assets reales = itinerarios (senderismo) + rutas bici (ciclismo)
// de la cartografía oficial OAPN (GeoServer SIGRED).
// Ventana: ene-2021 .. jun-2026 (2026 parcial; el análisis lo trata aparte).
// Tesela(s) Sentinel-2 orientativa(s): 29TNG / 29TNH (el script usa filterBounds,
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
  ee.Feature(ee.Geometry.LineString([[-8.94001, 42.37645], [-8.93898, 42.37646], [-8.93846, 42.37617], [-8.93766, 42.37609], [-8.93645, 42.37617], [-8.93521, 42.37572], [-8.93512, 42.37542]]), {"asset_id": "pn_islas_atlanticas_senderismo_union_ons_000", "nombre": "Unión-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.93659, 42.38432], [-8.93672, 42.38378], [-8.93546, 42.38316], [-8.93474, 42.38207]]), {"asset_id": "pn_islas_atlanticas_senderismo_union_ons_001", "nombre": "Unión-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.93529, 42.37399], [-8.93601, 42.37445], [-8.9357, 42.37533], [-8.93469, 42.37554], [-8.93477, 42.37659], [-8.93608, 42.37818], [-8.935, 42.38024], [-8.93489, 42.38187], [-8.93408, 42.38312], [-8.93212, 42.38435], [-8.93164, 42.38585], [-8.93081, 42.38694], [-8.92984, 42.38751], [-8.92965, 42.389], [-8.92862, 42.38965], [-8.9279, 42.3906], [-8.92718, 42.39081], [-8.92694, 42.3913], [-8.92584, 42.39165]]), {"asset_id": "pn_islas_atlanticas_senderismo_union_ons_002", "nombre": "Unión-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.94021, 42.36552], [-8.94013, 42.36484], [-8.93974, 42.36396]]), {"asset_id": "pn_islas_atlanticas_senderismo_union_ons_003", "nombre": "Unión-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.78574, 42.6149], [-8.78625, 42.61451], [-8.78706, 42.61427], [-8.78771, 42.61466], [-8.78844, 42.61475], [-8.78963, 42.61565], [-8.78996, 42.61615], [-8.79001, 42.61662], [-8.7887, 42.61766], [-8.78882, 42.61803], [-8.78845, 42.61906], [-8.7883, 42.61908], [-8.78854, 42.61933], [-8.78856, 42.61967], [-8.78828, 42.62016], [-8.7868, 42.62031], [-8.78559, 42.61991], [-8.78396, 42.62019], [-8.78344, 42.62058], [-8.78336, 42.62005], [-8.78382, 42.61958], [-8.78409, 42.61878], [-8.78242, 42.61712], [-8.78256, 42.61663], [-8.78317, 42.61589], [-8.78373, 42.61574], [-8.7855, 42.61581], [-8.78574, 42.6149]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_b_cortegada_004", "nombre": "Ruta B-CORTEGADA", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-9.01291, 42.46623], [-9.012, 42.46729], [-9.01187, 42.46785], [-9.01145, 42.46843], [-9.01056, 42.4687], [-9.00916, 42.46841], [-9.00764, 42.46863], [-9.0062, 42.46935], [-9.00481, 42.46945], [-9.0044, 42.46993], [-9.00392, 42.47011], [-9.00242, 42.4699], [-9.00159, 42.47028], [-9.00178, 42.47066]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_del_faro_salvora_005", "nombre": "Ruta del Faro-SÁLVORA", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.89932, 42.2269], [-8.89935, 42.22712], [-8.90132, 42.22687], [-8.90097, 42.22895], [-8.90137, 42.23031], [-8.90162, 42.23054], [-8.90253, 42.23063], [-8.90364, 42.23167], [-8.9037, 42.2322], [-8.9033, 42.23247], [-8.90327, 42.23301], [-8.90364, 42.2334], [-8.90357, 42.23445], [-8.9042, 42.23694], [-8.90406, 42.23839], [-8.90512, 42.23949], [-8.90485, 42.23994], [-8.90511, 42.24029], [-8.90522, 42.24109], [-8.90426, 42.24159], [-8.90341, 42.2431], [-8.90366, 42.24285], [-8.9038, 42.24226], [-8.90302, 42.24187], [-8.90291, 42.24259], [-8.90309, 42.24314], [-8.90295, 42.24308], [-8.9026, 42.24253], [-8.90262, 42.24234], [-8.90262, 42.24259], [-8.90308, 42.24314], [-8.90291, 42.24259], [-8.9031, 42.24204], [-8.90283, 42.24114], [-8.90427, 42.24098], [-8.90481, 42.24046], [-8.90485, 42.23994]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_de_monteagudo_cies_006", "nombre": "Ruta de Monteagudo-CÍES", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.90132, 42.22683], [-8.90312, 42.2251], [-8.90527, 42.22495], [-8.90631, 42.2239], [-8.90639, 42.22256], [-8.90674, 42.22208], [-8.9066, 42.22136], [-8.90607, 42.22104], [-8.90522, 42.22003], [-8.90412, 42.21912], [-8.90293, 42.21678], [-8.9034, 42.21651], [-8.9033, 42.21733], [-8.90357, 42.21772], [-8.90372, 42.21718], [-8.90423, 42.21711], [-8.90447, 42.21727], [-8.90503, 42.21678], [-8.9055, 42.21682], [-8.90583, 42.21658], [-8.90672, 42.21672], [-8.90694, 42.21733], [-8.90681, 42.21767], [-8.90703, 42.21799], [-8.90697, 42.21895], [-8.90749, 42.2193], [-8.90699, 42.21899], [-8.90704, 42.21799], [-8.90681, 42.21767], [-8.90694, 42.21733], [-8.90673, 42.21671], [-8.90713, 42.21617], [-8.90835, 42.21601], [-8.90834, 42.21535], [-8.9092, 42.21492], [-8.91007, 42.21515], [-8.91067, 42.21478], [-8.91326, 42.21484], [-8.91436, 42.21361], [-8.91411, 42.21424], [-8.91455, 42.21373], [-8.9143, 42.2141], [-8.91458, 42.21394], [-8.91453, 42.21421], [-8.91468, 42.21396], [-8.91466, 42.21425]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_monte_faro_007", "nombre": "Ruta Monte Faro", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.93175, 42.37712], [-8.9321, 42.37665], [-8.93286, 42.37624], [-8.93425, 42.37425], [-8.93544, 42.37391], [-8.93673, 42.3739], [-8.9373, 42.3741], [-8.9393, 42.37362], [-8.93889, 42.37423], [-8.93979, 42.37506], [-8.93973, 42.37567], [-8.94002, 42.37654], [-8.94002, 42.37831], [-8.93946, 42.37883], [-8.93959, 42.3794], [-8.93874, 42.38033], [-8.93813, 42.3806], [-8.9368, 42.38069], [-8.93703, 42.38114], [-8.93697, 42.38161], [-8.93647, 42.38225], [-8.93722, 42.38262], [-8.93574, 42.38274], [-8.93562, 42.38099], [-8.93502, 42.3803], [-8.93611, 42.37814], [-8.93485, 42.37674], [-8.9347, 42.37563], [-8.93488, 42.37543], [-8.93576, 42.37532], [-8.93601, 42.3743], [-8.93547, 42.374], [-8.93419, 42.37428], [-8.93287, 42.37624], [-8.93211, 42.37665], [-8.93175, 42.37712]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_del_faro_ons_008", "nombre": "Ruta del Faro-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.93179, 42.37716], [-8.93216, 42.37668], [-8.93287, 42.37634], [-8.93316, 42.37754], [-8.93273, 42.37792], [-8.93273, 42.37839], [-8.93213, 42.37945], [-8.93146, 42.37933], [-8.93105, 42.37947], [-8.92995, 42.3804], [-8.93006, 42.37959], [-8.93074, 42.37884], [-8.93057, 42.37851], [-8.93066, 42.37829], [-8.93162, 42.37766], [-8.93178, 42.37719]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_del_castelo_ons_009", "nombre": "Ruta del Castelo-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.9317, 42.37702], [-8.93203, 42.3766], [-8.93281, 42.37618], [-8.93413, 42.37425], [-8.93532, 42.37395], [-8.93543, 42.37321], [-8.93501, 42.37261], [-8.93566, 42.37185], [-8.93763, 42.37109], [-8.93748, 42.37079], [-8.93836, 42.36768], [-8.93837, 42.36626], [-8.93901, 42.36551], [-8.93957, 42.36538], [-8.94043, 42.36554], [-8.94279, 42.36687], [-8.94404, 42.36671], [-8.94465, 42.3662], [-8.94489, 42.36563], [-8.94487, 42.3649], [-8.94418, 42.36429], [-8.94363, 42.36312], [-8.94507, 42.36135], [-8.94483, 42.3608], [-8.94382, 42.36043], [-8.9458, 42.36005], [-8.94382, 42.36043], [-8.94294, 42.35979], [-8.94222, 42.35953], [-8.94136, 42.3598], [-8.9405, 42.35966], [-8.93906, 42.35909], [-8.93888, 42.35863], [-8.939, 42.35799], [-8.93889, 42.35866], [-8.93928, 42.35929], [-8.9391, 42.35999], [-8.93962, 42.36068], [-8.939, 42.36196], [-8.93891, 42.36256], [-8.93926, 42.36286], [-8.93968, 42.36249], [-8.94003, 42.36254], [-8.94038, 42.36288], [-8.94053, 42.36357], [-8.93922, 42.36409], [-8.93755, 42.3641], [-8.93678, 42.36451], [-8.93491, 42.3668], [-8.93485, 42.36863], [-8.93274, 42.37275], [-8.93332, 42.37398], [-8.93317, 42.37537], [-8.93163, 42.37632], [-8.9317, 42.37702]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_sur_ons_010", "nombre": "Ruta Sur-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.78574, 42.6149], [-8.7855, 42.61581], [-8.78373, 42.61574], [-8.78317, 42.61589], [-8.78256, 42.61663], [-8.78236, 42.61735], [-8.78184, 42.61754], [-8.78028, 42.61756], [-8.77961, 42.61815], [-8.77858, 42.61868], [-8.77846, 42.61895], [-8.77875, 42.61956], [-8.77861, 42.62011], [-8.77875, 42.62055], [-8.78015, 42.62177], [-8.78031, 42.62215], [-8.78241, 42.62148], [-8.78378, 42.62031], [-8.78432, 42.62009], [-8.78511, 42.6201], [-8.78559, 42.61991], [-8.7868, 42.62031], [-8.78819, 42.62019], [-8.78846, 42.61996], [-8.78854, 42.61933], [-8.7883, 42.61908], [-8.78845, 42.61906], [-8.78882, 42.61803], [-8.7887, 42.61766], [-8.78948, 42.61697], [-8.78991, 42.61685], [-8.79004, 42.61648], [-8.78987, 42.61596], [-8.7891, 42.61515], [-8.78844, 42.61475], [-8.78771, 42.61466], [-8.78731, 42.61431], [-8.78625, 42.61451], [-8.78574, 42.6149]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_a_cortegada_011", "nombre": "Ruta A-CORTEGADA", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-9.01008, 42.47626], [-9.00986, 42.47572], [-9.00918, 42.47521], [-9.00837, 42.47413], [-9.00766, 42.47253], [-9.00632, 42.47198], [-9.00538, 42.46942]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_de_la_aldea_salvora_012", "nombre": "Ruta de la Aldea-SÁLVORA", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.89941, 42.22686], [-8.89947, 42.22703], [-8.90131, 42.22678], [-8.90289, 42.22516], [-8.9037, 42.22492], [-8.9052, 42.22492], [-8.90625, 42.22385], [-8.90626, 42.22285], [-8.90667, 42.22208], [-8.90662, 42.2215], [-8.90405, 42.21915], [-8.90308, 42.21744], [-8.90286, 42.21681], [-8.90298, 42.21647], [-8.90336, 42.21629], [-8.90467, 42.21468], [-8.90601, 42.21448], [-8.90618, 42.21389], [-8.90678, 42.21315], [-8.90725, 42.21301], [-8.9069, 42.21333], [-8.90759, 42.21337], [-8.90845, 42.21373], [-8.90921, 42.21371], [-8.91003, 42.21324], [-8.91135, 42.21314], [-8.91211, 42.21329], [-8.91266, 42.21229]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_del_faro_da_porta_cies_013", "nombre": "Ruta del Faro da Porta-CÍES", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.89935, 42.22689], [-8.89939, 42.22709], [-8.90135, 42.22685], [-8.90102, 42.22895], [-8.90115, 42.2297], [-8.90154, 42.23046], [-8.90256, 42.23061], [-8.9028, 42.23099], [-8.90368, 42.23166], [-8.90374, 42.23222], [-8.90339, 42.23242], [-8.90331, 42.23274], [-8.90335, 42.23309], [-8.90371, 42.23339], [-8.90456, 42.23349], [-8.90502, 42.23284], [-8.90498, 42.23179], [-8.90541, 42.23149], [-8.90616, 42.23137], [-8.90617, 42.22991], [-8.90557, 42.22929], [-8.90657, 42.22926]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_del_alto_do_principe_cies_014", "nombre": "Ruta del Alto do Principe-CÍES", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.93172, 42.37713], [-8.93206, 42.37662], [-8.93284, 42.37619], [-8.93423, 42.37422], [-8.93544, 42.37386], [-8.93674, 42.37385], [-8.93729, 42.37405], [-8.93942, 42.37352], [-8.93896, 42.37423], [-8.93986, 42.37505], [-8.93979, 42.37567], [-8.94009, 42.37651], [-8.94009, 42.37829], [-8.93951, 42.37887], [-8.93969, 42.37951], [-8.93958, 42.38081], [-8.93876, 42.384], [-8.93786, 42.38444], [-8.93661, 42.38434], [-8.93645, 42.38465], [-8.93543, 42.38533], [-8.93455, 42.38572], [-8.934, 42.38625], [-8.9334, 42.38642], [-8.93175, 42.38867], [-8.93174, 42.38983], [-8.93137, 42.39104], [-8.93015, 42.39156], [-8.92967, 42.39234], [-8.92882, 42.39271], [-8.92869, 42.39305], [-8.92912, 42.39347], [-8.92891, 42.39377], [-8.9272, 42.3931], [-8.92648, 42.39217], [-8.92628, 42.39227], [-8.92619, 42.39283], [-8.92574, 42.39214], [-8.92497, 42.39257], [-8.92573, 42.39219], [-8.92578, 42.39118], [-8.92611, 42.39085], [-8.92618, 42.39016], [-8.92739, 42.38892], [-8.92809, 42.38847], [-8.92811, 42.38809], [-8.92897, 42.38723], [-8.92901, 42.38602], [-8.93039, 42.38443], [-8.93041, 42.38301], [-8.93096, 42.38258], [-8.93092, 42.38206], [-8.93169, 42.38146], [-8.93234, 42.38143], [-8.93271, 42.38094], [-8.93218, 42.37942], [-8.93279, 42.37839], [-8.93279, 42.37793], [-8.93321, 42.37755], [-8.93294, 42.37632], [-8.93274, 42.37627]]), {"asset_id": "pn_islas_atlanticas_senderismo_ruta_norte_ons_015", "nombre": "Ruta Norte-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.90837, 42.21594], [-8.90784, 42.21568], [-8.90754, 42.21529], [-8.90712, 42.21335]]), {"asset_id": "pn_islas_atlanticas_senderismo_union_cies_016", "nombre": "Unión-CÍES", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.94365, 42.36303], [-8.94294, 42.36322], [-8.94166, 42.36316], [-8.94052, 42.36362]]), {"asset_id": "pn_islas_atlanticas_senderismo_union_ons_017", "nombre": "Unión-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
  ee.Feature(ee.Geometry.LineString([[-8.93762, 42.3711], [-8.93866, 42.37118], [-8.93946, 42.37172], [-8.93961, 42.37316], [-8.93939, 42.3735]]), {"asset_id": "pn_islas_atlanticas_senderismo_union_ons_018", "nombre": "Unión-ONS", "geom_type": "LINESTRING", "category": "senderismo"}),
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
Map.addLayer(assets, {color: 'red'}, 'Parque Nacional Marítimo-Terrestre de las Islas Atlánticas de Galicia assets');

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
  description: 'pn_islas_atlanticas_indices_multiyear',
  folder: 'SNTO_exports',
  fileNamePrefix: 'pn_islas_atlanticas_gee_timeseries',
  fileFormat: 'CSV',
  selectors: [
    'asset_id', 'nombre', 'category', 'year', 'month', 'date',
    'ndvi', 'ndmi', 'evi',
    'ndvi_p25', 'ndvi_p75', 'ndvi_stdDev',
    'data_source'
  ]
});
