"""
SNTO — Temporal GIF animation orchestration service (ADR-015)
============================================================

Application-facing use case for the bounded, synchronous, user-triggered temporal
GIF. The UI calls this; it never builds EE collections or calls
``getVideoThumbURL`` directly.

Dependency direction: UI → this service → ``analysis/change_detection/animation``
→ ``integrations/earth_engine/video``.

Pipeline: validate → cached EE client → resolve registered territory → geometry →
plan frame windows (local) → build one masked collection + a pre-visualised frame
per window → **one grouped ``getInfo``** of all frame scene counts → drop empty
frames (≥ 2 usable required) → chronological visualised ``ImageCollection`` →
``getVideoThumbURL`` → **immediately fetch the GIF bytes** (the signed URL is
never stored/logged) with an 8 MiB cap + timeout + GIF-magic validation → typed
:class:`AnimatedArtifact`.

Frame-quality policy (documented): **scene count is checked per frame** (one
grouped call); the full per-pixel valid-pixel coverage is **not** recomputed for
every frame (that would add repeated expensive ``reduceRegion`` work). The GIF is
exploratory / observational, not a validated measurement.
"""
from __future__ import annotations

import logging
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable

from src.analysis.change_detection.animation import (
    ANIMATION_PLANNER_VERSION,
    DEFAULT_MAX_FRAMES,
    MAX_FRAMES,
    MAX_SPAN_MONTHS,
    MIN_FRAMES,
    build_frame,
    build_video_collection,
    calendar_month_span,
    plan_frame_windows,
    scene_counts_expr,
)
from src.analysis.change_detection.models import CompositeKind
from src.config import territories
from src.config.settings import Settings
from src.config.territories import TerritoryConfig
from src.integrations.earth_engine.client import get_change_explorer_client
from src.integrations.earth_engine.collections import (
    S2_COLLECTION_ID,
    bbox_to_ee_rectangle,
)
from src.integrations.earth_engine.errors import map_ee_exception
from src.integrations.earth_engine.video import (
    ALLOWED_FPS,
    ALLOWED_VIDEO_DIMENSIONS,
    DEFAULT_FPS,
    DEFAULT_VIDEO_DIMENSIONS,
    get_video_thumbnail_url,
)
from src.services.change_explorer_service import (
    COMPOSITE_METHOD_VERSION,
    VISUALISATION_VERSION,
)

logger = logging.getLogger(__name__)

# ── Hard limits (mirrored from the analysis/video layers for request checks) ──
DATASET_ID = S2_COLLECTION_ID
MAX_GIF_BYTES = 8 * 1024 * 1024  # 8 MiB response cap (mandatory — cached bytes)
GIF_HTTP_TIMEOUT_S = 30  # conservative, explicit connect+read timeout
CHANGE_ANIMATION_CACHE_TTL_SECONDS = 900
_ANIMATION_PRODUCTS = (CompositeKind.TRUE_COLOUR, CompositeKind.NDVI)
_GIF_MAGIC = (b"GIF87a", b"GIF89a")

EVIDENCE_LABEL = (
    "Animación exploratoria de composiciones temporales Sentinel-2. Los cambios "
    "visibles pueden reflejar estacionalidad, nubosidad residual, fenología, "
    "incendios, manejo territorial u otros factores. No demuestra causalidad "
    "turística ni sustituye validación de campo."
)


# ── Typed animation errors (GIF fetch / usable-frame conditions) ──────────────

class AnimationError(RuntimeError):
    """Base for animation-specific (non-EE) failures."""


class InsufficientUsableFramesError(AnimationError):
    """Fewer than two frames had any Sentinel-2 scenes after empty-frame removal."""


class GifDownloadError(AnimationError):
    """The generated GIF could not be retrieved (network / HTTP)."""


class GifTimeoutError(GifDownloadError):
    """Timed out downloading the generated GIF."""


class GifTooLargeError(GifDownloadError):
    """The GIF response exceeded the 8 MiB cap."""


class GifInvalidError(GifDownloadError):
    """The response was not a valid GIF (magic bytes absent)."""


