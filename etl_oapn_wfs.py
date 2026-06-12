"""
SNTO ETL — Descarga e integración de capas oficiales OAPN (WFS)
================================================================
Los KML del OAPN en data/raw_assets/raster_data/PNSG/ son NetworkLinks a un
GeoServer (https://sigred.oapn.es/geoserverOAPN/). Este script descarga la
GEOMETRÍA REAL vía WFS GetFeature (GeoJSON), recorta cada capa al bbox del
Parque Nacional Sierra de Guadarrama y guarda GeoJSON limpios en
data/raw_assets/vector_data/oapn/.

Capas (workspace : view):
  LimitesParquesNacionalesZPP_visor : view_red_oapn_limite_pn_visor   (límite PN)
  LimitesParquesNacionalesZPP_visor : view_red_oapn_zpp_visor         (zona perif.)
  UsoPublico_visor                  : view_vis_oapn_itinerarios_visor (sendas oficiales)
  UsoPublico_visor                  : view_vis_oapn_iti_bici_visor     (rutas bici)
  SistemasNaturales_visor           : view_snl_vegetacion_visor       (vegetación)
  AreasInfluenciaSocioeconomica_visor : view_red_oapn_influencia_socioeconomica_visor

Uso:
    python etl_oapn_wfs.py
"""
from __future__ import annotations

import io
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import geopandas as gpd
from shapely.geometry import box

_ROOT = Path(__file__).resolve().parent
OUT_DIR = _ROOT / "data" / "raw_assets" / "vector_data" / "oapn"

BASE = "https://sigred.oapn.es/geoserverOAPN"

# bbox PNSG (W, S, E, N) en EPSG:4326 — coincide con territories.py
PNSG_BBOX = (-4.21, 40.65, -3.58, 41.08)

# (workspace, layer, nombre_salida)
LAYERS = [
    ("LimitesParquesNacionalesZPP_visor", "view_red_oapn_limite_pn_visor",   "oapn_limite_pn"),
    ("LimitesParquesNacionalesZPP_visor", "view_red_oapn_zpp_visor",         "oapn_zpp"),
    ("UsoPublico_visor",                  "view_vis_oapn_itinerarios_visor", "oapn_itinerarios"),
    ("UsoPublico_visor",                  "view_vis_oapn_iti_bici_visor",    "oapn_iti_bici"),
    ("UsoPublico_visor",                  "view_vis_oapn_centros_ptos_info_visor", "oapn_centros_info"),
    ("ZonificacionPRUG_visor",            "view_zon_zonificacion_prug_visor", "oapn_prug_zonificacion"),
    ("SistemasNaturales_visor",           "view_snl_vegetacion_visor",       "oapn_vegetacion"),
    ("AreasInfluenciaSocioeconomica_visor", "view_red_oapn_influencia_socioeconomica_visor", "oapn_influencia_socioec"),
]

SEP = "=" * 72


def wfs_url(workspace: str, layer: str) -> str:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": f"{workspace}:{layer}",
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",   # fuerza salida lon,lat (GeoJSON estándar)
    }
    return f"{BASE}/{workspace}/wfs?" + urllib.parse.urlencode(params)


def fetch(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "SNTO-ETL/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def main() -> None:
    print(SEP)
    print("  SNTO ETL — Capas oficiales OAPN (WFS) → recorte PNSG")
    print(f"  GeoServer: {BASE}")
    print(f"  bbox PNSG: {PNSG_BBOX}")
    print(SEP)
    print()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clip = gpd.GeoDataFrame(geometry=[box(*PNSG_BBOX)], crs="EPSG:4326")

    # Filtro opcional: subcadenas de nombre. Ej: python etl_oapn_wfs.py prug centros
    filters = [a.lower() for a in sys.argv[1:]]
    layers = [l for l in LAYERS if not filters or any(f in l[2].lower() for f in filters)]
    if filters:
        print(f"  Filtro activo: {filters} → {len(layers)} capa(s)\n")

    results = []
    for workspace, layer, out_name in layers:
        url = wfs_url(workspace, layer)
        print(f"  ▶ {out_name}")
        try:
            t0 = time.time()
            raw = fetch(url)
            dt = time.time() - t0
            tmp = OUT_DIR / f"_{out_name}_full.geojson"
            tmp.write_bytes(raw)
            gdf = gpd.read_file(tmp)
            n_total = len(gdf)
            if gdf.crs is None:
                gdf = gdf.set_crs(epsg=4326)
            elif gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(epsg=4326)

            # Recorte espacial a PNSG (intersección con el bbox)
            pnsg = gpd.sjoin(gdf, clip, predicate="intersects", how="inner")
            pnsg = pnsg.drop(columns=[c for c in pnsg.columns if c.startswith("index_")], errors="ignore")
            n_pnsg = len(pnsg)

            out_path = OUT_DIR / f"{out_name}.geojson"
            if n_pnsg > 0:
                pnsg.to_file(out_path, driver="GeoJSON")
            tmp.unlink(missing_ok=True)

            geom_types = sorted(set(pnsg.geometry.geom_type)) if n_pnsg else []
            print(f"      {n_total} features (red) → {n_pnsg} en PNSG  "
                  f"[{','.join(geom_types) or '—'}]  ({len(raw)//1024} KB, {dt:.1f}s)")
            results.append((out_name, n_total, n_pnsg, geom_types))
        except Exception as exc:
            print(f"      ERROR: {type(exc).__name__}: {exc}")
            results.append((out_name, -1, -1, []))
        print()

    print(SEP)
    print("  RESUMEN")
    print(SEP)
    for name, nt, npn, gt in results:
        status = "OK" if npn > 0 else ("VACÍO/ERROR" if npn <= 0 else "")
        print(f"  {name:<26} red={nt:>5}  PNSG={npn:>4}  {','.join(gt):<20} [{status}]")
    print()
    print(f"  Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
