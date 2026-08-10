"""
SNTO — Plot ↔ satellite support-cell matching for Paper 1 (Phase 3 / B-04)
===========================================================================
Maps a field plot to the *satellite support that produced its value*, per
``docs/paper1/SPATIAL_MATCHING_PROTOCOL.md``. This is the piece the repository
did not have: ``src/ui/services/field_agreement.py`` pairs at **asset** level,
giving every plot in an asset the same satellite value — pseudo-replication
with near-total ties. Paper 1 pairs at **plot ↔ 20 m cell** instead.

Why 20 m and not 10 m
---------------------
NDMI's B11 is natively 20 m; the pipeline *resamples* it to a 10 m grid, which
changes representation, not information. Two adjacent 10 m cells drawing on the
same original 20 m observation are not independent. So the matching support is
a 20 m cell aligned to the native B11 grid in EPSG:25830.

Grid alignment (the silent-failure guard)
------------------------------------------
Sentinel-2 UTM tiles place pixel corners at integer multiples of the band
resolution, and standard tile origins are multiples of far more than 20 m, so a
20 m grid anchored at the EPSG:25830 origin (0, 0) coincides with the true B11
pixel boundaries. ``extract_plot_value`` **verifies** this against the actual
raster transform and raises :class:`GridMisalignment` rather than silently
resampling — CRS/grid mismatch is exactly where this class of code fails
quietly.

Independence rules (SPATIAL_MATCHING_PROTOCOL.md §4)
---------------------------------------------------
* SM-1 impact/control centres ≥ 40 m apart (non-adjacent cells).
* SM-2 no two analysis plots share a cell.
* SM-3 a control plot is ≥ 100 m from *any* mapped trail.
* SM-4 a plot is ≥ 1 cell inside the raster footprint (no edge cells).
* SM-5 plots in the same segment are clustered, not excluded — handled
  statistically downstream, so this module only records ``segment_id``.

Never fabricates: a plot whose support has < 70 % valid pixels raises
:class:`InsufficientCoverage` rather than returning an averaged value over the
masked remainder.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from src.validation.acquisition_manifest import (
    DEFAULT_VALID_PIXEL_MIN_PCT,
    SCL_EXCLUDE_PLOT_EXTRACTION,
)

# Matching support and grid, per SPATIAL_MATCHING_PROTOCOL.md §3.
CELL_SIZE_M = 20.0
GRID_EPSG = 25830                       # UTM 30N — the pipeline's CRS
GRID_ORIGIN = (0.0, 0.0)                # EPSG:25830; S2 tile corners are ≡0 (mod 20)
WGS84_EPSG = 4326

# SM-1 / SM-3 thresholds (SPATIAL_MATCHING_PROTOCOL.md §4).
MIN_PAIR_SEPARATION_M = 2 * CELL_SIZE_M   # 40 m — non-adjacent cells
MIN_CONTROL_TRAIL_CLEARANCE_M = 100.0
EDGE_MARGIN_CELLS = 1                      # SM-4

# Alignment tolerance: a raster origin this far (m) off the grid is a mismatch.
_ALIGN_TOL_M = 0.5


class SpatialMatchError(Exception):
    """Base class for spatial-matching failures."""


class GridMisalignment(SpatialMatchError):
    """The raster grid does not align with the 20 m support grid."""


class CRSMismatch(SpatialMatchError):
    """The raster CRS is not the expected grid CRS (no silent reprojection)."""


class InsufficientCoverage(SpatialMatchError):
    """The plot's support has too few valid pixels to yield a value."""


# ── Coordinate transformers (built once; pyproj is thread-safe to reuse) ────
_TO_GRID = Transformer.from_crs(WGS84_EPSG, GRID_EPSG, always_xy=True)
_TO_WGS84 = Transformer.from_crs(GRID_EPSG, WGS84_EPSG, always_xy=True)


