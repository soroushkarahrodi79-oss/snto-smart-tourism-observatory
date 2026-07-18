"""Regression tests for the Fase 6.1 semantic design-system rules."""

from src.ui.layout import _BASE_CSS
from src.ui.render_helpers import _alert_accent


def test_semantic_card_hierarchy_is_defined() -> None:
    assert ".snto-decision-card" in _BASE_CSS
    assert ".snto-asset-card" in _BASE_CSS
    assert ".snto-evidence-card" in _BASE_CSS
    assert "border: 1px solid var(--snto-border-hairline)" in _BASE_CSS
    assert "box-shadow: none" in _BASE_CSS


def test_typographic_intent_and_accessible_body_size_are_defined() -> None:
    assert ".snto-decision-value" in _BASE_CSS
    assert "font-size: 1.45rem" in _BASE_CSS
    assert ".snto-context-value" in _BASE_CSS
    assert "font-size: 1.05rem" in _BASE_CSS
    assert ".snto-body-copy" in _BASE_CSS
    assert "font-size: 0.875rem" in _BASE_CSS


def test_asset_card_accent_is_driven_by_alert_severity() -> None:
    assert _alert_accent("CRITICAL_INTERVENTION") == "#c62828"
    assert _alert_accent("URGENT_MONITORING") == "#e65100"
    assert _alert_accent("PREVENTIVE_ACTION") == "#1565c0"
    assert _alert_accent("NORMAL") == "#2e7d32"
    assert _alert_accent("UNKNOWN") == _alert_accent("NORMAL")
