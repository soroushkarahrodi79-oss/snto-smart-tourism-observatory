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
_FINANCIAL_LABELS = {"Total asignado", "Delta EHS portafolio", "Delta visitantes"}


def _render(view_value: str) -> dict:
    at = AppTest.from_file(_APP, default_timeout=120)
    at.run()
    at.session_state["view_mode"] = ViewMode(view_value)
    at.run()
    assert not at.exception, (
        f"app.py lanzó excepción en vista {view_value}: "
        f"{[e.value for e in at.exception]}"
    )
    return {
        "md": " ".join(m.value for m in at.markdown),
        "info": " ".join(i.value for i in at.info),
        "fin": {
            f"{m.label}={m.value}" for m in at.metric
            if m.label in _FINANCIAL_LABELS
        },
    }


@pytest.fixture(scope="module")
def rendered() -> dict:
    # El mapa (pydeck) es ortogonal a este test de modulación de TEXTO y lo cubre
    # test_map_layers, que además instala un stub global de ``pydeck`` en
    # sys.modules durante la colección; en la suite completa ese stub haría que
    # ``st.pydeck_chart`` fallara al serializar un deck falso. Neutralizamos solo
    # ``st.pydeck_chart`` mientras renderizamos, y lo restauramos después: el
    # texto que sí verificamos (resúmenes, planes, banners, KPIs) no depende del
    # mapa, y no tocamos el estado de ningún otro test.
    import streamlit as st

    _orig = st.pydeck_chart
    st.pydeck_chart = lambda *a, **k: None
    try:
        return {m.value: _render(m.value) for m in view_modes()}
    finally:
        st.pydeck_chart = _orig


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


def test_financial_figures_are_identical_across_views(rendered: dict):
    # Condición de producto: las cifras financieras NO cambian por audiencia.
    fin = [rendered[v]["fin"] for v in ("tecnica", "gestor", "tribunal")]
    assert fin[0], "no se capturó ninguna métrica financiera"
    assert fin[0] == fin[1] == fin[2], f"cifras financieras divergen: {fin}"
