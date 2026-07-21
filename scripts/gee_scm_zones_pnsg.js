/**
 * SNTO — Multi-scale SCM zone export (v2.2), Google Earth Engine Code Editor.
 * =========================================================================
 * Exports OBSERVED core / near / landscape monthly NDVI & NDMI per PNSG asset,
 * so the Spatial Causality Module runs on real zonal signals instead of the
 * α-decay simulation (src/spatial_causality/zone_loader.py consumes the output).
 *
 * Zones match src/spatial_causality/analyzer.py EXACTLY:
 *   core      : 0–50 m buffer around the asset geometry
 *   near      : 50–200 m annulus
 *   landscape : 200–1000 m annulus
 *
 * Source: Sentinel-2 SR Harmonized (COPERNICUS/S2_SR_HARMONIZED), same tile
 * (T30TVL) and 2021–2026 window as Pipeline A. SCL cloud/shadow mask applied.
 *
 * OWNER-RUN: this is executed in the GEE Code Editor (Earth Engine account
 * required); it is not run by CI or the agent. Export the per-asset table, then
 * reshape to the loader's JSON:
 *   {"asset_id": "...", "zones": {"core":[{"year","month","ndvi","ndmi"}...],
 *                                 "near":[...], "landscape":[...]}}
 * and drop it in src/spatial_causality/zones/<asset_id>.json.
 */

// ── Config ────────────────────────────────────────────────────────────────
var ASSETS = ee.FeatureCollection('users/OWNER/pnsg_assets');  // asset points/lines
var START = '2021-01-01';
var END   = '2026-01-01';
var CORE_M = 50, NEAR_M = 200, LAND_M = 1000;

// ── Cloud/shadow mask via SCL (per-biome correction lives in the OAPN pass) ──
function maskS2(img) {
  var scl = img.select('SCL');
  var good = scl.neq(3)   // shadow
    .and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10))  // clouds/cirrus
    .and(scl.neq(11));    // snow
  return img.updateMask(good).divide(10000);
}

function addIndices(img) {
  var ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi');
  var ndmi = img.normalizedDifference(['B8', 'B11']).rename('ndmi');
  return img.addBands(ndvi).addBands(ndmi);
}

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterDate(START, END)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
  .map(maskS2).map(addIndices);

// ── Zone geometries: annuli via buffer differences ──────────────────────────
function zonesFor(feature) {
  var g = feature.geometry();
  var core = g.buffer(CORE_M);
  var near = g.buffer(NEAR_M).difference(core);
  var land = g.buffer(LAND_M).difference(g.buffer(NEAR_M));
  return { core: core, near: near, landscape: land };
}

// ── Monthly zonal means, emitted as one row per asset/zone/month ────────────
var months = ee.List.sequence(0, ee.Date(END).difference(ee.Date(START), 'month').subtract(1));

var rows = ASSETS.map(function (feat) {
  var z = zonesFor(feat);
  var perZone = ee.List(['core', 'near', 'landscape']).map(function (zoneName) {
    var geom = ee.Dictionary(z).get(zoneName);
    var monthly = months.map(function (m) {
      var start = ee.Date(START).advance(m, 'month');
      var comp = s2.filterDate(start, start.advance(1, 'month')).mean();
      var stats = comp.select(['ndvi', 'ndmi']).reduceRegion({
        reducer: ee.Reducer.mean(), geometry: geom, scale: 10, maxPixels: 1e9,
      });
      return ee.Feature(null, {
        asset_id: feat.get('asset_id'),
        zone: zoneName,
        year: start.get('year'),
        month: start.get('month'),
        ndvi: stats.get('ndvi'),
        ndmi: stats.get('ndmi'),
      });
    });
    return monthly;
  }).flatten();
  return perZone;
}).flatten();

Export.table.toDrive({
  collection: ee.FeatureCollection(rows),
  description: 'pnsg_scm_zones_2021_2026',
  fileFormat: 'CSV',
  selectors: ['asset_id', 'zone', 'year', 'month', 'ndvi', 'ndmi'],
});
