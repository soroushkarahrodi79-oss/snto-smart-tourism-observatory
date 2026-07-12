"""
scripts/run_field_validation.py
===============================
Execute (or scaffold) the field-validation campaign of
``docs/field_validation_protocol.md`` for a park (issue #26).

Two modes:

  --init      Write a CSV recording template pre-seeded with the priority assets
              (measurement columns blank, to be filled in the field).
  (default)   Ingest a filled CSV + the real satellite trends, co-locate by
              asset, and emit a Markdown report with the satellite↔field
              Spearman correlation, the control–impact (BACI) contrast and the
              **confusion matrix** (satellite alert vs field-degraded).

Never fabricates ground-truth: with no measured plots the report states that
the campaign is pending rather than inventing agreement.

Uso:
    python scripts/run_field_validation.py --park pnsg --init
    python scripts/run_field_validation.py --park pnsg \\
        --observations clean_assets/field_validation/pnsg_field_observations.csv
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.platform.satellite_trends import load_asset_trends, park_label
from src.validation import (
    build_pairs,
    confusion_matrix,
    control_impact_contrast,
    field_index_by_asset,
    load_field_observations,
    split_impact_control,
    validate_satellite_vs_field,
    write_template,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_OUT_DIR = _ROOT / "clean_assets/field_validation"

# Priority assets to visit first (issue #26): the two PNSG assets with a
# significant NDVI trend. Coordinates from clean_assets/pnsg_assets.py. Each is
# seeded with one impact plot (on the corridor) and one control plot (same
# habitat, far from the trail); measurement columns stay blank.
_PRIORITY_SEED: dict[str, list[dict]] = {
    "pnsg": [
        {"plot_id": "porrones_impact_1",
         "asset_id": "pnsg_escalada_maliciosa_porrones",
         "lat": 40.7405, "lon": -3.9251, "distance_to_trail_m": 0,
         "is_control": "false", "stratum": "escalada-roquedo"},
        {"plot_id": "porrones_control_1",
         "asset_id": "pnsg_escalada_maliciosa_porrones",
         "lat": 40.7405, "lon": -3.9251, "distance_to_trail_m": 80,
         "is_control": "true", "stratum": "escalada-roquedo"},
        {"plot_id": "nevero_impact_1",
         "asset_id": "pnsg_vuelo_libre_el_nevero",
         "lat": 40.983965, "lon": -3.836133, "distance_to_trail_m": 0,
         "is_control": "false", "stratum": "vuelo-libre-pastizal"},
        {"plot_id": "nevero_control_1",
         "asset_id": "pnsg_vuelo_libre_el_nevero",
         "lat": 40.983965, "lon": -3.836133, "distance_to_trail_m": 80,
         "is_control": "true", "stratum": "vuelo-libre-pastizal"},
    ],
}


def _init(park: str) -> None:
    seed = _PRIORITY_SEED.get(park, [])
    if not seed:
        log.warning("No hay activos prioritarios sembrados para '%s'.", park)
    path = _OUT_DIR / f"{park}_field_observations_template.csv"
    write_template(path, seed)
    log.info("Plantilla de registro → %s (%d filas semilla).", path, len(seed))
    log.info("Rellena las columnas de medición en campo y ejecuta sin --init.")


def _render_report(park: str, observations: list, trends: list) -> str:
    trends_by_id = {t.asset_id: t for t in trends}
    idx_by_asset = field_index_by_asset(observations)
    measured = {k: v for k, v in idx_by_asset.items() if v is not None}
    impact, control = split_impact_control(observations)

    lines = [
        f"# Validación de campo — {park_label(park)}",
        "",
        "> Informe generado por `scripts/run_field_validation.py`. Refleja los "
        "datos de campo disponibles; no sobre-afirma validez.",
        "",
        f"- Plots totales: **{len(observations)}** "
        f"(impacto {len(impact)}, control {len(control)}).",
        f"- Activos con índice de campo medido: **{len(measured)}**.",
        "",
    ]

    if not measured:
        lines += [
            "## Estado: campaña pendiente",
            "",
            "No hay plots con mediciones (compactación / cobertura / erosión). "
            "La plantilla está lista pero la verdad-terreno aún no se ha "
            "recogido, así que **no se computan métricas de acuerdo** "
            "(no-negotiable: no inventar evidencia de validación).",
        ]
        return "\n".join(lines) + "\n"

    # Confusion matrix (satellite alert vs field degraded), per asset.
    pairs = build_pairs(trends_by_id, idx_by_asset)
    cm = confusion_matrix(pairs)
    lines += [
        "## Matriz de confusión satélite↔campo (clase positiva = alerta/degradado)",
        "",
        f"- n = **{cm.n}** activos co-localizados.",
        "",
        "| | Campo degradado | Campo sano |",
        "|---|:-:|:-:|",
        f"| **Satélite alerta** | {cm.tp} (TP) | {cm.fp} (FP) |",
        f"| **Satélite sin alerta** | {cm.fn} (FN) | {cm.tn} (TN) |",
        "",
        f"- Exactitud: {cm.accuracy} · Precisión: {cm.precision} · "
        f"Sensibilidad: {cm.recall} · F1: {cm.f1}",
        f"- Cohen's κ: **{cm.cohen_kappa}** — {cm.verdict}",
        "",
    ]

    # Continuous agreement + BACI over co-located plots with indices.
    sat_field_pairs = []
    for asset_id, fidx in measured.items():
        tr = trends_by_id.get(asset_id)
        if tr is not None and tr.sens_slope is not None:
            # satellite stress proxy: negative slope ⇒ degradation (stress up)
            sat_field_pairs.append((-tr.sens_slope * 1e4, fidx))
    if len(sat_field_pairs) >= 3:
        agr = validate_satellite_vs_field(sat_field_pairs)
        lines += [
            "## Correlación satélite↔campo (Spearman)",
            "",
            f"- ρ = **{agr.spearman}** (n={agr.n}) — {agr.verdict}",
            "",
        ]

    impact_idx = [o.degradation_index() for o in impact
                  if o.degradation_index() is not None]
    control_idx = [o.degradation_index() for o in control
                   if o.degradation_index() is not None]
    if impact_idx and control_idx:
        ci = control_impact_contrast(impact_idx, control_idx)
        lines += [
            "## Contraste control–impacto (BACI)",
            "",
            f"- Media impacto {ci.mean_impact} vs control {ci.mean_control} "
            f"(Δ={ci.delta}).",
            f"- Cliff's δ = **{ci.cliffs_delta}** — {ci.verdict}",
            "",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--park", default="pnsg", help="Slug del parque.")
    p.add_argument("--init", action="store_true",
                   help="Escribir plantilla de registro y salir.")
    p.add_argument("--observations", type=Path, default=None,
                   help="CSV de observaciones de campo rellenado.")
    args = p.parse_args()

    if args.init:
        _init(args.park)
        return

    obs_path = args.observations or (
        _OUT_DIR / f"{args.park}_field_observations.csv"
    )
    if not Path(obs_path).exists():
        log.error("No existe %s. Genera la plantilla con --init y rellénala.",
                  obs_path)
        return

    observations = load_field_observations(obs_path)
    trends = load_asset_trends(park=args.park)
    log.info("%s: %d observaciones, %d activos con tendencia satelital.",
             park_label(args.park), len(observations), len(trends))

    report = _render_report(args.park, observations, trends)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = _OUT_DIR / f"{args.park}_field_validation_report.md"
    out.write_text(report, encoding="utf-8")
    log.info("Informe → %s", out)


if __name__ == "__main__":
    main()
