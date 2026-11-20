#!/usr/bin/env python
# ruff: noqa: E501
"""Build the self-contained static SNTO evidence snapshot (``site/index.html``).

WHY
===
The Azure-hosted dashboard was suspended for cost reasons. This script produces
a single HTML file — no backend, no database, no network requests, no external
scripts/fonts/tiles — from the evidence already versioned in ``clean_assets/``:

  * ``pnsg_assets.geojson``                 — 21 PNSG assets (point geometry);
  * ``timeseries/pnsg_gee_timeseries.csv``  — monthly Sentinel-2 NDVI series;
  * ``timeseries/analysis/mk_trends_pnsg.json`` — seasonally adjusted
    Mann-Kendall trends (read through ``src.platform.satellite_trends``).

SCOPE (deliberately narrow — see docs/product/static-demo-options.md)
=====================================================================
Only *derived Sentinel-2 vegetation-index* evidence (claim ladder L2). It never
renders alerts, budgets, simulations, forecasts or any SYNTHETIC/SIMULATED
value, and it makes no statement about visitor pressure, causation, field
validation (#26) or management action.

The output is deterministic (no timestamps from the clock) so
``--check`` can gate drift in CI/tests.

Usage:
    python scripts/build_static_report.py            # write site/index.html
    python scripts/build_static_report.py --check    # exit 1 if out of date
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src._version import __version__  # noqa: E402
from src.platform.satellite_trends import AssetTrend, load_asset_trends  # noqa: E402

ASSETS = ROOT / "clean_assets" / "pnsg_assets.geojson"
SERIES = ROOT / "clean_assets" / "timeseries" / "pnsg_gee_timeseries.csv"
OUT = ROOT / "site" / "index.html"

DOI = "https://doi.org/10.5281/zenodo.20818269"
REPO = "https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory"

# Trend label + marker shape. Wording is descriptive of the *index* only:
# a NDVI change is not impact, pressure or "degradation" of the trail.
_TREND = {
    "increasing": ("NDVI en aumento", "up"),
    "decreasing": ("NDVI en descenso", "down"),
}
_DEFAULT_TREND = ("Sin tendencia significativa", "dot")
_COLOR = {"up": "#1b7f5c", "down": "#b4531a", "dot": "#6b7280"}


def _trend_label(t: AssetTrend) -> tuple[str, str]:
    if not t.significant:
        return _DEFAULT_TREND
    return _TREND.get(t.trend, _DEFAULT_TREND)


def _read_series_span() -> tuple[str, str, int]:
    dates, n = [], 0
    with SERIES.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            dates.append(row["date"])
            n += 1
    return min(dates), max(dates), n


def _marker(shape: str, x: float, y: float, r: float = 6.0) -> str:
    c = _COLOR[shape]
    if shape == "up":
        pts = f"{x:.1f},{y - r:.1f} {x - r:.1f},{y + r:.1f} {x + r:.1f},{y + r:.1f}"
    elif shape == "down":
        pts = f"{x:.1f},{y + r:.1f} {x - r:.1f},{y - r:.1f} {x + r:.1f},{y - r:.1f}"
    else:
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 0.8:.1f}" fill="{c}"/>'
    return f'<polygon points="{pts}" fill="{c}"/>'


def _anchor(g: dict | None) -> tuple[float, float] | None:
    """Representative point: the vertex mean (NOT a true centroid) of any geometry."""
    if not g:
        return None
    if g["type"] == "Point":
        return tuple(g["coordinates"][:2])
    if g["type"] == "LineString":
        v = g["coordinates"]
    elif g["type"] == "Polygon":
        v = g["coordinates"][0]
    else:
        return None
    return (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))


def _map_svg(features: list[dict], shapes: dict[str, str]) -> str:
    """Offline schematic map: equirectangular projection with cos(lat) scaling.

    One representative point per asset (vertex mean of the real
    point/line/polygon geometry), no basemap (tiles would be an external dependency and an
    attribution/licence surface). It is a *location sketch*, not cartography.
    """
    pts = []
    for f in features:
        c = _anchor(f["geometry"])
        if c:
            pts.append((f["properties"]["asset_id"], c[0], c[1]))
    lons = [p[1] for p in pts]
    lats = [p[2] for p in pts]
    lat0 = math.radians(sum(lats) / len(lats))
    w, h, pad = 520.0, 420.0, 28.0
    dx = (max(lons) - min(lons)) * math.cos(lat0) or 1e-9
    dy = (max(lats) - min(lats)) or 1e-9
    s = min((w - 2 * pad) / dx, (h - 2 * pad) / dy)
    ox = (w - dx * s) / 2
    oy = (h - dy * s) / 2
    out = [
        f'<svg viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-labelledby="mapt mapd" '
        'xmlns="http://www.w3.org/2000/svg">',
        '<title id="mapt">Croquis de localización de los 21 activos del PNSG</title>',
        '<desc id="mapd">Un punto representativo por activo, sin mapa base; la forma indica la tendencia NDVI '
        "(triángulo arriba: aumento, abajo: descenso, círculo: sin tendencia significativa).</desc>",
        f'<rect width="{w:.0f}" height="{h:.0f}" fill="none" stroke="#c9ced6"/>',
    ]
    for aid, lon, lat in pts:
        x = ox + (lon - min(lons)) * math.cos(lat0) * s
        y = h - (oy + (lat - min(lats)) * s)
        out.append(_marker(shapes.get(aid, "dot"), x, y))
    out.append("</svg>")
    return "\n".join(out)


def _spark(values: list[tuple[str, float]], shape: str) -> str:
    if len(values) < 2:
        return ""
    w, h = 120.0, 30.0
    lo = min(v for _, v in values)
    hi = max(v for _, v in values)
    rng = (hi - lo) or 1e-9
    step = w / (len(values) - 1)
    pts = " ".join(
        f"{i * step:.1f},{h - 3 - (v - lo) / rng * (h - 6):.1f}"
        for i, (_, v) in enumerate(values)
    )
    label = ", ".join(f"{y}: {v:.3f}" for y, v in values)
    return (
        f'<svg class="spark" viewBox="0 0 {w:.0f} {h:.0f}" role="img" '
        f'aria-label="NDVI medio anual — {html.escape(label)}">'
        f'<polyline points="{pts}" fill="none" stroke="{_COLOR[shape]}" stroke-width="1.8"/></svg>'
    )


def build_html() -> str:
    fc = json.loads(ASSETS.read_text(encoding="utf-8"))
    names = {
        f["properties"]["asset_id"]: f["properties"] for f in fc["features"]
    }
    trends = {t.asset_id: t for t in load_asset_trends()}
    d0, d1, n_rows = _read_series_span()
    shapes = {aid: _trend_label(t)[1] for aid, t in trends.items()}

    n_up = sum(1 for s in shapes.values() if s == "up")
    n_down = sum(1 for s in shapes.values() if s == "down")
    n_flat = len(shapes) - n_up - n_down

    rows = []
    order = sorted(
        trends.values(),
        key=lambda t: (-(_trend_label(t)[1] == "down"), t.p_value, t.asset_id),
    )
    for t in order:
        props = names.get(t.asset_id, {})
        label, shape = _trend_label(t)
        years = [
            (y, v)
            for y, v in sorted(t.annual_mean_ndvi.items())
            if y not in t.partial_years
        ]
        slope = "—" if t.sens_slope is None else f"{t.sens_slope:+.5f}"
        ci = (
            "—"
            if not t.sens_slope_ci
            else f"[{t.sens_slope_ci[0]:+.5f}, {t.sens_slope_ci[1]:+.5f}]"
        )
        rows.append(
            "<tr>"
            f'<th scope="row">{html.escape(str(props.get("name", t.asset_id)))}'
            f'<span class="sub">{html.escape(str(props.get("category", t.category)))}</span></th>'
            f'<td><span class="tag {shape}">{_marker_html(shape)} {html.escape(label)}</span></td>'
            f"<td>{_spark(years, shape)}</td>"
            f'<td class="num">{t.n_observations}</td>'
            f'<td class="num">{t.p_value:.3f}</td>'
            f'<td class="num">{slope}<span class="sub">IC95 {ci}</span></td>'
            "</tr>"
        )

    return _TEMPLATE.format(
        version=html.escape(__version__),
        d0=d0, d1=d1, n_rows=n_rows,
        n_assets=len(trends), n_up=n_up, n_down=n_down, n_flat=n_flat,
        map_svg=_map_svg(fc["features"], shapes),
        rows="\n".join(rows),
        doi=DOI, repo=REPO,
    )


def _marker_html(shape: str) -> str:
    return {"up": "▲", "down": "▼", "dot": "●"}[shape]


_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SNTO — Instantánea estática de evidencia Sentinel-2 (PNSG)</title>
<meta name="description" content="Instantánea estática y reproducible de las tendencias NDVI Sentinel-2 de 21 activos del PNSG. No es el dashboard interactivo ni una validación de campo.">
<style>
:root{{--bg:#fafaf7;--fg:#1c2330;--mut:#5b6472;--line:#d9dde3;--card:#fff;--warn:#fff4e0;--warnb:#e0b46b}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14181f;--fg:#e8ebf0;--mut:#a1a9b6;--line:#2c3340;--card:#1b2029;--warn:#2b2417;--warnb:#7a5f2c}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1040px;margin:0 auto;padding:20px 16px 48px}}
h1{{font-size:1.5rem;margin:.2em 0}} h2{{font-size:1.15rem;margin:1.6em 0 .5em}}
.lead{{color:var(--mut);margin:.2em 0 1em}}
.notice{{background:var(--warn);border:1px solid var(--warnb);border-radius:8px;padding:12px 14px;margin:14px 0}}
.notice ul{{margin:.4em 0 0;padding-left:1.2em}}
.grid{{display:grid;gap:16px;grid-template-columns:1fr}}
@media(min-width:820px){{.grid{{grid-template-columns:minmax(0,5fr) minmax(0,4fr)}}}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}}
.kpis{{display:flex;flex-wrap:wrap;gap:10px;margin:0;padding:0;list-style:none}}
.kpis li{{flex:1 1 130px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}}
.kpis b{{display:block;font-size:1.4rem}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}}
table{{border-collapse:collapse;width:100%;min-width:640px;font-size:.92rem}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}}
thead th{{position:sticky;top:0;background:var(--card);font-size:.8rem;color:var(--mut);text-transform:uppercase;letter-spacing:.03em}}
th[scope=row]{{font-weight:600}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.sub{{display:block;font-weight:400;color:var(--mut);font-size:.78rem}}
.tag.up{{color:#1b7f5c}} .tag.down{{color:#b4531a}} .tag.dot{{color:var(--mut)}}
.tag{{white-space:nowrap;font-weight:600}}
.spark{{width:120px;height:30px}}
svg{{max-width:100%;height:auto}}
footer{{color:var(--mut);font-size:.85rem;margin-top:28px;border-top:1px solid var(--line);padding-top:14px}}
a{{color:inherit}}
</style>
</head>
<body>
<main>
<h1>SNTO — Instantánea estática de evidencia Sentinel-2</h1>
<p class="lead">Parque Nacional de la Sierra de Guadarrama (PNSG) · {n_assets} activos · serie mensual {d0} → {d1} · generada desde el código v{version}</p>

<div class="notice" role="note">
<strong>Qué es y qué no es esta página.</strong> Es una instantánea reproducible, sin servidor ni base de datos, de los resultados ya calculados. <strong>No</strong> es el dashboard interactivo (suspendido por coste de alojamiento; el estado de la ciencia no depende de él).
<ul>
<li>Muestra <strong>solo evidencia derivada de Sentinel-2</strong> (índice NDVI; nivel L2 del contrato científico). No incluye alertas, presupuestos, simulaciones ni proyecciones.</li>
<li>Un cambio de NDVI <strong>no</strong> es presión de visitantes ni impacto turístico: no existe serie de uso a escala de activo y la causa no está establecida.</li>
<li><strong>Sin validación de campo</strong> (issue #26 pendiente). No es una recomendación de cierre, cupo ni gasto.</li>
</ul>
</div>

<ul class="kpis" aria-label="Resumen">
<li><b>{n_assets}</b>activos con serie</li>
<li><b>{n_up}</b>NDVI en aumento (p&lt;0,05)</li>
<li><b>{n_flat}</b>sin tendencia significativa</li>
<li><b>{n_down}</b>NDVI en descenso (p&lt;0,05)</li>
</ul>

<h2>Localización y tendencia</h2>
<div class="grid">
<div class="card">{map_svg}
<p class="sub">Croquis sin mapa base (sin teselas externas); cada activo se dibuja en un punto representativo (media de vértices de su geometría real, no su huella). ▲ aumento · ▼ descenso · ● sin tendencia significativa. Forma y color codifican lo mismo.</p></div>
<div class="card">
<strong>Cómo leerlo</strong>
<ul>
<li>Tendencia: Mann-Kendall sobre NDVI mensual <em>desestacionalizado</em>, con corrección de empates y pendiente de Sen (IC 95 %).</li>
<li><code>p</code> es aproximada y <strong>no</strong> está corregida por comparaciones múltiples ({n_assets} activos).</li>
<li>El año en curso es parcial y se excluye de la línea anual.</li>
<li>Es un índice agregado sobre la huella del activo (píxeles Sentinel-2 de 10 m): sensible a nubes residuales, nieve y fenología. Úsese como señal de <em>dónde mirar</em>, no como diagnóstico.</li>
</ul>
</div>
</div>

<h2>Detalle por activo</h2>
<p class="sub">Orden: primero descensos, luego por p creciente. Línea = NDVI medio anual (años completos).</p>
<div class="wrap" tabindex="0" aria-label="Tabla de activos (desplazable)">
<table>
<thead><tr><th>Activo</th><th>Tendencia NDVI</th><th>Media anual</th><th class="num">N meses</th><th class="num">p</th><th class="num">Pendiente de Sen (NDVI/mes)</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>

<h2>Procedencia y límites</h2>
<ul>
<li><strong>Fuente:</strong> Sentinel-2 L2A (colección GEE <code>S2_SR_HARMONIZED</code>), {n_rows} observaciones activo-mes; exportación versionada en <code>clean_assets/</code>. Fecha de la última observación: {d1}.</li>
<li><strong>Clase de evidencia:</strong> derivada de observación satelital real (L2). No es observación de campo.</li>
<li><strong>Reproducir:</strong> <code>python scripts/build_static_report.py</code> regenera este archivo desde los datos del repositorio, sin red.</li>
<li><strong>Cita y metodología:</strong> <a href="{doi}">DOI 10.5281/zenodo.20818269</a> · <a href="{repo}">repositorio</a>.</li>
</ul>

<footer>
Contiene datos Copernicus Sentinel-2 modificados (2025-2026). Software y documentación bajo la licencia del repositorio (ver LICENSE); los datos de terceros conservan sus licencias originales.
</footer>
</main>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="fail if site/index.html is stale")
    args = ap.parse_args()
    new = build_html()
    if args.check:
        cur = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if cur != new:
            print("site/index.html is out of date — run scripts/build_static_report.py")
            return 1
        print("site/index.html is up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(new, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(new):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
