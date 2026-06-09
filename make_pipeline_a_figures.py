"""
SNTO — Figuras del Pipeline A (Sierra del Rincón)
==================================================
Genera, a partir de los resultados de run_pipeline_a_filemode.py:
  1. docs/figures/ehs_map.png          — mapa de senderos coloreados por EHS_verano
  2. docs/figures/delta_ehs_hist.png   — histograma de ΔEHS (alerta estacional)
  3. docs/figures/scm_breakdown.png    — desglose de la clasificación causal SCM

Entrada:
  data/outputs/pipeline_a_results.csv                  (cifras por sendero)
  data/raw_assets/vector_data/hiking_trails.geojson    (geometrías OSM)
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from shapely.ops import linemerge, unary_union

_ROOT = Path(__file__).resolve().parent
CSV = _ROOT / "data" / "outputs" / "pipeline_a_results.csv"
TRAILS = _ROOT / "data" / "raw_assets" / "vector_data" / "hiking_trails.geojson"
FIGDIR = _ROOT / "docs" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

SCM_COLORS = {
    "LOCALIZED_IMPACT": "#d7191c",
    "MIXED": "#fdae61",
    "LANDSCAPE_DRIVEN": "#1a9641",
}


def load_geometries() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(TRAILS)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    merged = []
    for name, grp in gdf.groupby("name"):
        geom = unary_union(list(grp.geometry.values))
        try:
            geom = linemerge(geom)
        except Exception:
            pass
        merged.append({"name": name, "geometry": geom})
    return gpd.GeoDataFrame(merged, crs="EPSG:4326").to_crs("EPSG:25830")


def main() -> None:
    df = pd.read_csv(CSV)
    geo = load_geometries()
    g = geo.merge(df, on="name", how="inner")
    print(f"Senderos unidos: {len(g)} / {len(df)} filas CSV")

    # ── Figura 1: mapa EHS_verano ─────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 9))
    g.plot(
        ax=ax, column="ehs_summer", cmap="RdYlGn_r", linewidth=2.2,
        legend=True, legend_kwds={"label": "EHS verano  (alto = peor estado ecológico)",
                                  "shrink": 0.6},
    )
    # Resaltar top-5 por delta_ehs con etiqueta
    top5 = g.sort_values("delta_ehs", ascending=False).head(5)
    for _, r in top5.iterrows():
        c = r.geometry.centroid
        ax.annotate(r["name"][:22], xy=(c.x, c.y), fontsize=7, color="black",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="0.5", alpha=0.8))
    ax.set_title("Salud ambiental por sendero (EHS verano) — Reserva de la Biosfera Sierra del Rincón\n"
                 "73 senderos · 149,4 km · Sentinel-2 (modo NDVI-only)", fontsize=11)
    ax.set_xlabel("Easting (EPSG:25830, m)"); ax.set_ylabel("Northing (m)")
    ax.ticklabel_format(style="plain")
    fig.tight_layout()
    fig.savefig(FIGDIR / "ehs_map.png", dpi=150)
    plt.close(fig)
    print("OK ehs_map.png")

    # ── Figura 2: histograma ΔEHS ─────────────────────────────────────────────
    d = df["delta_ehs"].dropna()
    n_pos = int((d > 0).sum())
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.hist(d, bins=24, color="#4575b4", edgecolor="white")
    ax.axvline(0, color="#d7191c", linestyle="--", linewidth=1.6)
    ax.axvline(d.mean(), color="black", linestyle=":", linewidth=1.4,
               label=f"media = {d.mean():.2f}")
    ax.set_title("Distribución de ΔEHS (EHS verano − EHS primavera) — señal de alerta estacional", fontsize=11)
    ax.set_xlabel("ΔEHS  (>0 = degradación amplificada hacia el verano)")
    ax.set_ylabel("nº de senderos")
    ax.annotate(f"{n_pos} / {len(d)} senderos\ncon ΔEHS > 0 (alerta)",
                xy=(0.97, 0.92), xycoords="axes fraction", ha="right", va="top",
                fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="#fde0dd", ec="#d7191c"))
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGDIR / "delta_ehs_hist.png", dpi=150)
    plt.close(fig)
    print("OK delta_ehs_hist.png")

    # ── Figura 3: desglose SCM ────────────────────────────────────────────────
    counts = df["scm_class"].value_counts()
    order = ["LOCALIZED_IMPACT", "MIXED", "LANDSCAPE_DRIVEN"]
    vals = [int(counts.get(k, 0)) for k in order]
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(order, vals, color=[SCM_COLORS[k] for k in order], edgecolor="white")
    for b, v in zip(bars, vals):
        ax.annotate(str(v), xy=(b.get_x() + b.get_width() / 2, v), ha="center",
                    va="bottom", fontsize=11, fontweight="bold")
    ax.set_title("Atribución causal de la degradación (SCM) — 73 senderos", fontsize=11)
    ax.set_ylabel("nº de senderos")
    ax.set_ylim(0, max(vals) * 1.18)
    fig.tight_layout()
    fig.savefig(FIGDIR / "scm_breakdown.png", dpi=150)
    plt.close(fig)
    print("OK scm_breakdown.png")

    print(f"Figuras en: {FIGDIR}")


if __name__ == "__main__":
    main()
