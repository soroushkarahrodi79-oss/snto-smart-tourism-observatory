"""The real app in public-demo mode, over a populated temporary database.

One AppTest run only (see ``test_urgent_actions_tab.py`` for why). The
normal-mode counterpart that does render the triage buttons lives there.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest

from src.config.settings import settings
from src.persistence import session as session_mod
from src.persistence.models import Alert, Base, ManagedAsset, Territory

_APP = str(Path(__file__).resolve().parents[2] / "app.py")


def _reset_engine() -> None:
    if session_mod._engine is not None:
        session_mod._engine.dispose()
    session_mod._engine = None
    session_mod._SessionLocal = None


def test_app_runs_read_only(monkeypatch, tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'demo.db'}"
    setup = create_engine(url)
    Base.metadata.create_all(setup)
    with Session(setup) as s:
        territory = Territory(slug="pnsg", name="PNSG", budget_eur=1000.0)
        s.add(territory)
        s.flush()
        asset = ManagedAsset(
            territory_id=territory.id, external_asset_id="pnsg-001",
            name="Sendero Circular", asset_type="trail", geometry_geojson="{}",
            region="Madrid",
        )
        s.add(asset)
        s.flush()
        alert = Alert(asset_id=asset.id, level="CRITICAL_INTERVENTION")
        alert.risk_score = 0.9
        s.add(alert)
        s.commit()
    setup.dispose()

    monkeypatch.setattr(settings, "snto_database_url", url)
    monkeypatch.setattr(settings, "snto_public_demo", True)
    _reset_engine()

    import streamlit as st

    decks: list = []
    monkeypatch.setattr(st, "pydeck_chart", lambda *a, **k: decks.append(a))
    try:
        at = AppTest.from_file(_APP, default_timeout=120)
        at.run()

        assert not at.exception
        captions = " ".join(c.value for c in at.caption)
        assert "Public research demo · Read-only" in captions
        # Persisted records are still readable...
        assert "Sendero Circular" in " ".join(m.value for m in at.markdown)
        # ...but there is no control that would change them.
        labels = [b.label for b in at.button]
        writes = ("Asignar", "Escalar", "Descartar", "Avanzar", "Registrar", "Crear")
        for word in writes:
            assert not [label for label in labels if word in label], word
        assert "triaje y ciclo de vida desactivados" in captions
        assert "registro de parcelas desactivado" in captions
        assert "gestión de tenencia desactivada" in captions
        # Analytical surfaces are intact.
        assert decks, "spatial map was not rendered"
        assert at.get("download_button")
        charts = ("plotly_chart", "vega_lite_chart", "arrow_vega_lite_chart")
        assert any(at.get(kind) for kind in charts)
        assert at.slider
    finally:
        _reset_engine()
