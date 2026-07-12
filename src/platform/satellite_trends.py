"""
SNTO — Real Satellite Trend Loader (v1.1.0, corrected v1.1.1)
===============================================================
Loads the Mann-Kendall trend analysis computed from REAL Sentinel-2 imagery
(2021–2026, GEE export) and turns it into dashboard-ready structures.

Unlike the simulated monthly series rendered by ``charts.build_time_series_chart``,
this module surfaces the *empirical* multi-year trend per asset:
  * NDVI Mann-Kendall direction + significance (τ, p), computed on the
    harmonically **deseasonalized**, tie-corrected series (v1.1.1) — not the
    raw monthly series used in v1.1.0,
  * Sen's slope with its 95% non-parametric confidence interval (Gilbert 1987),
  * annual mean NDVI (drought signal: 2022 collapse, 2023 recovery),
  * worst / best year and the overall NDVI range.

Pipeline producing the input JSON::

    build_pnsg_assets.py        → clean_assets/pnsg_assets.geojson
    gee_code_editor_pnsg.js     → pnsg_gee_timeseries_2021_2025.csv  (real S2)
    run_timeseries_analysis.py  → analysis/mk_trends_pnsg.json       (this input)

Pure logic (no Streamlit) so it stays unit-testable and reusable.

Runtime memory profile (v1.1.0)
-------------------------------
The dashboard's Tab 6 ("Evolución Temporal") runtime footprint is small: this
module parses a ~15 KB JSON (21 assets) into frozen dataclasses — on the order of
hundreds of KB resident, bounded by ``tests/unit/test_satellite_trends.py``
(``test_loader_memory_bounded``, <25 MB peak). It does **not** read rasters or the
265 KB monthly CSV at request time. The genuinely heavy paths are OFFLINE and out
of the serving process:
  * ``scripts/run_timeseries_analysis.py`` (consumes the GEE CSV → this JSON),
  * Tab 2's 900 MB ``spring/summer_raster.tif`` map layers.
In ``app.py`` the loader is wrapped by ``_cached_trends`` (``@st.cache_data``) so
the JSON parse happens once per session, not on every widget rerun.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_ANALYSIS_DIR = _ROOT / "clean_assets" / "timeseries" / "analysis"

# The baseline (validated) park. Loaders default to it so every existing
# no-argument caller keeps resolving ``mk_trends_pnsg.json`` unchanged.
DEFAULT_PARK = "pnsg"

# Human-readable park names for the dashboard selector (v1.2.0 OAPN network).
# Keys are the ``<park>`` slug used in ``mk_trends_<park>.json`` / GEE templates.
PARK_LABELS: dict[str, str] = {
    "pnsg": "Sierra de Guadarrama (PNSG)",
    "pn_aiguestortes": "Aigüestortes i Estany de Sant Maurici",
    "pn_cabaneros": "Cabañeros",
    "pn_cabrera": "Archipiélago de Cabrera",
    "pn_donana": "Doñana",
    "pn_garajonay": "Garajonay",
    "pn_islas_atlanticas": "Islas Atlánticas de Galicia",
    "pn_monfrague": "Monfragüe",
    "pn_ordesa": "Ordesa y Monte Perdido",
    "pn_picos_europa": "Picos de Europa",
    "pn_sierra_nevada": "Sierra Nevada",
    "pn_sierra_nieves": "Sierra de las Nieves",
    "pn_tablas_daimiel": "Tablas de Daimiel",
    "pn_taburiente": "Caldera de Taburiente",
    "pn_teide": "Teide",
    "pn_timanfaya": "Timanfaya",
}

# Significance threshold (matches run_timeseries_analysis.py)
_P_SIGNIFICANT = 0.05


def _trends_json_for(park: str) -> Path:
    """Resolve the Mann-Kendall JSON path for a given park slug."""
    return _ANALYSIS_DIR / f"mk_trends_{park}.json"


def park_label(park: str) -> str:
    """Human-readable name for a park slug (falls back to the slug itself)."""
    return PARK_LABELS.get(park, park)


def available_parks() -> list[str]:
    """Parks that have a computed ``mk_trends_<park>.json``, PNSG first.

    Lets the dashboard build its park selector dynamically: a pilot park
    (Tablas, Monfragüe) appears only once its analysis JSON exists, so the UI
    never offers a park without real data.
    """
    if not _ANALYSIS_DIR.exists():
        return []
    parks = [
        p.stem[len("mk_trends_"):]
        for p in _ANALYSIS_DIR.glob("mk_trends_*.json")
    ]
    # Baseline park first, then the rest alphabetically (stable UI order).
    parks.sort(key=lambda k: (k != DEFAULT_PARK, k))
    return parks

# Human-readable Spanish trend labels (UI-neutral wording)
_TREND_ES: dict[str, str] = {
    "increasing": "↗ mejora",
    "decreasing": "↘ degradación",
    "no trend": "→ estable",
    "insufficient data": "· sin datos suficientes",
}


@dataclass(frozen=True)
class AssetTrend:
    """One asset's empirical multi-year NDVI trend (real Sentinel-2)."""

    asset_id: str
    category: str
    n_observations: int
    tau: float
    p_value: float
    trend: str                       # 'increasing' | 'decreasing' | 'no trend'
    annual_mean_ndvi: dict[str, float]
    partial_years: list[str]         # años sin temporada completa (fuera del ranking)
    worst_year: str | None
    best_year: str | None
    ndvi_min: float | None
    ndvi_max: float | None
    sens_slope: float | None = None          # NDVI units/month (Sen's slope)
    sens_slope_ci: tuple[float, float] | None = None  # 95% CI (Gilbert 1987)
    deseasonalised: bool = False             # harmonic decomposition applied (v1.1.1)
    method: str = "raw+mann_kendall"         # provenance string from the pipeline

    @property
    def significant(self) -> bool:
        return self.p_value < _P_SIGNIFICANT

    @property
    def trend_es(self) -> str:
        return _TREND_ES.get(self.trend, "→ estable")

    @property
    def is_alert(self) -> bool:
        """Significant degradation → field-inspection candidate."""
        return self.trend == "decreasing" and self.significant


