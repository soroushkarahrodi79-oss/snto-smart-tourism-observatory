"""I-3 (Phase 0.5G) — truthful generation-freshness resolver.

Guards that the dashboard's *as-of* value comes from committed run-context
provenance or an explicit "not recorded" state — never a fabricated current or
fixed date (the old hard-coded ``REPORT_DATE`` / render-clock behaviour).

Machine-readable / presentation boundary:
  - ``provenance.date`` (and ``dashboard.report_date``) are ``str | None`` —
    ``None`` is the machine-readable absence, never the string "no registrada".
  - UI surfaces call ``display_generation_date(value)`` or fall back inline
    ``value or "no registrada"`` to obtain the human-readable form.
"""
from __future__ import annotations

import json
from datetime import date

from src.platform.freshness import (
    GenerationProvenance,
    display_generation_date,
    generation_date_token,
    resolve_generation_provenance,
)


def _write_run_context(outputs_root, territory: str, payload: dict) -> None:
    d = outputs_root / territory
    d.mkdir(parents=True, exist_ok=True)
    (d / "run_context.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


# ── C. Valid provenance timestamp is surfaced ────────────────────────────────
def test_valid_run_context_is_surfaced(tmp_path) -> None:
    _write_run_context(
        tmp_path,
        "pnsg",
        {"timestamp_utc": "2026-06-12T09:30:00+00:00", "git_sha": "abc1234"},
    )
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)

    assert prov.available is True
    assert prov.generated_utc == "2026-06-12T09:30:00+00:00"
    assert prov.date == "2026-06-12"
    assert prov.short == "2026-06-12"
    assert prov.slug == "2026-06-12"
    assert "2026-06-12" in prov.long
    assert "abc1234" in prov.long


# ── D. Missing provenance → explicit unavailable, never a fabricated date ─────
def test_missing_run_context_is_explicitly_unavailable(tmp_path) -> None:
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)

    assert prov.available is False
    assert prov.generated_utc is None
    assert prov.date is None
    assert prov.short == "no registrada"
    assert prov.slug == "sin-fecha"
    assert "no registrada" in prov.long


def test_unavailable_never_uses_today(tmp_path) -> None:
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)
    today = date.today().isoformat()

    # The honest "unavailable" state must not leak the current date anywhere.
    assert today not in prov.short
    assert today not in prov.slug
    assert today not in prov.long


def test_run_context_without_timestamp_is_unavailable(tmp_path) -> None:
    _write_run_context(tmp_path, "pnsg", {"git_sha": "abc1234"})  # no timestamp
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)
    assert prov.available is False


def test_corrupt_run_context_degrades_to_unavailable(tmp_path) -> None:
    d = tmp_path / "pnsg"
    d.mkdir(parents=True)
    (d / "run_context.json").write_text("{not json", encoding="utf-8")
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)
    assert prov.available is False


def test_slug_is_filename_safe(tmp_path) -> None:
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)
    # The unavailable slug feeds download filenames; it must carry no space.
    assert " " not in prov.slug


# ── The repository as committed has no run context (fresh-clone reality) ──────
def test_repo_pnsg_has_no_committed_run_context() -> None:
    """Documents current reality: no committed run_context.json for PNSG.

    ``data/outputs/pnsg/`` holds ``pipeline_a_summary.json`` (no timestamp) but
    no ``run_context.json`` — so the live app honestly reports "no registrada".
    This is intentional; ingesting a real run context later upgrades it with no
    code change (mirrors the resolver's available branch, tested above).
    """
    prov = resolve_generation_provenance("pnsg")
    assert isinstance(prov, GenerationProvenance)
    assert prov.available is False


# ── Machine-readable None / presentation boundary ─────────────────────────────

def test_date_property_is_none_when_unavailable(tmp_path) -> None:
    """The machine-readable absence is ``None``, not the string "no registrada"."""
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)
    assert prov.date is None  # machine-readable absence


def test_date_property_is_string_when_available(tmp_path) -> None:
    _write_run_context(
        tmp_path, "pnsg",
        {"timestamp_utc": "2026-08-10T08:00:00+00:00", "git_sha": "def5678"},
    )
    prov = resolve_generation_provenance("pnsg", outputs_root=tmp_path)
    assert prov.date == "2026-08-10"  # real ISO date string, not None


# ── Presentation helpers ──────────────────────────────────────────────────────

def test_display_generation_date_none_returns_label() -> None:
    assert display_generation_date(None) == "no registrada"


def test_display_generation_date_real_returns_unchanged() -> None:
    assert display_generation_date("2026-06-12") == "2026-06-12"


def test_generation_date_token_none_is_filename_safe() -> None:
    token = generation_date_token(None)
    assert token == "no-registrada"
    assert " " not in token


def test_generation_date_token_real_returns_unchanged() -> None:
    assert generation_date_token("2026-06-12") == "2026-06-12"


# ── Dashboard machine-readable absence ───────────────────────────────────────

def test_dashboard_report_date_is_none_without_run_context(tmp_path) -> None:
    """load_dashboard stores None in dashboard.report_date when no run_context exists."""
    from src.platform.freshness import resolve_generation_provenance as _resolve
    prov = _resolve("pnsg", outputs_root=tmp_path)
    assert prov.date is None  # the value that flows into compute_executive_dashboard


# ── Report builder machine-readable absence ───────────────────────────────────

def test_territorial_brief_stores_none_not_today(tmp_path) -> None:
    """build_territorial_brief stores None — never silently substitutes today."""
    from src.reporting.territorial_brief import (
        build_territorial_brief,
        render_territorial_brief_markdown,
    )
    brief = build_territorial_brief([], territory_name="PNSG", report_date=None)
    assert brief["metadata"]["report_date"] is None
    md = render_territorial_brief_markdown(brief)
    assert "no registrada" in md
    assert "None" not in md
    today = date.today().isoformat()
    assert today not in md


def test_cets_stores_none_not_today() -> None:
    """build_cets_readiness stores None — never silently substitutes today."""
    from src.reporting.cets_readiness import (
        EvidenceSignals,
        build_cets_readiness,
        render_cets_readiness_markdown,
    )

    signals = EvidenceSignals(
        satellite_real=False,
        mobility_real=False,
        socioeconomic_series=False,
        field_measured_plots=0,
        scm_real_zones=0,
    )
    report = build_cets_readiness(
        territory_name="PNSG", park="pnsg", report_date=None, signals=signals
    )
    assert report["metadata"]["report_date"] is None
    md = render_cets_readiness_markdown(report)
    assert "no registrada" in md
    assert "None" not in md
    today = date.today().isoformat()
    assert today not in md


def test_prug_stores_none_not_today() -> None:
    """build_prug_monitoring stores None — never silently substitutes today."""
    from src.reporting.prug_monitoring import build_prug_monitoring

    report = build_prug_monitoring("snr", report_date=None)
    assert report["metadata"]["report_date"] is None


# ── Filename token contract ────────────────────────────────────────────────────

def test_date_stamp_none_yields_no_registrada() -> None:
    """_date_stamp(None) must not produce a filename with spaces or 'None'."""
    from src.ui.tabs.tab_reports import _date_stamp
    token = _date_stamp(None)
    assert token == "no-registrada"
    assert " " not in token
    assert "None" not in token


def test_date_stamp_real_date_passthrough() -> None:
    from src.ui.tabs.tab_reports import _date_stamp
    assert _date_stamp("2026-06-12") == "2026-06-12"