# ── Models (frozen; no EE object, no secrets, no signed URL) ──────────────────

@dataclass(frozen=True)
class ChangeAnimationRequest:
    """Validated, hashable animation request. No credentials, EE objects or URLs."""

    territory_id: str
    product: CompositeKind
    start: date
    end: date
    max_cloud_pct: float
    dimensions: int
    max_frame_count: int
    frames_per_second: int

    def __post_init__(self) -> None:
        if isinstance(self.start, datetime) or isinstance(self.end, datetime):
            raise TypeError("animation dates must be datetime.date, not datetime.")
        if not isinstance(self.start, date) or not isinstance(self.end, date):
            raise TypeError("animation start/end must be datetime.date.")
        if self.product not in _ANIMATION_PRODUCTS:
            raise ValueError(
                f"unsupported animation product {self.product!r}; choose one of "
                f"{[p.value for p in _ANIMATION_PRODUCTS]}."
            )
        if self.start >= self.end:
            raise ValueError("animation start must be before end.")
        span = calendar_month_span(self.start, self.end)
        if span > MAX_SPAN_MONTHS:
            raise ValueError(
                f"animation span {span} months exceeds the {MAX_SPAN_MONTHS}-month max."
            )
        if span < MIN_FRAMES:
            raise ValueError(
                "animation span is too short to form at least two frames."
            )
        if not (0.0 <= self.max_cloud_pct <= 100.0):
            raise ValueError("max_cloud_pct must be in [0, 100].")
        if self.dimensions not in ALLOWED_VIDEO_DIMENSIONS:
            raise ValueError(
                f"dimensions must be one of {ALLOWED_VIDEO_DIMENSIONS}."
            )
        if isinstance(self.max_frame_count, bool) or not isinstance(
            self.max_frame_count, int
        ):
            raise ValueError("max_frame_count must be an int.")
        if not (MIN_FRAMES <= self.max_frame_count <= MAX_FRAMES):
            raise ValueError(
                f"max_frame_count must be in [{MIN_FRAMES}, {MAX_FRAMES}]."
            )
        if self.frames_per_second not in ALLOWED_FPS:
            raise ValueError(f"frames_per_second must be one of {ALLOWED_FPS}.")

    def cache_key(self, bbox: tuple[float, float, float, float]) -> tuple[Any, ...]:
        """Deterministic key over every output-affecting input (no secrets/URLs)."""
        return (
            self.territory_id,
            bbox,
            self.start.isoformat(),
            self.end.isoformat(),
            self.product.value,
            float(self.max_cloud_pct),
            int(self.dimensions),
            int(self.max_frame_count),
            int(self.frames_per_second),
            DATASET_ID,
            COMPOSITE_METHOD_VERSION,
            VISUALISATION_VERSION,
            ANIMATION_PLANNER_VERSION,
        )


@dataclass(frozen=True)
class AnimationFrameMetadata:
    """Per-frame metadata (no EE object)."""

    frame_index: int
    frame_start: str
    frame_end: str
    ee_end_exclusive: str
    scene_count: int
    product: CompositeKind
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
            "ee_end_exclusive": self.ee_end_exclusive,
            "scene_count": self.scene_count,
            "product": self.product.value,
            "warning": self.warning,
        }


@dataclass(frozen=True)
class AnimatedArtifact:
    """The generated GIF as in-memory bytes plus safe metadata.

    ``gif_bytes`` is excluded from ``repr`` and never serialised; no signed URL,
    credentials or EE object is retained.
    """

    territory_id: str
    territory_name: str
    product: CompositeKind
    dimensions: int
    frames_per_second: int
    frame_count: int
    planned_frame_count: int
    frames: tuple[AnimationFrameMetadata, ...]
    warnings: tuple[str, ...]
    byte_size: int
    generated_at: datetime
    request: ChangeAnimationRequest
    evidence_label: str = EVIDENCE_LABEL
    mime_type: str = "image/gif"
    gif_bytes: bytes = field(repr=False, default=b"")

    def to_dict(self) -> dict[str, Any]:
        """Metadata-only — never includes the GIF bytes."""
        return {
            "territory_id": self.territory_id,
            "territory_name": self.territory_name,
            "product": self.product.value,
            "dimensions": self.dimensions,
            "frames_per_second": self.frames_per_second,
            "frame_count": self.frame_count,
            "planned_frame_count": self.planned_frame_count,
            "frames": [f.to_dict() for f in self.frames],
            "warnings": list(self.warnings),
            "byte_size": self.byte_size,
            "mime_type": self.mime_type,
            "generated_at": self.generated_at.isoformat(),
        }


