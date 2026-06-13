"""
SNTO — Reproducible run context (F6)
====================================
Captures, per pipeline execution, the provenance needed to reproduce or audit a
result: git commit, UTC timestamp, Python version, and the run parameters
(territory, years, mode…). Written next to the outputs as ``run_context.json``
so every result folder answers "which code and which parameters produced this?".

This complements the F2 series manifest (what data) with the run provenance
(what code / when / how it was invoked).
"""
from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _git_sha() -> str:
    """Short git commit hash, or 'unknown' outside a repo / without git."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _git_dirty() -> bool:
    """True if the working tree has uncommitted changes (best-effort)."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        return out.returncode == 0 and bool(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


@dataclass(frozen=True)
class RunContext:
    """Provenance of a single pipeline run."""
    tool: str
    git_sha: str
    git_dirty: bool
    timestamp_utc: str
    python_version: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_json(
        self, outdir: str | Path, filename: str = "run_context.json"
    ) -> Path:
        p = Path(outdir)
        p.mkdir(parents=True, exist_ok=True)
        path = p / filename
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path


def capture(tool: str, **params: Any) -> RunContext:
    """Capture the current run context for ``tool`` with arbitrary parameters."""
    return RunContext(
        tool=tool,
        git_sha=_git_sha(),
        git_dirty=_git_dirty(),
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        python_version=platform.python_version(),
        params=dict(params),
    )
