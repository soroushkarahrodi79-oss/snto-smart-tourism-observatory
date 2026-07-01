"""
SNTO — Pipeline A: Multi-Year Time Series Analysis (GEE Edition)
================================================================
Primary territory: Parque Nacional Sierra de Guadarrama (PNSG). Territory is
selectable via --territory from the registry (src/config/territories.py).

Fetches the territory's reference series (PNSG: monthly 2021–2026, see
src/temporal/series_spec.py) via Google Earth Engine for each hiking trail,
runs the Mann-Kendall trend test on NDVI / NDMI / EVI gated by the temporal
validity tier (src/temporal/trend_gate.py), computes the Environmental Health
Score (EHS) with the dense-canopy adaptive weight rule, and writes per-trail
results plus a provenance manifest (src/temporal/manifest.py) to CSV and JSON.

This script is the TEMPORAL counterpart of run_pipeline_a_filemode.py (which
computes EHS from two seasonal raster snapshots).  Both modes are valid; this
one is preferred for scientific reporting because it uses 5 years of monthly
observations and produces statistically rigorous trend significance.

Prerequisites:
  1. pip install earthengine-api
  2. earthengine authenticate        (first time on this machine)
  3. Set GEE_PROJECT env var, or pass --project on the command line.

Usage:
  python run_pipeline_a_timeseries.py
  python run_pipeline_a_timeseries.py --project my-gee-project
  python run_pipeline_a_timeseries.py --years 2022 2023 2024
  python run_pipeline_a_timeseries.py --dry-run    # offline, uses mock data

Inputs  : data/raw_assets/vector_data/<territory trails>.geojson
Outputs : data/outputs/<territory>/pipeline_a_ts_results.csv
          data/outputs/<territory>/pipeline_a_ts_summary.json
          data/outputs/<territory>/pipeline_a_ts_manifest.json
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import statistics
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import geopandas as gpd
from shapely.ops import linemerge, unary_union

from src.assets.models import (
    AssetObservation, AssetType, GeoJSONGeometry, GeometryType, TourismAsset,
)
from src.config import territories
from src.config.logging_setup import configure_logging
from src.config.run_context import capture as capture_run_context
from src.features.spectral import extract_spectral_features
from src.risk_engine.ehs import EHSComponents, compute_ehs, interpret_ehs
from src.temporal import (
    PNSG_5Y, assess_trend_readiness, build_manifest_from_observations,
    spec_for_territory,
)
from src.time_series.confidence import block_bootstrap_ci
from src.time_series.mann_kendall import (
    MannKendallResult, classify_trend_severity, mann_kendall_test,
)

configure_logging()
logger = logging.getLogger("pipeline_a_ts")

SEP = "=" * 72
DIV = "-" * 72

_VECTOR_DIR = _ROOT / "data" / "raw_assets" / "vector_data"
_OUTDIR_ROOT = _ROOT / "data" / "outputs"

DEFAULT_TERRITORY = "pnsg"                 # territorio principal del observatorio
DEFAULT_YEARS = PNSG_5Y.years()            # 2021 … 2026 (serie de referencia)


# ── Trail loading ──────────────────────────────────────────────────────────────

def load_trails(path: Path) -> gpd.GeoDataFrame:
    """Load hiking trails from GeoJSON and dissolve to one geometry per name."""
    gdf = gpd.read_file(path)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    merged: list[dict] = []
    for name, grp in gdf.groupby("name"):
        geom = unary_union(list(grp.geometry.values))
        try:
            geom = linemerge(geom)
        except Exception:
            pass
        merged.append({"name": name, "geometry": geom})
    out = gpd.GeoDataFrame(merged, crs="EPSG:4326")
    out.insert(0, "id", range(1, len(out) + 1))
    return out


def _gdf_row_to_asset(row, region: str) -> TourismAsset:
    """Convert a GeoDataFrame row (LineString geometry) to a TourismAsset."""
    geom = row.geometry
    # GeoJSON LineString coordinates are [[lon, lat], ...]
    coords = list(geom.coords)
    return TourismAsset(
        asset_id=str(row.id),
        name=str(row.name),
        asset_type=AssetType.TRAIL,
        geometry=GeoJSONGeometry(
            type=GeometryType.LINESTRING,
            coordinates=[[c[0], c[1]] for c in coords],
        ),
        region=region,
        country="Spain",
    )


# ── Mock fallback for --dry-run ────────────────────────────────────────────────

def _mock_observations(asset_id: str, years: list[int]) -> list[AssetObservation]:
    """Generate synthetic monthly observations (no GEE needed) for --dry-run."""
    import math, random
    rng = random.Random(hash(asset_id) & 0xFFFF)
    obs = []
    base_ndvi = rng.uniform(0.30, 0.65)
    base_ndmi = rng.uniform(0.05, 0.30)
    base_evi  = rng.uniform(0.20, 0.45)
    # Introduce a slight declining trend (0.001 NDVI/month) for realism
    for yr_idx, year in enumerate(sorted(years)):
        for month in range(1, 13):
            t = yr_idx * 12 + (month - 1)
            seasonal = 0.12 * math.sin(2 * math.pi * (month - 4) / 12)
            noise = rng.gauss(0, 0.02)
            trend = -0.0008 * t
            ndvi = max(0.0, min(1.0, base_ndvi + seasonal + noise + trend))
            ndmi = max(-1.0, min(1.0, base_ndmi + 0.5 * seasonal + rng.gauss(0, 0.01)))
            evi  = max(0.0, min(1.0, base_evi  + 0.8 * seasonal + rng.gauss(0, 0.015) + 0.5 * trend))
            obs.append(AssetObservation(
                asset_id=asset_id, year=year, month=month,
                ndvi=round(ndvi, 4), ndmi=round(ndmi, 4), evi=round(evi, 4),
                cloud_cover_pct=0.0, data_source="mock:dry-run",
            ))
    return obs


# ── Per-trail analysis ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _EHSBundle:
    """EHS plus the intermediate inputs the caller reports alongside it."""

    components: EHSComponents
    mk_ndvi: MannKendallResult
    mean_ndvi: float
    mean_ndmi: float
    mean_evi: float | None
    n_anomalous: int


def _count_severe_anomalies(ndvi_series: list[float]) -> int:
    """Months with |z-score| >= 1.5 relative to the series mean/std."""
    try:
        mean = statistics.mean(ndvi_series)
        std = statistics.stdev(ndvi_series)
    except statistics.StatisticsError:
        return 0
    if std <= 0:
        return 0
    return sum(1 for v in ndvi_series if abs(v - mean) / std >= 1.5)


def _ehs_from_observations(observations: list[AssetObservation]) -> _EHSBundle:
    """Compute the EHS (and the inputs feeding it) from an observation list.

    Single source of truth shared by the point estimate and the bootstrap, so
    the confidence interval is centred on the very computation it quantifies.
    Bootstrapping over whole observations (not bare NDVI values) keeps the
    NDVI / NDMI / EVI channels of each month aligned in every resample.
    """
    ndvi_series = [o.ndvi for o in observations]
    features = extract_spectral_features(observations)
    mk_ndvi = mann_kendall_test(ndvi_series)
    n_anomalous = _count_severe_anomalies(ndvi_series)
    residual_std = (
        float(statistics.stdev(ndvi_series)) if len(ndvi_series) > 1 else 0.0
    )
    components = compute_ehs(
        mean_ndvi=features.mean_ndvi,
        mk_result=mk_ndvi,
        n_anomalous_months=n_anomalous,
        n_total_months=len(observations),
        residual_std=residual_std,
        mean_evi=features.mean_evi,
    )
    return _EHSBundle(
        components=components,
        mk_ndvi=mk_ndvi,
        mean_ndvi=features.mean_ndvi,
        mean_ndmi=features.mean_ndmi,
        mean_evi=features.mean_evi,
        n_anomalous=n_anomalous,
    )


def analyse_trail(
    asset: TourismAsset,
    observations: list[AssetObservation],
    ehs_bootstrap: int = 0,
) -> dict:
    """Run MK test + EHS for one trail given its full observation list.

    When ``ehs_bootstrap`` > 0, attach a 95 % moving-block bootstrap confidence
    interval for the EHS (reproducible: the RNG is seeded from the asset id).
    """
    gate = assess_trend_readiness(len(observations))
    if not gate.mann_kendall_justified:
        return {
            "asset_id": asset.asset_id,
            "name": asset.name,
            "n_obs": len(observations),
            "trend_readiness": gate.readiness.value,
            "mann_kendall_justified": gate.mann_kendall_justified,
            "error": "insufficient_observations",
        }

    mk_ndmi = mann_kendall_test([o.ndmi for o in observations])

    bundle = _ehs_from_observations(observations)
    mk_ndvi = bundle.mk_ndvi
    ehs_components = bundle.components
    trend_label = classify_trend_severity(mk_ndvi)

    # EHS uncertainty band (optional; the heavy MK re-computation runs n_boot×).
    ehs_ci_low = ehs_ci_high = ehs_ci_width = None
    if ehs_bootstrap > 0 and len(observations) >= 4:
        ci = block_bootstrap_ci(
            observations,
            lambda obs: _ehs_from_observations(obs).components.ehs,
            n_boot=ehs_bootstrap,
            alpha=0.05,
            seed=zlib.crc32(asset.asset_id.encode("utf-8")),
        )
        ehs_ci_low = round(ci.lower, 1)
        ehs_ci_high = round(ci.upper, 1)
        ehs_ci_width = round(ci.upper - ci.lower, 1)

    return {
        "asset_id": asset.asset_id,
        "name": asset.name,
        "n_obs": len(observations),
        "years_covered": f"{observations[0].year}–{observations[-1].year}",
        "mean_ndvi": round(bundle.mean_ndvi, 4),
        "mean_ndmi": round(bundle.mean_ndmi, 4),
        "mean_evi": round(bundle.mean_evi, 4) if bundle.mean_evi is not None else None,
        # Mann-Kendall NDVI
        "mk_ndvi_direction": mk_ndvi.trend_direction,
        "mk_ndvi_slope": mk_ndvi.sens_slope,
        "mk_ndvi_p": mk_ndvi.p_value,
        "mk_ndvi_significant": mk_ndvi.is_significant,
        "mk_ndvi_tau": mk_ndvi.kendalls_tau,
        # Mann-Kendall NDMI
        "mk_ndmi_direction": mk_ndmi.trend_direction,
        "mk_ndmi_slope": mk_ndmi.sens_slope,
        "mk_ndmi_p": mk_ndmi.p_value,
        "mk_ndmi_significant": mk_ndmi.is_significant,
        # EHS
        "ehs": ehs_components.ehs,
        "ehs_label": interpret_ehs(ehs_components.ehs),
        "ehs_ci_low": ehs_ci_low,
        "ehs_ci_high": ehs_ci_high,
        "ehs_ci_width": ehs_ci_width,
        "ehs_baseline_risk": ehs_components.baseline_risk,
        "ehs_trend_risk": ehs_components.trend_risk,
        "ehs_anomaly_risk": ehs_components.anomaly_risk,
        "ehs_is_dense_canopy": ehs_components.is_dense_canopy,
        "trend_severity": trend_label,
        "trend_readiness": gate.readiness.value,
        "mann_kendall_justified": gate.mann_kendall_justified,
        "n_anomalous_months": bundle.n_anomalous,
        "data_source": observations[0].data_source,
        "error": None,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="SNTO Pipeline A — multi-year time series via GEE"
    )
    parser.add_argument(
        "--territory", default=DEFAULT_TERRITORY,
        help=f"Territory key from the registry (default: {DEFAULT_TERRITORY}). "
             f"Available: {', '.join(territories.list_keys())}",
    )
    parser.add_argument(
        "--project", default=os.environ.get("GEE_PROJECT", ""),
        help="Google Earth Engine project ID (or set GEE_PROJECT env var)",
    )
    parser.add_argument(
        "--years", nargs="+", type=int, default=DEFAULT_YEARS,
        metavar="YEAR",
        help=f"Calendar years to include (default: {DEFAULT_YEARS[0]}–{DEFAULT_YEARS[-1]})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Use synthetic mock data instead of GEE (for offline testing)",
    )
    parser.add_argument(
        "--ehs-bootstrap", type=int, default=300, metavar="N",
        help="Nº de réplicas bootstrap de bloques para el IC 95%% del EHS "
             "(0 para desactivar; por defecto 300).",
    )
    parser.add_argument(
        "--key-file", default="",
        help="Path to GEE service-account JSON key (optional; uses personal auth if omitted)",
    )
    args = parser.parse_args(argv)

    try:
        terr = territories.get(args.territory)
    except KeyError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    spec = spec_for_territory(args.territory, min(args.years), max(args.years))
    trails_path = _VECTOR_DIR / terr.trails_geojson
    outdir = _OUTDIR_ROOT / args.territory

    print(SEP)
    print("  SNTO — Pipeline A: Multi-Year Time Series (GEE Edition)")
    print(f"  Territory : {terr.display_name}")
    print(f"  Series    : {spec.label()} · {spec.cadence.value} · tile {spec.s2_tile}")
    print(f"  Years     : {args.years}")
    if args.dry_run:
        print("  Mode      : DRY-RUN (synthetic mock data — no GEE connection)")
    else:
        print(f"  GEE project : {args.project or '(personal auth)'}")
    print(SEP)
    print()

    # ── Load trails ───────────────────────────────────────────────────────────
    if not trails_path.exists():
        logger.error("Trails GeoJSON not found: %s", trails_path)
        sys.exit(1)

    trails = load_trails(trails_path)
    logger.info("Loaded %d trails (dissolved by name)", len(trails))

    # ── Initialise adapter ────────────────────────────────────────────────────
    if args.dry_run:
        adapter = None
    else:
        if not args.project:
            logger.error(
                "GEE project ID required. Set GEE_PROJECT env var or pass --project."
            )
            sys.exit(1)
        from src.ingestion.gee_adapter import GEEAdapter
        adapter = GEEAdapter(project_id=args.project, key_file=args.key_file)

    # ── Process each trail ────────────────────────────────────────────────────
    outdir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    all_observations: list[AssetObservation] = []   # union for the series manifest
    n_trails = len(trails)

    for i, row in enumerate(trails.itertuples(), 1):
        name = str(row.name)
        asset_id = str(row.id)
        logger.info("[%d/%d] Processing: %s", i, n_trails, name)

        # Simplify MultiLineString to LineString for GEE compatibility
        geom = row.geometry
        if geom.geom_type == "MultiLineString":
            geom = max(geom.geoms, key=lambda g: g.length)

        # Rebuild row with simplified geometry for _gdf_row_to_asset
        from types import SimpleNamespace
        simple_row = SimpleNamespace(id=asset_id, name=name, geometry=geom)

        try:
            asset = _gdf_row_to_asset(simple_row, region=terr.display_name)
        except Exception as exc:
            logger.warning("Skipping '%s' (geometry conversion failed): %s", name, exc)
            continue

        try:
            if args.dry_run:
                observations = _mock_observations(asset_id, args.years)
            else:
                observations = adapter.fetch_multiyear_time_series(asset, args.years)
        except Exception as exc:
            logger.error("GEE fetch failed for '%s': %s", name, exc)
            results.append({
                "asset_id": asset_id, "name": name,
                "n_obs": 0, "error": str(exc),
            })
            continue

        all_observations.extend(observations)
        result = analyse_trail(asset, observations, ehs_bootstrap=args.ehs_bootstrap)
        results.append(result)
        ci_low, ci_high = result.get("ehs_ci_low"), result.get("ehs_ci_high")
        ci_str = f" [IC95 {ci_low}–{ci_high}]" if ci_low is not None else ""
        logger.info(
            "  EHS=%.1f%s (%s)  NDVI trend=%s (p=%.3f)  dense_canopy=%s",
            result.get("ehs", float("nan")),
            ci_str,
            result.get("ehs_label", "?"),
            result.get("mk_ndvi_direction", "?"),
            result.get("mk_ndvi_p", 1.0),
            result.get("ehs_is_dense_canopy", False),
        )

    if not results:
        logger.error("No results produced. Check trails GeoJSON and GEE connectivity.")
        sys.exit(1)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    csv_path = outdir / "pipeline_a_ts_results.csv"
    all_keys = list(results[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    # ── Compute summary ────────────────────────────────────────────────────────
    valid = [r for r in results if r.get("error") is None]
    ehs_vals = [r["ehs"] for r in valid if r.get("ehs") is not None]
    degrading = [r for r in valid if r.get("mk_ndvi_direction") == "decreasing" and r.get("mk_ndvi_significant")]
    dense_canopy = [r for r in valid if r.get("ehs_is_dense_canopy")]

    def _mean(xs): return round(sum(xs) / len(xs), 4) if xs else None

    # Series-level provenance manifest (coverage + trust tier per period).
    manifest = build_manifest_from_observations(spec, all_observations)
    manifest_path = manifest.write_json(outdir / "pipeline_a_ts_manifest.json")

    summary = {
        "territory": args.territory,
        "n_trails_total": len(results),
        "n_trails_valid": len(valid),
        "years": args.years,
        "ehs_mean": _mean(ehs_vals),
        "ehs_min": round(min(ehs_vals), 1) if ehs_vals else None,
        "ehs_max": round(max(ehs_vals), 1) if ehs_vals else None,
        "ehs_ci_width_mean": _mean(
            [r["ehs_ci_width"] for r in valid if r.get("ehs_ci_width") is not None]
        ),
        "ehs_bootstrap_n": args.ehs_bootstrap,
        "n_significant_decline": len(degrading),
        "n_dense_canopy": len(dense_canopy),
        "pct_degrading": round(100 * len(degrading) / max(len(valid), 1), 1),
        # Temporal coverage + readiness (F2)
        "series_n_expected": manifest.n_expected(),
        "series_n_present": manifest.n_present(),
        "series_coverage": manifest.coverage(),
        "series_dominant_status": manifest.dominant_status().value,
        "n_trails_trend_capable": sum(
            1 for r in valid if r.get("mann_kendall_justified")
        ),
        "mode": "dry-run" if args.dry_run else "GEE:S2_SR_HARMONIZED",
    }

    json_path = outdir / "pipeline_a_ts_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Reproducible run provenance (git sha, timestamp, params) next to outputs.
    ctx_path = capture_run_context(
        tool="run_pipeline_a_timeseries",
        territory=args.territory,
        years=args.years,
        cadence=spec.cadence.value,
        mode="dry-run" if args.dry_run else "GEE:S2_SR_HARMONIZED",
    ).write_json(outdir)

    # ── Print summary ─────────────────────────────────────────────────────────
    print()
    print(DIV)
    print("  RESUMEN — Pipeline A Time Series (Mann-Kendall + EHS)")
    print(DIV)
    for k, v in summary.items():
        print(f"  {k:<34} {v}")

    print()
    ranked = sorted(
        [r for r in valid if r.get("mk_ndvi_slope") is not None],
        key=lambda r: r["mk_ndvi_slope"],
    )[:5]
    if ranked:
        print("  TOP-5 senderos por declive NDVI (Sen's slope más negativo):")
        for r in ranked:
            evi_str = f"EVI={r['mean_evi']:.3f}" if r["mean_evi"] is not None else "EVI=n/a"
            dc_str = " [DENSE]" if r.get("ehs_is_dense_canopy") else ""
            print(
                f"    {r['name'][:38]:<38}  slope={r['mk_ndvi_slope']:+.5f}  "
                f"EHS={r['ehs']:5.1f}  {evi_str}{dc_str}"
            )

    print()
    print(f"  CSV      : {csv_path}")
    print(f"  JSON     : {json_path}")
    print(f"  MANIFEST : {manifest_path}")
    print(f"  RUN CTX  : {ctx_path}")
    print(SEP)


if __name__ == "__main__":
    main()
