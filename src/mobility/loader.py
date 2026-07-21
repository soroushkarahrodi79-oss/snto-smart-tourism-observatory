"""
SNTO — Mobility snapshot & reference loaders (v2.2).

Mirrors ``src/socioeconomic/loader.py``: pure I/O, cached, with an honest
``mobility_snapshot_exists()`` gate so the dashboard falls back to the labeled
curated estimate when the real feed has not been ingested yet.

Two artifacts:
  * the **reference** crosswalk (real MITMA zone <-> PNSG municipality), shipped
    in-package and always present;
  * the **snapshot** of real inbound trips, produced by ``etl_mobility.py`` from
    the (multi-GB, not-bundled) MITMA daily files — absent until the owner runs
    the ETL, exactly like the socioeconomic snapshot is produced from source.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.mobility.models import MobilitySnapshot, MobilityZone

_REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
_SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshot"
PNSG_ZONES_PATH = _REFERENCE_DIR / "pnsg_mobility_zones.json"
SNAPSHOT_PATH = _SNAPSHOT_DIR / "mobility.json"


@dataclass(frozen=True)
class ZoneRef:
    """One real MITMA-zone ↔ PNSG-municipality mapping row."""

    mitma_zone_id: str | None
    ine_code: str
    name: str
    resolved: bool


def mobility_snapshot_exists(path: Path | None = None) -> bool:
    """True once ``etl_mobility.py`` has produced the real inbound-trip snapshot."""
    return (path or SNAPSHOT_PATH).exists()


@lru_cache(maxsize=2)
def load_pnsg_zones(path: Path | None = None) -> list[ZoneRef]:
    """The real MITMA-zone crosswalk shipped in-package (always available)."""
    data = json.loads((path or PNSG_ZONES_PATH).read_text(encoding="utf-8"))
    return [
        ZoneRef(
            mitma_zone_id=z.get("mitma_zone_id"),
            ine_code=str(z["ine_code"]),
            name=str(z.get("name", "")),
            resolved=bool(z.get("resolved", False)),
        )
        for z in data.get("zones", [])
    ]


@lru_cache(maxsize=2)
def load_mobility(path: Path | None = None) -> MobilitySnapshot | None:
    """Real inbound-mobility snapshot, or ``None`` when not yet ingested."""
    p = path or SNAPSHOT_PATH
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    zones = {
        code: MobilityZone.from_dict(d)
        for code, d in data.get("zones", {}).items()
    }
    return MobilitySnapshot(
        schema_version=data.get("schema_version", ""),
        source_period=data.get("source_period", ""),
        generated_at=data.get("generated_at", ""),
        source=data.get("source", {}),
        zones=zones,
    )
