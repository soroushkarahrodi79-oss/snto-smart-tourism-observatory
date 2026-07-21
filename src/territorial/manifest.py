"""
Machine-tracked evidence class for the curated territorial layer (v2.1).

The satellite series carries a ``SeriesManifest`` whose every period is
classified with a :class:`~src.temporal.manifest.DataStatus`; the curated
territorial layer (``src/territorial/fixtures.py``) had no machine-readable
equivalent — its "calibrated, not observed" nature lived only in docstrings
and in the hand-written lineage records of the asset page (Fase 6.7d).

This module closes that gap ("Evidence-tracking gap", v2.1 of
``docs/roadmap/plan_v3_roadmap.md``): the layer is wrapped in a
:class:`TerritorialLayerManifest` that reuses the *same* ``DataStatus``
vocabulary as the satellite series, so any consumer (UI, API, tests) can ask
the layer what it is instead of trusting prose. The fixtures are expert-curated
estimates — ``CALIBRATED``, never ``REAL`` — and a regression test pins that.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.temporal.manifest import DataStatus, classify_source
from src.territorial.models import TerritorialAsset

# Strategic-metadata fields of TerritorialAsset that are curated estimates
# (expert-assigned, no persisted per-asset source or measurement date).
CURATED_FIELDS: tuple[str, ...] = (
    "visitor_capacity_annual",
    "economic_importance",
    "accessibility_score",
)

# Free-text source of the layer. Written so that
# ``classify_source(TERRITORIAL_LAYER_SOURCE)`` maps to CALIBRATED — the same
# classifier the satellite manifest uses; a test asserts the two agree.
TERRITORIAL_LAYER_SOURCE = (
    "curated expert calibration (fixtures.py); no field measurement"
)

_LAYER_CAVEAT = (
    "Atributos estratégicos curados (aforo anual, importancia económica, "
    "accesibilidad): asignación experta de orden de magnitud, sin conteo de "
    "visitantes ni medición de campo persistida por activo."
)


@dataclass(frozen=True)
class TerritorialLayerManifest:
    """Evidence class + inventory for one territory's curated asset layer."""

    territory_key: str
    data_status: DataStatus
    data_source: str
    curated_fields: tuple[str, ...]
    n_assets: int
    caveat: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["data_status"] = self.data_status.value
        d["curated_fields"] = list(self.curated_fields)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def write_json(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json() + "\n", encoding="utf-8")
        return p


def build_territorial_manifest(
    territory_key: str,
    assets: list[TerritorialAsset],
) -> TerritorialLayerManifest:
    """Manifest for a curated fixture territory.

    The status is derived through :func:`classify_source` — the exact
    classifier the satellite ``SeriesManifest`` uses — not hardcoded, so the
    two evidence-tracking paths cannot drift apart silently.
    """
    return TerritorialLayerManifest(
        territory_key=territory_key,
        data_status=classify_source(TERRITORIAL_LAYER_SOURCE),
        data_source=TERRITORIAL_LAYER_SOURCE,
        curated_fields=CURATED_FIELDS,
        n_assets=len(assets),
        caveat=_LAYER_CAVEAT,
    )
