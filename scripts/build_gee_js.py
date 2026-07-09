"""
scripts/build_gee_js.py
=========================
Convierte clean_assets/pnsg_assets.geojson en un script JavaScript listo
para pegar en el GEE Code Editor (code.earthengine.google.com).

El JS resultante:
  - Embebe los 21 assets reales como ee.FeatureCollection
  - Aplica buffer 50 m (puntos) / 30 m (líneas) server-side
  - Calcula NDVI/NDMI/EVI mensuales 2021-2025 con máscara SCL
  - Exporta un CSV a Google Drive (carpeta SNTO_exports)

Uso:
    python scripts/build_gee_js.py
    → genera scripts/gee_code_editor_pnsg.js
"""

from __future__ import annotations

import json
from pathlib import Path

GEOJSON = Path("clean_assets/pnsg_assets.geojson")
OUT_JS = Path("scripts/gee_code_editor_pnsg.js")


def _geom_js(gtype: str, coords) -> str:
    """Construye la expresión ee.Geometry.* en JS."""
    c = json.dumps(coords)
    if gtype == "Point":
        return f"ee.Geometry.Point({c})"
    if gtype == "LineString":
        return f"ee.Geometry.LineString({c})"
    if gtype == "Polygon":
        return f"ee.Geometry.Polygon({c})"
    raise ValueError(gtype)


def build() -> str:
    fc = json.loads(GEOJSON.read_text(encoding="utf-8"))

    feature_lines = []
    for feat in fc["features"]:
        p = feat["properties"]
        gtype = feat["geometry"]["type"]
        geom = _geom_js(gtype, feat["geometry"]["coordinates"])
        props = json.dumps({
            "asset_id": p["asset_id"],
            "geom_type": p["geom_type"],
            "category": p["category"],
        }, ensure_ascii=False)
        feature_lines.append(f"  ee.Feature({geom}, {props}),")

    features_block = "\n".join(feature_lines)

    return f"""// ============================================================================
// SNTO — Extracción NDVI/NDMI/EVI mensual 2021–2026 para assets del PNSG
// GENERADO por scripts/build_gee_js.py — pegar en code.earthengine.google.com
// ----------------------------------------------------------------------------
// 21 assets reales (vuelo libre, escalada, ciclismo, zonas de reserva).
// Ventana: ene-2021 .. jun-2026 (2026 es parcial; el análisis lo trata aparte).
// Exporta un CSV a Google Drive → carpeta "SNTO_exports".
// ============================================================================

// ── Configuración ───────────────────────────────────────────────────────────
var MGRS_TILE = '30TVL';            // OJO: sin la 'T' inicial en GEE
var START = ee.Date.fromYMD(2021, 1, 1);
var N_MONTHS = 66;                   // 2021-01 .. 2026-06 (2026 parcial: ene-jun)
var POINT_BUFFER_M = 50;
var LINE_BUFFER_M  = 30;
var SCALE_M = 10;

// ── Assets PNSG (embebidos desde pnsg_assets.geojson) ───────────────────────
var rawAssets = ee.FeatureCollection([
{features_block}
]);

// Aplicar buffer según tipo de geometría (puntos y líneas) server-side
var assets = rawAssets.map(function(f) {{
  var gt = ee.String(f.get('geom_type'));
  var geom = ee.Geometry(ee.Algorithms.If(
    gt.equals('POINT'), f.geometry().buffer(POINT_BUFFER_M),
    ee.Algorithms.If(
      gt.equals('LINESTRING'), f.geometry().buffer(LINE_BUFFER_M),
      f.geometry()
    )
  ));
  return f.setGeometry(geom);
}});

print('Assets cargados:', assets.size());
Map.centerObject(assets, 11);
Map.addLayer(assets, {{color: 'red'}}, 'PNSG assets');

// ── Colección Sentinel-2 + máscara SCL + índices ────────────────────────────
function maskAndIndex(image) {{
  var scl = image.select('SCL');
  var mask = scl.neq(0).and(scl.neq(1)).and(scl.neq(3))
    .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  var sr = image.select(['B2', 'B4', 'B8', 'B11']).divide(10000);
  var ndvi = sr.normalizedDifference(['B8', 'B4']).rename('ndvi');
  var ndmi = sr.normalizedDifference(['B8', 'B11']).rename('ndmi');
  var evi = sr.expression(
    '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
    {{NIR: sr.select('B8'), RED: sr.select('B4'), BLUE: sr.select('B2')}}
  ).rename('evi');
  return sr.addBands([ndvi, ndmi, evi]).updateMask(mask)
           .copyProperties(image, ['system:time_start']);
}}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filter(ee.Filter.eq('MGRS_TILE', MGRS_TILE))
  .filterDate(START, START.advance(N_MONTHS, 'month'))
  .map(maskAndIndex);

// ── Estadística mensual por asset (server-side, sin getInfo) ─────────────────
var months = ee.List.sequence(0, N_MONTHS - 1);

var perMonth = months.map(function(m) {{
  m = ee.Number(m);
  var start = START.advance(m, 'month');
  var end = start.advance(1, 'month');
  var composite = s2.filterDate(start, end).median();

  var reducer = ee.Reducer.mean()
    .combine({{reducer2: ee.Reducer.percentile([25, 75]), sharedInputs: true}})
    .combine({{reducer2: ee.Reducer.stdDev(), sharedInputs: true}});

  var stats = composite.select(['ndvi', 'ndmi', 'evi']).reduceRegions({{
    collection: assets,
    reducer: reducer,
    scale: SCALE_M
  }});

  // Añadir año/mes y renombrar la media a ndvi/ndmi/evi
  return stats.map(function(f) {{
    return f.setGeometry(null).set({{
      year: start.get('year'),
      month: start.get('month'),
      date: start.format('YYYY-MM-dd'),
      ndvi: f.get('ndvi_mean'),
      ndmi: f.get('ndmi_mean'),
      evi:  f.get('evi_mean'),
      data_source: 'GEE:S2_SR_HARMONIZED'
    }});
  }});
}});

var flat = ee.FeatureCollection(perMonth).flatten();

// Filtrar meses sin datos (NDVI nulo por nubosidad total)
flat = flat.filter(ee.Filter.notNull(['ndvi']));

print('Filas estimadas (puede tardar):', flat.size());
print('Muestra (primeras 5 filas):', flat.limit(5));

// ── Export a Google Drive ────────────────────────────────────────────────────
Export.table.toDrive({{
  collection: flat,
  description: 'PNSG_indices_multiyear',
  folder: 'SNTO_exports',
  fileNamePrefix: 'pnsg_gee_timeseries',
  fileFormat: 'CSV',
  selectors: [
    'asset_id', 'year', 'month', 'date',
    'ndvi', 'ndmi', 'evi',
    'ndvi_p25', 'ndvi_p75', 'ndvi_stdDev',
    'data_source'
  ]
}});
"""


def main() -> None:
    if not GEOJSON.exists():
        raise SystemExit(f"Falta {GEOJSON}. Ejecuta antes: python scripts/build_pnsg_assets.py")
    OUT_JS.write_text(build(), encoding="utf-8")
    print(f"JS generado: {OUT_JS}")
    print("Pega su contenido en https://code.earthengine.google.com")


if __name__ == "__main__":
    main()
