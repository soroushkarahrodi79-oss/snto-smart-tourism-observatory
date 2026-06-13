"""
SNTO — Data Provenance & Confidence Surfacing (F3)
==================================================
Turns the provenance the system already holds into explicit, dashboard-ready
labels. The audit asked the observatory to make crystal clear, at the point of
display, *what kind of datum* the user is looking at (real satellite / curated
expert / synthetic demo) and *how much* it supports a decision.

This module is pure logic (no Streamlit). It:
  * maps a ``DataStatus`` to a UI badge (emoji, label, colour, caveat);
  * detects the real Sentinel-2 scene dates actually processed for a territory
    by parsing the ``.SAFE`` product names under its raw raster folder, so the
    acquisition dates shown are traceable to real inputs, not hard-coded;
  * summarises the current temporal *snapshot* provenance (how many scenes,
    which inference the depth sustains via the F2 ``trend_gate``);
  * reads the F2 time-series manifest when present to report coverage.

The result is consumed by ``app.py`` to render a "Calidad y trazabilidad del
dato" panel with an explicit confidence caveat.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.config import territories
from src.temporal import (
    DataStatus,
    TrendReadiness,
    assess_trend_readiness,
)

_ROOT = Path(__file__).resolve().parents[2]
_RAW_RASTER_DIR = _ROOT / "data" / "raw_assets" / "raster_data"
_OUTPUTS_DIR = _ROOT / "data" / "outputs"

# Sentinel-2 L2A product name → acquisition date (e.g. S2A_MSIL2A_20250810T110701_...)
_SAFE_DATE_RE = re.compile(r"S2[AB]_MSIL2A_(\d{8})T", re.IGNORECASE)

# Dashboard key → pipeline territory folder (mirrors real_trails._DASHBOARD_TO_TERRITORY).
_DASHBOARD_TO_TERRITORY: dict[str, str] = {
    "snr": "sierra_del_rincon",
    "pnsg": "pnsg",
}


@dataclass(frozen=True)
class StatusBadge:
    emoji: str
    label: str
    color: str
    caveat: str


_STATUS_BADGE: dict[DataStatus, StatusBadge] = {
    DataStatus.REAL: StatusBadge(
        "🛰️", "Dato satelital real", "#0F6E56",
        "Observación directa Sentinel-2 L2A. Apta para diagnóstico y alerta.",
    ),
    DataStatus.CALIBRATED: StatusBadge(
        "📐", "Dato calibrado por experto", "#B7791F",
        "Reconstrucción calibrada con literatura / anomalías AEMET-Copernicus. "
        "No es observación directa: validar antes de decidir.",
    ),
    DataStatus.SYNTHETIC: StatusBadge(
        "🧪", "Demo sintética", "#A32D2D",
        "Datos generados para demostración del sistema. NO usar para decisión real.",
    ),
    DataStatus.MISSING: StatusBadge(
        "—", "Sin dato", "#9e9e9e",
        "Periodo sin observación válida.",
    ),
}


def data_status_badge(status: DataStatus) -> StatusBadge:
    """UI badge (emoji, label, colour, caveat) for a data-status tier."""
    return _STATUS_BADGE.get(status, _STATUS_BADGE[DataStatus.MISSING])


def detect_scene_dates(territory_key: str) -> list[str]:
    """Acquisition dates (YYYY-MM-DD) of the real S2 scenes processed for a territory.

    Parses ``.SAFE`` product names under the territory's raw raster folder. Returns
    a sorted, de-duplicated list. Empty when the folder or products are absent —
    the caller degrades gracefully rather than inventing dates.
    """
    try:
        cfg = territories.get(territory_key)
    except KeyError:
        return []
    folder = _RAW_RASTER_DIR / cfg.raw_raster_folder
    if not folder.exists():
        return []
    dates: set[str] = set()
    for entry in folder.iterdir():
        m = _SAFE_DATE_RE.match(entry.name)
        if m:
            raw = m.group(1)  # YYYYMMDD
            dates.add(f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}")
    return sorted(dates)


@dataclass(frozen=True)
class SnapshotProvenance:
    """Provenance + confidence of the current real Pipeline A snapshot."""
    status: DataStatus
    n_scenes: int
    scene_dates: list[str]
    readiness: TrendReadiness
    mann_kendall_justified: bool
    seasonal_delta_valid: bool
    inference_label: str   # what the depth sustains, in plain Spanish
    caveat: str            # confidence caveat for the UI


def snapshot_provenance(dashboard_key: str) -> SnapshotProvenance:
    """Describe the temporal depth + inference validity of the real snapshot.

    The current real Pipeline A output is a seasonal snapshot (a small number of
    Sentinel-2 scenes). This routes the scene count through the F2 trend gate so
    the dashboard states honestly whether a trend claim is justified.
    """
    territory_key = _DASHBOARD_TO_TERRITORY.get(dashboard_key, dashboard_key)
    scene_dates = detect_scene_dates(territory_key)
    n_scenes = len(scene_dates) if scene_dates else 2  # filemode uses spring+summer
    gate = assess_trend_readiness(n_scenes)

    if gate.mann_kendall_justified:
        inference = (
            f"{n_scenes} escenas: tendencia Mann-Kendall computable "
            f"({gate.readiness.value})."
        )
        caveat = (
            "Tendencia inter-anual disponible. Reportar con su nivel de "
            "confianza (DCS) explícito."
        )
    else:
        inference = (
            f"{n_scenes} escenas: ΔEHS estacional válido; tendencia "
            f"Mann-Kendall NO aplicable (requiere serie 2021–2026, ya "
            f"estructurada — ver docs/temporal_series_design.md)."
        )
        caveat = (
            "⚠️ Señal de alerta temprana, no veredicto de intervención formal. "
            "La priorización indica dónde mirar primero, no una orden de gasto."
        )

    return SnapshotProvenance(
        status=DataStatus.REAL,
        n_scenes=n_scenes,
        scene_dates=scene_dates,
        readiness=gate.readiness,
        mann_kendall_justified=gate.mann_kendall_justified,
        seasonal_delta_valid=gate.seasonal_delta_valid,
        inference_label=inference,
        caveat=caveat,
    )


def load_timeseries_coverage(dashboard_key: str) -> Optional[dict[str, Any]]:
    """Coverage block of the F2 time-series manifest, if it has been produced.

    Returns the ``coverage`` dict (n_expected, n_present, fraction,
    dominant_status, n_gaps) or None when no manifest exists yet — i.e. the
    multi-year series has not been ingested.
    """
    territory_key = _DASHBOARD_TO_TERRITORY.get(dashboard_key, dashboard_key)
    path = _OUTPUTS_DIR / territory_key / "pipeline_a_ts_manifest.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload.get("coverage")
