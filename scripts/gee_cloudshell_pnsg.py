"""
scripts/gee_cloudshell_pnsg.py
================================
Script Earth Engine para ejecutar en Google Cloud Shell (proyecto GCP).
Genera el script base de Gemini Cloud Assist, CORREGIDO y alineado con el
pipeline SNTO (columnas compatibles con run_timeseries_analysis.py).

Extrae NDVI/NDMI/EVI mensuales 2021-2025 para assets del PNSG (tile 30TVL)
y exporta un CSV a Google Cloud Storage.

Correcciones vs. el script original de Gemini
---------------------------------------------
  1. MGRS_TILE = '30TVL'  (SIN la "T" — bug que dejaba el export vacío)
  2. Columnas de salida renombradas a ndvi/ndmi/evi (no ndvi_mean) para que
     run_timeseries_analysis.py las lea directamente.
  3. Conserva también _p25/_p75/_std para análisis espacial.
  4. asset_id corregido: pnsg_senda_herreros.

Ejecución en Cloud Shell
------------------------
    # 1. Habilitar APIs (una vez)
    gcloud services enable earthengine.googleapis.com --project=pure-episode-499118-r8
    gcloud services enable storage.googleapis.com    --project=pure-episode-499118-r8

    # 2. Crear el bucket si no existe (una vez)
    gcloud storage buckets create gs://snto-observatory --location=EU --project=pure-episode-499118-r8

    # 3. Autenticar Earth Engine (una vez)
    earthengine authenticate

    # 4. Instalar y ejecutar
    pip install earthengine-api
    python scripts/gee_cloudshell_pnsg.py

    # 5. Descargar el resultado cuando la tarea termine (~5-10 min)
    gcloud storage cp gs://snto-observatory/timeseries/pnsg_indices_report.csv \\
        clean_assets/timeseries/pnsg_gee_timeseries_2021_2025.csv
"""

import json
from pathlib import Path

import ee

# ── 1. Inicialización ──────────────────────────────────────────────────────────
PROJECT_ID = "pure-episode-499118-r8"
ee.Initialize(project=PROJECT_ID)

# ── Configuración ──────────────────────────────────────────────────────────────
BUCKET = "snto-observatory"
# IMPORTANTE: la propiedad MGRS_TILE en GEE NO lleva la "T" inicial.
MGRS_TILE = "30TVL"
START_YEAR = 2021
END_YEAR = 2025

# Umbral de nubosidad de escena para saltar un mes
MAX_SCENE_CLOUD_PCT = 70

# Buffers por tipo de geometría (m)
POINT_BUFFER_M = 50
LINE_BUFFER_M = 30

# ── Assets PNSG (cargados del GeoJSON generado por build_pnsg_assets.py) ────────
# Sube clean_assets/pnsg_assets.geojson a Cloud Shell junto a este script.
ASSETS_GEOJSON = Path("clean_assets/pnsg_assets.geojson")


def load_assets():
    """Lee el GeoJSON y construye ee.Geometry con buffer según tipo."""
    fc = json.loads(ASSETS_GEOJSON.read_text(encoding="utf-8"))
    out = []
    for feat in fc["features"]:
        gtype = feat["geometry"]["type"]
        coords = feat["geometry"]["coordinates"]
        asset_id = feat["properties"]["asset_id"]
        if gtype == "Point":
            geom = ee.Geometry.Point(coords).buffer(POINT_BUFFER_M)
        elif gtype == "LineString":
            geom = ee.Geometry.LineString(coords).buffer(LINE_BUFFER_M)
        elif gtype == "Polygon":
            geom = ee.Geometry.Polygon(coords)
        else:
            print(f"Tipo no soportado en {asset_id}: {gtype} — saltando")
            continue
        out.append({"id": asset_id, "geom": geom})
    print(f"Cargados {len(out)} assets desde {ASSETS_GEOJSON}")
    return out


assets = load_assets()


# ── Funciones de procesamiento ─────────────────────────────────────────────────

