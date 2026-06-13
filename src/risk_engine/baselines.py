"""
SNTO — Stratified Spectral Baselines (F4)
=========================================
The operational EHS anchors each trail to scene-level percentiles (P90 healthy
reference / P10 degraded floor) computed over *all* background vegetation
pixels of the image (``calculate_delta_ehs._compute_scene_baselines``). That is
robust to radiometric drift between scenes, but it has a known weakness the
audit flagged: if a drought depresses the whole landscape, the "healthy" P90 is
depressed too, so a regionally stressed trail can still look fine relative to
its equally-stressed surroundings.

The fix is to compare each trail against what is healthy *for its own stratum*
(habitat / altitude band / aspect / lithology) rather than against the whole
scene. This module computes per-stratum baselines from labelled pixels, with an
explicit, defensible fallback: a stratum with too few valid pixels borrows the
pooled (scene-level) baseline rather than producing an unstable percentile.

It is data-source agnostic: callers supply ``(value, stratum_label)`` pairs.
Today the only per-trail categorical readily available is the PRUG zone (PNSG);
altitude / aspect / slope stratification additionally requires a DEM, and a
habitat stratifier requires the Natura 2000 / vegetation layer rasterised to the
scene grid (see ``docs/baselines_uncertainty_design.md``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

# Matches the >=100 valid-pixel guard in calculate_delta_ehs._compute_scene_baselines.
DEFAULT_MIN_PIXELS = 100


@dataclass(frozen=True)
class Baseline:
    """Healthy reference (p_base) and degraded floor (p_floor) for one stratum."""
    stratum: str
    p_base: float
    p_floor: float
    n: int
    fell_back: bool  # True when the pooled baseline was substituted


@dataclass(frozen=True)
class StratifiedBaselineSet:
    """Per-stratum baselines plus the pooled (scene-level) baseline."""
    pooled: Baseline
    by_stratum: dict[str, Baseline]
    p_base_pct: int
    p_floor_pct: int
    min_pixels: int

    def for_stratum(self, stratum: Optional[str]) -> Baseline:
        """Return the stratum's baseline, or the pooled one when unavailable.

        Unknown / None strata fall back to pooled — the same conservative
        behaviour as a stratum with insufficient pixels.
        """
        if stratum is not None and stratum in self.by_stratum:
            return self.by_stratum[stratum]
        return self.pooled

    def n_fell_back(self) -> int:
        return sum(1 for b in self.by_stratum.values() if b.fell_back)


def _percentiles(
    values: np.ndarray, p_base_pct: int, p_floor_pct: int
) -> tuple[float, float]:
    return (
        float(np.percentile(values, p_base_pct)),
        float(np.percentile(values, p_floor_pct)),
    )


def compute_stratified_baselines(
    values: Sequence[float],
    strata: Sequence[Optional[str]],
    p_base_pct: int = 90,
    p_floor_pct: int = 10,
    min_pixels: int = DEFAULT_MIN_PIXELS,
) -> StratifiedBaselineSet:
    """Compute pooled + per-stratum P_base / P_floor baselines.

    Args:
        values: spectral index values (e.g. NDVI) of background pixels.
        strata: stratum label per value (same length); None means "unlabelled".
        p_base_pct: healthy-reference percentile (default 90).
        p_floor_pct: degraded-floor percentile (default 10).
        min_pixels: a stratum with fewer valid values borrows the pooled
            baseline (``fell_back=True``) instead of an unstable percentile.

    Returns:
        StratifiedBaselineSet. ``pooled`` is always computed from all finite
        values; ``by_stratum`` has one entry per distinct non-None label seen.

    Raises:
        ValueError if there are fewer than ``min_pixels`` finite values overall
        (mirrors the scene-baseline guard — the raster does not cover the AOI).
    """
    if len(values) != len(strata):
        raise ValueError("values and strata must have equal length")

    arr = np.asarray(values, dtype=np.float64)
    lab = np.asarray(strata, dtype=object)
    finite = np.isfinite(arr)
    arr, lab = arr[finite], lab[finite]

    if arr.size < min_pixels:
        raise ValueError(
            f"only {arr.size} finite values (< {min_pixels}); baseline pool "
            f"insufficient — does the raster cover the study area?"
        )

    pb, pf = _percentiles(arr, p_base_pct, p_floor_pct)
    pooled = Baseline("__pooled__", pb, pf, int(arr.size), fell_back=False)

    by_stratum: dict[str, Baseline] = {}
    for label in {x for x in lab.tolist() if x is not None}:
        sub = arr[lab == label]
        if sub.size < min_pixels:
            by_stratum[str(label)] = Baseline(
                str(label), pooled.p_base, pooled.p_floor, int(sub.size),
                fell_back=True,
            )
        else:
            spb, spf = _percentiles(sub, p_base_pct, p_floor_pct)
            by_stratum[str(label)] = Baseline(
                str(label), spb, spf, int(sub.size), fell_back=False,
            )

    return StratifiedBaselineSet(
        pooled=pooled,
        by_stratum=by_stratum,
        p_base_pct=p_base_pct,
        p_floor_pct=p_floor_pct,
        min_pixels=min_pixels,
    )
