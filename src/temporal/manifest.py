"""
SNTO — Temporal Series Provenance Manifest (F2 scaffolding)
===========================================================
A reproducible, auditable record of *which* periods actually populate a series
and *how trustworthy* each one is. The audit asked for every result to carry:
valid pixels, cloud cover, acquisition date, composition method, data source,
and a real/calibrated/synthetic flag. The manifest is where that provenance
lives for the temporal layer; the live dashboard (F3) reads it to label
coverage and confidence honestly.

The manifest is built from a ``SeriesSpec`` (the expected periods) and the
``AssetObservation`` records that ingestion produced. Periods present in the
spec but absent from the observations are recorded as gaps (``present=False``),
so coverage is never silently overstated.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from src.temporal.series_spec import SeriesSpec


class DataStatus(str, Enum):
    """Trust tier of a datum — surfaced verbatim in the dashboard."""
    REAL = "real"              # real satellite observation
    CALIBRATED = "calibrated"  # literature/expert-calibrated reconstruction
    SYNTHETIC = "synthetic"    # mock / demo
    MISSING = "missing"        # period expected but no valid datum


def classify_source(data_source: Optional[str]) -> DataStatus:
    """Map a free-text ``data_source`` string to a DataStatus tier."""
    if not data_source:
        return DataStatus.MISSING
    s = data_source.lower()
    if "mock" in s or "synthetic" in s or "dry-run" in s:
        return DataStatus.SYNTHETIC
    if "calibr" in s:
        return DataStatus.CALIBRATED
    if "gee" in s or "s2" in s or "sentinel" in s or "stac" in s:
        return DataStatus.REAL
    return DataStatus.CALIBRATED


@dataclass(frozen=True)
class PeriodRecord:
    """Provenance for one period of the series."""
    period_key: str
    year: int
    month: Optional[int]
    present: bool
    data_status: DataStatus
    n_valid_pixels: Optional[int] = None
    valid_pixel_pct: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    composition_method: Optional[str] = None
    data_source: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["data_status"] = self.data_status.value
        return d


@dataclass
class SeriesManifest:
    """Coverage + provenance for a territory's series against its spec."""
    territory_key: str
    spec: SeriesSpec
    records: list[PeriodRecord] = field(default_factory=list)

    # ── Coverage ──
    def n_expected(self) -> int:
        return self.spec.n_expected()

    def n_present(self) -> int:
        return sum(1 for r in self.records if r.present)

    def coverage(self) -> float:
        """Fraction of expected periods that carry a valid datum [0, 1]."""
        exp = self.n_expected()
        return round(self.n_present() / exp, 4) if exp else 0.0

    def gaps(self) -> list[str]:
        """Period keys expected by the spec but missing a valid datum."""
        return [r.period_key for r in self.records if not r.present]

    def dominant_status(self) -> DataStatus:
        """Most frequent trust tier among present periods (MISSING if none)."""
        present = [r.data_status for r in self.records if r.present]
        if not present:
            return DataStatus.MISSING
        return max(set(present), key=present.count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "territory_key": self.territory_key,
            "spec": {
                "start_year": self.spec.start_year,
                "end_year": self.spec.end_year,
                "cadence": self.spec.cadence.value,
                "s2_tile": self.spec.s2_tile,
                "indices": list(self.spec.indices),
                "min_valid_pixel_pct": self.spec.min_valid_pixel_pct,
                "collection": self.spec.collection,
            },
            "coverage": {
                "n_expected": self.n_expected(),
                "n_present": self.n_present(),
                "fraction": self.coverage(),
                "dominant_status": self.dominant_status().value,
                "n_gaps": len(self.gaps()),
            },
            "records": [r.to_dict() for r in self.records],
        }

    def write_json(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return p


def build_manifest_from_observations(
    spec: SeriesSpec,
    observations: list[Any],
    composition_method: str = "monthly_median",
) -> SeriesManifest:
    """Build a territory-level coverage manifest from AssetObservation records.

    A period counts as *present* if any observation falls in it (territory-level
    coverage). Per-period quality fields take the best available observation
    (highest valid-pixel fraction), so the manifest reflects the strongest
    evidence the series holds for that period.

    Args:
        spec: the series plan defining expected periods.
        observations: iterable of AssetObservation-like objects exposing
            ``year``, ``month``, ``cloud_cover_pct``, ``data_source`` and an
            optional ``ndvi_stats`` with ``pixel_count`` / ``valid_pixel_pct``.
        composition_method: how each period's composite was built.

    Returns:
        SeriesManifest with one PeriodRecord per expected period.
    """
    # Index best observation per (year, month).
    best: dict[tuple[int, int], Any] = {}
    for o in observations:
        key = (int(o.year), int(o.month))
        prev = best.get(key)
        if prev is None or _valid_pct(o) >= _valid_pct(prev):
            best[key] = o

    records: list[PeriodRecord] = []
    for period in spec.periods():
        obs = (best.get((period.year, period.month))
               if period.month is not None else None)
        if obs is None:
            records.append(PeriodRecord(
                period_key=period.key, year=period.year, month=period.month,
                present=False, data_status=DataStatus.MISSING,
            ))
            continue
        stats = getattr(obs, "ndvi_stats", None)
        records.append(PeriodRecord(
            period_key=period.key,
            year=period.year,
            month=period.month,
            present=True,
            data_status=classify_source(getattr(obs, "data_source", None)),
            n_valid_pixels=getattr(stats, "pixel_count", None) if stats else None,
            valid_pixel_pct=getattr(stats, "valid_pixel_pct", None) if stats else None,
            cloud_cover_pct=getattr(obs, "cloud_cover_pct", None),
            composition_method=composition_method,
            data_source=getattr(obs, "data_source", None),
        ))

    return SeriesManifest(territory_key=spec.territory_key, spec=spec, records=records)


def _valid_pct(obs: Any) -> float:
    """Best-effort valid-pixel fraction for ranking observations of a period."""
    stats = getattr(obs, "ndvi_stats", None)
    if stats is not None and getattr(stats, "valid_pixel_pct", None) is not None:
        return float(stats.valid_pixel_pct)
    cloud = getattr(obs, "cloud_cover_pct", None)
    return 1.0 - (float(cloud) / 100.0) if cloud is not None else 0.0
