"""
SNTO — Satellite acquisition manifest for Paper 1 field validation (Phase 4 / B-06)
=====================================================================================
Governs which Sentinel-2 imagery Paper 1's field observations are compared
against, per ``docs/paper1/SATELLITE_FIELD_MATCHING_PLAN.md``. The manifest is
committed *before* extraction, so a third party can regenerate the exact
composite from its scene IDs — this is the Paper-1 provenance record, and it
does not depend on ``src/platform/provenance.py``'s directory scan, which
reads rasters that are git-ignored and absent on a clean checkout.

The manifest also encodes the SCL masking asymmetry the matching plan
requires: bare/rock pixels (SCL class 5) are excluded from the scene-level
healthy baseline but *retained* at plot extraction, where they are real
degradation signal rather than sensor noise. Collapsing these to one
exclusion list would silently erase that distinction — ``validate_manifest``
checks for exactly that mistake.

Never fabricates: a manifest with no fixed acquisition window has
``window_start``/``window_end`` = ``None`` and ``scene_ids`` = ``()``, and
that is the *only* valid state for ``ManifestStatus.PLANNED``. Advancing past
PLANNED without a real window or real scene IDs is a validation error, not a
silently accepted default.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence


class ManifestStatus(str, Enum):
    """Lifecycle of one acquisition manifest. Stages are never skipped."""
    PLANNED = "planned"                          # schema fixed, no window yet
    WINDOW_DEFINED = "window_defined"             # window fixed, scenes not queried
    SCENES_IDENTIFIED = "scenes_identified"       # real scene IDs recorded
    COMPOSITE_GENERATED = "composite_generated"   # composite raster produced
    CHECKED = "checked"                           # verified against an extraction run


# ── Frozen matching-plan constants (SATELLITE_FIELD_MATCHING_PLAN.md §2) ───
# These govern the Paper-1 VALIDATION composite only. They are declared here,
# not read from src/config/constants.py, which governs the OPERATIONAL EHS
# pipeline (calculate_delta_ehs.py) and must stay untouched by this module —
# Paper 1 validates the shipped indicator; it does not fork its constants.
DEFAULT_TILE = "T30TVL"
DEFAULT_CLOUD_THRESHOLD_PCT = 20.0
DEFAULT_MIN_SCENES_IN_COMPOSITE = 3
DEFAULT_COMPOSITE_METHOD = "median"
DEFAULT_MAX_OFFSET_DAYS_PRIMARY = 15
DEFAULT_MAX_OFFSET_DAYS_MAX = 30
DEFAULT_VALID_PIXEL_MIN_PCT = 70.0
DEFAULT_VALID_PIXEL_FLAG_PCT = 90.0

# SCL classes excluded from the scene-level P90/P10 healthy-reference baseline.
# 3=cloud shadow, 5=bare soil/rock, 6=water, 8=cloud medium prob., 9=cloud
# high prob., 10=cirrus, 11=snow. Class 5 is excluded here: including bare
# rock would bias the "healthy" reference upward.
SCL_EXCLUDE_BASELINE: tuple[int, ...] = (3, 5, 6, 8, 9, 10, 11)

# SCL classes excluded at PLOT extraction. Class 5 is deliberately RETAINED
# (removed from the exclusion set) — bare/degraded ground at a trail plot is
# real signal, not sensor noise, per the matching plan's declared asymmetry.
# Do not "simplify" this to match SCL_EXCLUDE_BASELINE.
SCL_EXCLUDE_PLOT_EXTRACTION: tuple[int, ...] = (3, 6, 8, 9, 10, 11)


@dataclass(frozen=True)
class AcquisitionManifest:
    """One Paper-1 satellite acquisition record, from planning through
    verification against an extraction run. All fields are plain JSON-safe
    types so the manifest round-trips through ``write_manifest``/``load_manifest``
    without a schema library."""
    status: ManifestStatus
    tile: str = DEFAULT_TILE
    cloud_threshold_pct: float = DEFAULT_CLOUD_THRESHOLD_PCT
    min_scenes_in_composite: int = DEFAULT_MIN_SCENES_IN_COMPOSITE
    composite_method: str = DEFAULT_COMPOSITE_METHOD
    max_offset_days_primary: int = DEFAULT_MAX_OFFSET_DAYS_PRIMARY
    max_offset_days_max: int = DEFAULT_MAX_OFFSET_DAYS_MAX
    valid_pixel_min_pct: float = DEFAULT_VALID_PIXEL_MIN_PCT
    valid_pixel_flag_pct: float = DEFAULT_VALID_PIXEL_FLAG_PCT
    scl_exclude_baseline: tuple[int, ...] = SCL_EXCLUDE_BASELINE
    scl_exclude_plot_extraction: tuple[int, ...] = SCL_EXCLUDE_PLOT_EXTRACTION
    window_start: Optional[str] = None      # ISO date "YYYY-MM-DD"; None until fixed
    window_end: Optional[str] = None
    scene_ids: tuple[str, ...] = ()         # e.g. "S2B_MSIL2A_20270615T110629_..."
    sensor_mix: tuple[str, ...] = ()        # e.g. ("S2A",) or ("S2A", "S2B")
    generated_at: str = ""
    commit_hash: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


def _current_commit_hash() -> str:
    """Best-effort git HEAD short hash for provenance; "" if unavailable —
    never fabricated as a placeholder-looking-real value."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        return out.stdout.strip()
    except Exception:
        return ""


