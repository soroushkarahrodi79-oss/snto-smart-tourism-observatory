"""
scripts/paper1/figure_02_pipeline.py
====================================
Paper-1 Figure 2: the analytical pipeline schematic, from Sentinel-2 to the
satellite↔field statistics, per ``docs/paper1/FIGURE_PLAN.md``. Boxes are
colour-coded by evidence class; exclusion/matching gates are drawn as gates
carrying their thresholds, so the transparency claim is visible at a glance.

No data inputs — this is a schematic. It still emits a provenance sidecar with
the commit hash so the figure version is traceable. Vector (PDF + SVG) output.

The evidence-class palette is the Okabe-Ito subset in ``_figutil`` (validated
CVD-safe); colour is never the sole channel — every box also carries text, and
the legend names each class.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.paper1._figutil import (  # noqa: E402
    EVIDENCE_COLORS,
    build_provenance,
    write_sidecar,
)

_OUT_DIR = _ROOT / "docs" / "paper1" / "figures"


def _box(ax, xy, w, h, text, cls, *, fontsize=8):
    from matplotlib.patches import FancyBboxPatch

    x, y = xy
    color = EVIDENCE_COLORS[cls]
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.2, edgecolor=color, facecolor=color + "22", zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, zorder=3, wrap=True)


def _gate(ax, xy, w, h, text):
    """A parallelogram gate carrying a threshold (constant/method colour)."""
    from matplotlib.patches import Polygon

    x, y = xy
    color = EVIDENCE_COLORS["constant"]
    skew = 0.18
    pts = [(x + skew, y), (x + w, y), (x + w - skew, y + h), (x, y + h)]
    ax.add_patch(Polygon(pts, closed=True, linewidth=1.1, edgecolor=color,
                         facecolor=color + "22", zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=6.8, style="italic", zorder=3)


def _arrow(ax, p0, p1):
    from matplotlib.patches import FancyArrowPatch

    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=11,
        linewidth=1.0, color="#555555", zorder=1))


def render() -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig, ax = plt.subplots(figsize=(9.0, 7.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    bw, bh = 3.2, 0.9

    # ── Satellite branch (left column, top→down) ──
    _box(ax, (0.4, 10.6), bw, bh, "Sentinel-2 L2A\ncomposite (T30TVL)", "real")
    _gate(ax, (0.4, 9.2), bw, bh, "SCL mask · excl. 3,5,6,8,9,10,11\n(class 5 retained at plot)")
    _box(ax, (0.4, 7.8), bw, bh, "NDVI (10 m) · NDMI (20 m)", "real")
    _box(ax, (0.4, 6.4), bw, bh, "per-scene P90 / P10\nanchors", "constant")
    _box(ax, (0.4, 5.0), bw, bh, "EHS at 20 m support cell", "real")

    for y0 in (10.6, 9.2, 7.8, 6.4):
        _arrow(ax, (2.0, y0), (2.0, y0 - 0.5))

    # ── Field branch (right column, top→down) ──
    _box(ax, (6.4, 10.6), bw, bh, "Field campaign\n5 subplots / 20 m plot", "real")
    _box(ax, (6.4, 9.2), bw, bh, "field degradation index\n(compaction·cover·erosion)", "real")
    _box(ax, (6.4, 7.8), bw, bh, "corridor mean\n(tread · verge · matrix)", "real")
    for y0 in (10.6, 9.2):
        _arrow(ax, (8.0, y0), (8.0, y0 - 0.5))

    # ── Matching gate (centre) ──
    _gate(ax, (3.4, 3.4), 3.2, 1.0, "plot ↔ 20 m cell matching\n≤ 30 d offset · ≥ 70 % valid px")
    _arrow(ax, (2.0, 5.0), (4.4, 4.4))     # EHS → matching
    _arrow(ax, (8.0, 7.8), (5.6, 4.4))     # corridor field mean → matching

    # ── Statistics (bottom) ──
    _box(ax, (3.4, 1.6), 3.2, 1.0,
         "Spearman ρ · Cliff's δ\nconfusion matrix / κ", "constant", fontsize=8)
    _arrow(ax, (5.0, 3.4), (5.0, 2.6))

    # ── Legend ──
    legend_items = [
        Patch(facecolor=EVIDENCE_COLORS["real"] + "22",
              edgecolor=EVIDENCE_COLORS["real"], label="REAL (satellite / field / cartography)"),
        Patch(facecolor=EVIDENCE_COLORS["constant"] + "22",
              edgecolor=EVIDENCE_COLORS["constant"], label="expert-set constant / method gate"),
    ]
    ax.legend(handles=legend_items, loc="lower left", fontsize=7,
              frameon=False, bbox_to_anchor=(0.0, -0.02))

    ax.set_title("SNTO satellite↔field validation pipeline (Paper 1)", fontsize=12)
    fig.text(0.5, 0.015,
             "Only REAL evidence enters the primary analysis (Contract §K). "
             "Thresholds shown are expert-set and uncalibrated until #26.",
             ha="center", fontsize=6.8)

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf = _OUT_DIR / "figure_02_pipeline.pdf"
    svg = _OUT_DIR / "figure_02_pipeline.svg"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    plt.close(fig)

    prov = build_provenance({}, params={"kind": "schematic", "no_data_inputs": True})
    write_sidecar(pdf, prov)
    write_sidecar(svg, prov)
    return pdf


if __name__ == "__main__":
    out = render()
    print(f"Figure 2 → {out}")
