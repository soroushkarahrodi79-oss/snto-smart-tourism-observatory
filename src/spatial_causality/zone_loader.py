"""
Real multi-scale zone loader for the Spatial Causality Module (v2.2).

The SCM classifies degradation as human-localized vs landscape/climate-driven by
comparing NDVI across three concentric zones (core ≤50 m, near ≤200 m, landscape
≤1000 m). Until now those zones were **simulated** from the single-buffer series
by an α-decay function — a plausible but synthetic spatial gradient.

This module lets the SCM consume **observed** zones exported from Google Earth
Engine (``scripts/gee_scm_zones_pnsg.js``), so attribution can move from
SIMULATED to REAL where the export exists. It mirrors the mobility/socioeconomic
pattern: an honest ``real_zones_exist()`` gate and a loader that returns ``None``
when the export has not been produced, so :func:`analyse_asset` falls back to the
labelled simulation rather than blurring the two.

Export format (per asset, one JSON under ``src/spatial_causality/zones/``):
``{"asset_id", "zones": {"core"|"near"|"landscape": [
      {"year","month","ndvi","ndmi","cloud_cover_pct"?}, ...]}}``
NDVI/NDMI are real zonal means (Sentinel-2, same tile/period as Pipeline A).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.assets.models import AssetObservation

_ZONES_DIR = Path(__file__).resolve().parent / "zones"
_REQUIRED_ZONES = ("core", "near", "landscape")


def _zone_path(asset_id: str, base: Path | None = None) -> Path:
    return (base or _ZONES_DIR) / f"{asset_id}.json"


def real_zones_exist(asset_id: str, base: Path | None = None) -> bool:
    """True when a real multi-scale GEE export exists for this asset."""
    return _zone_path(asset_id, base).exists()


@lru_cache(maxsize=256)
def load_real_zones(
    asset_id: str, base: Path | None = None
) -> dict[str, list[AssetObservation]] | None:
    """Observed core/near/landscape series for an asset, or ``None`` if absent.

    Returns ``None`` (not an empty dict) when the export is missing or malformed,
    so the caller falls back to the simulation honestly. Each observation is
    tagged ``data_source="scm_real:<zone>"`` → the result is classed REAL.
    """
    path = _zone_path(asset_id, base)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    zones = raw.get("zones", {})
    if not all(z in zones and zones[z] for z in _REQUIRED_ZONES):
        return None

    out: dict[str, list[AssetObservation]] = {}
    for zone in _REQUIRED_ZONES:
        obs_list: list[AssetObservation] = []
        for row in zones[zone]:
            obs_list.append(
                AssetObservation(
                    asset_id=asset_id,
                    year=int(row["year"]),
                    month=int(row["month"]),
                    ndvi=float(row["ndvi"]),
                    ndmi=float(row["ndmi"]),
                    cloud_cover_pct=float(row.get("cloud_cover_pct", 0.0)),
                    data_source=f"scm_real:{zone}",
                )
            )
        out[zone] = obs_list
    return out
