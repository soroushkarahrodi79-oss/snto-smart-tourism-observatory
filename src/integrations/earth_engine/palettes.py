"""
SNTO — Visualisation parameters for the Visual Change Explorer (ADR-015)
=======================================================================

Centralised, documented display settings so rendering parameters live in exactly
one place (never scattered through analysis or UI code). Each :class:`Visualization`
converts to the dict Earth Engine's ``getThumbURL`` expects via
:meth:`Visualization.to_ee_params`.

Colours encode *direction/magnitude of change only* — they are a visual aid and
imply **no** scientific severity category.

Alignment note: the same fixed ``min``/``max`` per product is applied to both the
before and after images (they share one ``Visualization``), so like-for-like
panels are **not** independently auto-stretched.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.integrations.earth_engine.collections import (
    BAND_BLUE,
    BAND_GREEN,
    BAND_RED,
    DNDVI_BAND,
    NDVI_BAND,
)


@dataclass(frozen=True)
class Visualization:
    """A documented set of EE visualisation parameters."""

    bands: tuple[str, ...]
    min: float
    max: float
    palette: tuple[str, ...] | None = None
    legend: str = ""

    def to_ee_params(self) -> dict[str, Any]:
        """Return the ``getThumbURL`` visualisation dict (bands/min/max[/palette])."""
        params: dict[str, Any] = {
            "bands": list(self.bands),
            "min": self.min,
            "max": self.max,
        }
        if self.palette is not None:
            params["palette"] = list(self.palette)
        return params


# ── True colour ───────────────────────────────────────────────────────────────
# Sentinel-2 SR is stored as DN = reflectance × 10 000. A 0–3000 DN stretch
# (≈ 0.00–0.30 reflectance) is the conventional true-colour range for vegetated
# scenes; it keeps forests/soil legible without blowing out bright surfaces.
TRUE_COLOUR = Visualization(
    bands=(BAND_RED, BAND_GREEN, BAND_BLUE),
    min=0.0,
    max=3000.0,
    legend="Sentinel-2 SR true colour (DN 0–3000 ≈ reflectance 0.00–0.30).",
)

# ── NDVI ──────────────────────────────────────────────────────────────────────
# Fixed 0.0–0.9 range with a brown→green ramp: bare/soil low, dense canopy high.
NDVI = Visualization(
    bands=(NDVI_BAND,),
    min=0.0,
    max=0.9,
    palette=(
        "#a50026",  # ~0.0  bare / stressed
        "#d73027",
        "#fdae61",
        "#fee08b",
        "#d9ef8b",
        "#66bd63",
        "#1a9850",  # ~0.9  dense healthy canopy
    ),
    legend="NDVI 0.0 (bare/stressed) → 0.9 (dense healthy vegetation).",
)

# ── dNDVI (difference) ────────────────────────────────────────────────────────
# Diverging, symmetric ±0.4 range: red = NDVI decrease, near-white ≈ no change,
# green = NDVI increase. Symmetry keeps zero visually neutral. Display only —
# no severity thresholds are implied.
DNDVI = Visualization(
    bands=(DNDVI_BAND,),
    min=-0.4,
    max=0.4,
    palette=(
        "#b2182b",  # strong decrease
        "#ef8a62",
        "#f7f7f7",  # ~0  no change (neutral)
        "#67a9cf",
        "#2166ac",  # strong increase
    ),
    legend=(
        "dNDVI −0.4 (NDVI decrease) → 0 (no change) → +0.4 (NDVI increase); "
        "diverging, display only, no severity categories."
    ),
)
