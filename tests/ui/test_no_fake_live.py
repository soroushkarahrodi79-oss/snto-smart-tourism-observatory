"""I-3 (Phase 0.5G) — the dashboard must not imply a live data feed.

Static-source contracts (mirroring ``test_app_shell.py``'s approach: read the
sources, no heavy Streamlit render). They fail loudly if the removed fake-live
machinery — 60 s autorefresh, a render-clock "Actualizado" timestamp, a cycle
counter, a pulsing "live" dot, or the hard-coded global report date — is
reintroduced.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_APP_SRC = (_ROOT / "app.py").read_text(encoding="utf-8")
_WIDGETS_SRC = (_ROOT / "src/ui/render_widgets.py").read_text(encoding="utf-8")
_LAYOUT_SRC = (_ROOT / "src/ui/layout.py").read_text(encoding="utf-8")
_REQUIREMENTS = (_ROOT / "requirements.txt").read_text(encoding="utf-8")


# ── A. No fake live refresh ──────────────────────────────────────────────────
def test_app_does_not_autorefresh() -> None:
    assert "st_autorefresh" not in _APP_SRC
    assert "streamlit_autorefresh" not in _APP_SRC


def test_no_render_clock_or_cycle_counter() -> None:
    assert "Actualizado:" not in _WIDGETS_SRC
    assert "ciclo #" not in _WIDGETS_SRC
    assert "refresh_count" not in _WIDGETS_SRC


def test_no_pulsing_live_dot() -> None:
    # Neither the element nor its CSS keyframes may return.
    assert "snto-pulse" not in _WIDGETS_SRC
    assert "snto-pulse" not in _LAYOUT_SRC
    assert "@keyframes snto-pulse" not in _LAYOUT_SRC


# ── B. No browser-clock freshness ────────────────────────────────────────────
def test_alert_strip_has_no_wall_clock() -> None:
    # The live-alert module must not read the current time for a freshness label.
    assert "datetime.now(" not in _WIDGETS_SRC
    assert "date.today(" not in _WIDGETS_SRC


# ── No hard-coded global report date ─────────────────────────────────────────
def test_no_hardcoded_report_date_literal() -> None:
    assert "REPORT_DATE" not in _LAYOUT_SRC
    assert "2026-06-12" not in _LAYOUT_SRC


# ── Dependency declaration is preserved (usage was removed) ──────────────────
# Per Phase 0.5 audit policy, Phase 0.5 does not change dependencies: usage is
# removed in I-3 but the dependency declaration in requirements.txt is retained.
# A separate cleanup PR removes it once no other consumer references it.
def test_autorefresh_usage_removed_from_app() -> None:
    # Belt-and-suspenders: _APP_SRC already asserted above; this makes the
    # dependency-vs-usage contract explicit in one place.
    assert "st_autorefresh(" not in _APP_SRC
    assert "streamlit_autorefresh" not in _APP_SRC
