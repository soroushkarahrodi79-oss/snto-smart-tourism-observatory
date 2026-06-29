"""
scripts/extract_gee_timeseries_pnsg.py
=======================================
Extrae series temporales NDVI/NDMI/EVI mensuales 2021-2025 para los assets
del PNSG usando Google Earth Engine → guarda CSV en clean_assets/timeseries/.

Este script alimenta DIRECTAMENTE el pipeline (time_series, risk_engine)
sin necesidad de descargar imágenes .SAFE completas (~800 MB cada una).

Ventajas sobre la descarga de .SAFE:
  - Extracción inmediata (~5 min para todos los assets vs ~50 GB de descarga)
  - Directamente consumible por src/time_series/ y src/risk_engine/
  - Cálculo de NDVI/NDMI/EVI con máscara SCL ya implementada en GEEAdapter

Autenticación GEE
-----------------
Necesitas un proyecto GEE. Opciones:
  a) Personal (más fácil):
       earthengine authenticate
       python scripts/extract_gee_timeseries_pnsg.py --project TU_PROYECTO_GEE

  b) Service account:
       python scripts/extract_gee_timeseries_pnsg.py --project TU_PROYECTO --key-file creds.json

Instalación
-----------
    pip install earthengine-api

Resultado
---------
  clean_assets/timeseries/
    pnsg_gee_timeseries_2021_2025.csv   ← todas las observaciones
    pnsg_gee_timeseries_2021_2025.json  ← formato para pipeline
    per_asset/
      {asset_id}_2021_2025.csv          ← una por asset

Uso rápido
----------
    python scripts/extract_gee_timeseries_pnsg.py --project snto-observatory-gee --dry-run
    python scripts/extract_gee_timeseries_pnsg.py --project snto-observatory-gee
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Permitir `import src.*` al ejecutar el script directamente desde scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Assets PNSG reales ─────────────────────────────────────────────────────────
# Cargados desde clean_assets/pnsg_assets.geojson (generado por
# scripts/build_pnsg_assets.py a partir de shapefiles oficiales PRUG).

YEARS = list(range(2021, 2026))
OUTPUT_DIR = Path("clean_assets/timeseries")
ASSETS_GEOJSON = Path("clean_assets/pnsg_assets.geojson")


# ── Construcción de TourismAsset desde el GeoJSON ─────────────────────────────

def _build_assets():
    """Construye objetos TourismAsset desde clean_assets/pnsg_assets.geojson."""
    import json

    from src.assets.models import AssetType, GeoJSONGeometry, GeometryType, TourismAsset

    if not ASSETS_GEOJSON.exists():
        raise FileNotFoundError(
            f"No se encontró {ASSETS_GEOJSON}.\n"
            f"Ejecuta primero: python scripts/build_pnsg_assets.py"
        )

    type_map = {
        "Point":      GeometryType.POINT,
        "LineString": GeometryType.LINESTRING,
        "Polygon":    GeometryType.POLYGON,
    }
    # El modelo valida que el geometry.type concuerde con el asset_type
    asset_type_map = {
        GeometryType.POINT:      AssetType.VIEWPOINT,
        GeometryType.LINESTRING: AssetType.TRAIL,
        GeometryType.POLYGON:    AssetType.RECREATIONAL_AREA,
    }

    fc = json.loads(ASSETS_GEOJSON.read_text(encoding="utf-8"))
    assets = []
    for feat in fc["features"]:
        props = feat["properties"]
        gtype = type_map[feat["geometry"]["type"]]
        assets.append(TourismAsset(
            asset_id=props["asset_id"],
            name=props.get("name", props["asset_id"]),
            asset_type=asset_type_map[gtype],
            geometry=GeoJSONGeometry(type=gtype, coordinates=feat["geometry"]["coordinates"]),
            region="PNSG",
            metadata={"category": props.get("category", "")},
        ))
    return assets


# ── Exportar resultados ────────────────────────────────────────────────────────

def _obs_to_row(obs) -> dict:
    row = {
        "asset_id":       obs.asset_id,
        "year":           obs.year,
        "month":          obs.month,
        "date":           f"{obs.year}-{obs.month:02d}-01",
        "ndvi":           round(obs.ndvi, 4),
        "ndmi":           round(obs.ndmi, 4),
        "evi":            round(obs.evi, 4) if obs.evi is not None else "",
        "cloud_cover_pct": obs.cloud_cover_pct,
        "data_source":    obs.data_source,
    }
    if obs.ndvi_stats:
        row["ndvi_mean"]   = round(obs.ndvi_stats.mean, 4)
        row["ndvi_median"] = round(obs.ndvi_stats.median, 4)
        row["ndvi_p25"]    = round(obs.ndvi_stats.p25, 4)
        row["ndvi_p75"]    = round(obs.ndvi_stats.p75, 4)
        row["ndvi_std"]    = round(obs.ndvi_stats.std, 4)
        row["valid_pix_pct"] = obs.ndvi_stats.valid_pixel_pct
    return row


def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    log.info("CSV guardado: %s (%d filas)", path, len(rows))


def save_json(all_obs: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "metadata": {
            "generated": datetime.utcnow().isoformat() + "Z",
            "tile": "T30TVL",
            "years": YEARS,
            "assets": len({o.asset_id for o in all_obs}),
            "observations": len(all_obs),
            "source": "GEE:COPERNICUS/S2_SR_HARMONIZED",
        },
        "observations": [_obs_to_row(o) for o in all_obs],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log.info("JSON guardado: %s", path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae series temporales PNSG 2021-2025 vía GEE")
    parser.add_argument("--project",  required=True, help="ID del proyecto GEE (ej: snto-observatory-gee)")
    parser.add_argument("--key-file", default="",   help="Ruta al JSON de service account (opcional)")
    parser.add_argument("--years",    nargs="+", type=int, default=YEARS)
    parser.add_argument("--assets",   nargs="+", default=[], help="IDs de assets a procesar (vacío = todos)")
    parser.add_argument("--dry-run",  action="store_true", help="Validar config sin llamar a GEE")
    args = parser.parse_args()

    # Construir assets desde el GeoJSON (no requiere GEE — valida config)
    assets = _build_assets()
    if args.assets:
        assets = [a for a in assets if a.asset_id in args.assets]
        if not assets:
            log.error("Ningún asset coincide con %s", args.assets)
            sys.exit(1)

    log.info("Assets a procesar: %d", len(assets))
    log.info("Años: %s", args.years)

    if args.dry_run:
        log.info("[DRY-RUN] Configuración válida. Assets:")
        for a in assets:
            log.info("  - %s (%s)", a.asset_id, a.geometry.type.value)
        return

    # Verificar que earthengine-api está instalado (solo ejecución real)
    try:
        import ee  # noqa: F401
    except ImportError:
        log.error(
            "earthengine-api no está instalado.\n"
            "  pip install earthengine-api\n"
            "  earthengine authenticate"
        )
        sys.exit(1)

    from src.ingestion.gee_adapter import GEEAdapter

    adapter = GEEAdapter(
        project_id=args.project,
        key_file=args.key_file,
    )

    all_observations = []
    per_asset_rows: dict[str, list[dict]] = {}

    for i, asset in enumerate(assets, 1):
        log.info("[%d/%d] Procesando %s ...", i, len(assets), asset.asset_id)
        try:
            obs_list = adapter.fetch_multiyear_time_series(asset, years=args.years)
        except Exception as exc:
            log.error("  Error en %s: %s", asset.asset_id, exc)
            continue

        all_observations.extend(obs_list)
        per_asset_rows[asset.asset_id] = [_obs_to_row(o) for o in obs_list]
        log.info("  → %d observaciones válidas", len(obs_list))

        # Guardar CSV individual por asset
        csv_asset_path = OUTPUT_DIR / "per_asset" / f"{asset.asset_id}_2021_2025.csv"
        save_csv(per_asset_rows[asset.asset_id], csv_asset_path)

    if not all_observations:
        log.error("No se obtuvieron observaciones. Verifica la autenticación GEE.")
        sys.exit(1)

    # Exportar todo
    all_rows = [_obs_to_row(o) for o in all_observations]
    save_csv(all_rows, OUTPUT_DIR / "pnsg_gee_timeseries_2021_2025.csv")
    save_json(all_observations, OUTPUT_DIR / "pnsg_gee_timeseries_2021_2025.json")

    log.info(
        "\n=== COMPLETO: %d observaciones para %d assets ===",
        len(all_observations), len(assets),
    )
    log.info("Siguiente paso → python scripts/run_timeseries_analysis.py")


if __name__ == "__main__":
    main()
