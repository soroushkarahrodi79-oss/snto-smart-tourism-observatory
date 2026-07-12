"""
SNTO — Field-observation CSV I/O (F5 / issue #26)
=================================================
The field team records ground-truth on a spreadsheet, not in Python. This
module reads/writes the field-observation record in a plain CSV whose columns
mirror ``FieldObservation`` (``docs/field_validation_protocol.md`` §1), so a
campaign can be filled in the field and ingested here without a database.

Empty cells become ``None`` (honest missing data — never coerced to 0). The
writer emits a header-only template plus any seed rows, so the priority assets
can be pre-listed with their coordinates while the measurement columns stay
blank until the field visit.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from src.validation.field import FieldObservation

# CSV column order — mirrors FieldObservation. Kept explicit so the template and
# the loader never drift apart.
FIELDNAMES = [
    "plot_id", "asset_id", "lat", "lon", "distance_to_trail_m", "is_control",
    "soil_compaction_mpa", "veg_cover_pct", "erosion_class", "trail_width_m",
    "visitor_count", "photo_ref", "stratum", "observed_at",
]

_FLOAT_COLS = {
    "lat", "lon", "distance_to_trail_m", "soil_compaction_mpa",
    "veg_cover_pct", "trail_width_m",
}
_INT_COLS = {"erosion_class", "visitor_count"}


def _num(value: str, cast) -> Optional[float]:
    value = (value or "").strip()
    if value == "":
        return None
    return cast(value)


def _bool(value: str) -> bool:
    return (value or "").strip().lower() in {"1", "true", "sí", "si", "yes", "x"}


def load_field_observations(path: str | Path) -> list[FieldObservation]:
    """Read a field-observation CSV into ``FieldObservation`` records.

    Blank measurement cells load as ``None``. Rows whose ``plot_id`` is empty or
    starts with ``#`` (comment / example rows) are skipped.
    """
    out: list[FieldObservation] = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            plot_id = (row.get("plot_id") or "").strip()
            if not plot_id or plot_id.startswith("#"):
                continue
            out.append(FieldObservation(
                plot_id=plot_id,
                asset_id=(row.get("asset_id") or "").strip() or None,
                lat=float(_num(row.get("lat", ""), float) or 0.0),
                lon=float(_num(row.get("lon", ""), float) or 0.0),
                distance_to_trail_m=float(
                    _num(row.get("distance_to_trail_m", ""), float) or 0.0
                ),
                is_control=_bool(row.get("is_control", "")),
                soil_compaction_mpa=_num(row.get("soil_compaction_mpa", ""), float),
                veg_cover_pct=_num(row.get("veg_cover_pct", ""), float),
                erosion_class=_num(row.get("erosion_class", ""), int),
                trail_width_m=_num(row.get("trail_width_m", ""), float),
                visitor_count=_num(row.get("visitor_count", ""), int),
                photo_ref=(row.get("photo_ref") or "").strip() or None,
                stratum=(row.get("stratum") or "").strip() or None,
                observed_at=(row.get("observed_at") or "").strip() or None,
            ))
    return out


def write_template(path: str | Path, seed_rows: list[dict]) -> Path:
    """Write a header + seed rows CSV template (measurement columns blank)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in seed_rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})
    return path
