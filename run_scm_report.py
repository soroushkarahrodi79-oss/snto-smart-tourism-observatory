"""
SNTO Spatial Causality Module (SCM) Report
Masatrigo Trail, Badajoz, Extremadura, Spain
"""
from __future__ import annotations

from src.assets.models import AssetType, GeoJSONGeometry, TourismAsset
from src.geospatial.geometry import enrich_asset_geometry
from src.ingestion.multiyear_adapter import MultiYearAdapter
from src.risk_engine.human_pressure import GeoProximityFactors, compute_geo_human_pressure
from src.spatial_causality.analyzer import (
    CORE_OUTER_M,
    LANDSCAPE_OUTER_M,
    NEAR_OUTER_M,
    SpatialCausalityAnalyzer,
)

SEP = "=" * 72
DIV = "-" * 72
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

MASATRIGO_GEO = {
    "geo_proximity": {
        "road_km": 0.82, "settlement_km": 4.51, "poi_count_5km": 4,
        "trail_network_km": 2.83, "mean_slope_deg": 7.6,
    }
}

# Hypothetical high-pressure comparator (for context)
HIGH_PRESSURE_GEO = {
    "geo_proximity": {
        "road_km": 0.10, "settlement_km": 0.80, "poi_count_5km": 18,
        "trail_network_km": 6.50, "mean_slope_deg": 3.0,
    }
}


def print_zone_table(result):
    zones = result.zones
    print(f"  {'Zone':>12}  {'Radius (m)':>12}  {'Mean NDVI':>10}  "
          f"{'Mean NDMI':>10}  {'Sen Slope':>10}  {'Volatility':>11}  {'Anom %':>7}")
    print("  " + DIV[:80])
    for name in ["core", "near", "landscape"]:
        z = zones[name]
        rng = f"{z.inner_radius_m}-{z.outer_radius_m}"
        print(
            f"  {name:>12}  {rng:>12}  {z.mean_ndvi:10.4f}  "
            f"{z.mean_ndmi:10.4f}  {z.ndvi_sens_slope:+10.6f}  "
            f"{z.ndvi_volatility:11.5f}  {z.anomaly_frequency*100:6.1f}%"
        )


def print_gradient_table(result):
    g = result.gradient
    print(f"  Core - Near          : {g.core_near_delta:+.5f}")
    print(f"  Near - Landscape     : {g.near_landscape_delta:+.5f}")
    print(f"  Core - Landscape     : {g.core_landscape_delta:+.5f}")
    print(f"  Spatial Impact Gradient (SIG)  : {g.spatial_impact_gradient:.5f}")
    print(f"  Cross-zone correlation (r)     : {g.cross_zone_correlation:.4f}")


