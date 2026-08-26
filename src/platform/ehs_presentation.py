"""
SNTO — Presentation mapping for the canonical EHS condition partition (K-24).

Business logic (the enum, the ordered bands, the classifier) lives in
``src.risk_engine.ehs``. This module holds ONLY presentation concerns —
Spanish labels and colours — derived from that single canonical source, so
no PURE-EHS surface needs to carry its own literal cut-points.

Two axes are kept deliberately distinct (do not collapse them):
  - CONDITION: what state is the asset in? (Spanish label, matches the
    canonical EHSCondition — for the spectral diagnostic legend.)
  - URGENCY:   how urgently does it need investment? (existing five-word
    trail-priority vocabulary + colours, unchanged from pre-K-24 — for
    src.platform.real_trails intervention-priority bands.)

Both derive from the same EHS_CONDITION_BANDS partition; they differ only in
vocabulary/colour, not in boundaries.
"""
from __future__ import annotations

from src.risk_engine.ehs import EHS_CONDITION_BANDS, EHSCondition, classify_ehs_condition

# ── CONDITION — Spanish label + colour, for the spectral diagnostic legend ────
# Colours are the RdYlGn (ColorBrewer 5-class diverging) anchors already used
# across the map layers, now keyed to the canonical bands instead of the old
# 30/45/60/75/85 literals.
CONDITION_LABEL_ES: dict[EHSCondition, str] = {
    EHSCondition.CRITICAL:  "Crítico",
    EHSCondition.POOR:      "Deficiente",
    EHSCondition.MODERATE:  "Moderado",
    EHSCondition.GOOD:      "Bueno",
    EHSCondition.EXCELLENT: "Excelente",
}

CONDITION_COLOR: dict[EHSCondition, str] = {
    EHSCondition.CRITICAL:  "#d73027",
    EHSCondition.POOR:      "#fdae61",
    EHSCondition.MODERATE:  "#ffffbf",
    EHSCondition.GOOD:      "#a6d96a",
    EHSCondition.EXCELLENT: "#1a9850",
}


def condition_legend_items() -> list[tuple[str, str]]:
    """Ordered (hex, label) legend entries, worst → best, from the canonical bands."""
    items: list[tuple[str, str]] = []
    bands = EHS_CONDITION_BANDS
    for i, (low, cond) in enumerate(bands):
        hi = bands[i + 1][0] if i + 1 < len(bands) else None
        label_range = f"< {hi:.0f}" if low == 0.0 and hi is not None else (
            f">= {low:.0f}" if hi is None else f"{low:.0f}-{hi:.0f}"
        )
        items.append((CONDITION_COLOR[cond], f"EHS {label_range} — {CONDITION_LABEL_ES[cond]}"))
    return items


# ── URGENCY — trail-priority vocabulary + colour (src.platform.real_trails) ───
# Historical five-word vocabulary and colours preserved verbatim (only the
# boundaries that assign a health value to a word move, from 0/30/45/60/75 to
# the canonical 0/40/60/75/90).
URGENCY_LABEL_ES: dict[EHSCondition, str] = {
    EHSCondition.CRITICAL:  "Crítica",
    EHSCondition.POOR:      "Alta",
    EHSCondition.MODERATE:  "Media",
    EHSCondition.GOOD:      "Baja",
    EHSCondition.EXCELLENT: "Mínima",
}

URGENCY_COLOR: dict[EHSCondition, str] = {
    EHSCondition.CRITICAL:  "#c62828",
    EHSCondition.POOR:      "#e65100",
    EHSCondition.MODERATE:  "#f9a825",
    EHSCondition.GOOD:      "#558b2f",
    EHSCondition.EXCELLENT: "#2e7d32",
}


def priority_for_health(health: float | None) -> tuple[str, str]:
    """Return (urgency_label_es, hex_color) for a summer-health value, or
    ("Sin dato", grey) when health is unknown."""
    if health is None:
        return ("Sin dato", "#9e9e9e")
    condition = classify_ehs_condition(health)
    return (URGENCY_LABEL_ES[condition], URGENCY_COLOR[condition])


# ── Spectral gradient — continuous colour interpolation, NOT semantic bands ───
# This is a visual ramp for map rendering: colours are interpolated smoothly
# between stops. The stops are anchored on the canonical band boundaries so
# the ramp agrees with the discrete legend, but the ramp itself is not a
# semantic partition — do not add extra stops just to make the gradient look
# better (K-24 Phase C item D).
_SPECTRAL_RAMP_STOPS: list[tuple[float, list[int]]] = [
    (0.0,                      [165,   0,  38]),  # deep red    — critical
    (EHS_CONDITION_BANDS[1][0], [215,  48,  39]),  # red         — poor
    (EHS_CONDITION_BANDS[2][0], [253, 174,  97]),  # orange      — moderate (low end)
    (EHS_CONDITION_BANDS[3][0], [255, 255, 191]),  # pale yellow — good (low end)
    (EHS_CONDITION_BANDS[4][0], [166, 217, 106]),  # yellow-green— excellent (low end)
    (100.0,                    [ 26, 152,  80]),  # deep green  — excellent (top)
]


def ehs_to_rgba(ehs: float | None, alpha: int = 220, none_color: list[int] | None = None) -> list[int]:
    """Interpolate an RGBA colour from the canonical-anchored spectral ramp.

    Shared by src.platform.map_layers (synthetic-geometry spectral view) and
    src.platform.real_trails (real-trace Pipeline A map) so both draw from
    one ramp instead of two independently literal copies.
    """
    if ehs is None:
        return list(none_color) if none_color is not None else [158, 158, 158, alpha]
    e = max(0.0, min(100.0, ehs))
    ramp = _SPECTRAL_RAMP_STOPS
    for i in range(len(ramp) - 1):
        lo_val, lo_rgb = ramp[i]
        hi_val, hi_rgb = ramp[i + 1]
        if lo_val <= e <= hi_val:
            t = (e - lo_val) / (hi_val - lo_val) if hi_val != lo_val else 0.0
            return [
                int(lo_rgb[0] + t * (hi_rgb[0] - lo_rgb[0])),
                int(lo_rgb[1] + t * (hi_rgb[1] - lo_rgb[1])),
                int(lo_rgb[2] + t * (hi_rgb[2] - lo_rgb[2])),
                alpha,
            ]
    return [128, 128, 128, alpha]  # pragma: no cover — unreachable, e is clamped to [0,100]
