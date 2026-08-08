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

# Sentinel-2 L2A product name → sensor id + acquisition date
# e.g. S2A_MSIL2A_20250810T110701_... → sensor "S2A", date "20250810".
_SAFE_SCENE_RE = re.compile(r"(S2[AB])_MSIL2A_(\d{8})T", re.IGNORECASE)

# Dashboard key → pipeline territory folder (mirrors real_trails mapping).
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


@dataclass(frozen=True)
class SceneReference:
    """A single real Sentinel-2 source scene: its sensor and acquisition date.

    Keeps the sensor id and its acquisition date *paired*, so callers cannot lose
    the correspondence by carrying two independent lists.
    """
    sensor_id: str          # "S2A" / "S2B"
    acquisition_date: str   # YYYY-MM-DD


def detect_scene_references(territory_key: str) -> list[SceneReference]:
    """Sensor+date of the real S2 source scenes present for a territory.

    Parses ``.SAFE`` product names under the territory's raw raster folder,
    capturing both the sensor id (``S2A``/``S2B``) and the acquisition date.
    Returns a sorted (by date, then sensor), de-duplicated list. Empty when the
    folder or products are absent — the caller degrades gracefully rather than
    inventing scenes.
    """
    try:
        cfg = territories.get(territory_key)
    except KeyError:
        return []
    folder = _RAW_RASTER_DIR / cfg.raw_raster_folder
    if not folder.exists():
        return []
    refs: set[SceneReference] = set()
    for entry in folder.iterdir():
        m = _SAFE_SCENE_RE.match(entry.name)
        if m:
            sensor = m.group(1).upper()
            raw = m.group(2)  # YYYYMMDD
            date = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
            refs.add(SceneReference(sensor_id=sensor, acquisition_date=date))
    return sorted(refs, key=lambda r: (r.acquisition_date, r.sensor_id))


def detect_scene_dates(territory_key: str) -> list[str]:
    """Acquisition dates (YYYY-MM-DD) of the real S2 scenes for a territory.

    Compatibility wrapper over :func:`detect_scene_references`: returns the
    sorted, de-duplicated acquisition dates. Empty when no local ``.SAFE``
    products are present.
    """
    refs = detect_scene_references(territory_key)
    return sorted({ref.acquisition_date for ref in refs})


def _derived_output_available(dashboard_key: str) -> bool:
    """Whether the committed Pipeline A derived GeoJSON exists for a territory.

    The derived output (``pipeline_a_results.geojson``) is git-tracked and can be
    genuinely present regardless of whether the ~900 MB raw ``.SAFE`` rasters are
    on disk. This is a self-contained check so provenance can distinguish
    "derived output absent" (State C) without depending on the UI having already
    loaded the dataset, and without importing ``real_trails`` (avoiding a cycle).
    """
    territory_key = _DASHBOARD_TO_TERRITORY.get(dashboard_key, dashboard_key)
    return (_OUTPUTS_DIR / territory_key / "pipeline_a_results.geojson").exists()


# Degraded (State B) wording — the derived artifact is real-Sentinel-derived, but
# its raw source scenes cannot be inspected here, so provenance is incomplete and
# the result is not locally reproducible. Kept as a constant so the UI, the
# reports and the regression tests all reference the same honest statement.
_DEGRADED_PROVENANCE_ES = (
    "Derivado de observaciones Sentinel-2 reales. Las escenas fuente no están "
    "disponibles en este entorno; la procedencia está incompleta y el resultado "
    "no es reproducible localmente."
)
_DEGRADED_DEPTH_ES = (
    "Artefacto derivado real disponible; profundidad temporal de la fuente no "
    "verificable localmente (escenas .SAFE ausentes)."
)
_MISSING_DEPTH_ES = "Sin salida derivada del Pipeline A para este territorio."
_MISSING_CAVEAT_ES = (
    "No hay resultados del Pipeline A para este territorio: no hay dato que "
    "describir."
)


@dataclass(frozen=True)
class SnapshotProvenance:
    """Provenance + confidence of the current real Pipeline A snapshot.

    Four orthogonal facts are kept explicit and separate — collapsing them was
    the defect this structure fixes:

    * ``derived_output_available`` — is the committed derived GeoJSON present?
    * ``raw_scenes_available`` — are the raw ``.SAFE`` source scenes on disk here?
    * ``provenance_complete`` — can the exact scenes/sensors/dates be re-derived?
    * ``locally_reproducible`` — could this environment rerun Pipeline A locally?

    ``locally_reproducible`` has a deliberately **narrow** meaning: the committed
    derived Pipeline A output is present here *and* the raw Sentinel-2 L2A source
    products the current snapshot needs are also present, so a local rerun is
    possible in this environment. It is set ``True`` only when both
    ``derived_output_available`` *and* valid detected raw scene references hold —
    never merely because some ``.SAFE`` file exists. It is **not** a claim of
    cross-machine or container reproducibility, independent scientific
    replication, complete archival provenance, or production reproducibility.

    ``status`` (``DataStatus``) is the *trust tier of the datum* and does not
    encode any of the four above: a derived artifact stays ``REAL`` while its raw
    source is unavailable locally.
    """
    status: DataStatus
    derived_output_available: bool
    raw_scenes_available: bool
    provenance_complete: bool
    # True only in State A: derived output present AND valid raw scene refs
    # detected here (a local rerun is possible). See the class docstring for the
    # narrow scope — not a cross-machine/independent-replication guarantee.
    locally_reproducible: bool
    n_scenes: Optional[int]           # None when source-scene metadata is unknown
    scene_dates: list[str]            # empty when unknown here
    scene_refs: list[SceneReference]  # paired sensor+date, empty when unknown here
    readiness: Optional[TrendReadiness]  # None when not derivable from local scenes
    mann_kendall_justified: bool
    seasonal_delta_valid: bool
    inference_label: str   # what the depth sustains, in plain Spanish
    caveat: str            # confidence caveat for the UI


