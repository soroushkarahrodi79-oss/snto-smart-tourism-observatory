"""
SNTO — Truthful generation freshness (I-3, Phase 0.5G)
=====================================================
Resolves the *as-of* provenance of a rendered territory output: **when the
pipeline that produced the currently-committed derived data actually ran**, or
an explicit "not recorded" state.

This exists because the dashboard used to hard-code a single global
``REPORT_DATE`` literal and paint a pulsing 60-second "live" indicator whose
timestamp was only the browser render clock — neither reflected data freshness.

The single truthful source is a committed ``run_context.json`` (see
``src/config/run_context.py``) written next to a pipeline's outputs, carrying a
real ``timestamp_utc`` and ``git_sha``. When no such artifact is associated with
the current output — the case in a fresh clone today — the honest answer is
*unavailable*, never a fabricated ``datetime.now()`` / ``date.today()`` /
app-startup / git-checkout / filesystem-mtime / hard-coded value.

An acquisition/observation date (a Sentinel-2 scene date) is a **different**
fact and is deliberately not resolved here (see ``src/platform/provenance.py``
and ADR / Phase 0.5C): a scene observed on date X and a pipeline run on date Y
must remain two separate facts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Repo root: src/platform/freshness.py -> parents[2].
_OUTPUTS_ROOT = Path(__file__).resolve().parents[2] / "data" / "outputs"

_UNAVAILABLE_SHORT = "no registrada"
_UNAVAILABLE_LONG = (
    "Fecha de generación de datos no registrada en este entorno"
)
_UNAVAILABLE_SLUG = "no-registrada"


@dataclass(frozen=True)
class GenerationProvenance:
    """Truthful *as-of* provenance for a rendered output.

    Either a real pipeline-generation timestamp (from a committed
    ``run_context.json``) or an explicit *unavailable* state. Never a fabricated
    current or fixed date.
    """

    available: bool
    generated_utc: str | None = None  # full ISO timestamp, only when available
    git_sha: str | None = None

    @property
    def date(self) -> str | None:
        """The ``YYYY-MM-DD`` portion of the generation timestamp, or None."""
        return self.generated_utc[:10] if self.generated_utc else None

    @property
    def short(self) -> str:
        """Compact value for inline UI (real date, or 'no registrada')."""
        return self.date or _UNAVAILABLE_SHORT

    @property
    def long(self) -> str:
        """Explicit sentence for provenance/audit surfaces."""
        if self.available and self.generated_utc:
            base = f"Datos generados el {self.date} (UTC)"
            return f"{base} · commit {self.git_sha}" if self.git_sha else base
        return _UNAVAILABLE_LONG

    @property
    def slug(self) -> str:
        """Filename-safe token (real date, or 'no-registrada')."""
        return self.date or _UNAVAILABLE_SLUG


def _valid_iso_timestamp(ts: str) -> bool:
    """Return True iff *ts* parses as an ISO-8601 datetime."""
    try:
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def display_generation_date(value: str | None) -> str:
    """Presentation helper: maps the machine-readable ``str | None`` date to a
    human-readable string for UI surfaces.  ``None`` → ``"no registrada"``.
    Use at every boundary where ``dashboard.report_date`` is shown in the UI.
    """
    return value or _UNAVAILABLE_SHORT


def generation_date_token(value: str | None) -> str:
    """Filename-safe token for the as-of date.  ``None`` → ``"no-registrada"``
    (no spaces, no ``None`` literal in a download filename).
    Same behaviour as ``_date_stamp(value)`` in ``tab_reports.py``.
    """
    return value or "no-registrada"


def resolve_generation_provenance(
    territory_key: str, *, outputs_root: str | Path | None = None
) -> GenerationProvenance:
    """Resolve the generation provenance for ``territory_key``'s current output.

    Reads ``<outputs_root>/<territory_key>/run_context.json`` when present and
    carrying a ``timestamp_utc``; otherwise returns an explicit *unavailable*
    result. Never invents a timestamp.
    """
    root = Path(outputs_root) if outputs_root is not None else _OUTPUTS_ROOT
    path = root / territory_key / "run_context.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return GenerationProvenance(available=False)
        ts = data.get("timestamp_utc")
        if isinstance(ts, str) and ts and _valid_iso_timestamp(ts):
            sha = data.get("git_sha")
            return GenerationProvenance(
                available=True,
                generated_utc=ts,
                git_sha=sha if isinstance(sha, str) and sha else None,
            )
    return GenerationProvenance(available=False)
