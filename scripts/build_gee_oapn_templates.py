"""
scripts/build_gee_oapn_templates.py
===================================
Genera un script JavaScript LISTO PARA PEGAR en el GEE Code Editor
(code.earthengine.google.com) por cada Parque Nacional de la Red OAPN,
replicando el modelo validado con el PNSG (scripts/build_gee_js.py).

Fuente cartográfica: GeoServer oficial OAPN SIGRED (WFS), las MISMAS capas
usadas para PNSG:
  - UsoPublico_visor:view_vis_oapn_itinerarios_visor  → senderos oficiales
  - UsoPublico_visor:view_vis_oapn_iti_bici_visor      → rutas bici
  - LimitesParquesNacionalesZPP_visor:..._limite_pn_visor → límite (centro/zoom)

Para cada parque (los 15 distintos de Guadarrama, ya resuelto en v1.1.0):
  - Descarga itinerarios + rutas bici de TODA la red y los agrupa por
    "Nombre Parque".
  - Simplifica geometrías (Douglas-Peucker ~12 m; luego se hace buffer ±30 m,
    así que no se pierde fidelidad útil) y redondea a 5 decimales.
  - Embebe cada itinerario/ruta como ee.Feature (categoría senderismo/ciclismo).
  - Emite el MISMO pipeline Sentinel-2 que PNSG: máscara SCL → NDVI/NDMI/EVI
    mensual 2021-01..2026-06 → Export CSV a Google Drive (carpeta SNTO_exports).
  - A diferencia de PNSG (que fijaba MGRS_TILE='30TVL'), usa .filterBounds(assets)
    para soportar parques que cruzan varias teselas Sentinel-2.

Salida: scripts/gee_templates_oapn/<key>.js  (uno por parque) + README.md

Uso:
    python scripts/build_gee_oapn_templates.py
    # opcional: limitar a un parque por subcadena
    python scripts/build_gee_oapn_templates.py donana teide

NOTA: NO modifica ningún archivo versionado del repo; solo escribe ficheros
nuevos en scripts/gee_templates_oapn/ (no trackeados).
"""
from __future__ import annotations

import json
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from shapely.geometry import shape, mapping
except ImportError:  # pragma: no cover
    raise SystemExit("Necesita shapely: pip install shapely")

_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = _ROOT / "scripts" / "gee_templates_oapn"

BASE = "https://sigred.oapn.es/geoserverOAPN"
WFS_ITINERARIOS = ("UsoPublico_visor", "view_vis_oapn_itinerarios_visor")
WFS_ITI_BICI = ("UsoPublico_visor", "view_vis_oapn_iti_bici_visor")

# ── Parámetros del pipeline (idénticos al modelo PNSG) ──────────────────────
START_YEAR = 2021
START_MONTH = 1
N_MONTHS = 66            # 2021-01 .. 2026-06 (2026 parcial)
POINT_BUFFER_M = 50
LINE_BUFFER_M = 30
SCALE_M = 10
SIMPLIFY_TOL = 0.00012  # grados ≈ 12 m (buffer posterior ±30 m lo absorbe)
ROUND_DP = 5

