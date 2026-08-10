"""
scripts/paper1/_figutil.py
==========================
Shared provenance helpers for the Paper-1 figure/table generators (Backlog
B-09). Every generated artifact must be reproducible from committed data and
carry a provenance sidecar recording the exact inputs (SHA-256) and the commit
it was built at, per ``docs/paper1/FIGURE_PLAN.md`` "Figure production
requirements".

No matplotlib import here: input validation and provenance are testable without
a plotting backend, so the "fail loudly on missing input" guarantee holds even
where matplotlib is absent (it is offline figure-tooling, not a runtime dep —
same status as ``make_pipeline_a_figures.py``).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

_ROOT = Path(__file__).resolve().parents[2]


class MissingInput(FileNotFoundError):
    """A required committed input is absent — raised before any rendering."""


def repo_root() -> Path:
    return _ROOT


def require_inputs(paths: Mapping[str, Path]) -> None:
    """Raise :class:`MissingInput` if any required input is absent.

    Called first in every generator so a missing file fails loudly with the
    offending path, never a half-rendered or silently-empty figure.
    """
    missing = {name: str(p) for name, p in paths.items() if not Path(p).exists()}
    if missing:
        raise MissingInput(
            "required committed input(s) absent — refusing to render: "
            + ", ".join(f"{n}={p}" for n, p in missing.items())
        )


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit_hash() -> str:
    """Best-effort short HEAD hash; '' if git is unavailable — never faked."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True, cwd=_ROOT,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def build_provenance(
    inputs: Mapping[str, Path], params: Mapping[str, object] | None = None,
) -> dict:
    """Provenance record: per-input SHA-256, commit hash, UTC timestamp."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit_hash": git_commit_hash(),
        "inputs": {
            name: {"path": str(Path(p).relative_to(_ROOT)) if _is_under_root(p)
                   else str(p),
                   "sha256": sha256_file(p)}
            for name, p in inputs.items()
        },
        "params": dict(params or {}),
    }


def _is_under_root(p: str | Path) -> bool:
    try:
        Path(p).resolve().relative_to(_ROOT)
        return True
    except ValueError:
        return False


def write_sidecar(artifact_path: str | Path, provenance: dict) -> Path:
    """Write ``<artifact>.provenance.json`` next to a generated artifact."""
    artifact_path = Path(artifact_path)
    side = artifact_path.with_suffix(artifact_path.suffix + ".provenance.json")
    side.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return side


# ── Colourblind-safe evidence-class palette (Okabe-Ito subset) ──────────────
# Validated with the dataviz skill's palette validator (CVD ΔE ≥ 13, normal-
# vision ΔE 15.6 — all PASS). Colour is never the sole channel: every box also
# carries its class name as text.
EVIDENCE_COLORS: dict[str, str] = {
    "real": "#0072B2",        # satellite / official cartography
    "calibrated": "#E69F00",  # expert-calibrated reconstruction
    "simulated": "#D55E00",   # scenario / α-decay simulation
    "synthetic": "#CC79A7",   # demo fixtures
    "constant": "#7A7A7A",    # expert-set parameter (neutral; not a data class)
}

# Sequential colormap for magnitude (EHS stress). cividis is perceptually
# uniform and CVD-safe by construction — do not swap for a rainbow.
SEQUENTIAL_CMAP = "cividis"