def new_planned_manifest(notes: str = "") -> AcquisitionManifest:
    """A manifest at the PLANNED stage: frozen matching-plan constants, no
    acquisition window yet. Honest about what has and has not been decided —
    this is the only entry point that does not require a real window/scenes."""
    return AcquisitionManifest(
        status=ManifestStatus.PLANNED,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        commit_hash=_current_commit_hash(),
        notes=notes,
    )


def validate_manifest(m: AcquisitionManifest) -> list[str]:
    """Schema/consistency problems for the manifest at its declared
    ``status``. Empty list = valid for that stage. Never mutates ``m``."""
    errors: list[str] = []

    if m.window_start and m.window_end and m.window_start >= m.window_end:
        errors.append("window_start must be before window_end")

    if m.cloud_threshold_pct < 0 or m.cloud_threshold_pct > 100:
        errors.append("cloud_threshold_pct out of [0, 100]")
    if m.valid_pixel_min_pct < 0 or m.valid_pixel_min_pct > 100:
        errors.append("valid_pixel_min_pct out of [0, 100]")
    if m.valid_pixel_flag_pct < m.valid_pixel_min_pct:
        errors.append("valid_pixel_flag_pct must be >= valid_pixel_min_pct")
    if m.max_offset_days_max < m.max_offset_days_primary:
        errors.append("max_offset_days_max must be >= max_offset_days_primary")
    if 5 in m.scl_exclude_plot_extraction:
        errors.append(
            "SCL class 5 (bare/rock) must be RETAINED at plot extraction — "
            "see SATELLITE_FIELD_MATCHING_PLAN.md §2 asymmetry"
        )
    if 5 not in m.scl_exclude_baseline:
        errors.append(
            "SCL class 5 (bare/rock) must be excluded from the scene-level "
            "baseline — see SATELLITE_FIELD_MATCHING_PLAN.md §2"
        )

    if m.status is ManifestStatus.PLANNED:
        return errors  # a fixed window/scenes is not required yet — that is the point

    if not (m.window_start and m.window_end):
        errors.append(f"status={m.status.value} requires window_start/window_end")

    if m.status in (ManifestStatus.SCENES_IDENTIFIED,
                    ManifestStatus.COMPOSITE_GENERATED,
                    ManifestStatus.CHECKED):
        if not m.scene_ids:
            errors.append(f"status={m.status.value} requires non-empty scene_ids")
        elif len(m.scene_ids) < m.min_scenes_in_composite:
            errors.append(
                f"only {len(m.scene_ids)} scene_ids, "
                f"min_scenes_in_composite={m.min_scenes_in_composite}"
            )
        if not m.sensor_mix:
            errors.append(f"status={m.status.value} requires sensor_mix")

    return errors


def write_manifest(m: AcquisitionManifest, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(m.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_manifest(path: str | Path) -> AcquisitionManifest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["status"] = ManifestStatus(data["status"])
    data["scene_ids"] = tuple(data.get("scene_ids", ()))
    data["sensor_mix"] = tuple(data.get("sensor_mix", ()))
    data["scl_exclude_baseline"] = tuple(
        data.get("scl_exclude_baseline", SCL_EXCLUDE_BASELINE))
    data["scl_exclude_plot_extraction"] = tuple(
        data.get("scl_exclude_plot_extraction", SCL_EXCLUDE_PLOT_EXTRACTION))
    return AcquisitionManifest(**data)


@dataclass(frozen=True)
class ManifestCheckReport:
    """Result of comparing a manifest's declared scenes to an extraction run."""
    ok: bool
    declared_not_used: tuple[str, ...]
    used_not_declared: tuple[str, ...]

    @property
    def summary(self) -> str:
        if self.ok:
            return "OK — extraction matches the committed manifest exactly."
        parts = []
        if self.declared_not_used:
            parts.append(f"declared but not used: {list(self.declared_not_used)}")
        if self.used_not_declared:
            parts.append(f"used but not declared: {list(self.used_not_declared)}")
        return "MISMATCH — " + "; ".join(parts)


def check_against_extraction(
    m: AcquisitionManifest, extracted_scene_ids: Sequence[str],
) -> ManifestCheckReport:
    """Fails loudly on any disagreement between the committed manifest and
    what an extraction run actually consumed — no silent drift between the
    provenance record and the analysis input (Contract §O, no interpolation
    of evidence extends to no undeclared substitution of scenes either)."""
    declared = set(m.scene_ids)
    used = set(extracted_scene_ids)
    return ManifestCheckReport(
        ok=declared == used,
        declared_not_used=tuple(sorted(declared - used)),
        used_not_declared=tuple(sorted(used - declared)),
    )
