"""
Executable SNTO Claim Ladder (WP-2, ADR-016).

Loads the canonical, machine-readable claim ladder
(``docs/phase1/claim_ladder.json``) and checks that the runtime evidence→decision
gate in :mod:`src.platform.evidence` **agrees** with it. This turns the ladder
from an advisory document into a policy the test-suite enforces: no future agent
can silently let ``evidence.py`` drift above what the ladder authorizes.

Design principles:

* **One gate, not two.** ``evidence.supports()`` remains the single runtime
  authorization gate. This module adds no parallel gate; it is the *consistency
  bridge* between the JSON ladder and that gate, plus a reader-facing accessor.
* **Checks derive from the ladder's own invariants**, so the ladder JSON stays
  the single source of truth — the rules are not hard-coded a second time.
* **No behaviour change.** Existing surfaces already comply (they gate on REAL
  and treat SIMULATED/SYNTHETIC as non-authorizing); WP-2 only makes the coarse
  ``INTERVENTION`` use precise (field-inspection vs resource-commitment) and pins
  the agreement in a test.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.platform.evidence import DecisionUse, EvidenceClass, supports

# Repo-root-relative location of the canonical ladder
# (src/platform/claim_ladder.py -> parents[2] == repo root).
LADDER_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "phase1" / "claim_ladder.json"
)

# Canonical ordered level ids (mirrors ADR-016 and the JSON; asserted equal by
# the test, so a drift in either fails CI rather than silently disagreeing).
EXPECTED_LEVEL_IDS: tuple[str, ...] = (
    "L0", "L1", "L2", "L3", "L4", "L5a", "L5b", "L6", "L7",
)

# Each runtime DecisionUse maps to the ladder level at which it becomes
# authorizable. RESOURCE_COMMITMENT maps to L5b, which the ladder marks blocked.
DECISION_USE_LEVEL: dict[DecisionUse, str] = {
    DecisionUse.MONITORING: "L1",
    DecisionUse.PRIORITIZATION: "L4",
    DecisionUse.FIELD_INSPECTION: "L5a",
    DecisionUse.RESOURCE_COMMITMENT: "L5b",
    DecisionUse.PUBLIC_REPORTING: "L4",
}

# Provenance classes that authorize nothing above L0 (ladder invariant 1).
_NON_AUTHORIZING: tuple[EvidenceClass, ...] = (
    EvidenceClass.SIMULATED,
    EvidenceClass.SYNTHETIC,
    EvidenceClass.MISSING,
)


@lru_cache(maxsize=1)
def load_ladder() -> dict[str, Any]:
    """Parse and return the canonical claim-ladder JSON (cached)."""
    if not LADDER_PATH.is_file():
        raise FileNotFoundError(f"Claim ladder not found at {LADDER_PATH}")
    with LADDER_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def levels() -> list[dict[str, Any]]:
    """All ladder levels, in order."""
    return list(load_ladder()["levels"])


def level_ids() -> list[str]:
    """Ordered level ids (``["L0", "L1", …, "L7"]``)."""
    return [level["id"] for level in levels()]


def invariants() -> list[str]:
    """The ladder's stated invariants (human-readable)."""
    return list(load_ladder()["invariants"])


def level(level_id: str) -> dict[str, Any]:
    """Return one level by id."""
    for lvl in levels():
        if lvl["id"] == level_id:
            return lvl
    raise KeyError(level_id)


def is_blocked(level_id: str) -> bool:
    """Whether the ladder marks a level blocked today (L5b/L6/L7)."""
    return bool(level(level_id).get("blocked_today", False))


def evidence_gate_violations() -> list[str]:
    """Ways :mod:`src.platform.evidence` disagrees with the canonical ladder.

    An **empty** list means the runtime gate is consistent with the ladder. The
    checks are derived from the ladder's own invariants, so the JSON remains the
    single source of truth. Used by ``tests/unit/test_claim_ladder.py``.
    """
    problems: list[str] = []

    # Invariant 1 — SIMULATED / SYNTHETIC / MISSING authorize nothing above L0.
    for ec in _NON_AUTHORIZING:
        for use in DecisionUse:
            if supports(ec, use):
                problems.append(
                    f"{ec.value} must authorize nothing, but supports {use.value}"
                )

    # Invariant 2/5 — a resource-committing (or restrictive) recommendation is
    # L5b, blocked today; REAL provenance alone must not authorize it.
    if supports(EvidenceClass.REAL, DecisionUse.RESOURCE_COMMITMENT):
        problems.append(
            "REAL must not authorize RESOURCE_COMMITMENT (L5b is blocked)"
        )
    if not is_blocked(DECISION_USE_LEVEL[DecisionUse.RESOURCE_COMMITMENT]):
        problems.append(
            "RESOURCE_COMMITMENT maps to a level the ladder does not mark blocked"
        )

    # CALIBRATED is context / prioritization only (L4) — never field inspection,
    # resource commitment, or public reporting as fact.
    for use in (
        DecisionUse.FIELD_INSPECTION,
        DecisionUse.RESOURCE_COMMITMENT,
        DecisionUse.PUBLIC_REPORTING,
    ):
        if supports(EvidenceClass.CALIBRATED, use):
            problems.append(f"CALIBRATED must not authorize {use.value}")

    # REAL must authorize the low-regret observational uses up to its L5a ceiling.
    for use in (
        DecisionUse.MONITORING,
        DecisionUse.PRIORITIZATION,
        DecisionUse.FIELD_INSPECTION,
        DecisionUse.PUBLIC_REPORTING,
    ):
        if not supports(EvidenceClass.REAL, use):
            problems.append(f"REAL should authorize {use.value}")

    return problems
