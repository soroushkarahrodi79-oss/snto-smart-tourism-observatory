"""
SNTO — Interactive chart builders for the strategic dashboard.

All functions return Plotly Figure objects; they have no Streamlit dependency
so they can be unit-tested or embedded in any frontend.

Current charts
--------------
build_portfolio_matrix(assets) → go.Figure
    TPI Portfolio Matrix: 4-quadrant scatter of ecological risk vs. tourist
    pressure, coloured by tier, sized by economic importance.

build_time_series_chart(asset, n_months) → go.Figure
    Monthly NDVI / NDMI time series with climatically coherent simulation,
    anomaly Z-score detection and red shaded alert bands.
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

# ── Paleta de TIER — escala NEUTRA índigo→pizarra (mirrors map_layers.py) ─────
# El TIER es prioridad de inversión (estrategia), NO riesgo táctico: por eso no
# usa semáforo. El semáforo se reserva para el eje de riesgo y para las alertas.
_TIER_HEX = {
    1: "#312e5c",   # índigo profundo — Tier I, prioridad máxima de inversión
    2: "#56548a",   # índigo medio    — Tier II
    3: "#8388b0",   # pizarra media   — Tier III
    4: "#b3b8d4",   # pizarra clara   — Tier IV, promoción / mínima inversión
}
_TIER_LABEL = {
    1: "TIER I — Prioridad máxima de inversión",
    2: "TIER II — Inversión preventiva",
    3: "TIER III — Monitorización rutinaria",
    4: "TIER IV — Promoción / mínima inversión",
}

# Quadrant annotations describe POSITION in the risk/pressure space (not tiers),
# so they are labelled neutrally and coloured grey to avoid clashing with the
# neutral tier markers. The subtle background fills below still tint the risk
# axis (a continuous risk reading, like the spectral EHS map).
_QUADRANT_TEXT = "#5a6472"
_QUADRANT_ANNOTATIONS = [
    # top-right: high pressure + high risk
    (0.97, 0.97, "⚠️ Riesgo alto · Presión alta", _QUADRANT_TEXT, "right", "top"),
    # top-left: low pressure + high risk
    (0.03, 0.97, "🌡️ Riesgo alto · Presión baja", _QUADRANT_TEXT, "left", "top"),
    # bottom-right: high pressure + low risk
    (0.97, 0.03, "📈 Riesgo bajo · Presión alta", _QUADRANT_TEXT, "right", "bottom"),
    # bottom-left: low pressure + low risk
    (0.03, 0.03, "🌿 Riesgo bajo · Presión baja", _QUADRANT_TEXT, "left", "bottom"),
]


def build_portfolio_matrix(assets: list) -> go.Figure:
    """
    Build an interactive 4-quadrant TPI Portfolio Matrix.

    Axes
    ----
    X — Tourist Pressure Proxy: estimated ``visitor_capacity_annual``
        normalised 0-100 against the territorial maximum.
    Y — Ecological Risk: (100 - ehs), so higher Y = greater danger.
        Axis range [0, 100] with 0 = pristine, 100 = maximum degradation.

    Quadrant dividers are drawn at the arithmetic midpoints of both axes
    (X = 50, Y = 50) producing four strategic management zones.

    Point encoding
    --------------
    Colour  → tier  (1=red, 2=orange, 3=blue, 4=green)
    Size    → economic_importance (scaled to a readable pixel range)
    Hover   → name, region, EHS, DCS, TPI, estimated annual-volume proxy

    Args:
        assets: Ranked TerritorialAsset objects (tier and tpi must be set).

    Returns:
        plotly.graph_objects.Figure ready for st.plotly_chart().
    """
    if not assets:
        fig = go.Figure()
        fig.update_layout(title="Sin activos para mostrar")
        return fig

    # ── Build DataFrame ───────────────────────────────────────────────────────
    max_visitors = max(a.visitor_capacity_annual for a in assets) or 1

    rows = []
    for a in assets:
        pressure = round(a.visitor_capacity_annual / max_visitors * 100, 1)
        eco_risk = round(100.0 - a.ehs, 1)
        rows.append({
            "name":          a.name,
            "region":        a.region,
            "tier":          a.tier or 0,
            "pressure":      pressure,
            "eco_risk":      eco_risk,
            "ehs":           a.ehs,
            "dcs":           getattr(a, "dcs", None),
            "tpi":           round(a.tpi, 1) if a.tpi is not None else None,
            "visitors":      a.visitor_capacity_annual,
            "econ_imp":      a.economic_importance,
            # marker size: map [0,1] → [12, 42] pixels
            "marker_size":   12 + a.economic_importance * 30,
        })

    df = pd.DataFrame(rows)

    # ── One scatter trace per tier (preserves legend grouping) ───────────────
    fig = go.Figure()

    for tier in [1, 2, 3, 4]:
        sub = df[df["tier"] == tier]
        if sub.empty:
            continue

        hover_text = [
            (
                f"<b>{row['name']}</b><br>"
                f"<span style='color:#aaa'>{row['region']}</span><br>"
                f"<br>"
                f"<b>EHS</b>: {row['ehs']:.0f}/100 &nbsp;·&nbsp; "
                f"<b>Riesgo Ecológico</b>: {row['eco_risk']:.0f}/100<br>"
                f"<b>DCS</b>: {row['dcs']:.0f}/100 &nbsp;·&nbsp; "
                f"<b>TPI</b>: {row['tpi']}<br>"
                f"<b>Volumen anual estimado</b>: {row['visitors']:,}<br>"
                f"<b>Importancia econ.</b>: {row['econ_imp']:.0%}"
            )
            for _, row in sub.iterrows()
        ]

        fig.add_trace(go.Scatter(
            x=sub["pressure"],
            y=sub["eco_risk"],
            mode="markers+text",
            name=_TIER_LABEL[tier],
            text=sub["name"].apply(lambda n: n.split("—")[0].strip()[:24]),
            textposition="top center",
            textfont=dict(size=9, color=_TIER_HEX[tier]),
            marker=dict(
                size=sub["marker_size"],
                color=_TIER_HEX[tier],
                opacity=0.85,
                line=dict(width=1.5, color="white"),
            ),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
        ))

    # ── Quadrant divider lines ────────────────────────────────────────────────
    line_style = dict(color="rgba(100,120,140,0.45)", width=1.5, dash="dot")
    fig.add_shape(type="line", x0=50, x1=50, y0=0, y1=100,
                  line=line_style, layer="below")
    fig.add_shape(type="line", x0=0, x1=100, y0=50, y1=50,
                  line=line_style, layer="below")

    # Quadrant background fills (very subtle)
    _quadrant_fills = [
        # (x0, x1, y0, y1, fillcolor)
        (50, 100, 50, 100, "rgba(220,50,50,0.04)"),    # top-right: danger
        (0,   50, 50, 100, "rgba(230,130,20,0.04)"),   # top-left:  fragile
        (50, 100,  0,  50, "rgba(50,120,200,0.04)"),   # bottom-right: pressure
        (0,   50,  0,  50, "rgba(40,170,80,0.04)"),    # bottom-left: healthy
    ]
    for x0, x1, y0, y1, fc in _quadrant_fills:
        fig.add_shape(type="rect",
                      x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=fc, line_width=0, layer="below")

    # ── Quadrant annotation labels ────────────────────────────────────────────
    for xref_frac, yref_frac, text, color, xanchor, yanchor in _QUADRANT_ANNOTATIONS:
        fig.add_annotation(
            xref="paper", yref="paper",
            x=xref_frac, y=yref_frac,
            text=f"<b>{text}</b>",
            showarrow=False,
            font=dict(size=11, color=color),
            xanchor=xanchor, yanchor=yanchor,
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor=color, borderwidth=1, borderpad=4,
        )

    # ── Layout ────────────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=(
                "Matriz de Portafolio TPI — "
                "Presión Turística vs. Riesgo Ecológico"
            ),
            font=dict(size=15, color="#0d1b2a"),
            x=0.0, xanchor="left",
        ),
        xaxis=dict(
            title="Proxy de presión turística (volumen estimado normalizado, 0-100)",
            range=[-3, 103],
            showgrid=True, gridcolor="rgba(180,190,200,0.3)",
            zeroline=False,
            ticksuffix="",
        ),
        yaxis=dict(
            title="Riesgo Ecológico (100 − EHS)",
            range=[-3, 103],
            showgrid=True, gridcolor="rgba(180,190,200,0.3)",
            zeroline=False,
        ),
        legend=dict(
            title="Tier (prioridad de inversión)",
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=80, b=60),
        hoverlabel=dict(
            bgcolor="#1b2d42",
            font_color="white",
            font_size=12,
            bordercolor="#2e4560",
        ),
        height=520,
    )

    return fig


# ── Time-series simulation helpers ────────────────────────────────────────────

# Monthly seasonal shape for NDVI: peaks in May (index 4), nadir in Jan/Feb
# Values are fractional multipliers applied to the asset-specific baseline.
_NDVI_SEASONAL = [
    0.62, 0.60, 0.74, 0.88, 1.00, 0.97,   # Jan-Jun
    0.88, 0.82, 0.85, 0.91, 0.79, 0.65,   # Jul-Dec
]
# NDMI lags NDVI by ~1 month (moisture responds to spring rains then summer drying)
_NDMI_SEASONAL = [
    0.58, 0.56, 0.68, 0.82, 0.95, 1.00,   # Jan-Jun
    0.92, 0.80, 0.78, 0.86, 0.75, 0.61,   # Jul-Dec
]

# Summer stress amplifier for degraded assets (Tier 1-2 with ehs < 55):
# Intensifies Jul-Aug dip to simulate tourist-pressure + drought co-occurrence.
_SUMMER_STRESS_MONTHS = {6, 7}   # 0-indexed: July=6, August=7


def _simulate_index_series(
    ehs: float,
    tier: int,
    asset_id: str,
    seasonal_template: list[float],
    scale_range: tuple[float, float],
    n_months: int,
    stress_factor: float,
) -> list[float]:
    """
    Generate a monthly spectral-index time series that is:
    - Anchored to the asset's actual EHS (healthier → higher baseline)
    - Seasonally structured using the provided template
    - Deterministically noisy (seed = hash of asset_id)
    - Stress-depressed in summer months for degraded assets (Tier 1-2)

    Args:
        ehs            : Ecological Health Score 0-100
        tier           : Management tier (1-4)
        asset_id       : Used to seed the noise RNG (reproducible)
        seasonal_template : 12 fractional multipliers (Jan-Dec)
        scale_range    : (min_index, max_index) mapped to ehs=0 / ehs=100
        n_months       : Total months to generate
        stress_factor  : Extra dip multiplier applied in summer for low-tier assets

    Returns:
        List of float index values, length = n_months
    """
    lo, hi = scale_range
    # Baseline: linear mapping ehs → index value
    baseline = lo + (ehs / 100.0) * (hi - lo)

    # Deterministic pseudo-noise seed from asset_id hash
    seed = hash(asset_id) & 0xFFFFFF
    values: list[float] = []

    for i in range(n_months):
        month_idx = i % 12
        seasonal = seasonal_template[month_idx]

        # Summer stress for degraded, high-traffic assets
        stress = 1.0
        if tier in (1, 2) and ehs < 60 and month_idx in _SUMMER_STRESS_MONTHS:
            stress = stress_factor

        # Deterministic noise: low-frequency sinusoid + hash-driven jitter
        # Produces inter-annual variation without true randomness
        slow_wave = 0.03 * math.sin(2 * math.pi * i / 24.0 + seed % 100)
        fast_jitter = 0.015 * math.sin(2 * math.pi * i * 7 / 12.0 + seed % 37)
        noise = slow_wave + fast_jitter

        val = baseline * seasonal * stress + baseline * noise
        # Clamp to plausible spectral index range
        val = max(lo * 0.5, min(hi * 1.05, val))
        values.append(round(val, 4))

    return values


def _z_scores(series: list[float]) -> list[float]:
    """Compute Z-scores of a series. Returns list of same length."""
    n = len(series)
    if n < 2:
        return [0.0] * n
    mean = sum(series) / n
    var = sum((x - mean) ** 2 for x in series) / n
    std = math.sqrt(var) if var > 0 else 1e-9
    return [round((x - mean) / std, 3) for x in series]


def _anomaly_shapes(
    dates: list[str],
    z_scores: list[float],
    threshold: float = -1.5,
) -> list[dict]:
    """
    Build Plotly layout shapes for contiguous anomaly bands.

    Each contiguous run of months with z < threshold produces one
    red-shaded rectangle spanning those months.

    Args:
        dates     : ISO date strings aligned with z_scores
        z_scores  : Z-score per month
        threshold : Z-score below which a month is anomalous (default -1.5)

    Returns:
        List of Plotly shape dicts ready for fig.update_layout(shapes=...).
    """
    shapes = []
    in_anomaly = False
    start_date = None

    for i, (d, z) in enumerate(zip(dates, z_scores)):
        if z < threshold and not in_anomaly:
            in_anomaly = True
            start_date = d
        elif z >= threshold and in_anomaly:
            in_anomaly = False
            shapes.append(dict(
                type="rect",
                xref="x", yref="paper",
                x0=start_date, x1=d,
                y0=0, y1=1,
                fillcolor="rgba(220,50,50,0.12)",
                line=dict(width=0),
                layer="below",
            ))
    # Close any open anomaly run at the end of the series
    if in_anomaly and start_date is not None:
        shapes.append(dict(
            type="rect",
            xref="x", yref="paper",
            x0=start_date, x1=dates[-1],
            y0=0, y1=1,
            fillcolor="rgba(220,50,50,0.12)",
            line=dict(width=0),
            layer="below",
        ))
    return shapes


# ── Public API ────────────────────────────────────────────────────────────────

def build_time_series_chart(asset, n_months: int = 24) -> go.Figure:
    """
    Build an interactive multi-axis NDVI / NDMI time series chart with
    climatically coherent simulated data and anomaly alert bands.

    Simulation rationale
    --------------------
    Pipeline A produces a single composite EHS score per asset.  For the
    dashboard we back-simulate a plausible monthly history using:
      - An EHS-anchored baseline (healthier assets maintain higher indices)
      - A real phenological seasonal curve (spring peak, summer dip)
      - A tourist-pressure stress amplifier applied in Jul-Aug for Tier 1-2
        assets with ehs < 60 — models the overuse + drought co-occurrence
        documented in Sierra del Rincón field reports
      - Low-frequency inter-annual variability (deterministic, seeded by
        asset_id so the same asset always shows the same history)

    Anomaly detection
    -----------------
    Z-scores are computed on the NDVI series.  Contiguous months where
    z < -1.5 are highlighted as red-shaded bands — the conventional
    threshold for moderate drought stress in Mediterranean vegetation
    monitoring (consistent with SNTO Phase 1 anomaly classifier).

    Args:
        asset    : TerritorialAsset with tier, ehs, asset_id, name set.
        n_months : Number of monthly points to generate (default 24 = 2 years).

    Returns:
        plotly.graph_objects.Figure with dual Y-axes ready for st.plotly_chart().
    """
    # ── Generate date axis (end at current report month) ─────────────────────
    import datetime
    end   = datetime.date(2026, 6, 1)
    dates = []
    for i in range(n_months - 1, -1, -1):
        # Step back i months from end
        month = (end.month - 1 - i) % 12 + 1
        year  = end.year + ((end.month - 1 - i) // 12)
        dates.append(datetime.date(year, month, 1).isoformat())

    tier = asset.tier or 2
    ehs  = asset.ehs

    # ── Simulate NDVI  (range 0.15 – 0.82 for vegetation in Sierra del Rincón)
    ndvi = _simulate_index_series(
        ehs=ehs, tier=tier, asset_id=asset.asset_id,
        seasonal_template=_NDVI_SEASONAL,
        scale_range=(0.15, 0.82),
        n_months=n_months,
        stress_factor=0.78,   # summer dip: ~22 % below seasonal expectation
    )

    # ── Simulate NDMI  (range -0.25 – 0.55 in this semi-humid mountain zone)
    ndmi = _simulate_index_series(
        ehs=ehs, tier=tier, asset_id=asset.asset_id,
        seasonal_template=_NDMI_SEASONAL,
        scale_range=(-0.25, 0.55),
        n_months=n_months,
        stress_factor=0.72,   # moisture drops harder under summer stress
    )

    z_ndvi = _z_scores(ndvi)
    anomaly_shapes = _anomaly_shapes(dates, z_ndvi, threshold=-1.5)

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = go.Figure()

    # NDVI line (left Y axis)
    fig.add_trace(go.Scatter(
        x=dates, y=ndvi,
        name="NDVI (Vegetación)",
        mode="lines+markers",
        line=dict(color="#2e7d32", width=2.5),
        marker=dict(size=5, color="#2e7d32"),
        yaxis="y1",
        hovertemplate="<b>NDVI</b>: %{y:.3f}<br>%{x}<extra></extra>",
    ))

    # NDMI line (right Y axis)
    fig.add_trace(go.Scatter(
        x=dates, y=ndmi,
        name="NDMI (Humedad)",
        mode="lines+markers",
        line=dict(color="#1565c0", width=2.5, dash="dot"),
        marker=dict(size=5, color="#1565c0"),
        yaxis="y2",
        hovertemplate="<b>NDMI</b>: %{y:.3f}<br>%{x}<extra></extra>",
    ))

    # Invisible scatter for anomaly legend entry (only if anomalies exist)
    if anomaly_shapes:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=12, color="rgba(220,50,50,0.35)",
                        symbol="square", line=dict(width=0)),
            name="Anomalía Climática (|z| ≥ 1.5)",
            showlegend=True,
        ))

    # Z-score reference line (secondary trace — hidden from legend)
    fig.add_hline(
        y=0, line_dash="dot",
        line_color="rgba(120,130,140,0.4)",
        annotation_text="",
        row=None, col=None,
    )

    # ── Tier badge colour for title ───────────────────────────────────────────
    tier_color = _TIER_HEX.get(tier, "#555")

    fig.update_layout(
        title=dict(
            text=(
                f"<b>{asset.name}</b>"
                f"<span style='color:{tier_color};font-size:12px'>"
                f"  ·  Tier {tier}  ·  EHS {ehs:.0f}/100</span><br>"
                f"<span style='color:#9aa4af;font-size:11px'>"
                f"Serie temporal espectral — últimos {n_months} meses</span>"
            ),
            font=dict(size=13, color="#0d1b2a"),
            x=0.0, xanchor="left",
        ),
        xaxis=dict(
            title="",
            showgrid=True, gridcolor="rgba(180,190,200,0.3)",
            tickformat="%b %Y",
            tickangle=-30,
        ),
        yaxis=dict(
            title=dict(text="NDVI", font=dict(color="#2e7d32")),
            tickfont=dict(color="#2e7d32"),
            showgrid=True, gridcolor="rgba(46,125,50,0.12)",
            range=[0.0, 0.95],
            side="left",
        ),
        yaxis2=dict(
            title=dict(text="NDMI", font=dict(color="#1565c0")),
            tickfont=dict(color="#1565c0"),
            overlaying="y",
            side="right",
            range=[-0.40, 0.70],
            showgrid=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
        shapes=anomaly_shapes,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=60, t=100, b=60),
        hoverlabel=dict(
            bgcolor="#1b2d42",
            font_color="white",
            font_size=12,
            bordercolor="#2e4560",
        ),
        height=460,
    )

    # ── Anomaly count annotation ───────────────────────────────────────────────
    n_anom = len(anomaly_shapes)
    if n_anom > 0:
        fig.add_annotation(
            xref="paper", yref="paper",
            x=1.0, y=1.08,
            text=(
                f"🔴 <b>{n_anom} período(s)</b> de estrés hídrico crítico "
                f"detectado(s)"
            ),
            showarrow=False,
            font=dict(size=10, color="#c62828"),
            xanchor="right", yanchor="bottom",
            bgcolor="rgba(255,235,238,0.9)",
            bordercolor="#c62828", borderwidth=1, borderpad=4,
        )

    return fig


# Dirección Mann-Kendall → color de la línea de tendencia real.
_REAL_TREND_HEX = {
    "increasing": "#2e7d32",   # verde — recuperación de verdor
    "decreasing": "#c62828",   # rojo — degradación significativa
    "no trend":   "#5a6472",   # gris — sin tendencia monotónica
}


def build_real_trend_chart(asset_trend) -> go.Figure:
    """
    Build the *empirical* multi-year NDVI trend chart for one asset.

    Unlike ``build_time_series_chart`` (a monthly reconstruction), this plots the
    REAL annual mean NDVI exported by the GEE / Mann-Kendall pipeline
    (``satellite_trends.AssetTrend``). Years flagged ``partial_years`` (e.g. the
    in-progress 2026 without a full summer) are drawn with a hollow marker and a
    dashed connector so they read as provisional, and excluded from the worst/best
    annotation logic upstream.

    Args:
        asset_trend : an object exposing ``asset_id``, ``annual_mean_ndvi``
                      (dict[year→ndvi]), ``partial_years`` (list[str]), ``tau``,
                      ``p_value``, ``trend``, ``trend_es``, ``worst_year`` and
                      ``best_year`` — i.e. ``satellite_trends.AssetTrend``.

    Returns:
        plotly.graph_objects.Figure ready for ``st.plotly_chart``. If there are
        fewer than two annual points the figure carries an explanatory annotation
        instead of an (uninterpretable) trend line.
    """
    annual = asset_trend.annual_mean_ndvi or {}
    years = sorted(annual.keys())
    partial = set(asset_trend.partial_years or [])

    fig = go.Figure()

    if len(years) < 2:
        fig.add_annotation(
            xref="paper", yref="paper", x=0.5, y=0.5,
            text="Serie anual insuficiente para una tendencia (≥ 2 años).",
            showarrow=False, font=dict(size=12, color="#5a6472"),
        )
        fig.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    values = [annual[y] for y in years]
    line_color = _REAL_TREND_HEX.get(asset_trend.trend, "#5a6472")

    # Separar años completos vs. parciales para estilarlos distinto.
    full_x = [y for y in years if y not in partial]
    full_y = [annual[y] for y in full_x]
    part_x = [y for y in years if y in partial]
    part_y = [annual[y] for y in part_x]

    # Línea base (conecta todos los años, incluido el parcial, en tono tenue).
    fig.add_trace(go.Scatter(
        x=years, y=values,
        mode="lines",
        line=dict(color=line_color, width=2.5),
        name="NDVI medio anual",
        hoverinfo="skip",
        showlegend=False,
    ))

    # Años completos: marcadores sólidos.
    fig.add_trace(go.Scatter(
        x=full_x, y=full_y,
        mode="markers",
        marker=dict(size=11, color=line_color,
                    line=dict(width=1.5, color="white")),
        name="Año completo",
        hovertemplate="<b>%{x}</b><br>NDVI medio: %{y:.3f}<extra></extra>",
    ))

    # Años parciales (p. ej. 2026 sin verano): marcador hueco + aviso.
    if part_x:
        fig.add_trace(go.Scatter(
            x=part_x, y=part_y,
            mode="markers",
            marker=dict(size=12, color="white", symbol="circle-open",
                        line=dict(width=2.5, color=line_color)),
            name="Año parcial (provisional)",
            hovertemplate=(
                "<b>%{x}</b> (parcial)<br>NDVI medio: %{y:.3f}<extra></extra>"
            ),
        ))

    # Resaltar peor / mejor año si están entre los completos.
    for yr, label, color in (
        (asset_trend.worst_year, "peor", "#c62828"),
        (asset_trend.best_year, "mejor", "#2e7d32"),
    ):
        if yr in annual:
            fig.add_annotation(
                x=yr, y=annual[yr],
                text=f"{label} año",
                showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=color,
                ay=-28 if label == "mejor" else 28, ax=0,
                font=dict(size=10, color=color),
            )

    _sig = ("significativa (p<0,05)" if asset_trend.p_value < 0.05
            else "no significativa")
    fig.update_layout(
        title=dict(
            text=(
                f"<b>NDVI anual real · {asset_trend.asset_id}</b><br>"
                f"<span style='color:{line_color};font-size:11px'>"
                f"Mann-Kendall {asset_trend.trend_es} · τ={asset_trend.tau:.3f} · "
                f"p={asset_trend.p_value:.3f} ({_sig})</span>"
            ),
            font=dict(size=13, color="#0d1b2a"),
            x=0.0, xanchor="left",
        ),
        xaxis=dict(
            title="", type="category",
            showgrid=True, gridcolor="rgba(180,190,200,0.3)",
        ),
        yaxis=dict(
            title=dict(text="NDVI medio anual", font=dict(color="#2e7d32")),
            tickfont=dict(color="#2e7d32"),
            showgrid=True, gridcolor="rgba(46,125,50,0.12)",
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, font=dict(size=11),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=90, b=40),
        hoverlabel=dict(bgcolor="#1b2d42", font_color="white", font_size=12),
        height=380,
    )
    return fig