@dataclass(frozen=True)
class TrendSummary:
    """Portfolio-level roll-up of the real satellite trends."""

    available: bool
    assets: list[AssetTrend] = field(default_factory=list)
    n_degrading: int = 0
    n_improving: int = 0
    n_stable: int = 0
    worst_year_global: str | None = None   # most frequent 'worst year' across assets
    # años parciales (p. ej. el año en curso, sin temporada completa)
    partial_years: list[str] = field(default_factory=list)

    @property
    def alerts(self) -> list[AssetTrend]:
        return [a for a in self.assets if a.is_alert]


def _category_from_id(asset_id: str) -> str:
    # 'pnsg_escalada_penalara' → 'escalada'
    parts = asset_id.split("_")
    return parts[1] if len(parts) > 1 else "otro"


def _resolve_category(asset_id: str, rec: dict) -> str:
    """Category of an asset, preferring the explicit ``category`` field.

    PNSG (v1.1.0) has no ``category`` in its JSON, so we fall back to parsing
    the id (``pnsg_<cat>_<slug>``). OAPN ids (v1.2.0) are multi-token
    (``pn_tablas_daimiel_senderismo_<slug>_<idx>``) where positional parsing
    breaks, so the pipeline persists an explicit ``category`` column that we use
    verbatim when present.
    """
    explicit = rec.get("category")
    if explicit:
        return str(explicit)
    return _category_from_id(asset_id)


def load_asset_trends(
    path: Path | None = None, park: str = DEFAULT_PARK
) -> list[AssetTrend]:
    """Parse the Mann-Kendall JSON into AssetTrend records (empty if missing).

    ``path`` wins when given (used by tests); otherwise the JSON is resolved
    from ``park`` → ``mk_trends_<park>.json``.
    """
    src = path or _trends_json_for(park)
    if not src.exists():
        return []

    raw = json.loads(src.read_text(encoding="utf-8"))
    trends: list[AssetTrend] = []
    for asset_id, rec in raw.items():
        mk = rec.get("mann_kendall_ndvi", {})
        rng = rec.get("ndvi_range", {})
        trends.append(AssetTrend(
            asset_id=asset_id,
            category=_resolve_category(asset_id, rec),
            n_observations=int(rec.get("n_observations", 0)),
            tau=float(mk.get("tau", 0.0)),
            p_value=float(mk.get("p_approx", 1.0)),
            trend=str(mk.get("trend", "no trend")),
            annual_mean_ndvi={
                str(k): float(v)
                for k, v in rec.get("annual_mean_ndvi", {}).items()
            },
            partial_years=[str(y) for y in rec.get("partial_years", [])],
            worst_year=rec.get("worst_ndvi_year"),
            best_year=rec.get("best_ndvi_year"),
            ndvi_min=rng.get("min"),
            ndvi_max=rng.get("max"),
            sens_slope=mk.get("sens_slope"),
            sens_slope_ci=(
                tuple(mk["sens_slope_ci"]) if mk.get("sens_slope_ci") else None
            ),
            deseasonalised=bool(mk.get("deseasonalised", False)),
            method=str(mk.get("method", "raw+mann_kendall")),
        ))
    return trends


def summarize_trends(
    path: Path | None = None, park: str = DEFAULT_PARK
) -> TrendSummary:
    """Build the portfolio roll-up consumed by the dashboard."""
    assets = load_asset_trends(path, park=park)
    if not assets:
        return TrendSummary(available=False)

    n_deg = sum(1 for a in assets if a.trend == "decreasing" and a.significant)
    n_imp = sum(1 for a in assets if a.trend == "increasing" and a.significant)
    n_sta = len(assets) - n_deg - n_imp

    # Most frequently 'worst' year — exposes the dominant drought signal (2022).
    worst_counts: dict[str, int] = {}
    for a in assets:
        if a.worst_year:
            worst_counts[a.worst_year] = worst_counts.get(a.worst_year, 0) + 1
    worst_global = max(worst_counts, key=worst_counts.get) if worst_counts else None

    # Most urgent first: degradation alerts, then by ascending p-value.
    assets_sorted = sorted(assets, key=lambda a: (not a.is_alert, a.p_value))

    # partial_years es global (idéntico en todos los assets); tomar del primero
    partial = assets[0].partial_years if assets else []

    return TrendSummary(
        available=True,
        assets=assets_sorted,
        n_degrading=n_deg,
        n_improving=n_imp,
        n_stable=n_sta,
        worst_year_global=worst_global,
        partial_years=partial,
    )


def find_trend(asset_name_or_id: str, assets: list[AssetTrend]) -> AssetTrend | None:
    """Best-effort match of a dashboard asset to its real-trend record.

    Matching is fuzzy because dashboard asset names ("Peñalara") differ from
    GEE asset_ids ("pnsg_escalada_penalara"). We normalise both to ascii-lower
    tokens and require the dashboard name tokens to appear in the asset_id.
    """
    import unicodedata

    def norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return s.lower()

    needle = norm(asset_name_or_id)
    needle_tokens = [t for t in needle.replace("-", " ").split() if len(t) > 3]
    if not needle_tokens:
        return None

    for a in assets:
        hay = a.asset_id.lower()
        if all(tok in hay for tok in needle_tokens):
            return a
    return None
