"""
Diagnosticar → Proyección de tendencia (v2.2).

The first forward-looking surface in the dashboard. It projects an asset's
**real** annual NDVI series (the empirical Sentinel-2 Mann-Kendall series shown
in «Evidenciar → Evidencia satelital») a few years ahead, with a
horizon-widening uncertainty band.

Evidence discipline (ADR-004 / CLAUDE.md), enforced visually and in copy:
the projection is an ``EvidenceClass.SIMULATED`` scenario — a "¿y si nada
cambia?", never an observation. It is drawn dashed/purple, badged, and its
caveat is shown; the panel states it backs no decision. This is why the surface
lives in *Diagnosticar* ("where is the signal heading?"), not in the evidence
layer.
"""
from __future__ import annotations

import streamlit as st

from src.forecasting import project_trend, threshold_crossing
from src.forecasting.projection import ThresholdDirection
from src.platform.charts import build_forecast_chart
from src.platform.evidence import descriptor
from src.platform.satellite_trends import (
    DEFAULT_PARK,
    available_parks,
    park_label,
    summarize_trends,
)


@st.cache_data(show_spinner=False)
def _cached_trends(park: str = DEFAULT_PARK):
    """Real Mann-Kendall trend summary, cached per session and park."""
    return summarize_trends(park=park)


def _annual_series(asset_trend) -> tuple[list[str], list[float]]:
    """Chronological (year_label, mean_ndvi) of an asset, partial years dropped.

    A partial year (current season incomplete) would bias the last point, so it
    is excluded from the series the projection is fit on — the same rule the
    real-trend panel uses for its worst/best-year ranking.
    """
    partial = set(asset_trend.partial_years)
    pairs = sorted(
        (y, v)
        for y, v in asset_trend.annual_mean_ndvi.items()
        if y not in partial
    )
    return [y for y, _ in pairs], [v for _, v in pairs]


def render_tab_forecast(ranked_assets, _view) -> None:
    """Render the trend-projection tab (v2.2)."""
    st.subheader("Proyección de tendencia — escenario 'si nada cambia'")

    sim = descriptor(project_trend([1.0, 2.0, 3.0], 1).evidence_class)
    st.markdown(
        f'<div style="padding:8px 14px;border-radius:6px;margin:2px 0 10px;'
        f'background:#f3effa;border-left:4px solid {sim.color};'
        f'font-size:0.83rem;color:#3a2d5c">'
        f'{sim.emoji} <b>{sim.label}</b> — {sim.caveat}</div>',
        unsafe_allow_html=True,
    )

    _parks = available_parks() or [DEFAULT_PARK]
    _park = DEFAULT_PARK
    if len(_parks) > 1:
        _park = st.selectbox(
            "Parque Nacional",
            options=_parks,
            index=_parks.index(DEFAULT_PARK) if DEFAULT_PARK in _parks else 0,
            format_func=park_label,
            key="forecast_park",
        )

    trends = _cached_trends(_park)
    if not trends.available:
        st.info(
            "No hay serie satelital real analizada para este parque todavía, "
            "así que no hay nada que proyectar. La proyección solo se ofrece "
            "sobre series empíricas (Sentinel-2), nunca sobre datos simulados.",
            icon="🛰️",
        )
        return

    # Only assets with enough real annual points to project honestly.
    projectable = [
        a for a in trends.assets if len(_annual_series(a)[1]) >= 3
    ]
    if not projectable:
        st.info(
            "Los activos de este parque no tienen aún suficientes años "
            "completos (mínimo 3) para una proyección defendible.",
            icon="⏳",
        )
        return

    labels = {f"{a.asset_id}  ·  {a.trend_es}": a for a in projectable}
    sel = st.selectbox(
        "Activo real (GEE) a proyectar",
        options=list(labels.keys()),
        index=0,
        help="Solo activos con serie NDVI real 2021–2026 y ≥3 años completos.",
        key="forecast_asset",
    )
    asset = labels[sel]

    col_h, col_a = st.columns(2)
    with col_h:
        horizon = st.select_slider(
            "Horizonte de proyección (años)",
            options=[1, 2, 3, 4, 5],
            value=3,
        )
    with col_a:
        conf = st.select_slider(
            "Nivel de confianza de la banda",
            options=[80, 90, 95],
            value=95,
            format_func=lambda v: f"{v}%",
        )

    years, series = _annual_series(asset)
    alpha = 1.0 - conf / 100.0
    fc = project_trend(series, horizon, alpha=alpha, clamp=(-1.0, 1.0))

    last_year = int(years[-1])
    future_years = [str(last_year + h) for h in range(1, horizon + 1)]

    # A degradation floor to illustrate threshold crossing: 10% below the
    # series' own minimum observed annual NDVI (illustrative, not a standard).
    floor = round(min(series) * 0.9, 3)
    crossing = threshold_crossing(fc, floor, ThresholdDirection.BELOW)

    st.plotly_chart(
        build_forecast_chart(
            years, series, future_years, fc,
            y_title="NDVI medio anual",
            title=f"{asset.asset_id} · proyección {horizon} año(s)",
            threshold=floor,
        ),
        use_container_width=True,
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Pendiente Sen (NDVI/año)", f"{fc.slope:+.4f}")
    m2.metric(
        "Banda al horizonte",
        f"[{fc.lower[-1]:.3f}, {fc.upper[-1]:.3f}]",
        help=f"Intervalo {conf}% en el año {future_years[-1]}.",
    )
    m3.metric("Años proyectados", horizon)

    # Honest reading of the slope CI: does the band even agree on direction?
    if fc.slope_lower < 0 < fc.slope_upper:
        st.caption(
            f"↔️ El intervalo {conf}% de la pendiente "
            f"[{fc.slope_lower:+.4f}, {fc.slope_upper:+.4f}] **cruza cero**: la "
            f"serie real no fija ni deterioro ni mejora, y la proyección lo "
            f"refleja abriéndose a ambos lados."
        )
    elif fc.slope < 0:
        when = (
            f"hacia el año {future_years[crossing.point_step - 1]}"
            if crossing.point_step is not None
            else "no dentro del horizonte mostrado"
        )
        st.caption(
            f"↘ Escenario de deterioro continuado: de mantenerse la pendiente, "
            f"el NDVI medio alcanzaría el umbral ilustrativo {floor:g} {when}. "
            f"Es un escenario, no una predicción validada."
        )
    else:
        st.caption("↗ Escenario de mejora continuada si la pendiente se mantiene.")

    if _view.section(technical=True):
        st.caption(
            f"🔬 Método: {fc.method}. Ancla Theil-Sen {fc.anchor:.3f} sobre "
            f"{fc.n_obs} años reales; banda del IC no paramétrico de la "
            f"pendiente de Sen (Gilbert 1987), que se ensancha con el horizonte. "
            f"Clase de evidencia: **{fc.evidence_class.value}** — no apta para "
            f"diagnóstico, priorización, gasto ni comunicación pública."
        )