TerritoryResolver = Callable[[str], TerritoryConfig]


def _resolve_territory(
    territory_id: str, resolver: TerritoryResolver
) -> TerritoryConfig:
    try:
        return resolver(territory_id)
    except KeyError as exc:
        raise ValueError(f"unknown territory '{territory_id}'.") from exc


# ── Safe signed-URL → bytes retrieval ─────────────────────────────────────────

def _fetch_gif_bytes(url: str) -> bytes:
    """Download the GIF, bounded and validated. The URL is never logged.

    Follows normal HTTPS redirects (stdlib default), uses an explicit timeout,
    reads incrementally and aborts above 8 MiB, and validates the GIF magic bytes.
    Never persists to disk. Maps failures to typed animation errors.
    """
    request = urllib.request.Request(url, method="GET")  # noqa: S310 - EE https URL
    chunks: list[bytes] = []
    total = 0
    try:
        with urllib.request.urlopen(  # noqa: S310 - signed EE https URL
            request, timeout=GIF_HTTP_TIMEOUT_S
        ) as response:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_GIF_BYTES:
                    raise GifTooLargeError(
                        f"GIF exceeds the {MAX_GIF_BYTES // (1024 * 1024)} MiB cap."
                    )
                chunks.append(chunk)
    except GifTooLargeError:
        raise
    except (socket.timeout, TimeoutError) as exc:
        raise GifTimeoutError("timed out downloading the GIF.") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            raise GifTimeoutError("timed out downloading the GIF.") from exc
        raise GifDownloadError("failed to download the GIF.") from exc

    data = b"".join(chunks)
    if data[:6] not in _GIF_MAGIC:
        raise GifInvalidError("response was not a valid GIF (magic bytes absent).")
    return data


# ── Public entry point ────────────────────────────────────────────────────────