def mask_s2_clouds(image):
    """Enmascara nubes/sombras/nieve con SCL y escala reflectancia a [0,1]."""
    scl = image.select("SCL")
    mask = (scl.neq(0).And(scl.neq(1)).And(scl.neq(3))
            .And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11)))
    # Escalar SOLO las bandas ópticas, no SCL/QA (divide por 10000 → reflectancia)
    scaled = image.select(["B2", "B4", "B8", "B11"]).divide(10000)
    return scaled.updateMask(mask)


def add_indices(image):
    """Calcula NDVI, NDMI y EVI sobre reflectancia escalada."""
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndmi = image.normalizedDifference(["B8", "B11"]).rename("ndmi")
    evi = image.expression(
        "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
        {"NIR": image.select("B8"), "RED": image.select("B4"), "BLUE": image.select("B2")},
    ).rename("evi")
    return image.addBands([ndvi, ndmi, evi])


# ── Pipeline ───────────────────────────────────────────────────────────────────
results = []

for year in range(START_YEAR, END_YEAR + 1):
    for month in range(1, 13):
        start_date = ee.Date.fromYMD(year, month, 1)
        end_date = start_date.advance(1, "month")

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filter(ee.Filter.eq("MGRS_TILE", MGRS_TILE))   # ← corregido: '30TVL'
            .filterDate(start_date, end_date)
        )

        monthly_cloud_avg = collection.aggregate_mean("CLOUDY_PIXEL_PERCENTAGE").getInfo()
        if monthly_cloud_avg is None or monthly_cloud_avg > MAX_SCENE_CLOUD_PCT:
            print(f"Saltando {year}-{month:02d}: nubosidad {monthly_cloud_avg}%")
            continue

        composite = collection.map(mask_s2_clouds).map(add_indices).median()

        reducer = (
            ee.Reducer.mean()
            .combine(ee.Reducer.percentile([25, 75]), sharedInputs=True)
            .combine(ee.Reducer.stdDev(), sharedInputs=True)
        )

        for asset in assets:
            stats = composite.select(["ndvi", "ndmi", "evi"]).reduceRegion(
                reducer=reducer,
                geometry=asset["geom"],
                scale=10,
                maxPixels=1e9,
            )

            # Renombrar a esquema del pipeline: ndvi/ndmi/evi = la media
            feature = ee.Feature(None, {
                "asset_id":        asset["id"],
                "year":            year,
                "month":           month,
                "date":            f"{year}-{month:02d}-01",
                "ndvi":            stats.get("ndvi_mean"),
                "ndmi":            stats.get("ndmi_mean"),
                "evi":             stats.get("evi_mean"),
                "ndvi_p25":        stats.get("ndvi_p25"),
                "ndvi_p75":        stats.get("ndvi_p75"),
                "ndvi_std":        stats.get("ndvi_stdDev"),
                "cloud_cover_pct": round(monthly_cloud_avg, 1),
                "data_source":     "GEE:S2_SR_HARMONIZED",
            })
            results.append(feature)

# ── Export a GCS ───────────────────────────────────────────────────────────────
output_fc = ee.FeatureCollection(results)

# Orden de columnas en el CSV (selectors garantiza el esquema esperado)
selectors = [
    "asset_id", "year", "month", "date",
    "ndvi", "ndmi", "evi",
    "ndvi_p25", "ndvi_p75", "ndvi_std",
    "cloud_cover_pct", "data_source",
]

task = ee.batch.Export.table.toCloudStorage(
    collection=output_fc,
    description=f"PNSG_Vegetation_Indices_{START_YEAR}_{END_YEAR}",
    bucket=BUCKET,
    fileNamePrefix="timeseries/pnsg_indices_report",
    fileFormat="CSV",
    selectors=selectors,
)
task.start()
print(f"Tarea de export iniciada. Task ID: {task.id}")
print("Monitoriza en: https://code.earthengine.google.com/tasks")
print(f"Resultado → gs://{BUCKET}/timeseries/pnsg_indices_report.csv")
