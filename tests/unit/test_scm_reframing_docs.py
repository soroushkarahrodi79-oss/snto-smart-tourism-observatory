"""SCM causal-reframing caveat is present in the module docs (Backlog B-08).

Documentation-only guard: asserts the "spatial contrast, not causal attribution"
caveat text is present in both SCM modules, so the reframing cannot be silently
dropped by a future edit. Behaviour is covered by the existing SCM suites
(test_spatial_causality.py, test_scm_real_zones.py); this file asserts nothing
about behaviour and must not.
"""
from __future__ import annotations

import re
from pathlib import Path

import src.spatial_causality.analyzer as analyzer

_ROOT = Path(__file__).resolve().parents[2]

_REQUIRED_PHRASES = [
    "SPATIAL CONTRAST, NOT CAUSAL ATTRIBUTION",
    "A localized spatial contrast is not evidence of causation",
    "expert-defined operational heuristics that have not been empirically",
    "SCM_REFRAMING.md",
    "documentation caveat only",
]


def _norm(text: str) -> str:
    """Collapse whitespace so phrase matching is robust to docstring line-wrapping."""
    return re.sub(r"\s+", " ", text)


def _analyzer_source() -> str:
    return _norm(Path(analyzer.__file__).read_text(encoding="utf-8"))


def _operational_source() -> str:
    return _norm((_ROOT / "run_scm_operational.py").read_text(encoding="utf-8"))


def test_analyzer_docstring_carries_non_causal_caveat():
    src = _analyzer_source()
    for phrase in _REQUIRED_PHRASES:
        assert phrase in src, f"missing caveat phrase in analyzer.py: {phrase!r}"


def test_operational_docstring_carries_non_causal_caveat():
    src = _operational_source()
    for phrase in _REQUIRED_PHRASES:
        assert phrase in src, f"missing caveat phrase in run_scm_operational.py: {phrase!r}"


def test_caveat_names_the_uncalibrated_thresholds():
    # The specific SIG thresholds must be named as heuristics, not left implicit.
    assert "0.15 / 0.07" in _analyzer_source()
    assert "0.15 / 0.07" in _operational_source()


def test_classification_labels_are_preserved_verbatim():
    # The reframing must NOT rename the output labels — downstream code and data
    # depend on them (SCM_REFRAMING.md §3: correct the language, not the code).
    src = _analyzer_source()
    for label in ("LOCALIZED_IMPACT", "LANDSCAPE_DRIVEN", "MIXED"):
        assert label in src


def test_analyzer_still_imports_and_exposes_its_api():
    # Cheap behavioural smoke check: the docstring edit did not break the module.
    assert hasattr(analyzer, "evidence_class_for_source")