# ── Registro de parques OAPN ────────────────────────────────────────────────
# key: slug corto · label: nombre OAPN exacto ("Nombre Parque") · mgrs: tesela(s)
# Sentinel-2 ORIENTATIVAS (el script usa filterBounds, no necesita exactitud).
# Guadarrama se EXCLUYE: ya resuelto en v1.1.0 (scripts/gee_code_editor_pnsg.js).
PARKS = [
    ("pn_aiguestortes", "Parque Nacional de Aigüestortes i Estany de Sant Maurici", "31TCH"),
    ("pn_cabrera",      "Parque Nacional Marítimo-Terrestre del Archipiélago de Cabrera", "31SDD"),
    ("pn_cabaneros",    "Parque Nacional de Cabañeros", "30SUJ / 30SVJ"),
    ("pn_taburiente",   "Parque Nacional de la Caldera de Taburiente", "28RBS"),
    ("pn_donana",       "Parque Nacional de Doñana", "29SQA / 29SQB"),
    ("pn_garajonay",    "Parque Nacional de Garajonay", "28RBS"),
    ("pn_islas_atlanticas", "Parque Nacional Marítimo-Terrestre de las Islas Atlánticas de Galicia", "29TNG / 29TNH"),
    ("pn_monfrague",    "Parque Nacional de Monfragüe", "29SQD / 30STK"),
    ("pn_ordesa",       "Parque Nacional de Ordesa y Monte Perdido", "30TYN / 31TBH"),
    ("pn_picos_europa", "Parque Nacional de los Picos de Europa", "30TUN / 30TUP"),
    ("pn_sierra_nevada", "Parque Nacional de Sierra Nevada", "30SVF / 30SWF / 30SVG / 30SWG"),
    ("pn_sierra_nieves", "Parque Nacional de la Sierra de las Nieves", "30SUF"),
    ("pn_tablas_daimiel", "Parque Nacional de las Tablas de Daimiel", "30SVJ"),
    ("pn_teide",        "Parque Nacional del Teide", "28RCS"),
    ("pn_timanfaya",    "Parque Nacional de Timanfaya", "28RES / 28RFS"),
]


def slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    out = []
    for ch in norm.lower():
        out.append(ch if ch.isalnum() else "_")
    s = "".join(out)
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def wfs_url(workspace: str, layer: str) -> str:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": f"{workspace}:{layer}",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }
    return f"{BASE}/{workspace}/wfs?" + urllib.parse.urlencode(params)


def fetch_layer(workspace: str, layer: str) -> dict:
    url = wfs_url(workspace, layer)
    req = urllib.request.Request(url, headers={"User-Agent": "SNTO-OAPN/1.0"})
    print(f"  ▶ WFS {layer} ...", flush=True)
    with urllib.request.urlopen(req, timeout=240) as resp:
        return json.loads(resp.read())


def _round(coords, dp=ROUND_DP):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], dp), round(coords[1], dp)]
    return [_round(c, dp) for c in coords]


def geom_js(gtype: str, coords) -> str:
    c = json.dumps(coords)
    ctor = {
        "Point": "ee.Geometry.Point",
        "LineString": "ee.Geometry.LineString",
        "MultiLineString": "ee.Geometry.MultiLineString",
        "Polygon": "ee.Geometry.Polygon",
        "MultiPolygon": "ee.Geometry.MultiPolygon",
    }.get(gtype)
    if ctor is None:
        raise ValueError(f"Tipo geom no soportado: {gtype}")
    return f"{ctor}({c})"


def build_features(park_label: str, key: str, itinerarios: dict, bici: dict) -> tuple[str, int]:
    """Construye el bloque JS de ee.Feature[] para un parque."""
    lines: list[str] = []
    idx = 0
    for layer_fc, category in ((itinerarios, "senderismo"), (bici, "ciclismo")):
        for feat in layer_fc["features"]:
            props = feat.get("properties") or {}
            if props.get("Nombre Parque") != park_label:
                continue
            geom = feat.get("geometry")
            if not geom:
                continue
            simp = shape(geom).simplify(SIMPLIFY_TOL, preserve_topology=False)
            if simp.is_empty:
                continue
            gj = mapping(simp)
            gtype = gj["type"]
            coords = _round(json.loads(json.dumps(gj["coordinates"])))
            nombre = (props.get("Nombre") or "s_n").strip()
            asset_id = f"{key}_{category}_{slugify(nombre)[:48]}_{idx:03d}"
            jprops = json.dumps(
                {
                    "asset_id": asset_id,
                    "nombre": nombre,
                    "geom_type": gtype.upper(),
                    "category": category,
                },
                ensure_ascii=False,
            )
            lines.append(f"  ee.Feature({geom_js(gtype, coords)}, {jprops}),")
            idx += 1
    return "\n".join(lines), idx


