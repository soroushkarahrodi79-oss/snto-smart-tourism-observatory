"""
scripts/build_pnsg_assets.py
==============================
Extrae assets turísticos REALES del PNSG desde los shapefiles oficiales
(PRUG Castilla y León, EPSG:25830), los reproyecta a EPSG:4326 (lon/lat),
los simplifica para Earth Engine y produce:

  clean_assets/pnsg_assets.geojson   ← fuente única de verdad para GEE
  clean_assets/pnsg_assets.py        ← mismo set como lista Python importable

Categorías de assets extraídas:
  - vuelo_libre  : puntos de despegue de parapente (alta exposición visual)
  - escalada     : huella (convex hull) de cada escuela de escalada
  - ciclismo     : rutas ciclables más largas (corredores de uso intensivo)
  - reserva      : polígonos "Zona de Reserva" (máximo valor ecológico)

Cada asset reduce su geometría a un tamaño manejable para reduceRegion:
  - Puntos     → buffer conceptual aplicado luego en el adapter (50 m)
  - Líneas     → simplificadas a tolerancia 20 m, buffer 30 m en el adapter
  - Polígonos  → simplificados a tolerancia 20 m, limitados en nº de vértices

Uso:
    pip install geopandas pyproj
    python scripts/build_pnsg_assets.py
    python scripts/build_pnsg_assets.py --max-cycling 6 --simplify 25
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from pathlib import Path

import geopandas as gpd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

SHP_DIR = Path(
    "data/raw_assets/raster_data/PNSG/Datos complementarios/data/raw/am.ren_cyl_pnsg_prug_shp"
)
OUT_GEOJSON = Path("clean_assets/pnsg_assets.geojson")
OUT_PY = Path("clean_assets/pnsg_assets.py")

WGS84 = "EPSG:4326"


# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(text: str, prefix: str) -> str:
    """'Circo de Peñalara' → 'pnsg_escalada_circo_de_penalara'."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return f"pnsg_{prefix}_{text}"


def _round_coords(geom, ndigits: int = 6):
    """Mapea recursivamente las coordenadas redondeándolas (reduce tamaño JSON)."""
    if isinstance(geom, (list, tuple)):
        if geom and isinstance(geom[0], (int, float)):
            return [round(float(c), ndigits) for c in geom]
        return [_round_coords(g, ndigits) for g in geom]
    return geom


def _count_vertices(coords) -> int:
    if isinstance(coords, (list, tuple)):
        if coords and isinstance(coords[0], (int, float)):
            return 1
        return sum(_count_vertices(c) for c in coords)
    return 0


# ── Extractores por categoría ──────────────────────────────────────────────────

def extract_takeoffs() -> list[dict]:
    """Puntos de despegue de vuelo libre."""
    g = gpd.read_file(SHP_DIR / "ren_cyl_pnsg_actvs_vl_despegue.shp").to_crs(WGS84)
    assets = []
    for _, row in g.iterrows():
        geom = row.geometry
        # MultiPoint → tomar el primer punto representativo
        pt = geom.geoms[0] if geom.geom_type == "MultiPoint" else geom
        assets.append({
            "asset_id": slugify(row["nombre"], "vuelo_libre"),
            "name": str(row["nombre"]),
            "category": "vuelo_libre",
            "geom_type": "POINT",
            "coordinates": _round_coords([pt.x, pt.y]),
        })
    return assets


def extract_climbing(simplify_m: float) -> list[dict]:
    """Huella (convex hull) de cada escuela de escalada."""
    g = gpd.read_file(SHP_DIR / "ren_cyl_pnsg_actvs_zonas_escal.shp")
    assets = []
    for escuela, group in g.dissolve(by="escuela").iterrows():
        if escuela is None:
            continue
        hull = group.geometry.convex_hull.simplify(simplify_m)
        hull_wgs = gpd.GeoSeries([hull], crs=g.crs).to_crs(WGS84).iloc[0]
        if hull_wgs.geom_type != "Polygon":
            continue
        coords = [list(hull_wgs.exterior.coords)]
        assets.append({
            "asset_id": slugify(escuela, "escalada"),
            "name": f"Escuela de escalada {escuela}",
            "category": "escalada",
            "geom_type": "POLYGON",
            "coordinates": _round_coords([[list(c) for c in coords[0]]]),
        })
    return assets


