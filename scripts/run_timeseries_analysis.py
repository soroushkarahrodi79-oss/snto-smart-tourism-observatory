"""
scripts/run_timeseries_analysis.py
====================================
Lee el CSV generado por extract_gee_timeseries_pnsg.py y produce:
  - Tendencias Mann-Kendall por asset (¿mejora o degradación 2021-2025?)
  - Resumen de anomalías por año (años secos/húmedos detectados)
  - Comparativa GEE vs datos sintéticos (MultiYearAdapter)
  - CSV de salida listo para el dashboard

Uso:
    python scripts/run_timeseries_analysis.py
    python scripts/run_timeseries_analysis.py --input clean_assets/timeseries/pnsg_gee_timeseries_2021_2025.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_INPUT = Path("clean_assets/timeseries/pnsg_gee_timeseries_2021_2025.csv")
OUTPUT_DIR = Path("clean_assets/timeseries/analysis")


# ── Mann-Kendall simplificado ─────────────────────────────────────────────────

def mann_kendall(series: list[float]) -> dict:
    """
    Test de Mann-Kendall para tendencia monotónica.
    Retorna: tau, p_approx, trend ('increasing'|'decreasing'|'no trend')
    """
    n = len(series)
    if n < 4:
        return {"tau": 0.0, "p_approx": 1.0, "trend": "insufficient data", "n": n}

    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            diff = series[j] - series[i]
            if diff > 0:
                s += 1
            elif diff < 0:
                s -= 1

    # Varianza (sin grupos repetidos para simplicidad)
    var_s = n * (n - 1) * (2 * n + 5) / 18.0

    if s > 0:
        z = (s - 1) / var_s ** 0.5
    elif s < 0:
        z = (s + 1) / var_s ** 0.5
    else:
        z = 0.0

    # p aproximada con distribución normal estándar (aproximación)
    import math
    p = 2 * (1 - _norm_cdf(abs(z)))

    tau = s / (n * (n - 1) / 2.0)

    if p < 0.05:
        trend = "increasing" if s > 0 else "decreasing"
    else:
        trend = "no trend"

    return {"tau": round(tau, 3), "z": round(z, 3), "p_approx": round(p, 4), "trend": trend, "n": n}


def _norm_cdf(x: float) -> float:
    import math
    return (1.0 + math.erf(x / math.sqrt(2))) / 2.0


# ── Carga de datos ─────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Análisis ──────────────────────────────────────────────────────────────────

def analyse(rows: list[dict]) -> dict:
    # Agrupar por asset_id
    by_asset: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_asset[r["asset_id"]].append(r)

    results = {}

    for asset_id, obs in by_asset.items():
        obs_sorted = sorted(obs, key=lambda r: (r["year"], r["month"]))
        ndvi_series = [float(r["ndvi"]) for r in obs_sorted if r["ndvi"]]
        ndmi_series = [float(r["ndmi"]) for r in obs_sorted if r["ndmi"]]

        mk_ndvi = mann_kendall(ndvi_series)
        mk_ndmi = mann_kendall(ndmi_series)

        # Promedio NDVI por año
        ndvi_by_year: dict[str, list[float]] = defaultdict(list)
        for r in obs:
            if r["ndvi"]:
                ndvi_by_year[r["year"]].append(float(r["ndvi"]))
        annual_ndvi = {yr: round(sum(v) / len(v), 4) for yr, v in ndvi_by_year.items()}

        # Detectar año con menor/mayor NDVI
        if annual_ndvi:
            worst_year  = min(annual_ndvi, key=annual_ndvi.get)
            best_year   = max(annual_ndvi, key=annual_ndvi.get)
        else:
            worst_year = best_year = None

        results[asset_id] = {
            "n_observations": len(obs_sorted),
            "mann_kendall_ndvi": mk_ndvi,
            "mann_kendall_ndmi": mk_ndmi,
            "annual_mean_ndvi": annual_ndvi,
            "worst_ndvi_year": worst_year,
            "best_ndvi_year":  best_year,
            "ndvi_range": {
                "min": round(min(ndvi_series), 4) if ndvi_series else None,
                "max": round(max(ndvi_series), 4) if ndvi_series else None,
            },
        }

        trend_icon = {
            "increasing": "↑",
            "decreasing": "↓",
            "no trend":   "→",
        }.get(mk_ndvi["trend"], "?")
        log.info(
            "  %-35s NDVI %s %s (τ=%.3f, p=%.3f)  peor=%s mejor=%s",
            asset_id,
            trend_icon, mk_ndvi["trend"],
            mk_ndvi["tau"], mk_ndvi["p_approx"],
            worst_year, best_year,
        )

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    if not args.input.exists():
        log.error(
            "No se encontró %s\n"
            "Ejecuta primero: python scripts/extract_gee_timeseries_pnsg.py --project TU_PROYECTO",
            args.input,
        )
        return

    log.info("Cargando %s ...", args.input)
    rows = load_csv(args.input)
    log.info("%d observaciones cargadas.", len(rows))

    log.info("\n=== Análisis Mann-Kendall NDVI/NDMI (2021-2025) ===")
    results = analyse(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUTPUT_DIR / "mk_trends_pnsg.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log.info("\nResultados guardados en %s", out_json)

    # Resumen ejecutivo
    n_degrading  = sum(1 for r in results.values() if r["mann_kendall_ndvi"]["trend"] == "decreasing")
    n_improving  = sum(1 for r in results.values() if r["mann_kendall_ndvi"]["trend"] == "increasing")
    n_stable     = sum(1 for r in results.values() if r["mann_kendall_ndvi"]["trend"] == "no trend")

    log.info("\n=== RESUMEN EJECUTIVO ===")
    log.info("  Assets en degradación (↓ NDVI significativo): %d", n_degrading)
    log.info("  Assets en mejora      (↑ NDVI significativo): %d", n_improving)
    log.info("  Assets estables       (sin tendencia clara) : %d", n_stable)
    log.info("\nSiguiente paso → conectar %s al dashboard app.py", out_json)


if __name__ == "__main__":
    main()
