"""
Smoke test for the "Acciones urgentes" tab (Fase 5, 5.9) via streamlit.testing.

Runs the real app once with ``_open_session`` monkeypatched to an in-memory
session holding one open alert, and asserts the tab renders the asset card, its
recommended action, and the lifecycle-advance button — the first UI↔persistent
backend integration point, exercised end-to-end through the Streamlit runtime.

Only a single AppTest run lives here on purpose: the full app pulls in heavy C
extensions (rasterio/pandas/pydeck) and running it more than once per process
alongside a persistent cross-thread SQLite connection segfaults. The empty
state, ordering, and field mapping are covered by the fast service unit tests
in ``tests/ui/test_urgent_actions_service.py``.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from streamlit.testing.v1 import AppTest

from src.persistence.models import Alert, Base, ManagedAsset, Recommendation, Territory

_APP = str(Path(__file__).resolve().parents[2] / "app.py")


def test_tab_renders_populated(monkeypatch) -> None:
    import src.ui.tabs.tab_urgent_actions as tab

    # StaticPool + check_same_thread=False: AppTest runs the script in a separate
    # thread, so the seeded in-memory DB must be shared across threads.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as seed:
            territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
            seed.add(territory)
            seed.flush()
            asset = ManagedAsset(
                territory_id=territory.id,
                external_asset_id="pnsg-trail-001",
                name="Sendero Circular",
                asset_type="trail",
                geometry_geojson="{}",
                region="Madrid",
            )
            seed.add(asset)
            seed.flush()
            alert = Alert(
                asset_id=asset.id, level="CRITICAL_INTERVENTION", risk_score=0.95
            )
            seed.add(alert)
            seed.flush()
            seed.add(Recommendation(alert_id=alert.id, action_label="Cerrar acceso"))
            seed.commit()

        @contextmanager
        def _populated_scope():
            with Session(engine) as s:
                yield s

        monkeypatch.setattr(tab, "_open_session", _populated_scope)

        import streamlit as st

        _orig = st.pydeck_chart
        st.pydeck_chart = lambda *a, **k: None
        try:
            at = AppTest.from_file(_APP, default_timeout=120)
            at.run()
        finally:
            st.pydeck_chart = _orig

        assert not at.exception
        rendered = " ".join(m.value for m in at.markdown)
        assert "Sendero Circular" in rendered
        assert "Cerrar acceso" in " ".join(c.value for c in at.caption)
        # The lifecycle-advance button is present for a detected asset.
        assert any("Avanzar" in b.label for b in at.button)
    finally:
        engine.dispose()
