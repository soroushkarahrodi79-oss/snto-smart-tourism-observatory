"""
SNTO — Change-detection analysis core (ADR-015).

Pure, Earth-Engine-object-in / object-out builders for the Visual Change
Explorer: median true-colour & NDVI composites, NDVI difference (dNDVI), and
quality metadata, plus the framework-free typed models. Orchestration, caching,
rendering and UI live elsewhere.
"""
from __future__ import annotations

from src.analysis.change_detection.composites import (
    ndvi_composite,
    true_colour_composite,
)
from src.analysis.change_detection.difference import ndvi_difference
from src.analysis.change_detection.models import (
    CompositeKind,
    CompositeProduct,
    DateWindow,
    QualityMetadata,
    WindowRole,
)
from src.analysis.change_detection.quality import (
    TOTAL_PIXELS_KEY,
    VALID_PIXELS_KEY,
    evaluate_quality,
    mean_scene_cloud_expr,
    pixel_counts_expr,
    scene_count_expr,
)

__all__ = [
    "CompositeKind",
    "CompositeProduct",
    "DateWindow",
    "QualityMetadata",
    "WindowRole",
    "true_colour_composite",
    "ndvi_composite",
    "ndvi_difference",
    "evaluate_quality",
    "scene_count_expr",
    "mean_scene_cloud_expr",
    "pixel_counts_expr",
    "VALID_PIXELS_KEY",
    "TOTAL_PIXELS_KEY",
]
