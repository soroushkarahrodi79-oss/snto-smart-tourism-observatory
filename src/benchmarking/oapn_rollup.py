"""OAPN network rollup / cross-park benchmarking (v3.0, roadmap action A15).

WHY
===
The multi-park replicability pilot (v1.2.0) produced **real** Sentinel-2 trend
series for three parks — PNSG (the active pilot) plus two OAPN trend pilots,
Tablas de Daimiel and Monfragüe. Thirteen more OAPN parks have GEE templates
prepared (`scripts/gee_templates_oapn/`) but their series are **not yet
validated** (pending per-biome SCL mask QA — see
`src.platform.territory_registry`). A network-level comparison is one of the
things the roadmap's v3.0 milestone names (A15, `plan_v3_roadmap.md`).

This module builds that comparison **honestly**: it rolls up only the parks
`src.platform.satellite_trends.available_parks()` resolves — i.e. parks with a
real, committed Mann-Kendall trend JSON on disk. It never folds the 13
unvalidated templates into a numeric claim (that would fabricate a network-wide
signal the evidence doesn't support, ADR-004); it only reports their *count*,
as explicit pending context.

Pure logic, no Streamlit — testable against the real committed trend fixtures
under `clean_assets/timeseries/analysis/` (the repo's existing convention for
`satellite_trends`-backed tests).
"""
from __future__ import annotations

from dataclasses import dataclass

from src.platform.satellite_trends import (
    available_parks,
    park_label,
    summarize_trends,
)
from src.platform.territory_registry import ValidationState, territory_profiles

# satellite_trends park keys (mirroring scripts/gee_templates_oapn/*.js) differ
# from the shorter territory_registry slugs for the two OAPN trend pilots —
# mapped explicitly rather than derived, so a future rename on either side
# fails loudly (a missing key) instead of silently mis-joining two parks.
_REGISTRY_SLUG_BY_TREND_PARK: dict[str, str] = {
    "pnsg": "pnsg",
    "pn_monfrague": "monfrague",
    "pn_tablas_daimiel": "tablas_daimiel",
}


@dataclass(frozen=True)
class ParkBenchmark:
    """One park's real-trend roll-up, as it enters the network comparison."""

    trend_park_key: str          # satellite_trends slug, e.g. "pn_monfrague"
    registry_slug: str | None    # territory_registry slug, or None if unmapped
    label: str
    validation_state: ValidationState | None
    n_assets: int
    n_degrading: int
    n_improving: int
    n_stable: int
    pct_degrading: float
    worst_year_global: str | None


@dataclass(frozen=True)
class OAPNRollup:
    """Network-level comparison across parks with REAL satellite trend data.

    ``n_parks_pending_validation`` is context, never folded into the totals:
    it counts templates that exist but are not yet on ``available_parks()``.
    """

    parks: list[ParkBenchmark]
    total_assets: int
    total_degrading: int
    n_parks_included: int
    n_parks_pending_validation: int


def build_rollup() -> OAPNRollup:
    """Cross-park benchmark over every park with real, committed trend data."""
    registry_by_slug = {p.slug: p for p in territory_profiles()}

    rows: list[ParkBenchmark] = []
    for trend_key in available_parks():
        summary = summarize_trends(park=trend_key)
        if not summary.available:
            continue
        registry_slug = _REGISTRY_SLUG_BY_TREND_PARK.get(trend_key)
        profile = registry_by_slug.get(registry_slug) if registry_slug else None
        n = len(summary.assets)
        rows.append(
            ParkBenchmark(
                trend_park_key=trend_key,
                registry_slug=registry_slug,
                label=park_label(trend_key),
                validation_state=profile.state if profile else None,
                n_assets=n,
                n_degrading=summary.n_degrading,
                n_improving=summary.n_improving,
                n_stable=summary.n_stable,
                pct_degrading=round(100.0 * summary.n_degrading / n, 1) if n else 0.0,
                worst_year_global=summary.worst_year_global,
            )
        )
    rows.sort(key=lambda r: r.pct_degrading, reverse=True)

    n_pending = sum(
        1
        for p in registry_by_slug.values()
        if p.state is ValidationState.TEMPLATE_UNVALIDATED
    )

    return OAPNRollup(
        parks=rows,
        total_assets=sum(r.n_assets for r in rows),
        total_degrading=sum(r.n_degrading for r in rows),
        n_parks_included=len(rows),
        n_parks_pending_validation=n_pending,
    )
