"""
Unit test for the tab's graceful degradation when the persistence backend has
no tables (Fase 5, 5.9) — the bug the integration smoke surfaced: a fresh dev
SQLite file with no schema must not crash the whole dashboard.
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import src.ui.tabs.tab_urgent_actions as tab


class _FakeSt:
    """Minimal Streamlit stand-in recording the calls the tab makes."""

    def __init__(self) -> None:
        self.infos: list[str] = []

    def subheader(self, *_a, **_k) -> None:  # noqa: D401
        pass

    def caption(self, *_a, **_k) -> None:
        pass

    def info(self, msg: str) -> None:
        self.infos.append(msg)


def test_uninitialised_backend_shows_info_not_crash(monkeypatch) -> None:
    # Engine with NO schema created -> querying "alerts" raises OperationalError.
    engine = create_engine("sqlite:///:memory:")

    @contextmanager
    def _scope():
        with Session(engine) as s:
            yield s

    fake = _FakeSt()
    monkeypatch.setattr(tab, "_open_session", _scope)
    monkeypatch.setattr(tab, "st", fake)

    # Must return cleanly (no exception) and surface the not-initialised notice.
    tab.render_tab_urgent_actions()

    assert any("no está inicializado" in m for m in fake.infos)
    engine.dispose()