_TEMPLATE = r"""// ============================================================================
// SNTO — Extracción NDVI/NDMI/EVI mensual 2021–2026 · @@PARK_LABEL@@
// GENERADO por scripts/build_gee_oapn_templates.py — pegar en
// code.earthengine.google.com (replica el modelo validado del PNSG, v1.1.0).
// ----------------------------------------------------------------------------
// @@N_ASSETS@@ assets reales = itinerarios (senderismo) + rutas bici (ciclismo)
// de la cartografía oficial OAPN (GeoServer SIGRED).
// Ventana: ene-2021 .. jun-2026 (2026 parcial; el análisis lo trata aparte).
// Tesela(s) Sentinel-2 orientativa(s): @@MGRS@@ (el script usa filterBounds,
// así que NO necesita la tesela exacta y soporta parques multi-tesela).
// Exporta un CSV a Google Drive → carpeta "SNTO_exports".
// ============================================================================

// ── Configuración ───────────────────────────────────────────────────────────
var START = ee.Date.fromYMD(@@START_Y@@, @@START_M@@, 1);
var N_MONTHS = @@N_MONTHS@@;            // 2021-01 .. 2026-06 (2026 parcial)
var POINT_BUFFER_M = @@PT_BUF@@;
var LINE_BUFFER_M  = @@LN_BUF@@;
var SCALE_M = @@SCALE@@;

// ── Assets (embebidos desde cartografía oficial OAPN, simplificados ~12 m) ───
var rawAssets = ee.FeatureCollection([
@@FEATURES@@
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
Map.addLayer(assets, {color: 'red'}, '@@PARK_LABEL@@ assets');

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
  description: '@@KEY@@_indices_multiyear',
  folder: 'SNTO_exports',
  fileNamePrefix: '@@KEY@@_gee_timeseries',
  fileFormat: 'CSV',
  selectors: [
    'asset_id', 'nombre', 'category', 'year', 'month', 'date',
    'ndvi', 'ndmi', 'evi',
    'ndvi_p25', 'ndvi_p75', 'ndvi_stdDev',
    'data_source'
  ]
});
"""


def render(park_label: str, key: str, mgrs: str, features_block: str, n_assets: int) -> str:
    repl = {
        "@@PARK_LABEL@@": park_label,
        "@@N_ASSETS@@": str(n_assets),
        "@@MGRS@@": mgrs,
        "@@START_Y@@": str(START_YEAR),
        "@@START_M@@": str(START_MONTH),
        "@@N_MONTHS@@": str(N_MONTHS),
        "@@PT_BUF@@": str(POINT_BUFFER_M),
        "@@LN_BUF@@": str(LINE_BUFFER_M),
        "@@SCALE@@": str(SCALE_M),
        "@@FEATURES@@": features_block,
        "@@KEY@@": key,
    }
    out = _TEMPLATE
    for token, val in repl.items():
        out = out.replace(token, val)
    return out


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    filters = [a.lower() for a in sys.argv[1:]]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Descargando capas de uso público OAPN (red completa)...")
    itinerarios = fetch_layer(*WFS_ITINERARIOS)
    bici = fetch_layer(*WFS_ITI_BICI)
    print()

    summary = []
    for key, label, mgrs in PARKS:
        if filters and not any(fl in key or fl in slugify(label) for fl in filters):
            continue
        features_block, n_assets = build_features(label, key, itinerarios, bici)
        if n_assets == 0:
            print(f"  ⚠ {key}: 0 assets (¿nombre cambiado en WFS?) — omitido")
            summary.append((key, 0, 0))
            continue
        js = render(label, key, mgrs, features_block, n_assets)
        out_path = OUT_DIR / f"{key}.js"
        out_path.write_text(js, encoding="utf-8")
        kb = len(js.encode("utf-8")) // 1024
        print(f"  ✔ {key:<20} {n_assets:>3} assets  → {out_path.name} ({kb} KB)")
        summary.append((key, n_assets, kb))

    print("\nRESUMEN")
    for key, n, kb in summary:
        print(f"  {key:<22} assets={n:<4} {kb} KB")
    print(f"\nSalida: {OUT_DIR}")
    print("Pega el contenido de cada .js en https://code.earthengine.google.com")


if __name__ == "__main__":
    main()
