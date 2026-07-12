"""
scripts/export_gis.py
=====================
Exporta los activos de un parque + su tendencia satelital real + nivel de
evidencia como capa GIS (GeoJSON siempre; GeoPackage si geopandas está
disponible), lista para QGIS/ArcGIS (issue #25).

Uso:
    python scripts/export_gis.py                         # PNSG → GeoJSON + GPKG
    python scripts/export_gis.py --park pn_monfrague
    python scripts/export_gis.py --assets ruta/assets.geojson --no-gpkg
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.platform.satellite_trends import load_asset_trends, park_label
from src.reporting.gis_export import (
    build_feature_collection,
    export_geojson,
    export_geopackage,
)
from src.temporal.manifest import DataStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_DEFAULT_ASSETS = {"pnsg": _ROOT / "clean_assets/pnsg_assets.geojson"}
_OUT_DIR = _ROOT / "clean_assets/gis_export"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--park", default="pnsg", help="Slug del parque (v1.2.0 Red OAPN).")
    p.add_argument("--assets", type=Path, default=None,
                   help="GeoJSON de activos. Por defecto, el del parque si existe.")
    p.add_argument("--no-gpkg", action="store_true",
                   help="No intentar exportar GeoPackage (solo GeoJSON).")
    args = p.parse_args()

    assets_path = args.assets or _DEFAULT_ASSETS.get(args.park)
    if assets_path is None or not Path(assets_path).exists():
        log.error("No hay GeoJSON de activos para '%s'. Pasa --assets ruta.geojson.",
                  args.park)
        return

    with open(assets_path, encoding="utf-8") as f:
        assets = json.load(f)
    trends = load_asset_trends(park=args.park)
    log.info("%s: %d activos, %d con tendencia real.",
             park_label(args.park), len(assets.get("features", [])), len(trends))

    fc = build_feature_collection(
        assets, trends, evidence_level=DataStatus.REAL, park=args.park,
    )
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    gj = export_geojson(fc, _OUT_DIR / f"{args.park}_snto.geojson")
    log.info("GeoJSON → %s", gj)

    if not args.no_gpkg:
        try:
            gpkg = export_geopackage(fc, _OUT_DIR / f"{args.park}_snto.gpkg")
            log.info("GeoPackage → %s", gpkg)
        except RuntimeError as exc:
            log.warning("GeoPackage omitido: %s", exc)

    with_trend = fc["metadata"]["features_with_trend"]
    log.info("Hecho. %d features, %d con tendencia. Nivel de evidencia: %s.",
             fc["metadata"]["feature_count"], with_trend,
             fc["metadata"]["evidence_level"])


if __name__ == "__main__":
    main()
