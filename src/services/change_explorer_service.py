"""
SNTO — Visual Change Explorer orchestration service (ADR-015)
============================================================

The single application-facing use case that ties the accepted analysis core and
Earth Engine foundation together for the UI. The UI calls this; it never touches
Earth Engine, thumbnail construction, quality evaluation or cache keys directly.

Dependency direction (enforced): UI → this service →
``analysis/change_detection`` + ``integrations/earth_engine``.

Scope (this slice): registered SNTO territories only, `S2_SR_HARMONIZED` only,
True-Colour or NDVI swipe + a dNDVI static result, scene-level cloud threshold,
static PNG thumbnails. **No** GIF / `getVideoThumbURL`, **no** `getMapId` / tiles.

Earth Engine evaluation boundary: the analysis core builds *deferred* EE
expressions; this service is the one place that evaluates the minimum values
needed for UI metadata — **one** combined ``getInfo`` per date window (an
``ee.Dictionary`` of scene count, mean scene cloud, valid-pixel count and AOI
pixel count), never one request per metric, never inside dataclasses / builders /
UI, never at import.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from src.analysis.change_detection.composites import (
    ndvi_composite,
    true_colour_composite,
)
from src.analysis.change_detection.difference import ndvi_difference
from src.analysis.change_detection.models import (
    CompositeKind,
    DateWindow,
    QualityMetadata,
    WindowRole,
)
from src.analysis.change_detection.quality import (
    aoi_pixel_count_expr,
    evaluate_quality,
    mean_scene_cloud_expr,
    scene_count_expr,
    valid_pixel_count_expr,
)
from src.config import territories
from src.config.settings import Settings
from src.config.territories import TerritoryConfig
from src.integrations.earth_engine.client import get_change_explorer_client
from src.integrations.earth_engine.collections import (
    DNDVI_BAND,
    NDVI_BAND,
    S2_COLLECTION_ID,
    TRUE_COLOUR_BANDS,
    bbox_to_ee_rectangle,
    build_sentinel2_collection,
)
from src.integrations.earth_engine.errors import map_ee_exception
from src.integrations.earth_engine.palettes import (
    DNDVI,
    NDVI,
    TRUE_COLOUR,
    Visualization,
)
from src.integrations.earth_engine.render import (
    MAX_THUMBNAIL_DIMENSION,
    MIN_THUMBNAIL_DIMENSION,
    get_thumbnail_url,
)

logger = logging.getLogger(__name__)

# ── Versioned constants that affect output (part of the cache key) ────────────
COMPOSITE_METHOD_VERSION = "median-v1"
VISUALISATION_VERSION = "vis-v1"
DATASET_ID = S2_COLLECTION_ID

# Evidence label (kept in the dashboard's Spanish register). Real Sentinel-2, but
# a visual / seasonal early-warning product — never a field-validation claim.
EVIDENCE_LABEL = (
    "Observación real Sentinel-2 — salida visual / de alerta temprana estacional, "
    "no validada en campo."
)

# Cache TTL for the application-facing cached wrapper. Earth Engine's getThumbURL
# returns a *signed, temporary* URL whose exact lifetime is **not guaranteed by
# the API/code**; 600 s is a deliberately conservative bound that comfortably
# covers a single Streamlit interaction session (reruns are seconds apart) while
# staying well under any plausible signed-URL lifetime. The UI still degrades
# gracefully if a cached URL has expired.
CHANGE_EXPLORER_CACHE_TTL_SECONDS = 600

# Products the swipe supports (dNDVI is always computed as the difference layer).
_SWIPE_PRODUCTS = (CompositeKind.TRUE_COLOUR, CompositeKind.NDVI)
_PRODUCT_VIS: dict[CompositeKind, Visualization] = {
    CompositeKind.TRUE_COLOUR: TRUE_COLOUR,
    CompositeKind.NDVI: NDVI,
}
_PRODUCT_BANDS: dict[CompositeKind, tuple[str, ...]] = {
    CompositeKind.TRUE_COLOUR: TRUE_COLOUR_BANDS,
    CompositeKind.NDVI: (NDVI_BAND,),
}


# ── Request / result models (service-facing; no EE object, no secrets) ────────

class ResultStatus(str, Enum):
    OK = "ok"
    DEGRADED_COVERAGE = "degraded_coverage"
    NO_DATA = "no_data"


@dataclass(frozen=True)
class ChangeExplorerRequest:
    """A validated, hashable request. Holds no secrets and no EE module."""

    territory_id: str
    product: CompositeKind
    before: DateWindow
    after: DateWindow
    max_cloud_pct: float
    dimensions: int

    def __post_init__(self) -> None:
        if self.product not in _SWIPE_PRODUCTS:
            raise ValueError(
                f"unsupported swipe product {self.product!r}; "
                f"choose one of {[p.value for p in _SWIPE_PRODUCTS]}."
            )
        if not (0.0 <= self.max_cloud_pct <= 100.0):
            raise ValueError(
                f"max_cloud_pct must be in [0, 100], got {self.max_cloud_pct}."
            )
        if isinstance(self.dimensions, bool) or not isinstance(self.dimensions, int):
            raise ValueError("dimensions must be an int.")
        if not (MIN_THUMBNAIL_DIMENSION <= self.dimensions <= MAX_THUMBNAIL_DIMENSION):
            raise ValueError(
                f"dimensions {self.dimensions} out of bounds "
                f"[{MIN_THUMBNAIL_DIMENSION}, {MAX_THUMBNAIL_DIMENSION}]."
            )

    def cache_key(self, bbox: tuple[float, float, float, float]) -> tuple[Any, ...]:
        """Deterministic key over **all** output-affecting inputs.

        Includes the resolved AOI bbox, both windows (EE-exclusive dates),
        product, cloud threshold, dimensions, dataset id and the composite /
        visualisation versions. Excludes credentials, signed URLs, EE objects and
        the Settings object.
        """
        return (
            self.territory_id,
            bbox,
            (self.before.ee_start_date(), self.before.ee_end_date()),
            (self.after.ee_start_date(), self.after.ee_end_date()),
            self.product.value,
            float(self.max_cloud_pct),
            int(self.dimensions),
            DATASET_ID,
            COMPOSITE_METHOD_VERSION,
            VISUALISATION_VERSION,
        )


@dataclass(frozen=True)
class RenderedArtifact:
    """A rendered static thumbnail. The signed URL is temporary (expiry unknown).

    The URL is excluded from ``repr`` so it never leaks into logs/tracebacks.
    ``created_at`` is the only time we actually know; no fake expiry is invented.
    """

    product: CompositeKind
    role: WindowRole
    dimensions: int
    window: DateWindow
    visualization_id: str
    url: str = field(repr=False)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ChangeExplorerResult:
    """Everything the UI needs — and nothing more. No EE object, no secrets."""

    territory_id: str
    territory_name: str
    product: CompositeKind
    status: ResultStatus
    request: ChangeExplorerRequest
    before_quality: QualityMetadata
    after_quality: QualityMetadata
    warnings: tuple[str, ...]
    evidence_label: str
    generated_at: datetime
    before_artifact: RenderedArtifact | None = None
    after_artifact: RenderedArtifact | None = None
    dndvi_artifact: RenderedArtifact | None = None

    @property
    def has_swipe(self) -> bool:
        return self.before_artifact is not None and self.after_artifact is not None


# ── Territory resolution ──────────────────────────────────────────────────────

TerritoryResolver = Callable[[str], TerritoryConfig]


def usable_territories(
    resolver_list: Callable[[], list[str]] | None = None,
) -> list[tuple[str, str]]:
    """Return ``(territory_id, display_name)`` for territories with a usable AOI.

    "Usable" = has a valid `bbox_wgs84`. The UI lists only these; it never
    hardcodes a bbox or duplicates territory metadata.
    """
    list_keys = resolver_list or territories.list_keys
    out: list[tuple[str, str]] = []
    for key in list_keys():
        cfg = territories.get(key)
        bbox = cfg.bbox_wgs84
        if bbox and len(bbox) == 4 and bbox[0] < bbox[2] and bbox[1] < bbox[3]:
            out.append((key, cfg.display_name))
    return out


def _resolve_territory(
    territory_id: str, resolver: TerritoryResolver
) -> TerritoryConfig:
    try:
        return resolver(territory_id)
    except KeyError as exc:
        raise ValueError(f"unknown territory '{territory_id}'.") from exc


# ── Internal EE seams (module-level so tests can substitute them) ─────────────

def _build_window_collection(
    ee: Any, geometry: Any, window: DateWindow, max_cloud_pct: float
) -> Any:
    """Exactly **one** masked base collection per date window (no duplication)."""
    return build_sentinel2_collection(
        ee_module=ee,
        geometry=geometry,
        start_date=window.ee_start_date(),
        end_date=window.ee_end_date(),
        max_cloud_percentage=max_cloud_pct,
    )


def _evaluate_window_quality(
    ee: Any,
    *,
    base_collection: Any,
    ndvi_image: Any,
    geometry: Any,
    window: DateWindow,
    max_cloud_pct: float,
) -> QualityMetadata:
    """Evaluate a window's quality with a **single** combined ``getInfo``.

    Builds one ``ee.Dictionary`` of the four metrics and evaluates it once, then
    assembles :class:`QualityMetadata` offline. EE failures at evaluation time are
    mapped to the foundation's typed errors.
    """
    expr = ee.Dictionary(
        {
            "scene_count": scene_count_expr(base_collection),
            "mean_scene_cloud": mean_scene_cloud_expr(base_collection),
            "valid_pixels": valid_pixel_count_expr(
                ee_module=ee, ndvi_image=ndvi_image, region=geometry
            ),
            "aoi_pixels": aoi_pixel_count_expr(region=geometry),
        }
    )
    try:
        raw: dict[str, Any] = expr.getInfo()
    except Exception as exc:  # noqa: BLE001 - re-raised as typed, cause chained
        logger.warning("Earth Engine quality evaluation failed.")
        raise map_ee_exception(exc) from exc

    scene_count = _as_int(raw.get("scene_count"))
    valid_pixels = _as_int(raw.get("valid_pixels"))
    aoi_pixels = _as_int(raw.get("aoi_pixels"))
    mean_cloud = _as_float(raw.get("mean_scene_cloud"))
    return evaluate_quality(
        window=window,
        requested_max_cloud_pct=max_cloud_pct,
        scene_count=scene_count,
        valid_pixel_count=valid_pixels,
        aoi_pixel_count=aoi_pixels,
        mean_scene_cloud_pct=mean_cloud,
    )


def _as_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _as_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _render(
    image: Any,
    *,
    geometry: Any,
    vis: Visualization,
    dimensions: int,
    product: CompositeKind,
    role: WindowRole,
    window: DateWindow,
    visualization_id: str,
) -> RenderedArtifact:
    url = get_thumbnail_url(
        image=image,
        region=geometry,
        visualization=vis.to_ee_params(),
        dimensions=dimensions,
    )
    return RenderedArtifact(
        product=product,
        role=role,
        dimensions=dimensions,
        window=window,
        visualization_id=visualization_id,
        url=url,
    )


# ── Public entry point ────────────────────────────────────────────────────────

def run_change_explorer(
    request: ChangeExplorerRequest,
    *,
    app_settings: Settings | None = None,
    territory_resolver: TerritoryResolver | None = None,
) -> ChangeExplorerResult:
    """Run the Visual Change Explorer for *request* and return a typed result.

    Orchestration: validate → obtain the cached EE client (foundation) → resolve
    the registered AOI → one masked collection per window → composites → dNDVI
    (reusing the NDVI composites) → one combined quality ``getInfo`` per window →
    honest no-scenes / no-valid-pixels / low-coverage classification → aligned PNG
    thumbnails only when data exists. EE failures propagate as typed errors.
    """
    resolver = territory_resolver or territories.get
    cfg = _resolve_territory(request.territory_id, resolver)

    client = get_change_explorer_client(app_settings)
    ee = client.module()
    geometry = bbox_to_ee_rectangle(ee, cfg.bbox_wgs84)

    # One base collection per window; NDVI composites are computed for both (they
    # feed both the optional NDVI swipe and the always-computed dNDVI).
    cloud = request.max_cloud_pct
    base_before = _build_window_collection(ee, geometry, request.before, cloud)
    base_after = _build_window_collection(ee, geometry, request.after, cloud)
    ndvi_before = ndvi_composite(base_before)
    ndvi_after = ndvi_composite(base_after)

    before_quality = _evaluate_window_quality(
        ee,
        base_collection=base_before,
        ndvi_image=ndvi_before,
        geometry=geometry,
        window=request.before,
        max_cloud_pct=request.max_cloud_pct,
    )
    after_quality = _evaluate_window_quality(
        ee,
        base_collection=base_after,
        ndvi_image=ndvi_after,
        geometry=geometry,
        window=request.after,
        max_cloud_pct=request.max_cloud_pct,
    )

    warnings: list[str] = list(before_quality.warnings) + list(after_quality.warnings)
    generated_at = datetime.now(timezone.utc)

    def _renderable(q: QualityMetadata) -> bool:
        return bool(q.scene_count) and bool(q.valid_pixel_count)

    # No fabricated URLs for no-data products: only render when BOTH windows have
    # at least one scene and one valid pixel.
    if not (_renderable(before_quality) and _renderable(after_quality)):
        return ChangeExplorerResult(
            territory_id=cfg.key,
            territory_name=cfg.display_name,
            product=request.product,
            status=ResultStatus.NO_DATA,
            request=request,
            before_quality=before_quality,
            after_quality=after_quality,
            warnings=tuple(warnings),
            evidence_label=EVIDENCE_LABEL,
            generated_at=generated_at,
        )

    # Swipe composites for the chosen product (NDVI reuses the images above).
    if request.product is CompositeKind.NDVI:
        swipe_before, swipe_after = ndvi_before, ndvi_after
    else:
        swipe_before = true_colour_composite(base_before)
        swipe_after = true_colour_composite(base_after)
    product_vis = _PRODUCT_VIS[request.product]

    # dNDVI reuses the NDVI composites — no extra collection build.
    dndvi_image = ndvi_difference(before_ndvi=ndvi_before, after_ndvi=ndvi_after)

    # Aligned rendering: identical geometry + dimensions + fixed visualisation.
    before_artifact = _render(
        swipe_before, geometry=geometry, vis=product_vis, dimensions=request.dimensions,
        product=request.product, role=WindowRole.BEFORE, window=request.before,
        visualization_id=f"{request.product.value}:{VISUALISATION_VERSION}",
    )
    after_artifact = _render(
        swipe_after, geometry=geometry, vis=product_vis, dimensions=request.dimensions,
        product=request.product, role=WindowRole.AFTER, window=request.after,
        visualization_id=f"{request.product.value}:{VISUALISATION_VERSION}",
    )
    dndvi_artifact = _render(
        dndvi_image, geometry=geometry, vis=DNDVI, dimensions=request.dimensions,
        product=CompositeKind.DNDVI, role=WindowRole.DIFFERENCE, window=request.after,
        visualization_id=f"{DNDVI_BAND}:{VISUALISATION_VERSION}",
    )

    degraded = not (
        before_quality.adequate_coverage and after_quality.adequate_coverage
    )
    status = ResultStatus.DEGRADED_COVERAGE if degraded else ResultStatus.OK

    return ChangeExplorerResult(
        territory_id=cfg.key,
        territory_name=cfg.display_name,
        product=request.product,
        status=status,
        request=request,
        before_quality=before_quality,
        after_quality=after_quality,
        warnings=tuple(warnings),
        evidence_label=EVIDENCE_LABEL,
        generated_at=generated_at,
        before_artifact=before_artifact,
        after_artifact=after_artifact,
        dndvi_artifact=dndvi_artifact,
    )


# ── Application-facing cached wrapper (only Streamlit touch-point) ─────────────
# The cache key includes the resolved bbox + versions (via request.cache_key);
# exceptions are never cached as successes (st.cache_data does not cache raises).
# Built once at import; degrades to an uncached delegate without Streamlit so the
# module stays importable/testable outside a run context.
def _resolve_bbox_for_key(request: ChangeExplorerRequest) -> tuple[float, ...]:
    return _resolve_territory(request.territory_id, territories.get).bbox_wgs84


def _uncached_cached_run(request: ChangeExplorerRequest) -> ChangeExplorerResult:
    return run_change_explorer(request)


try:
    import streamlit as st

    @st.cache_data(ttl=CHANGE_EXPLORER_CACHE_TTL_SECONDS, show_spinner=False)
    def _cached_impl(
        cache_key: tuple[Any, ...], _request: ChangeExplorerRequest
    ) -> ChangeExplorerResult:
        # Only `cache_key` (a tuple of primitives) drives invalidation; `_request`
        # is leading-underscore so Streamlit does NOT hash the dataclass, it just
        # carries the inputs through to the orchestrator.
        return run_change_explorer(_request)

    def cached_run_change_explorer(
        request: ChangeExplorerRequest,
    ) -> ChangeExplorerResult:
        return _cached_impl(request.cache_key(_resolve_bbox_for_key(request)), request)

    def clear_change_explorer_cache() -> None:
        """Drop cached results (dev/testing)."""
        _cached_impl.clear()

except ModuleNotFoundError:  # pragma: no cover - streamlit is a declared dep

    def cached_run_change_explorer(
        request: ChangeExplorerRequest,
    ) -> ChangeExplorerResult:
        return run_change_explorer(request)

    def clear_change_explorer_cache() -> None:
        return None
