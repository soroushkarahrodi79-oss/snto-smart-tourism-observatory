"""
SNTO — Field observation schema (F5)
====================================
Structures for capturing ground-truth observations that validate the satellite
signal, per the protocol in ``docs/field_validation_protocol.md``. The audit's
strongest single improvement was: *demonstrate that the satellite EHS correlates
with degradation observed on the ground.* This module defines the data the field
campaign collects and a transparent composite **field degradation index** so it
can be correlated against the satellite stress score.

Convention: ``degradation_index`` follows the STRESS direction (0 = pristine,
100 = maximally degraded), matching ``src.metrics.semantics`` stress scores, so
a positive correlation with satellite stress is the expected validation result.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

# Penetrometer reading at/above which surface soil is treated as fully compacted.
# ~2-3 MPa is the range that restricts root penetration in montane soils.
SOIL_COMPACTION_MAX_MPA = 3.0


class ErosionClass(IntEnum):
    """Visual erosion severity (field-scored)."""
    NONE = 0
    LIGHT = 1
    MODERATE = 2
    SEVERE = 3


@dataclass(frozen=True)
class FieldObservation:
    """One georeferenced ground-truth plot.

    ``is_control=True`` marks a plot far from the trail in the same habitat — the
    reference against which trail-corridor (impact) plots are contrasted (BACI).
    Quality fields are optional; ``degradation_index`` uses whatever is present.
    """
    plot_id: str
    lat: float
    lon: float
    distance_to_trail_m: float
    is_control: bool
    asset_id: Optional[str] = None                 # SNTO asset this plot belongs to
    soil_compaction_mpa: Optional[float] = None   # penetrometer
    veg_cover_pct: Optional[float] = None          # 0-100
    erosion_class: Optional[int] = None            # ErosionClass 0-3
    trail_width_m: Optional[float] = None
    visitor_count: Optional[int] = None
    photo_ref: Optional[str] = None
    stratum: Optional[str] = None                  # habitat / altitude band
    observed_at: Optional[str] = None              # ISO date

    def degradation_index(self) -> Optional[float]:
        """Composite field degradation 0-100 (stress convention), or None.

        Combines the available components with equal weight:
          * soil compaction normalised by SOIL_COMPACTION_MAX_MPA,
          * vegetation cover deficit (100 - cover),
          * erosion class scaled to 0-100.
        Returns None when no component is present.
        """
        components: list[float] = []
        if self.soil_compaction_mpa is not None:
            ratio = self.soil_compaction_mpa / SOIL_COMPACTION_MAX_MPA
            components.append(min(1.0, max(0.0, ratio)) * 100.0)
        if self.veg_cover_pct is not None:
            components.append(max(0.0, min(100.0, 100.0 - self.veg_cover_pct)))
        if self.erosion_class is not None:
            components.append(max(0, min(3, int(self.erosion_class))) / 3.0 * 100.0)
        if not components:
            return None
        return round(sum(components) / len(components), 2)


def split_impact_control(
    observations: list[FieldObservation],
) -> tuple[list[FieldObservation], list[FieldObservation]]:
    """Partition observations into (impact, control) by the ``is_control`` flag."""
    impact = [o for o in observations if not o.is_control]
    control = [o for o in observations if o.is_control]
    return impact, control


def field_index_by_asset(
    observations: list[FieldObservation],
) -> dict[str, Optional[float]]:
    """Per-asset field degradation index (mean over that asset's impact plots).

    Only impact plots (``is_control=False``) with a computable
    ``degradation_index`` and a non-null ``asset_id`` contribute. An asset whose
    impact plots have no measured components maps to ``None`` — the caller must
    treat that as "no field datum", never as zero degradation.
    """
    sums: dict[str, list[float]] = {}
    for o in observations:
        if o.is_control or o.asset_id is None:
            continue
        idx = o.degradation_index()
        if idx is None:
            continue
        sums.setdefault(o.asset_id, []).append(idx)
    return {aid: round(sum(v) / len(v), 2) if v else None
            for aid, v in sums.items()}