def main():
    # Build Masatrigo asset
    asset = TourismAsset(
        asset_id="masatrigo-trail-001",
        name="Masatrigo Trail, Badajoz",
        asset_type=AssetType.TRAIL,
        geometry=GeoJSONGeometry(
            type="LineString", coordinates=[[-7.02, 38.88], [-7.00, 38.90]]
        ),
        region="Extremadura", country="Spain", elevation_m=420.0,
        metadata=MASATRIGO_GEO,
    )
    asset = enrich_asset_geometry(asset)

    # 2021-2025 multi-year record
    obs = MultiYearAdapter(2021, 2025).fetch_multiyear_series(asset)

    # Human pressure proxy
    geo = GeoProximityFactors.from_metadata(MASATRIGO_GEO)
    hp = compute_geo_human_pressure(geo)

    # SCM analysis — Masatrigo
    scm = SpatialCausalityAnalyzer(human_pressure=hp)
    zones = scm.simulate_zones(obs)
    result = scm.analyse(asset.asset_id, zones)

    # Hypothetical high-pressure comparator (shows module logic)
    geo_hp = GeoProximityFactors.from_metadata(HIGH_PRESSURE_GEO)
    hp_high = compute_geo_human_pressure(geo_hp)
    scm_hi = SpatialCausalityAnalyzer(human_pressure=hp_high)
    zones_hi = scm_hi.simulate_zones(obs)  # same base NDVI, different pressure
    result_hi = scm_hi.analyse("hypothetical-high-pressure", zones_hi)

    # ================================================================
    print(SEP)
    print("  SNTO -- SPATIAL CAUSALITY MODULE (SCM)")
    print("  Is observed change LOCAL (human) or LANDSCAPE (climate)?")
    print(SEP)
    print()
    print("  ASSET: Masatrigo Trail, Badajoz, Extremadura, Spain")
    print(f"  Human Pressure Index: {hp:.3f}  (geo-based, 0-1 scale)")
    print(f"  Multi-year observations: {len(obs)} (2021-2025, monthly)")
    print()

    # ── ZONE CONFIGURATION ────────────────────────────────────────────────
    print("SPATIAL ZONE CONFIGURATION")
    print(DIV)
    print(f"  Zone definitions for LINEAR TRAIL ASSET (buffer rings around axis):")
    print(f"  Core zone      : 0 to {CORE_OUTER_M} m  (direct trail surface and immediate edges)")
    print(f"  Near zone      : {CORE_OUTER_M} to {NEAR_OUTER_M} m  (trail margins, adjacent scrubland)")
    print(f"  Landscape zone : {NEAR_OUTER_M} to {LANDSCAPE_OUTER_M} m  (regional background)")
    print()
    print("  Scientific justification:")
    print("  - Core = spatial scale of trampling and path clearing impact")
    print("    (Marion & Leung 2001: most measurable NDVI change within 30-50m)")
    print("  - Near = transition zone between trail and undisturbed vegetation")
    print("  - Landscape = regional climate signal; unaffected by trail use")
    print()

    # ── SECTION 1: SPATIAL RESULTS TABLE ─────────────────────────────────
    print("SECTION 1 -- SPATIAL RESULTS TABLE (Masatrigo Trail)")
    print(DIV)
    print_zone_table(result)
    print()

    # ── SECTION 2: SPATIAL GRADIENT METRICS ──────────────────────────────
    print("SECTION 2 -- SPATIAL GRADIENT METRICS")
    print(DIV)
    print_gradient_table(result)
    print()
    sig = result.gradient.spatial_impact_gradient
    corr = result.gradient.cross_zone_correlation
    print("  Threshold reference:")
    print(f"    SIG > 0.15 AND r < 0.70  -->  LOCALIZED_IMPACT")
    print(f"    SIG < 0.07 AND r > 0.85  -->  LANDSCAPE_DRIVEN")
    print(f"    Otherwise                -->  MIXED")
    print()
    print(f"  Masatrigo: SIG = {sig:.4f}  {'<' if sig < 0.07 else ('>=' if sig > 0.15 else 'within')} landscape threshold")
    print(f"             r   = {corr:.4f}  {'>' if corr > 0.85 else ('<' if corr < 0.70 else 'within')} landscape threshold")
    print()

    # ── SECTION 3: CLASSIFICATION ─────────────────────────────────────────
    print("SECTION 3 -- CLASSIFICATION RESULT")
    print(DIV)
    print(f"  CLASSIFICATION : {result.classification}")
    print(f"  CONFIDENCE     : {result.confidence}")
    print()
    print("  Technical rationale:")
    # Word-wrap the rationale
    words = result.technical_rationale.split()
    line = "  "
    for w in words:
        if len(line) + len(w) + 1 > 72:
            print(line)
            line = "    " + w
        else:
            line += " " + w
    if line.strip():
        print(line)
    print()

    # ── SECTION 4: PLAIN LANGUAGE EXPLANATION ────────────────────────────
    print("SECTION 4 -- PLAIN LANGUAGE EXPLANATION")
    print(DIV)
    # Word-wrap
    words = result.plain_language.split()
    line = "  "
    for w in words:
        if len(line) + len(w) + 1 > 72:
            print(line)
            line = "  " + w
        else:
            line += " " + w
    if line.strip():
        print(line)
    print()

    # ── SECTION 5: MANAGEMENT IMPLICATION ────────────────────────────────
    print("SECTION 5 -- MANAGEMENT IMPLICATION")
    print(DIV)
    words = result.management_implication.split()
    line = "  "
    for w in words:
        if len(line) + len(w) + 1 > 72:
            print(line)
            line = "  " + w
        else:
            line += " " + w
    if line.strip():
        print(line)
    print()

    # ── COMPARATOR: HIGH PRESSURE SITE ───────────────────────────────────
    print(SEP)
    print("  COMPARATOR: Hypothetical High-Pressure Site")
    print(f"  (HP index = {hp_high:.3f}: road-adjacent, urban-fringe, high POI density)")
    print(SEP)
    print()
    print("SECTION 1 -- SPATIAL RESULTS (Comparator)")
    print(DIV)
    print_zone_table(result_hi)
    print()
    print("SECTION 2 -- SPATIAL GRADIENT (Comparator)")
    print(DIV)
    print_gradient_table(result_hi)
    print()
    print("SECTION 3 -- CLASSIFICATION (Comparator)")
    print(DIV)
    print(f"  CLASSIFICATION : {result_hi.classification}")
    print(f"  CONFIDENCE     : {result_hi.confidence}")
    print()

    # ── SIDE-BY-SIDE COMPARISON ───────────────────────────────────────────
    print(SEP)
    print("  SIDE-BY-SIDE MODULE COMPARISON")
    print(SEP)
    print()
    print(f"  {'Metric':40s}  {'Masatrigo':>12}  {'Comparator':>12}")
    print("  " + DIV[:68])
    print(f"  {'Human Pressure Index':40s}  {hp:12.3f}  {hp_high:12.3f}")
    zc = result.zones["core"]
    zl = result.zones["landscape"]
    zc2 = result_hi.zones["core"]
    zl2 = result_hi.zones["landscape"]
    print(f"  {'Core zone NDVI':40s}  {zc.mean_ndvi:12.4f}  {zc2.mean_ndvi:12.4f}")
    print(f"  {'Landscape NDVI':40s}  {zl.mean_ndvi:12.4f}  {zl2.mean_ndvi:12.4f}")
    print(f"  {'Core-Landscape NDVI delta':40s}  "
          f"{result.gradient.core_landscape_delta:+12.4f}  "
          f"{result_hi.gradient.core_landscape_delta:+12.4f}")
    print(f"  {'Spatial Impact Gradient (SIG)':40s}  "
          f"{result.gradient.spatial_impact_gradient:12.5f}  "
          f"{result_hi.gradient.spatial_impact_gradient:12.5f}")
    print(f"  {'Cross-zone correlation (r)':40s}  "
          f"{result.gradient.cross_zone_correlation:12.4f}  "
          f"{result_hi.gradient.cross_zone_correlation:12.4f}")
    print(f"  {'Classification':40s}  {result.classification:>12}  {result_hi.classification:>12}")
    print(f"  {'Confidence':40s}  {result.confidence:>12}  {result_hi.confidence:>12}")
    print()

    # ── SCIENTIFIC VALIDITY ASSESSMENT ────────────────────────────────────
    print(SEP)
    print("  SCM SCIENTIFIC VALIDITY ASSESSMENT")
    print(SEP)
    print()
    print("  WHAT THE SCM DOES WELL")
    print("  " + DIV[:55])
    strengths = [
        "Spatial scale logic is grounded in trampling literature (Marion & Leung",
        "  2001; Pickering et al. 2011): 0-50m is the correct impact scale.",
        "Cross-zone correlation correctly identifies climate-driven signals:",
        "  drought events suppress all zones equally (r > 0.90), which is the",
        "  defining signature of landscape forcing.",
        "SIG is scale-free (dimensionless ratio) and can be compared across",
        "  assets of different land cover types and baseline NDVI levels.",
        "Classification is reproducible, deterministic, and fully auditable.",
    ]
    for s in strengths:
        print(f"  + {s}")
    print()
    print("  LIMITATIONS")
    print("  " + DIV[:55])
    limits = [
        "Zone signals are SIMULATED from single-zone observations. Real",
        "  multi-scale GEE extraction (with distinct buffer geometries) would",
        "  provide genuinely independent zone data and higher scientific validity.",
        "The human pressure proxy drives the simulation — the SCM is not fully",
        "  independent of the existing risk model when simulated data is used.",
        "Spatial decay coefficients (alpha_core=0.12) are calibrated from",
        "  published trampling studies but not site-validated for Masatrigo.",
        "Cross-zone correlation uses temporal structure of the same base series;",
        "  full independence requires separate spatial acquisition per buffer.",
    ]
    for l_ in limits:
        print(f"  - {l_}")
    print()
    print("  PATH TO PRODUCTION-GRADE SCM")
    print("  " + DIV[:55])
    print("  1. In GEEAdapter: extract separate ee.Geometry.buffer() zones")
    print("     for each ring, compute NDVI reducers independently.")
    print("  2. Replace simulate_zones() with real multi-buffer GEE queries.")
    print("  3. No other architecture changes required -- the analysis")
    print("     pipeline (analyse(), classify()) runs identically.")
    print()
    print(SEP)


if __name__ == "__main__":
    main()
