"""Tests de los constructores de gráficos espectrales (Pestaña 6).

Cubren ``src/platform/charts.py``:
  · la SIMULACIÓN mensual (``build_time_series_chart`` y helpers) — determinismo,
    clamp de rango y amplificador de estrés estival;
  · el gráfico multianual REAL (``build_real_trend_chart``, Fase 4) sobre un
    ``AssetTrend`` empírico.

Las figuras Plotly se construyen sin Streamlit, así que corren headless en CI.
"""
from __future__ import annotations

from types import SimpleNamespace

import plotly.graph_objects as go
import pytest

from src.platform.charts import (
    _NDVI_SEASONAL,
    _anomaly_shapes,
    _simulate_index_series,
    _z_scores,
    build_real_trend_chart,
    build_time_series_chart,
)
from src.platform.satellite_trends import AssetTrend

# ── Helpers ─────────────────────────────────────────────────────────────────────

def _asset(asset_id="pnsg_x_y", name="Activo X", ehs=55.0, tier=2):
    return SimpleNamespace(asset_id=asset_id, name=name, ehs=ehs, tier=tier)


# ── build_time_series_chart ─────────────────────────────────────────────────────

def test_time_series_returns_figure_with_two_index_traces():
    fig = build_time_series_chart(_asset(), n_months=24)
    assert isinstance(fig, go.Figure)
    names = [t.name for t in fig.data]
    assert "NDVI (Vegetación)" in names
    assert "NDMI (Humedad)" in names


@pytest.mark.parametrize("n_months", [12, 24, 36])
def test_time_series_honors_window_length(n_months):
    fig = build_time_series_chart(_asset(), n_months=n_months)
    ndvi = next(t for t in fig.data if t.name == "NDVI (Vegetación)")
    assert len(ndvi.y) == n_months


def test_time_series_deterministic_for_same_asset():
    a = _asset(asset_id="pnsg_det_test", ehs=48.0, tier=1)
    y1 = list(next(t for t in build_time_series_chart(a, n_months=24).data
                   if t.name == "NDVI (Vegetación)").y)
    y2 = list(next(t for t in build_time_series_chart(a, n_months=24).data
                   if t.name == "NDVI (Vegetación)").y)
    assert y1 == y2     # misma semilla (hash del asset_id) → serie idéntica


# ── _simulate_index_series ──────────────────────────────────────────────────────

def test_simulate_clamps_within_scale_range():
    lo, hi = 0.15, 0.82
    series = _simulate_index_series(
        ehs=95.0, tier=4, asset_id="pnsg_clamp", seasonal_template=_NDVI_SEASONAL,
        scale_range=(lo, hi), n_months=36, stress_factor=0.78,
    )
    assert len(series) == 36
    assert all(lo * 0.5 <= v <= hi * 1.05 for v in series)


def test_simulate_summer_stress_only_for_degraded_tier12():
    """Tier 1-2 con EHS<60 deprime los meses de verano (índices 6 y 7);
    un activo Tier 3 con el mismo EHS/seed no aplica esa depresión."""
    kw = dict(
        asset_id="pnsg_same_seed", seasonal_template=_NDVI_SEASONAL,
        scale_range=(0.15, 0.82), n_months=12, stress_factor=0.78,
    )
    stressed = _simulate_index_series(ehs=40.0, tier=1, **kw)
    calm = _simulate_index_series(ehs=40.0, tier=3, **kw)

    # Meses de estrés (índices 6,7): el degradado Tier-1 cae por debajo.
    assert stressed[6] < calm[6]
    assert stressed[7] < calm[7]
    # Resto de meses: idénticos (mismo baseline, seed y estacionalidad).
    for i in (0, 1, 2, 3, 4, 5, 8, 9, 10, 11):
        assert stressed[i] == calm[i]


def test_simulate_no_stress_when_healthy():
    kw = dict(
        asset_id="pnsg_healthy", seasonal_template=_NDVI_SEASONAL,
        scale_range=(0.15, 0.82), n_months=12, stress_factor=0.78,
    )
    # EHS≥60 → sin estrés aunque sea Tier 1.
    t1 = _simulate_index_series(ehs=70.0, tier=1, **kw)
    t3 = _simulate_index_series(ehs=70.0, tier=3, **kw)
    assert t1 == t3


