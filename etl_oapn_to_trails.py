"""
SNTO ETL — Sendas oficiales OAPN → esquema del Pipeline A
==========================================================
Convierte data/raw_assets/vector_data/oapn/oapn_itinerarios.geojson (225 sendas
oficiales del PN Sierra de Guadarrama, descargadas por etl_oapn_wfs.py) al
esquema que consume el Pipeline A: {id, name, highway, sac_scale} + geometría.

Mapeo de dificultad → sac_scale (clasificación senderista del proyecto):
    Baja / 01            → hiking
    Media / 02           → mountain_hiking
    Alta / 03            → demanding_mountain_hiking
    (vacío / None)       → null

Salida: data/raw_assets/vector_data/pnsg_oapn_trails.geojson
Esta pasa a ser la cartografía OFICIAL de PNSG (territories.py la referencia).

Uso:
    python etl_oapn_to_trails.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent
SRC = _ROOT / "data" / "raw_assets" / "vector_data" / "oapn" / "oapn_itinerarios.geojson"
OUT = _ROOT / "data" / "raw_assets" / "vector_data" / "pnsg_oapn_trails.geojson"

PARK_NAME = "Parque Nacional de la Sierra de Guadarrama"

_DIFICULTAD_SAC: dict[str, str] = {
    "baja": "hiking",
    "media": "mountain_hiking",
    "alta": "demanding_mountain_hiking",
    "01": "hiking",
    "02": "mountain_hiking",
    "03": "demanding_mountain_hiking",
}


def _sac(dificultad) -> str | None:
    if dificultad is None:
        return None
    key = str(dificultad).strip().lower()
    return _DIFICULTAD_SAC.get(key)


def _highway(tipo_acceso) -> str:
    t = (tipo_acceso or "").lower()
    # "Pista"/"Carril" en el nombre suelen ser pistas; por acceso lo dejamos en path
    return "path" if "pie" in t else "track"


def main() -> None:
    print("=" * 72)
    print("  SNTO ETL — Sendas oficiales OAPN → esquema Pipeline A")
    print("=" * 72)
    if not SRC.exists():
        print(f"  ERROR: no existe {SRC}")
        print("  Ejecuta antes: python etl_oapn_wfs.py")
        sys.exit(1)

    fc = json.loads(SRC.read_text(encoding="utf-8"))
    feats_out = []
    skipped = 0
    sac_counts: dict[str, int] = {}
    for i, f in enumerate(fc.get("features", []), start=1):
        p = f.get("properties", {})
        geom = f.get("geometry")
        name = (p.get("Nombre") or "").strip()
        # Solo Guadarrama, con nombre y geometría lineal
        if p.get("Nombre Parque") != PARK_NAME:
            skipped += 1
            continue
        if not name or not geom or geom.get("type") not in ("LineString", "MultiLineString"):
            skipped += 1
            continue
        sac = _sac(p.get("Dificultad"))
        sac_counts[str(sac)] = sac_counts.get(str(sac), 0) + 1
        feats_out.append({
            "type": "Feature",
            "properties": {
                "id": 500000000 + i,                 # rango OAPN, no colisiona con OSM
                "name": name,
                "highway": _highway(p.get("Tipo Acceso")),
                "sac_scale": sac,
                "oapn_id": p.get("id"),
                "tipo_acceso": p.get("Tipo Acceso"),
                "dificultad": p.get("Dificultad") or None,
            },
            "geometry": geom,
        })

    out_fc = {"type": "FeatureCollection", "features": feats_out}
    OUT.write_text(json.dumps(out_fc, ensure_ascii=False), encoding="utf-8")

    print(f"  Entrada : {SRC.name}  ({len(fc.get('features', []))} features)")
    print(f"  Salida  : {OUT.name}  ({len(feats_out)} sendas oficiales)")
    print(f"  Omitidas: {skipped}")
    print(f"  sac_scale: {sac_counts}")
    print(f"  Ruta: {OUT}")


if __name__ == "__main__":
    main()
