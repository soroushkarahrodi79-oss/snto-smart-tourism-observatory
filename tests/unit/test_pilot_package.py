"""Contracts for the procurement-ready pilot package (A07).

The non-negotiables under test:

* Every commercial decision the system cannot make stays an **explicit open
  marker**, never a fabricated figure. A procurement document that quietly
  invents a price is worse than one that leaves a blank.
* The package never promises validation while campaign #26 is pending, and says
  so in its own words.
* Acceptance is tied to *measuring and reporting* the agreement, not to the
  result coming out positive — the opposite would incentivise the bias this
  project exists to avoid.
* Every relative link resolves, since this document is meant to be handed to an
  institution.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DOC = _ROOT / "docs" / "product" / "pilot-package.md"

# Decisions declared open in §1. Each must remain marked, unanswered, until the
# owner fills it in deliberately.
_OPEN_DECISIONS = ("D1", "D2", "D3", "D4", "D5", "D6", "D7")


def _text() -> str:
    return _DOC.read_text(encoding="utf-8")


# ── Commercial gaps stay gaps ────────────────────────────────────────────────

def test_document_exists_and_declares_its_open_state() -> None:
    text = _text()
    assert "decisiones comerciales y jurídicas siguen abiertas" in text
    assert "Ninguna cifra económica de este documento está inventada" in text


def test_every_declared_decision_is_listed_in_the_summary_table() -> None:
    text = _text()
    for decision in _OPEN_DECISIONS:
        assert f"| {decision} |" in text, f"{decision} falta en la tabla resumen §1"


def test_the_owner_only_decisions_carry_an_open_marker() -> None:
    """Every open decision is marked inline with 🔲 where it bites."""
    text = _text()
    for decision in _OPEN_DECISIONS:
        assert f"🔲 **{decision}" in text, f"{decision} sin marcador 🔲 en su sección"


def test_no_currency_figure_is_invented_anywhere() -> None:
    """The whole point: no price may appear until the owner sets one.

    Allows the one real figure quoted from the system (the indicative
    restoration budget is not part of this document) by asserting there is no
    euro amount at all.
    """
    text = _text()
    amounts = re.findall(r"\d[\d.,]*\s*(?:€|EUR\b|euros)", text)
    assert amounts == [], f"cifra económica inventada en el paquete: {amounts}"


def test_pricing_section_defers_rather_than_estimates() -> None:
    text = _text()
    assert "🔲 **D1 — Precio y desglose.** Pendiente" in text
    # Cost concepts may be listed, but no number attached to them.
    assert "Sentinel-2 y Copernicus son **abiertos**" in text


# ── Evidence honesty ─────────────────────────────────────────────────────────

def test_package_states_it_does_not_promise_prior_validation() -> None:
    text = _text()
    assert "No promete validación previa" in text
    assert "no** equivale a *\"validado en campo\"*" in text


def test_package_names_the_field_campaign_as_the_deliverable_not_a_given() -> None:
    text = _text()
    assert "la campaña de campo nunca se ha" in text
    assert "El piloto existe para ejecutarla" in text


def test_acceptance_is_not_conditioned_on_a_positive_result() -> None:
    """Paying only for a favourable finding would incentivise bias."""
    text = _text()
    assert "NO es que la correlación salga positiva" in text
    assert "se cumpla o no el umbral" in text


def test_package_carries_the_methodological_sample_minimum() -> None:
    """Numbers that ARE real must match the protocol (§5)."""
    text = _text()
    assert "3 parcelas co-localizadas" in text
    assert "15–20" in text


def test_out_of_scope_keeps_api_deployment_behind_its_adr() -> None:
    text = _text()
    assert "ADR-012" in text
    assert "Fuera de alcance" in text


# ── It is handed to an institution: links must resolve ───────────────────────

def test_every_relative_link_resolves() -> None:
    text = _text()
    broken: list[str] = []
    for target in re.findall(r"\]\(([^)#][^)]*)\)", text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (_DOC.parent / target).resolve().exists():
            broken.append(target)
    assert broken == [], f"enlaces rotos en el paquete de piloto: {broken}"


def test_product_index_links_the_package() -> None:
    index = (_ROOT / "docs" / "product" / "README.md").read_text(encoding="utf-8")
    assert "pilot-package.md" in index
