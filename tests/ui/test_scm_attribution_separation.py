"""I-4 (Phase 0.5H) — SCM attribution separated from real measurement at display.

Static-source contracts on the maintained real-trails diagnostic surface
(mirroring ``test_no_fake_live.py``'s approach: read the source, no heavy
Streamlit render). They fail loudly if:

* the stale, factually-wrong "Causa (SCM) es simulada" wording returns
  (the live Pipeline-A SCM classification is computed from real Sentinel-2
  rasters, not the α-decay simulator — it was never simulated); or
* the column/caption reverts to an unqualified "Causa" (implying a
  confirmed cause) instead of a model-attribution qualifier.

Historical audit docs under docs/audit/2026-snto-baseline/ are deliberately
NOT scanned here — they are frozen baseline evidence, not the live surface.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DIAGNOSTIC_SRC = (_ROOT / "src/ui/tabs/tab_diagnostic.py").read_text(encoding="utf-8")
_MAP_LAYERS_SRC = (_ROOT / "src/platform/map_layers.py").read_text(encoding="utf-8")
_REAL_TRAILS_SRC = (_ROOT / "src/platform/real_trails.py").read_text(encoding="utf-8")


def test_diagnostic_table_no_longer_says_causa_scm_column() -> None:
    assert '"Causa (SCM)"' not in _DIAGNOSTIC_SRC


def test_diagnostic_table_uses_atribucion_scm_column() -> None:
    assert '"Atribución SCM"' in _DIAGNOSTIC_SRC


def test_diagnostic_caption_no_longer_claims_scm_is_simulated() -> None:
    assert "es simulada" not in _DIAGNOSTIC_SRC


def test_diagnostic_caption_denies_causal_validation() -> None:
    assert "causa confirmada" in _DIAGNOSTIC_SRC.lower()


def test_diagnostic_has_no_bare_causal_claim() -> None:
    lowered = _DIAGNOSTIC_SRC.lower()
    assert "causado por" not in lowered
    assert "causa confirmada:" not in lowered


def test_diagnostic_source_imports_canonical_caveat() -> None:
    assert "SCM_ATTRIBUTION_CAVEAT" in _DIAGNOSTIC_SRC
    assert "SCM_ATTRIBUTION_LABEL" in _DIAGNOSTIC_SRC


def test_map_tooltip_no_longer_uses_bare_causa_field() -> None:
    assert "Causa: {scm}" not in _MAP_LAYERS_SRC


def test_map_tooltip_no_causal_confirmatory_wording() -> None:
    # The denial phrase ("...ni causa confirmada") legitimately contains the
    # substring "causa confirmada" — what must never appear is an unqualified
    # affirmative causal claim.
    lowered = _MAP_LAYERS_SRC.lower()
    assert "causado por" not in lowered
    assert "es la causa confirmada" not in lowered
    assert "causa confirmada:" not in lowered


def test_real_trails_defines_canonical_caveat_constant() -> None:
    assert "SCM_ATTRIBUTION_CAVEAT" in _REAL_TRAILS_SRC
    assert "SCM_ATTRIBUTION_LABEL" in _REAL_TRAILS_SRC


def test_real_trails_scm_label_map_avoids_causa_mixta() -> None:
    assert '"Causa mixta"' not in _REAL_TRAILS_SRC