@dataclass(frozen=True)
class SupportCell:
    """One 20 m satellite support cell on the native B11 grid, EPSG:25830.

    ``col``/``row`` index the grid from ``GRID_ORIGIN`` with y increasing
    northward; they are a *stable identity*, deliberately independent of any
    raster's row orientation so the same ground cell has the same id whatever
    scene is later extracted.
    """
    col: int
    row: int
    centre_x: float
    centre_y: float
    cell_size_m: float = CELL_SIZE_M
    epsg: int = GRID_EPSG

    @property
    def cell_id(self) -> str:
        return f"{self.epsg}:{self.cell_size_m:g}:{self.col}:{self.row}"

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(left, bottom, right, top) in EPSG:25830."""
        half = self.cell_size_m / 2.0
        return (self.centre_x - half, self.centre_y - half,
                self.centre_x + half, self.centre_y + half)


def _snap_xy(
    x: float, y: float,
    cell_size: float = CELL_SIZE_M, origin: tuple[float, float] = GRID_ORIGIN,
) -> SupportCell:
    """Snap a projected (EPSG:25830) point to its support cell. Deterministic."""
    ox, oy = origin
    col = math.floor((x - ox) / cell_size)
    row = math.floor((y - oy) / cell_size)
    centre_x = ox + (col + 0.5) * cell_size
    centre_y = oy + (row + 0.5) * cell_size
    return SupportCell(col=col, row=row, centre_x=centre_x, centre_y=centre_y,
                       cell_size_m=cell_size)


def snap_to_support_grid(
    lon: float, lat: float,
    cell_size: float = CELL_SIZE_M, origin: tuple[float, float] = GRID_ORIGIN,
) -> SupportCell:
    """Snap a WGS84 (lon, lat) plot position to its 20 m B11-grid support cell.

    Deterministic: two positions in the same cell return an equal
    :class:`SupportCell` (equal ``cell_id``).
    """
    x, y = _TO_GRID.transform(lon, lat)
    return _snap_xy(x, y, cell_size=cell_size, origin=origin)


def cell_separation_m(a: SupportCell, b: SupportCell) -> float:
    """Euclidean distance (m) between two cell centres in EPSG:25830."""
    return math.hypot(a.centre_x - b.centre_x, a.centre_y - b.centre_y)


# ── SM-1 / SM-2: pair and collision checks ──────────────────────────────────

@dataclass(frozen=True)
class PairIndependence:
    """Result of the SM-1/SM-2 check on one impact/control pair."""
    same_cell: bool          # SM-2 violated within the pair
    separation_m: float
    independent: bool        # SM-1 satisfied (and not same cell)
    reason: str


def check_pair_independence(
    impact: SupportCell, control: SupportCell,
    min_separation_m: float = MIN_PAIR_SEPARATION_M,
) -> PairIndependence:
    """SM-1: impact and control must fall in non-adjacent cells (≥ 40 m apart).

    A pair that shares a cell (SM-2) or is closer than ``min_separation_m`` is
    **not** independent; the caller excludes the whole pair
    (SPATIAL_MATCHING_PROTOCOL.md §4, Contract §L-7).
    """
    same = impact.cell_id == control.cell_id
    sep = cell_separation_m(impact, control)
    if same:
        return PairIndependence(True, sep, False,
                                "impact and control share a support cell (SM-2)")
    if sep < min_separation_m:
        return PairIndependence(
            False, sep, False,
            f"cells adjacent: {sep:.1f} m < {min_separation_m:.0f} m (SM-1)")
    return PairIndependence(False, sep, True, "independent")


def find_cell_collisions(cells: Sequence[SupportCell]) -> list[tuple[int, int]]:
    """SM-2 across the analysis: index pairs (i, j) with i<j sharing a cell.

    The caller excludes the *later* plot of each collision (deterministic:
    keep the earlier index), never silently averaging two plots in one cell.
    """
    seen: dict[str, int] = {}
    collisions: list[tuple[int, int]] = []
    for j, c in enumerate(cells):
        first = seen.get(c.cell_id)
        if first is None:
            seen[c.cell_id] = j
        else:
            collisions.append((first, j))
    return collisions


# ── SM-3: control plot clearance from the trail network ─────────────────────

def load_trail_network_utm(geojson_path: str | Path) -> list:
    """Load a trail FeatureCollection (EPSG:4326) reprojected to EPSG:25830.

    Returns shapely geometries in the grid CRS. Uses json + shapely + pyproj
    (no geopandas) to keep this a light dependency for a validation utility.
    """
    data = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    geoms = []
    for feat in data.get("features", []):
        geom = feat.get("geometry")
        if geom is None:
            continue
        geoms.append(shapely_transform(_TO_GRID.transform, shape(geom)))
    return geoms


def control_trail_clearance_m(
    lon: float, lat: float, trails_utm: Sequence,
) -> float:
    """Minimum distance (m) from a control plot to *any* trail in the network.

    ``trails_utm`` are geometries already in EPSG:25830 (see
    :func:`load_trail_network_utm`). Returns ``inf`` for an empty network.
    """
    if not trails_utm:
        return math.inf
    from shapely.geometry import Point
    x, y = _TO_GRID.transform(lon, lat)
    p = Point(x, y)
    return min(p.distance(g) for g in trails_utm)


def control_clearance_ok(
    lon: float, lat: float, trails_utm: Sequence,
    min_clearance_m: float = MIN_CONTROL_TRAIL_CLEARANCE_M,
) -> bool:
    """SM-3: True when a control plot is ≥ 100 m from every mapped trail."""
    return control_trail_clearance_m(lon, lat, trails_utm) >= min_clearance_m


# ── SM-4: edge-of-footprint check ───────────────────────────────────────────

def cell_inside_footprint(
    cell: SupportCell, raster_bounds: tuple[float, float, float, float],
    margin_cells: int = EDGE_MARGIN_CELLS,
) -> bool:
    """SM-4: True when the cell is ≥ ``margin_cells`` inside the raster bounds.

    ``raster_bounds`` is (left, bottom, right, top) in EPSG:25830. Edge cells
    are excluded because resampling artefacts contaminate the footprint margin.
    """
    left, bottom, right, top = raster_bounds
    m = margin_cells * cell.cell_size_m
    cl, cb, cr, ct = cell.bounds
    return (cl - m >= left and cb - m >= bottom
            and cr + m <= right and ct + m <= top)


# ── Extraction against a real composite ─────────────────────────────────────

@dataclass(frozen=True)
class PlotExtraction:
    """Per-plot satellite values + full provenance (SATELLITE_FIELD_MATCHING_PLAN.md §3).

    ``ehs`` is ``None`` here: EHS needs the scene-level P90/P10 baselines, which
    live with the composite processing, not with one plot. Compose it downstream
    via :func:`plot_stress_from_baselines` so the operational EHS formula is
    reused, never forked.
    """
    plot_id: str
    cell_id: str
    cell_centre_x: float
    cell_centre_y: float
    gps_to_cell_centre_m: float
    ndvi: Optional[float]
    ndmi: Optional[float]
    valid_pixel_fraction: float
    scl_classes_present: tuple[int, ...]
    scene_ids: tuple[str, ...]
    ehs: Optional[float] = None


def _require_grid_aligned(transform, crs_epsg: Optional[int]) -> None:
    """Raise unless the raster is in the grid CRS and its origin lies on the
    20 m support grid. This is the loud version of the silent CRS failure."""
    if crs_epsg is not None and int(crs_epsg) != GRID_EPSG:
        raise CRSMismatch(
            f"raster CRS EPSG:{crs_epsg} != grid EPSG:{GRID_EPSG} "
            "(no silent reprojection in Paper-1 extraction)")
    ox, oy = GRID_ORIGIN
    off_x = abs(((transform.c - ox) / CELL_SIZE_M) % 1.0)
    off_y = abs(((transform.f - oy) / CELL_SIZE_M) % 1.0)
    # normalise the modulo to the nearest boundary (….0 or ….999 both ≈ aligned)
    off_x = min(off_x, 1.0 - off_x) * CELL_SIZE_M
    off_y = min(off_y, 1.0 - off_y) * CELL_SIZE_M
    if off_x > _ALIGN_TOL_M or off_y > _ALIGN_TOL_M:
        raise GridMisalignment(
            f"raster origin ({transform.c}, {transform.f}) is {off_x:.2f}/"
            f"{off_y:.2f} m off the {CELL_SIZE_M:g} m support grid")


def _cell_pixel_window(cell: SupportCell, transform) -> tuple[int, int, int, int]:
    """(row0, col0, nrows, ncols) covering the cell in a north-up raster."""
    px = abs(transform.a)
    py = abs(transform.e)
    left, bottom, right, top = cell.bounds
    col0 = round((left - transform.c) / px)
    row0 = round((transform.f - top) / py)
    ncols = max(1, round(cell.cell_size_m / px))
    nrows = max(1, round(cell.cell_size_m / py))
    return row0, col0, nrows, ncols


def extract_plot_value(
    plot_id: str, lon: float, lat: float,
    ndvi_ndmi_raster,
    scene_ids: Sequence[str],
    scl_raster=None,
    scl_exclude: Sequence[int] = SCL_EXCLUDE_PLOT_EXTRACTION,
    min_valid_fraction: float = DEFAULT_VALID_PIXEL_MIN_PCT / 100.0,
    cell: Optional[SupportCell] = None,
) -> PlotExtraction:
    """Extract NDVI/NDMI + provenance for one plot from an open composite.

    ``ndvi_ndmi_raster`` is an open rasterio dataset with band 1 = NDVI and
    band 2 = NDMI (the ``prepare_raster.py`` layout), in EPSG:25830 aligned to
    the support grid. ``scl_raster`` is an optional open single-band SCL dataset
    over the same area.

    Raises :class:`GridMisalignment`/:class:`CRSMismatch` if the raster is not
    grid-aligned, and :class:`InsufficientCoverage` if the valid-pixel fraction
    is below ``min_valid_fraction`` — never an averaged value over a mostly
    masked cell.
    """
    import numpy as np

    crs_epsg = ndvi_ndmi_raster.crs.to_epsg() if ndvi_ndmi_raster.crs else None
    _require_grid_aligned(ndvi_ndmi_raster.transform, crs_epsg)

    if cell is None:
        cell = snap_to_support_grid(lon, lat)

    x, y = _TO_GRID.transform(lon, lat)
    gps_to_centre = math.hypot(x - cell.centre_x, y - cell.centre_y)

    row0, col0, nrows, ncols = _cell_pixel_window(cell, ndvi_ndmi_raster.transform)
    from rasterio.windows import Window
    win = Window(col0, row0, ncols, nrows)

    ndvi = ndvi_ndmi_raster.read(1, window=win).astype("float64")
    ndmi = ndvi_ndmi_raster.read(2, window=win).astype("float64")
    nodata = ndvi_ndmi_raster.nodata

    valid = np.isfinite(ndvi)
    if nodata is not None:
        valid &= (ndvi != nodata)

    scl_present: tuple[int, ...] = ()
    if scl_raster is not None:
        scl = _read_aligned_scl(scl_raster, cell, ndvi.shape)
        scl_present = tuple(sorted({int(v) for v in np.unique(scl)}))
        excluded = np.isin(scl, list(scl_exclude))
        valid &= ~excluded

    total = ndvi.size
    frac = float(valid.sum()) / float(total) if total else 0.0
    if frac < min_valid_fraction:
        raise InsufficientCoverage(
            f"plot {plot_id}: valid-pixel fraction {frac:.2f} < "
            f"{min_valid_fraction:.2f} at cell {cell.cell_id}")

    ndvi_mean = float(np.nanmean(np.where(valid, ndvi, np.nan)))
    ndmi_mean = float(np.nanmean(np.where(valid, ndmi, np.nan)))

    return PlotExtraction(
        plot_id=plot_id,
        cell_id=cell.cell_id,
        cell_centre_x=cell.centre_x,
        cell_centre_y=cell.centre_y,
        gps_to_cell_centre_m=round(gps_to_centre, 3),
        ndvi=round(ndvi_mean, 6),
        ndmi=round(ndmi_mean, 6),
        valid_pixel_fraction=round(frac, 4),
        scl_classes_present=scl_present,
        scene_ids=tuple(scene_ids),
    )


def _read_aligned_scl(scl_raster, cell: SupportCell, target_shape):
    """Read the SCL raster over the cell, resampled to ``target_shape`` so it
    aligns with the NDVI window. SCL is natively 20 m; nearest-neighbour
    preserves class labels (never interpolate class codes)."""
    import numpy as np
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    left, bottom, right, top = cell.bounds
    win = from_bounds(left, bottom, right, top, scl_raster.transform)
    arr = scl_raster.read(
        1, window=win, out_shape=target_shape,
        resampling=Resampling.nearest, boundless=True, fill_value=0,
    )
    return arr.astype(np.int16)


def plot_stress_from_baselines(
    ndvi: Optional[float], ndmi: Optional[float],
    ndvi_baseline: float, ndvi_floor: float,
    ndmi_baseline: float, ndmi_floor: float,
) -> Optional[float]:
    """Plot-level satellite stress (0–100) using the **operational** EHS formula.

    Lazily imports ``calculate_delta_ehs._trail_stress_score`` so the exact
    shipped formula (per-scene deficit, dense-canopy reweighting) is reused,
    never reimplemented — and so this module does not drag in the ETL script's
    DB/geopandas dependencies unless EHS is actually composed. The baselines
    are the scene-level P90/P10 percentiles the caller holds from composite
    processing; this module has no scene context of its own and will not invent
    them.
    """
    from calculate_delta_ehs import _trail_stress_score

    return _trail_stress_score(
        ndvi, ndmi, ndvi_baseline, ndvi_floor, ndmi_baseline, ndmi_floor,
    )
