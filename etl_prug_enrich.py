"""
SNTO ETL — Enriquecimiento PRUG (zonificación oficial) de la salida del Pipeline A
===================================================================================
Asigna a cada senda real del PN Sierra de Guadarrama su ZONA del Plan Rector de
Uso y Gestión (PRUG) y calcula un índice de prioridad que combina la degradación
ecológica (EHS satelital) con el nivel de protección de la zona.

  priority_index = (100 − salud_verano) × peso_protección        (rango 0–100)

Una senda muy degradada (salud baja) en Zona de Reserva (peso 1.0) sube al tope
de prioridad; la misma degradación en Zona de Uso Especial (peso 0.25) baja.
Esto da MÁS EFICACIA a la priorización: invierte donde más valor de conservación
hay en juego, no solo donde hay más verdor perdido.

Pesos de protección (jerarquía PRUG, de mayor a menor restricción):
  Zona de Reserva          → 1.00
  Zona de Uso Restringido  → 0.75
  Zona de Uso Moderado     → 0.50
  Zona de Uso Especial     → 0.25
  (fuera de zonificación)  → 0.20

Entrada : data/outputs/pnsg/pipeline_a_results.geojson  (salida del Pipeline A)
          data/raw_assets/vector_data/oapn/oapn_prug_zonificacion.geojson
Salida  : reescribe pipeline_a_results.geojson añadiendo a cada feature:
          prug_zone, prug_protection_weight, priority_index

Uso:
    python etl_prug_enrich.py            # PNSG (único territorio con PRUG)
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import geopandas as gpd

_ROOT = Path(__file__).resolve().parent
RESULTS = _ROOT / "data" / "outputs" / "pnsg" / "pipeline_a_results.geojson"
PRUG = _ROOT / "data" / "raw_assets" / "vector_data" / "oapn" / "oapn_prug_zonificacion.geojson"
UTM = "EPSG:25830"

PROTECTION_WEIGHT: dict[str, float] = {
    "Zona de Reserva":         1.00,
    "Zona de Uso Restringido": 0.75,
    "Zona de Uso Moderado":    0.50,
    "Zona de Uso Especial":    0.25,
}
WEIGHT_OUTSIDE = 0.20  # senda fuera de la zonificación PRUG (p. ej. en la ZPP)

SEP = "=" * 72


def main() -> None:
    print(SEP)
    print("  SNTO ETL — Enriquecimiento PRUG de la salida del Pipeline A (PNSG)")
    print(SEP)
    for p in (RESULTS, PRUG):
        if not p.exists():
            print(f"  ERROR: falta {p}")
            sys.exit(1)

    fc = json.loads(RESULTS.read_text(encoding="utf-8"))
    feats = fc["features"]
    trails = gpd.GeoDataFrame.from_features(feats, crs="EPSG:4326").to_crs(UTM)
    trails["_idx"] = range(len(trails))

    prug = gpd.read_file(PRUG).to_crs(UTM)
    prug = prug[prug.geometry.notna() & ~prug.geometry.is_empty][["Zona", "geometry"]].copy()

    # Zona dominante por longitud de intersección: overlay líneas × polígonos,
    # medir longitud de cada tramo y quedarse con la zona de mayor longitud.
    inter = gpd.overlay(
        trails[["_idx", "geometry"]], prug, how="intersection", keep_geom_type=False
    )
    inter = inter[inter.geometry.geom_type.isin(["LineString", "MultiLineString"])].copy()
    inter["seg_len"] = inter.geometry.length

    dominant: dict[int, str] = {}
    if len(inter):
        agg = inter.groupby(["_idx", "Zona"])["seg_len"].sum().reset_index()
        idx_best = agg.groupby("_idx")["seg_len"].idxmax()
        for _, row in agg.loc[idx_best].iterrows():
            dominant[int(row["_idx"])] = row["Zona"]

    # Escribir atributos de vuelta a cada feature
    counts: dict[str, int] = {}
    reserva_degradadas = 0
    for i, feat in enumerate(feats):
        zone = dominant.get(i)  # None si la senda no intersecta ninguna zona
        weight = PROTECTION_WEIGHT.get(zone, WEIGHT_OUTSIDE)
        deg = feat["properties"].get("ehs_summer")  # convenio pipeline: 0=sano,100=degradado
        salud = (100.0 - deg) if deg is not None else None
        priority = round((100.0 - salud) * weight, 1) if salud is not None else None

        feat["properties"]["prug_zone"] = zone or "Fuera de zonificación"
        feat["properties"]["prug_protection_weight"] = weight
        feat["properties"]["priority_index"] = priority

        label = zone or "Fuera de zonificación"
        counts[label] = counts.get(label, 0) + 1
        if zone == "Zona de Reserva" and salud is not None and salud < 60:
            reserva_degradadas += 1

    RESULTS.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")

    print(f"  Sendas enriquecidas: {len(feats)}")
    print("  Reparto por zona PRUG (zona dominante por longitud):")
    for z, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>3}  {z}")
    print(f"  Sendas degradadas (salud<60) en Zona de Reserva: {reserva_degradadas}")
    print()
    # Top-5 por índice de prioridad combinado
    ranked = sorted(
        [f["properties"] for f in feats if f["properties"].get("priority_index") is not None],
        key=lambda p: p["priority_index"], reverse=True,
    )[:5]
    print("  TOP-5 prioridad combinada (degradación × protección):")
    for p in ranked:
        salud = 100 - p["ehs_summer"]
        print(f"    idx={p['priority_index']:>5}  salud={salud:5.1f}  {p['prug_zone']:<24} {p['name'][:34]}")
    print()
    print(f"  Reescrito: {RESULTS}")


if __name__ == "__main__":
    main()
