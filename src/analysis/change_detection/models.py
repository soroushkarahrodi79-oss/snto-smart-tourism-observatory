"""
SNTO — Change-detection typed models (ADR-015)
==============================================

Frozen, framework-free dataclasses for the Visual Change Explorer analysis core.
No Earth Engine import, no network, no service-result model (that belongs to the
future orchestration layer, deliberately out of scope here).

Key safety rules for models that *hold* live EE objects (``CompositeProduct``):

* equality is **identity-based** (``eq=False``) so Python never invokes an EE
  image's overloaded ``==`` (which would build a server-side comparison image,
  not a bool);
* the EE image is excluded from ``repr`` (it is not JSON, and its repr is noise);
* :meth:`CompositeProduct.to_dict` serialises **metadata only** — never the live
  image — so nothing tries to JSON-encode an EE object;
* ``__post_init__`` does no network / no ``getInfo``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

# ── Date window ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DateWindow:
    """An immutable, timezone-free acquisition window.

    ``start`` / ``end`` are :class:`datetime.date` (never :class:`datetime`, to
    stay timezone-free). ``end_inclusive`` reflects the *user-facing* convention:
    by default the window includes ``end`` (so a same-day window ``[d, d]`` is one
    valid day). Earth Engine's ``filterDate`` is **end-exclusive**, so the
    inclusive→exclusive conversion happens **here, in exactly one place**
    (:meth:`ee_end_date`); no other module does date arithmetic, and nothing here
    reads the current date.

    Validation rejects reversed and empty windows: the *effective* EE-exclusive
    window must be non-empty (``start < exclusive_end``).
    """

    start: date
    end: date
    end_inclusive: bool = True

    def __post_init__(self) -> None:
        # datetime is a subclass of date; reject it to stay timezone-free.
        if isinstance(self.start, datetime) or isinstance(self.end, datetime):
            raise TypeError("DateWindow requires datetime.date, not datetime.")
        if not isinstance(self.start, date) or not isinstance(self.end, date):
            raise TypeError("DateWindow start/end must be datetime.date instances.")
        if self.start >= self._exclusive_end():
            raise ValueError(
                "empty or reversed date window: "
                f"start={self.start.isoformat()} end={self.end.isoformat()} "
                f"(end_inclusive={self.end_inclusive})"
            )

    def _exclusive_end(self) -> date:
        return self.end + timedelta(days=1) if self.end_inclusive else self.end

    def ee_start_date(self) -> str:
        """Inclusive start as an ISO ``YYYY-MM-DD`` string for ``filterDate``."""
        return self.start.isoformat()

    def ee_end_date(self) -> str:
        """EE-**exclusive** end as an ISO ``YYYY-MM-DD`` string for ``filterDate``.

        For an inclusive user window this is ``end + 1 day``; for an exclusive
        window it is ``end`` unchanged. This is the single inclusive→exclusive
        conversion point.
        """
        return self._exclusive_end().isoformat()

    @property
    def duration_days(self) -> int:
        """Number of days the window covers (>= 1)."""
        return (self._exclusive_end() - self.start).days

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "end_inclusive": self.end_inclusive,
            "ee_start": self.ee_start_date(),
            "ee_end_exclusive": self.ee_end_date(),
            "duration_days": self.duration_days,
        }


# ── Composite products ────────────────────────────────────────────────────────

class CompositeKind(str, Enum):
    TRUE_COLOUR = "true_colour"
    NDVI = "ndvi"
    DNDVI = "dndvi"


class WindowRole(str, Enum):
    BEFORE = "before"
    AFTER = "after"
    DIFFERENCE = "difference"


@dataclass(frozen=True, eq=False)
class CompositeProduct:
    """An **analytical** EE image plus its descriptor.

    ``image`` is the unrendered EE object (median reflectance / NDVI / dNDVI) — it
    is NOT an 8-bit visualised image and NOT a thumbnail URL. Rendering to a PNG
    URL is a separate step (``earth_engine.render.get_thumbnail_url``) that
    produces a plain ``str``; keeping the two apart is deliberate.
    """

    kind: CompositeKind
    role: WindowRole
    band_names: tuple[str, ...]
    image: Any = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Metadata-only serialisation — never touches the live EE image."""
        return {
            "kind": self.kind.value,
            "role": self.role.value,
            "band_names": list(self.band_names),
        }


# ── Quality metadata ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class QualityMetadata:
    """Per-window quality summary. Fully JSON-serialisable (holds no EE object).

    Two distinct cloud measures are kept **separate** on purpose:

    * ``requested_max_cloud_pct`` / ``mean_scene_cloud_pct`` come from
      ``CLOUDY_PIXEL_PERCENTAGE`` — whole-**scene** metadata;
    * ``valid_pixel_fraction`` is the SCL-derived valid-pixel coverage **within
      the AOI** for the composite — a per-pixel measure.

    Numeric fields are ``None`` until the service evaluates the EE expressions;
    :func:`~src.analysis.change_detection.quality.evaluate_quality` fills them.
    """

    dataset_id: str
    composite_method: str
    window: DateWindow
    requested_max_cloud_pct: float
    scene_count: int | None
    valid_pixel_count: int | None
    aoi_pixel_count: int | None
    valid_pixel_fraction: float | None
    mean_scene_cloud_pct: float | None
    min_valid_pixel_fraction: float
    warnings: tuple[str, ...] = ()

    @property
    def has_scenes(self) -> bool:
        return bool(self.scene_count)

    @property
    def adequate_coverage(self) -> bool:
        frac = self.valid_pixel_fraction
        return frac is not None and frac >= self.min_valid_pixel_fraction

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "composite_method": self.composite_method,
            "window": self.window.to_dict(),
            "requested_max_cloud_pct": self.requested_max_cloud_pct,
            "scene_count": self.scene_count,
            "valid_pixel_count": self.valid_pixel_count,
            "aoi_pixel_count": self.aoi_pixel_count,
            "valid_pixel_fraction": self.valid_pixel_fraction,
            "mean_scene_cloud_pct": self.mean_scene_cloud_pct,
            "min_valid_pixel_fraction": self.min_valid_pixel_fraction,
            "has_scenes": self.has_scenes,
            "adequate_coverage": self.adequate_coverage,
            "warnings": list(self.warnings),
        }
