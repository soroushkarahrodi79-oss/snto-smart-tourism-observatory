"""CI guards that documented evidence claims match live repository state.

Companion to ``test_version_sync.py`` (which pins version/DOI metadata the same
way). It exists because of a real incident: README and CLAUDE.md described v2.2
as shipping a "real MITMA feed replacing the mock" and an "SVI time-series with
a real trend", while none of the three v2.2 real-data feeds had actually been
ingested. The code was honest throughout — each path has an availability gate
and falls back to labelled curated/simulated behaviour — but the prose drifted,
which is precisely the overclaim ADR-004 and the project non-negotiables forbid.

HOW THESE GUARDS BEHAVE
=======================
Each feed below is **pinned to its current ingestion state**. Ingesting a feed
is a *good* outcome, so these guards must never obstruct it — instead the pin
fails loudly with the exact list of documents to update in the same PR. Flip the
pin to ``True``, correct the docs, and the guard keeps protecting the new claim.

The prose guards are conditional on the pin: while a feed is un-ingested, the
retired overclaim phrasings must not reappear (mirroring how
``test_version_sync`` asserts the retired Zenodo DOI stays absent). Once a feed
is genuinely ingested, those phrasings become accurate and the guard relaxes on
its own rather than blocking the truth.
"""
from pathlib import Path

from src.reporting.cets_readiness import resolve_signals

ROOT = Path(__file__).parent.parent

# ── Pinned ingestion state of the three v2.2 real-data feeds ─────────────────
# Flip a pin to True in the same PR that ingests the feed AND corrects the docs
# listed in DOCS_CLAIMING_EVIDENCE below.
MOBILITY_INGESTED = False
SCM_REAL_ZONES_INGESTED = False
SVI_SERIES_INGESTED = False

# Documents that make evidence claims and must be updated together.
DOCS_CLAIMING_EVIDENCE = (
    "README.md (§1 status table, §3 capabilities, §9 limitations)",
    "CLAUDE.md (Current Status → v2.2 bullet)",
)

_UPDATE_HINT = "Update: " + "; ".join(DOCS_CLAIMING_EVIDENCE)


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def _claude_md() -> str:
    return (ROOT / "CLAUDE.md").read_text(encoding="utf-8")


# ── Tripwires: pinned state vs live state ────────────────────────────────────

def test_mobility_ingestion_matches_its_pin() -> None:
    live = resolve_signals("pnsg").mobility_real
    assert live is MOBILITY_INGESTED, (
        f"Real MITMA mobility ingestion changed (live={live}, "
        f"pinned={MOBILITY_INGESTED}). If the snapshot now exists, this is good "
        f"news: flip MOBILITY_INGESTED and say so in the docs. {_UPDATE_HINT}"
    )


def test_scm_real_zone_ingestion_matches_its_pin() -> None:
    live = resolve_signals("pnsg").scm_zones_real
    assert live is SCM_REAL_ZONES_INGESTED, (
        f"Real multi-scale SCM zone exports changed (live={live}, "
        f"pinned={SCM_REAL_ZONES_INGESTED}). Causal attribution stops being a "
        f"simulation once these exist — that must be stated. {_UPDATE_HINT}"
    )


def test_svi_series_ingestion_matches_its_pin() -> None:
    live = resolve_signals("pnsg").socioeconomic_series
    assert live is SVI_SERIES_INGESTED, (
        f"SVI socioeconomic series availability changed (live={live}, "
        f"pinned={SVI_SERIES_INGESTED}). A second dated snapshot makes the "
        f"trend real. {_UPDATE_HINT}"
    )


def test_field_campaign_is_still_pending() -> None:
    """The #26 gate. If this fails the campaign ran — a project milestone."""
    signals = resolve_signals("pnsg")
    assert signals.field_validated is False, (
        f"Measured field plots now exist ({signals.field_measured_plots}). "
        "Run the agreement analysis (src/validation/agreement.py) and report "
        "the verdict honestly, pass or fail, before claiming validation. "
        f"{_UPDATE_HINT}"
    )


# ── Prose guards: retired overclaims must not reappear ───────────────────────

def test_readme_does_not_reclaim_a_real_mobility_feed() -> None:
    if MOBILITY_INGESTED:
        return  # the claim would now be true; nothing to guard
    readme = _readme()
    for phrase in (
        "feed **real de movilidad MITMA** sustituyendo el mock",
        "feed real de movilidad MITMA, capacidad LAC/ROS",
    ):
        assert phrase not in readme, (
            f"README re-introduces the retired overclaim {phrase!r} while "
            "src/mobility/snapshot/mobility.json does not exist. The honest "
            "claim is that the ingestion path and its gate shipped."
        )


def test_claude_md_does_not_reclaim_real_feeds() -> None:
    if MOBILITY_INGESTED and SVI_SERIES_INGESTED:
        return
    text = _claude_md()
    for phrase in (
        "real MITMA municipal-mobility feed replacing the old mock",
        "LAC/ROS carrying-capacity framework consuming real mobility",
        "SVI socioeconomic time-series with a real trend",
    ):
        assert phrase not in text, (
            f"CLAUDE.md re-introduces the retired overclaim {phrase!r}. These "
            "feeds are built with honest gates but are not ingested; see the "
            "v2.2 bullet for the accurate wording."
        )


def test_readme_limitations_section_documents_the_un_ingested_feeds() -> None:
    """§9 must keep carrying the gap while the feeds are empty."""
    if MOBILITY_INGESTED and SCM_REAL_ZONES_INGESTED and SVI_SERIES_INGESTED:
        return
    readme = _readme()
    assert "Honestidad sobre limitaciones" in readme
    assert "sin ingerir" in readme, (
        "README §9 must state that the v2.2 real-data paths are built but not "
        "ingested. Removing that line while the gates are empty is an "
        "overclaim by omission."
    )


# ── The canonical vocabulary must keep the simulated/synthetic distinction ──

def test_readiness_report_uses_the_five_tier_evidence_vocabulary() -> None:
    """ADR-004: 'simulated' must stay distinct from 'synthetic'.

    Guards against a future refactor swapping EvidenceClass back for
    temporal.manifest.DataStatus, which has no SIMULATED tier and would
    silently relabel model-derived projections as demo mocks.
    """
    from src.platform.evidence import EvidenceClass
    from src.reporting.cets_readiness import build_cets_readiness

    report = build_cets_readiness(territory_name="PNSG", park="pnsg")
    tiers = set(report["summary"]["by_evidence_class"])
    assert tiers == {e.value for e in EvidenceClass}
    assert "simulated" in tiers
