"""
Tests for build_forecast_chart — the SIMULATED projection chart.

The chart is a pure Plotly builder (no Streamlit), so we can assert it draws the
real history, the projection band, and — critically — that it visually flags the
projection as a scenario, never an observation.
"""
from __future__ import annotations

from src.forecasting import project_trend
from src.platform.charts import _SIM_COLOR, build_forecast_chart

_HISTORY_X = ["2021", "2022", "2023", "2024", "2025"]
_HISTORY_Y = [0.60, 0.58, 0.57, 0.55, 0.54]


def _chart(horizon: int = 3):
    fc = project_trend(_HISTORY_Y, horizon, clamp=(-1.0, 1.0))
    future_x = [str(2025 + h) for h in range(1, horizon + 1)]
    return build_forecast_chart(
        _HISTORY_X, _HISTORY_Y, future_x, fc, y_title="NDVI", title="asset-x"
    )


def test_chart_has_history_and_projection_traces() -> None:
    fig = _chart()
    names = [t.name for t in fig.data if t.name]
    assert "Serie real observada" in names
    assert "Proyección (escenario simulado)" in names
    assert "Banda de incertidumbre (escenario)" in names


def test_projection_uses_the_simulated_colour_and_dash() -> None:
    fig = _chart()
    proj = next(t for t in fig.data if t.name == "Proyección (escenario simulado)")
    assert proj.line.color == _SIM_COLOR
    assert proj.line.dash == "dash"


def test_title_flags_it_as_a_scenario() -> None:
    fig = _chart()
    assert "simulado" in fig.layout.title.text.lower()


def test_threshold_line_drawn_when_given() -> None:
    fc = project_trend(_HISTORY_Y, 3, clamp=(-1.0, 1.0))
    fig = build_forecast_chart(
        _HISTORY_X, _HISTORY_Y, ["2026", "2027", "2028"], fc, threshold=0.45
    )
    # add_hline registers a shape on the layout.
    assert any(getattr(s, "type", None) == "line" for s in fig.layout.shapes)


def test_band_trace_count_scales_with_horizon() -> None:
    fig = _chart(horizon=5)
    proj = next(t for t in fig.data if t.name == "Proyección (escenario simulado)")
    assert len(proj.y) == 5
