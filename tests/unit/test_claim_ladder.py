"""
WP-2 — the executable claim ladder agrees with the JSON, ADR-016 and evidence.py.

These tests pin the three representations of the SNTO claim ladder to each other
so none can drift:

* ``docs/phase1/claim_ladder.json`` — the canonical machine-readable ladder;
* ``docs/decisions/ADR-016-*.md`` — the ADR that adopts it;
* ``src/platform/evidence.py`` — the runtime evidence→decision gate.
"""
from __future__ import annotations

from pathlib import Path

from src.platform import claim_ladder
from src.platform.evidence import DecisionUse, EvidenceClass, supports

_ADR = (
    Path(__file__).resolve().parents[2]
    / "docs" / "decisions" / "ADR-016-claim-ladder-and-decision-gates.md"
)


def test_ladder_json_loads_with_l0_to_l7_in_order() -> None:
    assert claim_ladder.level_ids() == list(claim_ladder.EXPECTED_LEVEL_IDS)


def test_adr016_documents_the_same_levels() -> None:
    adr = _ADR.read_text(encoding="utf-8")
    for level in claim_ladder.levels():
        assert level["id"] in adr, f"ADR-016 is missing ladder level {level['id']}"
        # The ADR table also names each level; check a distinctive word from it.
        assert level["name"].split()[0].lower() in adr.lower()


def test_runtime_gate_agrees_with_the_ladder() -> None:
    # The single most important assertion: evidence.py must not drift above what
    # the canonical ladder authorizes.
    assert claim_ladder.evidence_gate_violations() == []


def test_blocked_levels_are_marked_blocked() -> None:
    for level_id in ("L5b", "L6", "L7"):
        assert claim_ladder.is_blocked(level_id), f"{level_id} must be blocked today"
    # The observational ceiling and everything below it are not blocked.
    for level_id in ("L0", "L1", "L2", "L3", "L4", "L5a"):
        assert not claim_ladder.is_blocked(level_id)


def test_resource_commitment_is_authorized_by_no_evidence_class() -> None:
    # L5b (resource-committing / restrictive) is blocked for every class,
    # including REAL — the whole point of the WP-2 split.
    for ec in EvidenceClass:
        assert not supports(ec, DecisionUse.RESOURCE_COMMITMENT), ec


def test_field_inspection_is_the_real_only_low_regret_use() -> None:
    assert supports(EvidenceClass.REAL, DecisionUse.FIELD_INSPECTION)
    assert not supports(EvidenceClass.CALIBRATED, DecisionUse.FIELD_INSPECTION)
    for ec in (EvidenceClass.SIMULATED, EvidenceClass.SYNTHETIC, EvidenceClass.MISSING):
        assert not supports(ec, DecisionUse.FIELD_INSPECTION)


def test_every_decision_use_maps_to_a_ladder_level() -> None:
    for use in DecisionUse:
        assert use in claim_ladder.DECISION_USE_LEVEL
        assert claim_ladder.DECISION_USE_LEVEL[use] in claim_ladder.EXPECTED_LEVEL_IDS


def test_ladder_json_declares_itself_enforced() -> None:
    # Once WP-2 lands, the ladder is enforced in code, not merely defined.
    assert claim_ladder.load_ladder()["status"] == "enforced"