def extract_cycling(simplify_m: float, max_n: int) -> list[dict]:
    """Rutas ciclables más largas (corredores de uso intensivo)."""
    g = gpd.read_file(SHP_DIR / "ren_cyl_pnsg_actvs_vias_cicl.shp")
    g = g[g.geometry.geom_type == "LineString"].sort_values("longitud", ascending=False).head(max_n)
    g = g.to_crs(WGS84)
    assets = []
    for _, row in g.iterrows():
        line = row.geometry.simplify(simplify_m / 111_000.0)  # grados aprox
        coords = [list(c) for c in line.coords]
        assets.append({
            "asset_id": slugify(row["nombre"], "ciclismo"),
            "name": str(row["nombre"]),
            "category": "ciclismo",
            "geom_type": "LINESTRING",
            "coordinates": _round_coords(coords),
        })
    return assets


def extract_reserve(simplify_m: float, max_n: int) -> list[dict]:
    """Polígonos Zona de Reserva (máximo valor ecológico), mayores por área."""
    g = gpd.read_file(SHP_DIR / "ren_cyl_pnsg_zonific.shp")
    g = g[g["zonifica"] == "Zona de Reserva"].copy()
    g["_area"] = g.geometry.area
    g = g.sort_values("_area", ascending=False).head(max_n)
    assets = []
    for _, row in g.iterrows():
        simp = row.geometry.simplify(simplify_m)
        simp_wgs = gpd.GeoSeries([simp], crs=g.crs).to_crs(WGS84).iloc[0]
        # MultiPolygon → quedarnos con el anillo del polígono mayor
        poly = max(simp_wgs.geoms, key=lambda p: p.area) if simp_wgs.geom_type == "MultiPolygon" else simp_wgs
        if poly.geom_type != "Polygon":
            continue
        coords = [[list(c) for c in poly.exterior.coords]]
        assets.append({
            "asset_id": slugify(row["nombre"], "reserva"),
            "name": str(row["nombre"]),
            "category": "reserva",
            "geom_type": "POLYGON",
            "coordinates": _round_coords(coords),
        })
    return assets


# ── Salida ─────────────────────────────────────────────────────────────────────

def write_geojson(assets: list[dict]) -> None:
    features = []
    for a in assets:
        features.append({
            "type": "Feature",
            "properties": {
                "asset_id": a["asset_id"],
                "name": a["name"],
                "category": a["category"],
                "geom_type": a["geom_type"],
            },
            "geometry": {
                "type": a["geom_type"].capitalize() if a["geom_type"] != "LINESTRING" else "LineString",
                "coordinates": a["coordinates"],
            },
        })
    fc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
          "features": features}
    OUT_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=1, ensure_ascii=False)
    log.info("GeoJSON escrito: %s (%d assets)", OUT_GEOJSON, len(assets))


def write_python(assets: list[dict]) -> None:
    lines = [
        '"""Auto-generado por scripts/build_pnsg_assets.py — NO editar a mano."""',
        "# Assets reales del PNSG extraídos de shapefiles PRUG (EPSG:4326).",
        "# Formato: (asset_id, geom_type, coordinates, name, category)",
        "",
        "PNSG_ASSETS = [",
    ]
    for a in assets:
        lines.append(
            f"    ({a['asset_id']!r}, {a['geom_type']!r}, {a['coordinates']!r}, "
            f"{a['name']!r}, {a['category']!r}),"
        )
    lines.append("]")
    OUT_PY.parent.mkdir(parents=True, exist_ok=True)
    OUT_PY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Python escrito: %s", OUT_PY)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--simplify", type=float, default=20.0, help="Tolerancia simplificación (m)")
    p.add_argument("--max-cycling", type=int, default=6, help="Nº rutas ciclables (top por longitud)")
    p.add_argument("--max-reserve", type=int, default=5, help="Nº zonas de reserva (top por área)")
    args = p.parse_args()

    if not SHP_DIR.exists():
        log.error("No se encontró el directorio de shapefiles: %s", SHP_DIR)
        return

    log.info("Extrayendo assets reales del PNSG...")
    assets: list[dict] = []
    assets += extract_takeoffs()
    assets += extract_climbing(args.simplify)
    assets += extract_cycling(args.simplify, args.max_cycling)
    assets += extract_reserve(args.simplify, args.max_reserve)

    # Resumen por categoría + control de tamaño de geometría
    by_cat: dict[str, int] = {}
    for a in assets:
        by_cat[a["category"]] = by_cat.get(a["category"], 0) + 1
        nv = _count_vertices(a["coordinates"])
        if nv > 200:
            log.warning("  %s tiene %d vértices — considera subir --simplify", a["asset_id"], nv)

    log.info("Total: %d assets → %s", len(assets), by_cat)
    for a in assets:
        log.info("  [%s] %s (%s)", a["category"], a["asset_id"], a["geom_type"])

    write_geojson(assets)
    write_python(assets)
    log.info("\nListo. Los scripts GEE ahora pueden leer clean_assets/pnsg_assets.geojson")


if __name__ == "__main__":
    main()
