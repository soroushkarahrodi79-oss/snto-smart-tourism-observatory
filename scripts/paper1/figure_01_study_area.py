"""
scripts/paper1/figure_01_study_area.py
======================================
Paper-1 Figure 1(b): the PNSG trail network coloured by summer EHS (satellite
stress), over the park boundary. Real OAPN cartography × real Sentinel-2 signal
— producible today from committed data (``docs/paper1/FIGURE_PLAN.md``).

Inputs (committed):
  data/outputs/pnsg/pipeline_a_results.geojson   — 218 trails + ehs_summer
  data/raw_assets/vector_data/oapn/oapn_limite_pn.geojson — park boundary

Outputs (docs/paper1/figures/):
  figure_01_study_area.pdf   — vector
  figure_01_study_area.png   — 300 dpi preview
  *.provenance.json          — input SHA-256 + commit hash

Fails loudly (``MissingInput``) rather than rendering a partial figure if an
input is absent. Honest scale: EHS is shown on a fixed 0 → data-max cividis
ramp (no truncation); the distribution is floor-concentrated (Phase 0 §5), so
most of the network reads low — that is the real signal, not a display choice.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.paper1._figutil import (  # noqa: E402
    SEQUENTIAL_CMAP,
    build_provenance,
    require_inputs,
    write_sidecar,
)

_TRAILS = _ROOT / "data" / "outputs" / "pnsg" / "pipeline_a_results.geojson"
_BOUNDARY = _ROOT / "data" / "raw_assets" / "vector_data" / "oapn" / "oapn_limite_pn.geojson"
_OUT_DIR = _ROOT / "docs" / "paper1" / "figures"
_STRESS_COL = "ehs_summer"
_GRID_EPSG = 25830  # UTM 30N — the matching-support CRS (SPATIAL_MATCHING_PROTOCOL.md)


def _load():
    import geopandas as gpd

    trails = gpd.read_file(_TRAILS)
    if _STRESS_COL not in trails.columns:
        raise KeyError(
            f"{_TRAILS.name} lacks '{_STRESS_COL}' — cannot colour by satellite stress")
    boundary = gpd.read_file(_BOUNDARY)
    # Reproject to the metric grid CRS; set a CRS defensively if the file omits one.
    if trails.crs is None:
        trails = trails.set_crs(4326)
    if boundary.crs is None:
        boundary = boundary.set_crs(4326)
    return trails.to_crs(_GRID_EPSG), boundary.to_crs(_GRID_EPSG)


def render() -> Path:
    require_inputs({"trails": _TRAILS, "boundary": _BOUNDARY})

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize

    trails, boundary = _load()
    n = len(trails)
    vmax = float(trails[_STRESS_COL].max())
    norm = Normalize(vmin=0.0, vmax=vmax)

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.0, 8.0))

    boundary.boundary.plot(ax=ax, color="#444444", linewidth=1.0, zorder=1)
    trails.plot(ax=ax, column=_STRESS_COL, cmap=SEQUENTIAL_CMAP, norm=norm,
                linewidth=1.4, zorder=2)

    sm = ScalarMappable(cmap=SEQUENTIAL_CMAP, norm=norm)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("EHS verano (0 = sin estrés · 100 = degradación máxima)", fontsize=9)

    ax.set_title(
        "PNSG — red de sendas OAPN coloreada por EHS satelital (verano)", fontsize=11)
    ax.set_xlabel("Este (m, EPSG:25830)", fontsize=8)
    ax.set_ylabel("Norte (m, EPSG:25830)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_aspect("equal")

    # Honest caption: n, evidence class of each layer, CRS, scale note.
    caption = (
        f"n = {n} sendas (cartografía oficial OAPN, clase REAL) · "
        f"señal EHS Sentinel-2 verano (clase REAL, sin validación de campo — #26) · "
        f"EPSG:25830 · rampa 0–{vmax:.1f} sin truncar; "
        f"distribución concentrada en valores bajos (Phase 0 §5)."
    )
    fig.text(0.5, 0.02, caption, ha="center", va="bottom", fontsize=6.5, wrap=True)
    fig.subplots_adjust(bottom=0.10)

    pdf = _OUT_DIR / "figure_01_study_area.pdf"
    png = _OUT_DIR / "figure_01_study_area.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    prov = build_provenance(
        {"trails": _TRAILS, "boundary": _BOUNDARY},
        params={"stress_column": _STRESS_COL, "grid_epsg": _GRID_EPSG,
                "cmap": SEQUENTIAL_CMAP, "vmin": 0.0, "vmax": vmax, "n_trails": n},
    )
    write_sidecar(pdf, prov)
    write_sidecar(png, prov)
    return pdf


if __name__ == "__main__":
    out = render()
    print(f"Figure 1(b) → {out}")
