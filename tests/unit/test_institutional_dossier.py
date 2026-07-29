"""Contracts for the OAPN institutional dossier generator (v3.0).

The non-negotiables under test:

* The published figures match the live sources exactly — the dossier that leaves
  the building cannot drift from the system it describes (it once claimed a
  restoration budget 7× under the real one).
* CETS coverage is never stated above what ``cets_readiness`` declares, and a
  principle whose live evidence is ``missing`` says so — the overclaim that was
  live in this document for Principle 10.
* No wording ever asserts field validation while campaign #26 is pending.
* Generation is deterministic and idempotent, so ``--check`` can gate CI without
  false alarms (this is why the exact test count is deliberately absent).
"""
from __future__ import annotations

from pathlib import Path

from scripts.build_dossier import DOSSIER, apply_blocks, missing_markers
from src.reporting.cets_readiness import build_cets_readiness
from src.reporting.institutional_dossier import (
    ALL_BLOCKS,
    BLOCK_FRAMEWORK,
    BLOCK_MATURITY,
    BLOCK_RESULTS,
    build_dossier_blocks,
    collect_facts,
)

_ROOT = Path(__file__).resolve().parents[2]


# ── Figures match their live sources ─────────────────────────────────────────

def test_results_block_matches_the_real_trail_summary() -> None:
    from src.platform.real_trails import get_real_trails

    summary = get_real_trails("pnsg").summary
    block = build_dossier_blocks("pnsg")[BLOCK_RESULTS]

    assert f"{summary['n_degrading_positive_delta']} de " in block
    assert str(summary["n_with_valid_delta"]) in block
    assert f"{summary['scm_localized']} localizados" in block
    assert f"{summary['scm_mixed']} mixtos" in block
    assert f"{summary['scm_landscape']} a escala de paisaje" in block


def test_budget_is_rendered_from_the_live_total_not_a_literal() -> None:
    from src.platform.real_trails import get_real_trails

    total = get_real_trails("pnsg").summary["total_budget_eur"]
    expected = f"{total:,.0f} €".replace(",", ".")
    assert expected in build_dossier_blocks("pnsg")[BLOCK_RESULTS]


def test_the_retired_stale_figures_are_gone_from_the_committed_dossier() -> None:
    """Regression pin on the specific drift this module was written to fix."""
    text = DOSSIER.read_text(encoding="utf-8")
    for stale in ("17 de 73 senderos", "~205.000 €", "474 tests"):
        assert stale not in text, f"cifra obsoleta reintroducida: {stale!r}"


# ── CETS coverage never exceeds what the module declares ─────────────────────

def test_framework_block_never_claims_direct_coverage_beyond_core() -> None:
    """Only a CORE principle may read "de forma directa"."""
    report = build_cets_readiness(territory_name="PNSG", park="pnsg")
    by_key = {p["key"]: p for p in report["principles"]}
    block = build_dossier_blocks("pnsg")[BLOCK_FRAMEWORK]

    for key, principle in by_key.items():
        number = principle["title"].split("·", 1)[0].strip()
        prefix = f"- **Principio {number}**"
        line = next(
            (ln for ln in block.splitlines() if ln.startswith(prefix)), None
        )
        if line is None:
            continue  # not one of the principles this section speaks to
        if principle["coverage"] != "core":
            assert "de forma directa" not in line, (
                f"{key} declared {principle['coverage']} but reads as direct"
            )


def test_principle_10_reports_its_missing_evidence() -> None:
    """The exact overclaim that was live: P10 stated as directly covered.

    While mobility is not ingested its evidence is ``missing``, so the block must
    say so rather than assert coverage the data does not back.
    """
    report = build_cets_readiness(territory_name="PNSG", park="pnsg")
    p10 = next(p for p in report["principles"] if p["key"] == "p10_flujos")
    block = build_dossier_blocks("pnsg")[BLOCK_FRAMEWORK]
    line = next(ln for ln in block.splitlines() if ln.startswith("- **Principio 10**"))

    if p10["evidence_class"] == "missing":
        assert "sin dato real hoy" in line
        assert "de forma directa" not in line


# ── Validation honesty ───────────────────────────────────────────────────────

def test_maturity_block_states_the_campaign_is_pending() -> None:
    block = build_dossier_blocks("pnsg")[BLOCK_MATURITY]
    assert "#26" in block
    assert "no se afirma validación de campo" in block


def test_maturity_block_reports_the_three_feed_gates() -> None:
    block = build_dossier_blocks("pnsg")[BLOCK_MATURITY]
    for feed in ("movilidad MITMA", "zonas SCM", "serie socioeconómica"):
        assert feed in block


def test_maturity_block_omits_a_brittle_test_count() -> None:
    """A number that changes every PR would make the CI check cry wolf."""
    block = build_dossier_blocks("pnsg")[BLOCK_MATURITY]
    assert "tests automatizados**" not in block
    assert "README" in block  # points at the live count instead


# ── Determinism, idempotence and the marker machinery ────────────────────────

def test_generation_is_deterministic() -> None:
    assert build_dossier_blocks("pnsg") == build_dossier_blocks("pnsg")


def test_every_declared_block_is_produced() -> None:
    blocks = build_dossier_blocks("pnsg")
    assert set(blocks) == set(ALL_BLOCKS)
    assert all(body.strip() for body in blocks.values())


def test_committed_dossier_carries_every_marker() -> None:
    assert missing_markers(DOSSIER.read_text(encoding="utf-8")) == []


def test_apply_blocks_replaces_only_between_markers() -> None:
    text = (
        "prosa intacta\n"
        "<!-- SNTO:AUTO:resultados -->\n"
        "viejo\n"
        "<!-- /SNTO:AUTO:resultados -->\n"
        "más prosa intacta\n"
    )
    out = apply_blocks(text, {"resultados": "nuevo"})
    assert "prosa intacta" in out
    assert "más prosa intacta" in out
    assert "nuevo" in out
    assert "viejo" not in out


def test_apply_blocks_is_idempotent() -> None:
    text = DOSSIER.read_text(encoding="utf-8")
    blocks = build_dossier_blocks("pnsg")
    once = apply_blocks(text, blocks)
    assert apply_blocks(once, blocks) == once


def test_apply_blocks_fills_an_empty_marker_pair() -> None:
    """First run on a freshly-marked document must populate it."""
    text = "<!-- SNTO:AUTO:marco -->\n<!-- /SNTO:AUTO:marco -->\n"
    out = apply_blocks(text, {"marco": "contenido"})
    assert "contenido" in out


def test_apply_blocks_skips_a_block_whose_markers_are_absent() -> None:
    text = "solo prosa\n"
    assert apply_blocks(text, {"resultados": "x"}) == text


# ── Honest absence ───────────────────────────────────────────────────────────

def test_collect_facts_returns_none_for_a_territory_without_trails() -> None:
    assert collect_facts("territorio_inexistente") is None


def test_results_block_degrades_honestly_without_trails() -> None:
    from src.reporting.institutional_dossier import _render_results

    block = _render_results(None)
    assert "Sin sendas reales" in block
    assert "€" not in block  # no fabricated budget


# ── The committed document is in sync ────────────────────────────────────────

def test_committed_dossier_is_up_to_date_with_live_data() -> None:
    """Mirrors `scripts/build_dossier.py --check`, enforced in the test suite."""
    original = DOSSIER.read_text(encoding="utf-8")
    regenerated = apply_blocks(original, build_dossier_blocks("pnsg"))
    assert regenerated == original, (
        "El dossier institucional está desactualizado. "
        "Ejecuta: python scripts/build_dossier.py"
    )