def run_change_animation(
    request: ChangeAnimationRequest,
    *,
    app_settings: Settings | None = None,
    territory_resolver: TerritoryResolver | None = None,
) -> AnimatedArtifact:
    """Generate a bounded temporal GIF and return it as a typed artifact."""
    resolver = territory_resolver or territories.get
    cfg = _resolve_territory(request.territory_id, resolver)

    windows = plan_frame_windows(request.start, request.end, request.max_frame_count)
    logger.info(
        "change_animation: start territory=%s product=%s dims=%d fps=%d "
        "planned_frames=%d bbox=%s range=%s..%s",
        cfg.key, request.product.value, request.dimensions,
        request.frames_per_second, len(windows), cfg.bbox_wgs84,
        request.start.isoformat(), request.end.isoformat(),
    )
    t0 = time.monotonic()

    client = get_change_explorer_client(app_settings)
    ee = client.module()
    geometry = bbox_to_ee_rectangle(ee, cfg.bbox_wgs84)

    images: list[Any] = []
    collections: list[Any] = []
    for idx, window in enumerate(windows):
        image, collection = build_frame(
            ee_module=ee,
            geometry=geometry,
            window=window,
            product=request.product,
            max_cloud_pct=request.max_cloud_pct,
            frame_index=idx,
        )
        images.append(image)
        collections.append(collection)

    # One grouped getInfo of all frame scene counts (never one call per frame).
    try:
        counts = scene_counts_expr(ee_module=ee, collections=collections).getInfo()
    except Exception as exc:  # noqa: BLE001 - re-raised as typed, cause chained
        logger.warning("Earth Engine frame scene-count evaluation failed.")
        raise map_ee_exception(exc) from exc

    usable_images: list[Any] = []
    frames_meta: list[AnimationFrameMetadata] = []
    warnings: list[str] = []
    for idx, (window, image, count) in enumerate(zip(windows, images, counts)):
        scene_count = int(count) if count is not None else 0
        warning = None
        if scene_count == 0:
            warning = (
                f"frame {idx} ({window.start.isoformat()}..{window.end.isoformat()}) "
                "omitted: no Sentinel-2 scenes."
            )
            warnings.append(warning)
        else:
            usable_images.append(image)
        frames_meta.append(
            AnimationFrameMetadata(
                frame_index=idx,
                frame_start=window.start.isoformat(),
                frame_end=window.end.isoformat(),
                ee_end_exclusive=window.ee_end_date(),
                scene_count=scene_count,
                product=request.product,
                warning=warning,
            )
        )

    if len(usable_images) < MIN_FRAMES:
        raise InsufficientUsableFramesError(
            f"only {len(usable_images)} frame(s) had Sentinel-2 scenes; at least "
            f"{MIN_FRAMES} are required. Widen the range or raise the cloud threshold."
        )

    video_collection = build_video_collection(ee_module=ee, images=usable_images)
    url = get_video_thumbnail_url(
        image_collection=video_collection,
        region=geometry,
        dimensions=request.dimensions,
        frames_per_second=request.frames_per_second,
    )
    gif_bytes = _fetch_gif_bytes(url)  # URL consumed here; never stored/logged.
    del url

    artifact = AnimatedArtifact(
        territory_id=cfg.key,
        territory_name=cfg.display_name,
        product=request.product,
        dimensions=request.dimensions,
        frames_per_second=request.frames_per_second,
        frame_count=len(usable_images),
        planned_frame_count=len(windows),
        frames=tuple(frames_meta),
        warnings=tuple(warnings),
        byte_size=len(gif_bytes),
        generated_at=datetime.now(timezone.utc),
        request=request,
        gif_bytes=gif_bytes,
    )
    logger.info(
        "change_animation: done territory=%s product=%s usable=%d/%d dims=%d "
        "fps=%d bytes=%d in %.1fs",
        cfg.key, request.product.value, artifact.frame_count,
        artifact.planned_frame_count, request.dimensions,
        request.frames_per_second, artifact.byte_size, time.monotonic() - t0,
    )
    return artifact


# ── Application-facing cached wrapper (only Streamlit touch-point) ────────────

DEFAULT_MAX_FRAME_COUNT = DEFAULT_MAX_FRAMES
DEFAULT_ANIMATION_DIMENSIONS = DEFAULT_VIDEO_DIMENSIONS
DEFAULT_ANIMATION_FPS = DEFAULT_FPS


def _resolve_bbox_for_key(
    request: ChangeAnimationRequest,
) -> tuple[float, float, float, float]:
    return _resolve_territory(request.territory_id, territories.get).bbox_wgs84


try:
    import streamlit as st

    @st.cache_data(ttl=CHANGE_ANIMATION_CACHE_TTL_SECONDS, show_spinner=False)
    def _cached_impl(
        cache_key: tuple[Any, ...], _request: ChangeAnimationRequest
    ) -> AnimatedArtifact:
        # Only `cache_key` (primitive tuple) is hashed by Streamlit; `_request`
        # is leading-underscore so the dataclass is not hashed. The cached value
        # holds the GIF bytes (bounded to 8 MiB); exceptions are never cached.
        return run_change_animation(_request)

    def cached_run_change_animation(
        request: ChangeAnimationRequest,
    ) -> AnimatedArtifact:
        return _cached_impl(request.cache_key(_resolve_bbox_for_key(request)), request)

    def clear_change_animation_cache() -> None:
        """Drop cached GIF artifacts (dev/testing)."""
        _cached_impl.clear()

except ModuleNotFoundError:  # pragma: no cover - streamlit is a declared dep

    def cached_run_change_animation(
        request: ChangeAnimationRequest,
    ) -> AnimatedArtifact:
        return run_change_animation(request)

    def clear_change_animation_cache() -> None:
        return None
