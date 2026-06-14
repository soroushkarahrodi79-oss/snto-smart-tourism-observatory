"""
SNTO — Socioeconomic snapshot loader (F9)
==========================================
Reads the curated snapshot produced by ``etl_socioeconomic.py``. Pure I/O — no
computation. Cached so the dashboard pays the parse cost once.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .mapping import normalize_name
from .models import Municipality

# Curated snapshot ships inside the package so it reaches CI and the Azure image
# (data/ is git-ignored and docker-ignored).
_SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshot"
SNAPSHOT_PATH = _SNAPSHOT_DIR / "municipalities.json"
TOURISM_ZONE_PATH = _SNAPSHOT_DIR / "pnsg_tourism_zone.json"


@dataclass(frozen=True)
class SocioeconomicSnapshot:
    schema_version: str
    source_snapshot_date: str
    n_municipalities: int
    n_full: int
    n_demographic_only: int
    sources: dict
    municipalities: dict[str, Municipality]  # ine_code -> Municipality

    def get(self, ine_code: str | None) -> Municipality | None:
        return self.municipalities.get(ine_code) if ine_code else None

    def name_to_ine(self) -> dict[str, str]:
        """Normalised municipality name -> INE code, derived from the snapshot.

        Lets the runtime resolve ``asset.region`` without needing the raw
        crosswalk CSV (which lives under the git/docker-ignored data/ tree).
        """
        return {
            normalize_name(m.name): m.ine_code
            for m in self.municipalities.values()
        }


def snapshot_exists(path: Path | None = None) -> bool:
    return (path or SNAPSHOT_PATH).exists()


@lru_cache(maxsize=2)
def load_municipalities(path: Path | None = None) -> SocioeconomicSnapshot:
    path = path or SNAPSHOT_PATH
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    munis = {
        code: Municipality.from_dict(d)
        for code, d in data.get("municipalities", {}).items()
    }
    return SocioeconomicSnapshot(
        schema_version=data.get("schema_version", ""),
        source_snapshot_date=data.get("source_snapshot_date", ""),
        n_municipalities=data.get("n_municipalities", len(munis)),
        n_full=data.get("n_full", 0),
        n_demographic_only=data.get("n_demographic_only", 0),
        sources=data.get("sources", {}),
        municipalities=munis,
    )


@lru_cache(maxsize=2)
def load_tourism_zone(path: Path | None = None) -> dict:
    path = path or TOURISM_ZONE_PATH
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))
