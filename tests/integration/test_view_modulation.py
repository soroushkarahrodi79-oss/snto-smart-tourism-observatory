"""Tests de contrato de la divulgación por vista/audiencia (F10 · Fase 2).

Levantan la app real con ``streamlit.testing`` y verifican que las tres vistas
(Técnica / Gestor / Auditoría) renderizan contenido DISTINTO en las pestañas que
deben modular, y —condición de producto— que las **cifras financieras son
idénticas** entre audiencias. Si alguien rompe la modulación editando ``app.py``,
o filtra una diferencia en los números financieros, estos tests fallan.

Son más lentos que los unitarios (ejecutan la app dos veces por vista), por eso
viven en ``tests/integration`` y comparten una sola renderización por vista.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.platform.views import ViewMode, get_view, view_modes

_APP = str(Path(__file__).resolve().parents[2] / "app.py")

# st.metric financieros que NO dependen de la vista (pestaña Simulador). Deben
# salir idénticos en las tres audiencias: las cifras no cambian, solo su lectura.
_FINANCIAL_LABELS = {
    "Coste de cartera",
    "Delta EHS portafolio",
    "Riesgo evitado (simulado)",
    "Delta visitantes",
}


def _run_app(view_value: str) -> AppTest:
    """Levanta la app y selecciona una vista. Neutraliza ``st.pydeck_chart`` (el
    mapa es ortogonal a estos tests y ``test_map_layers`` instala un stub global
    de ``pydeck`` que, sin esto, rompería la serialización del deck)."""
    import streamlit as st

    _orig = st.pydeck_chart
    st.pydeck_chart = lambda *a, **k: None
    try:
        at = AppTest.from_file(_APP, default_timeout=120)
        at.run()
        at.session_state["view_mode"] = ViewMode(view_value)
        at.run()
    finally:
        st.pydeck_chart = _orig
    return at


def _render(view_value: str) -> dict:
    at = _run_app(view_value)
    assert not at.exception, (
        f"app.py lanzó excepción en vista {view_value}: "
        f"{[e.value for e in at.exception]}"
    )
    map_mode = next(
        (r.value for r in at.radio if r.label == "Modo de visualización"), None
    )
    return {
        "md": " ".join(m.value for m in at.markdown),
        "info": " ".join(i.value for i in at.info),
        "warning": " ".join(w.value for w in at.warning),
        "fin": {
            f"{m.label}={m.value}" for m in at.metric
            if m.label in _FINANCIAL_LABELS
        },
        "sliders": {slider.label: slider.value for slider in at.slider},
        "map_mode": map_mode,
    }


@pytest.fixture(scope="module")
def rendered() -> dict:
    return {m.value: _render(m.value) for m in view_modes()}


def test_all_views_render_without_exception(rendered: dict):
    assert set(rendered) == {"tecnica", "gestor", "tribunal"}


def test_executive_summary_only_in_gestor(rendered: dict):
    needle = "Resumen de fiabilidad para dirección"
    assert needle in rendered["gestor"]["md"]
    assert needle not in rendered["tecnica"]["md"]
    assert needle not in rendered["tribunal"]["md"]


def test_action_first_panels_only_in_gestor(rendered: dict):
    # Portafolio TPI: plan prioritario lidera solo en Gestor.
    assert "Plan de acción prioritario" in rendered["gestor"]["md"]
    assert "Plan de acción prioritario" not in rendered["tecnica"]["md"]
    assert "Plan de acción prioritario" not in rendered["tribunal"]["md"]
    # Simulador: resumen de acción (st.info) solo en Gestor.
    assert "Plan con €" in rendered["gestor"]["info"]
    assert "Plan con €" not in rendered["tecnica"]["info"]
    assert "Plan con €" not in rendered["tribunal"]["info"]


def test_executive_header_figures_only_precede_gestor_home(rendered: dict):
    needle = "Salud ecológica media"
    assert needle in rendered["gestor"]["md"]
    assert needle not in rendered["tecnica"]["md"]
    assert needle not in rendered["tribunal"]["md"]


def test_each_view_shows_its_own_banner(rendered: dict):
    # Cada vista renderiza su propio banner y no el de las otras.
    distinctive = {
        "gestor": "prioridad, presupuesto y acción",
        "tecnica": "índices espectrales, baselines",
        "tribunal": "cada cifra lleva su procedencia",
    }
    for view, own in distinctive.items():
        assert own in get_view(ViewMode(view)).banner  # sanity del fixture de datos
        assert own in rendered[view]["md"], f"falta banner propio en {view}"
        for other_view, other in distinctive.items():
            if other_view != view:
                assert other not in rendered[view]["md"], (
                    f"vista {view} muestra el banner de {other_view}"
                )


def test_map_default_mode_follows_view(rendered: dict):
    # F10 Fase 3: Técnica/Auditoría abren el mapa en Espectral (dato crudo);
    # Gestor, en Gestión (tiers). El toggle sigue siendo override manual.
    assert "Gestión" in rendered["gestor"]["map_mode"]
    assert "Espectral" in rendered["tecnica"]["map_mode"]
    assert "Espectral" in rendered["tribunal"]["map_mode"]


def test_financial_figures_are_identical_across_views(rendered: dict):
    # Condición de producto: las cifras financieras NO cambian por audiencia.
    fin = [rendered[v]["fin"] for v in ("tecnica", "gestor", "tribunal")]
    assert fin[0], "no se capturó ninguna métrica financiera"
    assert fin[0] == fin[1] == fin[2], f"cifras financieras divergen: {fin}"


def test_budget_scenario_contract_is_visible_and_editable(rendered: dict):
    expected_sliders = {
        "Presupuesto anual de referencia (€)": 100_000,
        "Banda de coste (±%)": 20,
        "Eficacia realizada (%)": 80,
    }
    for view in ("tecnica", "gestor", "tribunal"):
        assert expected_sliders.items() <= rendered[view]["sliders"].items()
        assert "ESCENARIO SIMULADO" in rendered[view]["md"]
        assert "Riesgo evitado agregado" in rendered[view]["md"]


def test_pressure_capacity_contract_keeps_causal_caveat(rendered: dict):
    for view in ("tecnica", "gestor", "tribunal"):
        assert "MODELO DE PLANIFICACIÓN" in rendered[view]["md"]
        assert "TPI estacional estimado" in rendered[view]["md"]
        assert "Correlación ≠ causa" in rendered[view]["warning"]


def test_telemetry_records_view_when_enabled(tmp_path, monkeypatch):
    # F10 Fase 5: con SNTO_TELEMETRY=1 la app registra la vista en el log local.
    # Redirigimos DEFAULT_LOG a tmp para no tocar data/outputs del repo.
    from src.platform import telemetry

    log = tmp_path / "view_usage.jsonl"
    monkeypatch.setattr(telemetry, "DEFAULT_LOG", log)
    monkeypatch.setenv("SNTO_TELEMETRY", "1")

    at = _run_app("tribunal")
    assert not at.exception, [e.value for e in at.exception]
    assert any(e.get("view") == "tribunal" for e in telemetry.load_events(log))


def test_telemetry_writes_nothing_when_disabled(tmp_path, monkeypatch):
    from src.platform import telemetry

    log = tmp_path / "view_usage.jsonl"
    monkeypatch.setattr(telemetry, "DEFAULT_LOG", log)
    monkeypatch.delenv("SNTO_TELEMETRY", raising=False)

    at = _run_app("gestor")
    assert not at.exception, [e.value for e in at.exception]
    assert not log.exists()