# ── _z_scores ───────────────────────────────────────────────────────────────────

def test_z_scores_centered_and_sized():
    z = _z_scores([1.0, 2.0, 3.0, 4.0, 5.0])
    assert len(z) == 5
    assert sum(z) == pytest.approx(0.0, abs=1e-6)


def test_z_scores_degenerate_short_series():
    assert _z_scores([]) == []
    assert _z_scores([3.3]) == [0.0]


# ── _anomaly_shapes ─────────────────────────────────────────────────────────────

def test_anomaly_single_contiguous_run():
    dates = ["2021-01-01", "2021-02-01", "2021-03-01", "2021-04-01", "2021-05-01"]
    z = [0.0, -2.0, -2.0, 0.0, 0.0]      # run cerrado en índice 3
    shapes = _anomaly_shapes(dates, z, threshold=-1.5)
    assert len(shapes) == 1
    assert shapes[0]["x0"] == "2021-02-01"
    assert shapes[0]["x1"] == "2021-04-01"


def test_anomaly_open_run_closes_at_end():
    dates = ["2021-01-01", "2021-02-01", "2021-03-01"]
    z = [0.0, -2.0, -2.0]                # nunca vuelve sobre el umbral
    shapes = _anomaly_shapes(dates, z, threshold=-1.5)
    assert len(shapes) == 1
    assert shapes[0]["x1"] == "2021-03-01"   # cierra en el último punto


def test_anomaly_two_separate_runs():
    dates = [f"2021-{m:02d}-01" for m in range(1, 7)]
    z = [-2.0, 0.0, -2.0, -2.0, 0.0, 0.0]    # dos rachas
    shapes = _anomaly_shapes(dates, z, threshold=-1.5)
    assert len(shapes) == 2


def test_anomaly_none_when_no_breach():
    dates = ["2021-01-01", "2021-02-01"]
    assert _anomaly_shapes(dates, [0.0, -1.0], threshold=-1.5) == []


# ── build_real_trend_chart (Fase 4) ─────────────────────────────────────────────

def _real_trend(**kw) -> AssetTrend:
    base = dict(
        asset_id="pnsg_escalada_penalara", category="escalada", n_observations=60,
        tau=0.191, p_value=0.0316, trend="increasing",
        annual_mean_ndvi={"2021": 0.39, "2022": 0.36, "2023": 0.41,
                          "2024": 0.42, "2025": 0.41, "2026": 0.44},
        partial_years=["2026"], worst_year="2022", best_year="2024",
        ndvi_min=0.32, ndvi_max=0.48,
    )
    base.update(kw)
    return AssetTrend(**base)


def test_real_trend_plots_all_years_and_marks_partial():
    fig = build_real_trend_chart(_real_trend())
    assert isinstance(fig, go.Figure)
    # Línea base cubre los 6 años en orden.
    base_line = next(t for t in fig.data if t.mode == "lines")
    assert list(base_line.x) == ["2021", "2022", "2023", "2024", "2025", "2026"]
    # Existe una serie específica para el año parcial.
    partial = next((t for t in fig.data
                    if t.name == "Año parcial (provisional)"), None)
    assert partial is not None
    assert list(partial.x) == ["2026"]


def test_real_trend_color_reflects_direction():
    inc = build_real_trend_chart(_real_trend(trend="increasing"))
    dec = build_real_trend_chart(_real_trend(trend="decreasing"))
    inc_line = next(t for t in inc.data if t.mode == "lines")
    dec_line = next(t for t in dec.data if t.mode == "lines")
    assert inc_line.line.color == "#2e7d32"   # verde mejora
    assert dec_line.line.color == "#c62828"   # rojo degradación


def test_real_trend_insufficient_years_shows_annotation():
    fig = build_real_trend_chart(_real_trend(annual_mean_ndvi={"2021": 0.39}))
    assert len(fig.data) == 0                  # sin trazas de serie
    assert len(fig.layout.annotations) >= 1    # mensaje explicativo
