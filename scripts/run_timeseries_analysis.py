"""
scripts/run_timeseries_analysis.py
====================================
Lee el CSV generado por extract_gee_timeseries_pnsg.py y produce:
  - Tendencias Mann-Kendall por asset (¿mejora o degradación 2021-2026?)
  - Resumen de anomalías por año (años secos/húmedos detectados)
  - Comparativa GEE vs datos sintéticos (MultiYearAdapter)
  - CSV de salida listo para el dashboard

Uso:
    python scripts/run_timeseries_analysis.py
    python scripts/run_timeseries_analysis.py --prewhiten
    python scripts/run_timeseries_analysis.py --input clean_assets/timeseries/pnsg_gee_timeseries.csv
    # v1.2.0 Red OAPN — un parque distinto de PNSG:
    python scripts/run_timeseries_analysis.py \
        --input clean_assets/timeseries/pn_tablas_daimiel_gee_timeseries.csv \
        --park pn_tablas_daimiel
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.time_series.changepoint import pettitt_test
from src.time_series.confidence import sens_slope_ci
from src.time_series.trend_detection import deseasonalized_mann_kendall

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_INPUT = Path("clean_assets/timeseries/pnsg_gee_timeseries.csv")
OUTPUT_DIR = Path("clean_assets/timeseries/analysis")

# Un año se considera PARCIAL si globalmente le faltan meses (p. ej. el año en
# curso sin verano). Esos años se excluyen del ranking peor/mejor año porque su
# media no es comparable con años completos. Umbral: < 10 meses distintos.
_MIN_MONTHS_FULL_YEAR = 10


# ── Mann-Kendall (implementación validada + desestacionalización) ─────────────
# El test de Mann-Kendall asume observaciones intercambiables bajo H0. En una
# serie NDVI MENSUAL la fenología (pico primaveral + valle estival) es una señal
# periódica fuerte que viola ese supuesto e infla artificialmente la
# significancia. Por eso este pipeline ya NO usa una MK propia sobre la serie
# cruda: desestacionaliza con la descomposición armónica validada
# (src/time_series/decomposition.py) y ejecuta el test validado
# (src/time_series/mann_kendall.py, con corrección de empates y Sen's slope)
# sobre la serie sin componente estacional. Ver docs/nota_metodologica_temporalidad.md.

# Mapea la etiqueta del módulo validado ('no_trend') a la histórica del
# dashboard ('no trend') para no romper src/platform/satellite_trends.py.
_TREND_LABEL_COMPAT = {
    "increasing": "increasing",
    "decreasing": "decreasing",
    "no_trend": "no trend",
}
_SEASONAL_PERIOD = 12  # serie mensual → ciclo anual


def _mk_series(series: list[float], prewhiten: bool = False) -> dict:
    """Mann-Kendall sobre una serie VI mensual, desestacionalizada cuando se puede.

    Devuelve un superconjunto del esquema histórico (tau/z/p_approx/trend/n) para
    que el cargador del dashboard siga funcionando, más:
      * ``sens_slope`` (que EHS necesita) y su intervalo de confianza 95 %
        no-paramétrico (Gilbert 1987) en ``sens_slope_ci``,
      * banderas de procedencia (``deseasonalised``, ``prewhitened``, ``method``).

    Con ``prewhiten=True`` aplica pre-whitening libre de tendencia (Yue-Pilon
    2002) sobre la serie desestacionalizada para descontar la autocorrelación
    serial de lag-1 antes del test.
    """
    n = len(series)
    if n < 4:
        return {
            "tau": 0.0, "z": 0.0, "p_approx": 1.0, "trend": "insufficient data",
            "sens_slope": 0.0, "sens_slope_ci": None, "is_significant": False, "n": n,
            "deseasonalised": False, "prewhitened": False,
            "lag1_autocorr": None, "seasonality_strength": None, "method": "none",
        }

    # Cadena compartida con el pipeline en vivo (src/time_series/trend_detection).
    tr = deseasonalized_mann_kendall(
        series, period=_SEASONAL_PERIOD, prewhiten=prewhiten
    )
    mk = tr.mk

    # Punto de cambio abrupto (Pettitt) sobre la serie desestacionalizada, ANTES
    # del pre-whitening: detecta el régimen de la sequía sin que el blanqueado
    # de tendencia altere la localización de la ruptura.
    cp = pettitt_test(tr.deseasonalized_series)
    ci = sens_slope_ci(tr.tested_series)

    method = "harmonic_deseasonalised" if tr.deseasonalised else "raw"
    if tr.prewhitened:
        method += "+yue_pilon_prewhiten"
    method += "+mann_kendall"

    return {
        "tau": round(mk.kendalls_tau, 3),
        "z": round(mk.z_score, 3),
        "p_approx": round(mk.p_value, 4),
        "trend": _TREND_LABEL_COMPAT.get(mk.trend_direction, "no trend"),
        "sens_slope": mk.sens_slope,
        "sens_slope_ci": [round(ci.lower, 6), round(ci.upper, 6)],
        "is_significant": mk.is_significant,
        "n": mk.n,
        "deseasonalised": tr.deseasonalised,
        "prewhitened": tr.prewhitened,
        "lag1_autocorr": tr.lag1_autocorr,
        "seasonality_strength": tr.seasonality_strength,
        "method": method,
        # Punto de cambio abrupto (índice 0-based en la propia serie).
        "change_point_index": cp.change_index,
        "change_point_p": cp.p_value,
        "change_point_significant": cp.is_significant,
    }


# ── Carga de datos ─────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Análisis ──────────────────────────────────────────────────────────────────

def _detect_partial_years(rows: list[dict]) -> set[str]:
    """Años con < _MIN_MONTHS_FULL_YEAR meses distintos a nivel global.

    Detecta el año en curso (sin verano) para excluirlo del ranking anual.
    """
    months_by_year: dict[str, set[int]] = defaultdict(set)
    for r in rows:
        if r.get("month"):
            months_by_year[r["year"]].add(int(r["month"]))
    return {yr for yr, months in months_by_year.items()
            if len(months) < _MIN_MONTHS_FULL_YEAR}


def analyse(rows: list[dict], prewhiten: bool = False) -> dict:
    partial_years = _detect_partial_years(rows)
    if partial_years:
        log.info("Años parciales detectados (excluidos del peor/mejor año): %s",
                 ", ".join(sorted(partial_years)))

    # Agrupar por asset_id
    by_asset: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_asset[r["asset_id"]].append(r)

    results = {}

    for asset_id, obs in by_asset.items():
        # Orden cronológico REAL: year/month vienen como str del CSV, así que
        # ordenar por el texto colocaría "10","11","12" antes que "2". Convertir
        # a int antes de ordenar es imprescindible para que la serie temporal
        # (y por tanto Mann-Kendall y la desestacionalización) sean correctas.
        obs_sorted = sorted(obs, key=lambda r: (int(r["year"]), int(r["month"])))
        ndvi_rows = [r for r in obs_sorted if r["ndvi"]]
        ndvi_series = [float(r["ndvi"]) for r in ndvi_rows]
        ndmi_series = [float(r["ndmi"]) for r in obs_sorted if r["ndmi"]]

        # Mann-Kendall sobre la serie desestacionalizada (ver _mk_series).
        mk_ndvi = _mk_series(ndvi_series, prewhiten=prewhiten)
        mk_ndmi = _mk_series(ndmi_series, prewhiten=prewhiten)

        # Fecha del punto de cambio NDVI: el índice mapea 1:1 a ndvi_rows porque
        # la desestacionalización conserva orden y longitud de la serie.
        cp_idx = mk_ndvi.get("change_point_index")
        change_point_date = (
            ndvi_rows[cp_idx].get("date")
            if cp_idx is not None and cp_idx < len(ndvi_rows) else None
        )

        # Promedio NDVI por año
        ndvi_by_year: dict[str, list[float]] = defaultdict(list)
        for r in obs:
            if r["ndvi"]:
                ndvi_by_year[r["year"]].append(float(r["ndvi"]))
        annual_ndvi = {yr: round(sum(v) / len(v), 4) for yr, v in ndvi_by_year.items()}

        # Peor/mejor año SOLO sobre años completos (comparación justa)
        full_year_ndvi = {yr: v for yr, v in annual_ndvi.items() if yr not in partial_years}
        if full_year_ndvi:
            worst_year = min(full_year_ndvi, key=full_year_ndvi.get)
            best_year  = max(full_year_ndvi, key=full_year_ndvi.get)
        else:
            worst_year = best_year = None

        # Categoría explícita (senderismo/ciclismo/…) si el CSV la trae (OAPN
        # v1.2.0). PNSG (v1.1.0) no la exporta → se omite y el cargador del
        # dashboard la infiere del asset_id. Persistirla aquí evita el parseo
        # posicional frágil con los ids multi-token de OAPN.
        category = next((r["category"] for r in obs if r.get("category")), None)

        results[asset_id] = {
            "n_observations": len(obs_sorted),
            **({"category": category} if category else {}),
            "mann_kendall_ndvi": mk_ndvi,
            "mann_kendall_ndmi": mk_ndmi,
            "change_point": {
                "date": change_point_date,
                "p_approx": mk_ndvi.get("change_point_p"),
                "significant": mk_ndvi.get("change_point_significant"),
            },
            "annual_mean_ndvi": annual_ndvi,
            "partial_years": sorted(partial_years),
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
    parser.add_argument(
        "--park", default="pnsg",
        help="Slug del parque → salida mk_trends_<park>.json (v1.2.0 Red OAPN). "
             "Por defecto 'pnsg'. Ej: pn_tablas_daimiel, pn_monfrague.",
    )
    parser.add_argument(
        "--prewhiten", action="store_true",
        help="Aplicar pre-whitening libre de tendencia (Yue-Pilon 2002) para "
             "descontar la autocorrelación de lag-1 antes de Mann-Kendall.",
    )
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

    log.info("\n=== Análisis Mann-Kendall NDVI/NDMI (serie multianual) ===")
    if args.prewhiten:
        log.info("Pre-whitening Yue-Pilon ACTIVADO (descuenta autocorrelación lag-1).")
    results = analyse(rows, prewhiten=args.prewhiten)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUTPUT_DIR / f"mk_trends_{args.park}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    log.info("\nResultados guardados en %s", out_json)

    # Resumen ejecutivo
    n_degrading  = sum(1 for r in results.values() if r["mann_kendall_ndvi"]["trend"] == "decreasing")
    n_improving  = sum(1 for r in results.values() if r["mann_kendall_ndvi"]["trend"] == "increasing")
    n_stable     = sum(1 for r in results.values() if r["mann_kendall_ndvi"]["trend"] == "no trend")

    n_changepoint = sum(
        1 for r in results.values() if r["change_point"]["significant"]
    )
    # Fecha de ruptura más frecuente (señal de evento común, p. ej. sequía 2022).
    cp_dates: dict[str, int] = defaultdict(int)
    for r in results.values():
        if r["change_point"]["significant"] and r["change_point"]["date"]:
            cp_dates[r["change_point"]["date"][:7]] += 1
    cp_top = max(cp_dates, key=cp_dates.get) if cp_dates else None

    log.info("\n=== RESUMEN EJECUTIVO ===")
    log.info("  Assets en degradación (↓ NDVI significativo): %d", n_degrading)
    log.info("  Assets en mejora      (↑ NDVI significativo): %d", n_improving)
    log.info("  Assets estables       (sin tendencia clara) : %d", n_stable)
    log.info("  Assets con punto de cambio abrupto (Pettitt p<0.05): %d", n_changepoint)
    if cp_top:
        log.info("  Mes de ruptura más frecuente: %s (%d activos)",
                 cp_top, cp_dates[cp_top])
    log.info("\nSiguiente paso → conectar %s al dashboard app.py", out_json)


if __name__ == "__main__":
    main()