def snapshot_provenance(dashboard_key: str) -> SnapshotProvenance:
    """Describe the provenance + inference validity of the real snapshot honestly.

    Distinguishes three states without conflating the four provenance dimensions:

    * **State A** — raw ``.SAFE`` scenes present *and* derived GeoJSON present:
      ``REAL``, fully provenance-complete and locally reproducible; scene count,
      dates and sensors come from the real ``.SAFE`` filenames and route through
      the F2 trend gate.
    * **State B** — derived GeoJSON present but raw scenes absent (a normal fresh
      clone): still ``REAL`` (the committed artifact is real-Sentinel-derived),
      but ``raw_scenes_available``/``provenance_complete``/``locally_reproducible``
      are ``False``. Scene count is **unknown** (``None``, never fabricated), and
      the trend gate is *not* run on an invented count.
    * **State C** — derived GeoJSON absent: ``MISSING``. No REAL/direct-observation
      wording, no fabricated scene metadata.
    """
    territory_key = _DASHBOARD_TO_TERRITORY.get(dashboard_key, dashboard_key)
    scene_refs = detect_scene_references(territory_key)
    scene_dates = sorted({ref.acquisition_date for ref in scene_refs})
    raw_available = bool(scene_refs)
    derived_available = _derived_output_available(dashboard_key)

    # State C — the derived output itself is absent: nothing real to describe.
    if not derived_available:
        return SnapshotProvenance(
            status=DataStatus.MISSING,
            derived_output_available=False,
            raw_scenes_available=raw_available,
            provenance_complete=False,
            locally_reproducible=False,
            n_scenes=None,
            scene_dates=[],
            scene_refs=[],
            readiness=None,
            mann_kendall_justified=False,
            seasonal_delta_valid=False,
            inference_label=_MISSING_DEPTH_ES,
            caveat=_MISSING_CAVEAT_ES,
        )

    # State B — derived output present, raw source scenes unavailable here. The
    # artifact stays REAL-derived, but its temporal depth is not locally
    # verifiable, so we do NOT fabricate a scene count nor run the trend gate.
    if not raw_available:
        return SnapshotProvenance(
            status=DataStatus.REAL,
            derived_output_available=True,
            raw_scenes_available=False,
            provenance_complete=False,
            locally_reproducible=False,
            n_scenes=None,
            scene_dates=[],
            scene_refs=[],
            readiness=None,
            mann_kendall_justified=False,
            seasonal_delta_valid=False,
            inference_label=_DEGRADED_DEPTH_ES,
            caveat=_DEGRADED_PROVENANCE_ES,
        )

    # State A — raw scenes present + derived output present: fully traceable.
    n_scenes = len(scene_dates)
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
        derived_output_available=True,
        raw_scenes_available=True,
        provenance_complete=True,
        locally_reproducible=True,
        n_scenes=n_scenes,
        scene_dates=scene_dates,
        scene_refs=scene_refs,
        readiness=gate.readiness,
        mann_kendall_justified=gate.mann_kendall_justified,
        seasonal_delta_valid=gate.seasonal_delta_valid,
        inference_label=inference,
        caveat=caveat,
    )


def snapshot_status_badge(snapshot: SnapshotProvenance) -> StatusBadge:
    """Snapshot-specific badge that distinguishes State A / B / C.

    ``data_status_badge(DataStatus.REAL)`` cannot by itself tell a fully-traceable
    snapshot (State A) from a derived-only one whose raw provenance is unavailable
    locally (State B) — both are ``REAL``. This picks the honest presentation from
    the provenance-completeness fields, without weakening the generic REAL badge
    used elsewhere.
    """
    if snapshot.status is DataStatus.MISSING or not snapshot.derived_output_available:
        return _STATUS_BADGE[DataStatus.MISSING]
    if snapshot.provenance_complete:
        return _STATUS_BADGE[DataStatus.REAL]
    # State B — real-derived, but degraded local provenance.
    return StatusBadge(
        "🛰️", "Dato satelital real (derivado)", "#B7791F",
        _DEGRADED_PROVENANCE_ES,
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
