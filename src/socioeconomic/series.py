"""
Socioeconomic SVI time-series (v2.2).

The socioeconomic layer ships a single dated snapshot (2026-06), so the SVI is a
still frame: it says *how vulnerable* each municipality is, not *which way it is
moving*. This module assembles an SVI **series** across dated snapshots and
derives a per-municipality trend — so a shrinking, ageing, tourism-dependent
municipality reads differently from a stabilising one.

Honest by construction (same pattern as mobility/SCM):
  * additional periods are produced by re-running ``etl_socioeconomic.py`` at a
    new date into ``snapshot/history/municipalities_<YYYY-MM>.json`` — owner
    work, not bundled;
  * with a single snapshot the trend is reported as ``insufficient_history``,
    never a fabricated slope;
  * the SVI itself stays ``CALIBRATED`` (real INE/ALMUDENA figures, normalised),
    and so does its trend — this is not a satellite observation.

The trend uses the **socioeconomic-only** SVI (DEP tourism-dependence + DEM
demographic-fragility, ``asset_risk=None``): the environmental-exposure term
(EXP) already has its own satellite time-series, so mixing it in here would
double-count and blur provenance.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from src.socioeconomic.indicators import compute_svi
from src.socioeconomic.loader import (
    SNAPSHOT_PATH,
    SocioeconomicSnapshot,
    load_municipalities,
)
from src.socioeconomic.models import Municipality
from src.time_series.mann_kendall import pairwise_slopes

_HISTORY_DIR = SNAPSHOT_PATH.parent / "history"

# Slopes (SVI points per snapshot period) within ±this are read as "stable".
_STABLE_BAND = 0.5

STATUS_INSUFFICIENT = "insufficient_history"
DIR_RISING = "rising"       # vulnerability increasing
DIR_FALLING = "falling"     # vulnerability decreasing
DIR_STABLE = "stable"


@dataclass(frozen=True)
class SVITrend:
    """Per-municipality SVI trajectory across dated snapshots."""

    ine_code: str
    name: str
    periods: list[str]              # snapshot dates, chronological
    svi_series: list[float]         # socioeconomic-only SVI per period
    slope_per_period: float | None  # Sen's slope; None when < 2 points
    direction: str
    n_points: int
    status: str                     # "" when ok, "insufficient_history" otherwise
    data_status: str = "calibrated"

    def to_dict(self) -> dict[str, object]:
        return {
            "ine_code": self.ine_code,
            "name": self.name,
            "periods": self.periods,
            "svi_series": self.svi_series,
            "slope_per_period": self.slope_per_period,
            "direction": self.direction,
            "n_points": self.n_points,
            "status": self.status,
            "data_status": self.data_status,
        }


@dataclass(frozen=True)
class _DatedSnapshot:
    date: str
    snapshot: SocioeconomicSnapshot


def _snapshot_date(snap: SocioeconomicSnapshot, fallback: str) -> str:
    return snap.source_snapshot_date or fallback


@lru_cache(maxsize=1)
def load_snapshot_history() -> list[_DatedSnapshot]:
    """All dated socioeconomic snapshots, chronological.

    Always includes the current shipped snapshot; adds any dated files under
    ``snapshot/history/``. Sorted by date so the series is chronological.
    """
    dated: list[_DatedSnapshot] = []

    current = load_municipalities()
    dated.append(_DatedSnapshot(_snapshot_date(current, "current"), current))

    if _HISTORY_DIR.exists():
        for path in sorted(_HISTORY_DIR.glob("municipalities_*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            munis = {
                code: Municipality.from_dict(d)
                for code, d in data.get("municipalities", {}).items()
            }
            snap = SocioeconomicSnapshot(
                schema_version=data.get("schema_version", ""),
                source_snapshot_date=data.get("source_snapshot_date", path.stem[-7:]),
                n_municipalities=data.get("n_municipalities", len(munis)),
                n_full=data.get("n_full", 0),
                n_demographic_only=data.get("n_demographic_only", 0),
                sources=data.get("sources", {}),
                municipalities=munis,
            )
            dated.append(_DatedSnapshot(snap.source_snapshot_date, snap))

    # De-duplicate by date (a history file matching the current date wins once)
    # and sort chronologically.
    by_date: dict[str, _DatedSnapshot] = {}
    for d in dated:
        by_date[d.date] = d
    return [by_date[k] for k in sorted(by_date)]


def svi_history_available() -> bool:
    """True once at least two dated snapshots exist (a trend is computable)."""
    return len(load_snapshot_history()) >= 2


def _direction(slope: float) -> str:
    if slope > _STABLE_BAND:
        return DIR_RISING
    if slope < -_STABLE_BAND:
        return DIR_FALLING
    return DIR_STABLE


def compute_svi_trends(
    history: list[_DatedSnapshot] | None = None,
) -> dict[str, SVITrend]:
    """SVI trend per municipality across the dated snapshots.

    With a single snapshot every municipality is returned with
    ``status="insufficient_history"`` and ``slope_per_period=None`` — the state
    is real, the trend simply is not yet computable.
    """
    hist = history if history is not None else load_snapshot_history()

    # Socioeconomic-only SVI (asset_risk=None → EXP omitted) per period.
    per_period: list[tuple[str, dict[str, float]]] = []
    names: dict[str, str] = {}
    for dated in hist:
        svis = compute_svi(dated.snapshot, asset_risk=None)
        per_period.append((dated.date, {c: r.svi for c, r in svis.items()}))
        for code, r in svis.items():
            names[code] = r.name

    all_codes = sorted({c for _, d in per_period for c in d})
    n_periods = len(per_period)

    out: dict[str, SVITrend] = {}
    for code in all_codes:
        periods = [date for date, d in per_period if code in d]
        series = [d[code] for _, d in per_period if code in d]

        if len(series) < 2:
            out[code] = SVITrend(
                ine_code=code, name=names.get(code, ""),
                periods=periods, svi_series=series,
                slope_per_period=None, direction=DIR_STABLE,
                n_points=len(series), status=STATUS_INSUFFICIENT,
            )
            continue

        slopes = pairwise_slopes(series)
        slope = _median(slopes) if slopes else 0.0
        out[code] = SVITrend(
            ine_code=code, name=names.get(code, ""),
            periods=periods, svi_series=[round(v, 1) for v in series],
            slope_per_period=round(slope, 3),
            direction=_direction(slope),
            n_points=len(series), status="",
        )

    _ = n_periods  # kept for readability; series length is the authority
    return out


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else 0.5 * (s[mid - 1] + s[mid])


__all__ = [
    "SVITrend",
    "compute_svi_trends",
    "load_snapshot_history",
    "svi_history_available",
]
