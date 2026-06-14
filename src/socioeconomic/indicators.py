"""
SNTO — Socioeconomic indicators (F9)
=====================================
The analytic core that crosses the *municipal socioeconomic snapshot* with the
*environmental risk* of the observatory's assets.

Two outputs:

  SVI — Socioeconomic Vulnerability Index (0–100 per municipality)
      SVI = 100 · weighted_mean( DEP, DEM, EXP )      weights 0.40 / 0.30 / 0.30
        DEP  dependencia turística     (second homes %, tourism employment pc)
        DEM  fragilidad demográfica    (ageing %, 5-year population decline)
        EXP  exposición al riesgo      (aggregated EHS / SCM / tier of its assets)
      Weights renormalise over the components actually available, so a Segovia
      municipality (demographic-only, no EXP/DEP-tourism) still gets an honest,
      partial SVI instead of a fabricated one.

  CommunityImpact (0–100 per municipality)
      = 100 · EXP · DEP   — environmental risk *times* economic dependence.
      High where degraded assets sit in communities that live off them. This is
      the data-backed replacement for the dashboard's hand-tuned "jobs at risk".

All functions are pure: they take the snapshot + an asset-risk aggregation and
return dataclasses. Normalisation is min-max over the PNSG cohort.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .loader import SocioeconomicSnapshot
from .mapping import CrosswalkRow, load_crosswalk, normalize_name
from .models import Municipality

# Component weights (renormalised over available components)
W_DEP, W_DEM, W_EXP = 0.40, 0.30, 0.30


# ── Asset-risk aggregation (environmental side) ─────────────────────────────────
@dataclass(frozen=True)
class AssetRiskAgg:
    ine_code: str
    n_assets: int
    mean_health_deficit: float   # mean (100 - EHS)/100  → 0 healthy, 1 critical
    share_localized: float       # fraction with scm_classification == LOCALIZED_IMPACT
    share_tier12: float          # fraction in Tier 1 or 2
    visitors_tier12: int         # annual visitor capacity in Tier 1/2 assets

    def exposure(self) -> float:
        """EXP component 0..1."""
        return _clamp(
            0.5 * self.mean_health_deficit
            + 0.3 * self.share_tier12
            + 0.2 * self.share_localized
        )


def aggregate_asset_risk(
    assets: Iterable,
    name_to_ine: dict[str, str] | None = None,
    crosswalk: list[CrosswalkRow] | None = None,
) -> dict[str, AssetRiskAgg]:
    """
    Group assets by their municipality (via region name) and summarise risk.

    Assets are duck-typed: each needs ``region``, ``ehs``, ``scm_classification``,
    ``tier`` and ``visitor_capacity_annual``.

    The name→INE index can be supplied directly (e.g. from the snapshot via
    ``SocioeconomicSnapshot.name_to_ine()`` — the runtime path, no raw files), or
    derived from the crosswalk CSV (the ETL/offline path).
    """
    if name_to_ine is None:
        rows = crosswalk if crosswalk is not None else load_crosswalk()
        name_to_ine = {normalize_name(r.name): r.ine_code for r in rows}

    buckets: dict[str, list] = {}
    for a in assets:
        ine = name_to_ine.get(normalize_name(getattr(a, "region", "") or ""))
        if ine:
            buckets.setdefault(ine, []).append(a)

    out: dict[str, AssetRiskAgg] = {}
    for ine, group in buckets.items():
        n = len(group)
        mean_deficit = sum(max(0.0, (100.0 - a.ehs)) / 100.0 for a in group) / n
        share_local = sum(
            1 for a in group if a.scm_classification == "LOCALIZED_IMPACT"
        ) / n
        tier12 = [a for a in group if (a.tier or 99) <= 2]
        share_t12 = len(tier12) / n
        visitors_t12 = int(sum(a.visitor_capacity_annual for a in tier12))
        out[ine] = AssetRiskAgg(
            ine_code=ine, n_assets=n, mean_health_deficit=mean_deficit,
            share_localized=share_local, share_tier12=share_t12,
            visitors_tier12=visitors_t12,
        )
    return out


# ── SVI ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SVIResult:
    ine_code: str
    name: str
    province: str
    svi: float                       # 0..100
    dep: Optional[float]             # 0..1 (None if not computable)
    dem: Optional[float]
    exp: Optional[float]
    community_impact: Optional[float]  # 0..100 (needs EXP and DEP)
    components_available: list[str]
    completeness: str


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _minmax(value: Optional[float], lo: float, hi: float) -> Optional[float]:
    if value is None:
        return None
    if hi <= lo:
        return 0.5
    return _clamp((value - lo) / (hi - lo))


def _mean(values: list[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _tourism_emp_per_1000(m: Municipality) -> Optional[float]:
    if m.tourism_employment is None or not m.population:
        return None
    return m.tourism_employment / m.population * 1000.0


def compute_svi(
    snapshot: SocioeconomicSnapshot,
    asset_risk: dict[str, AssetRiskAgg] | None = None,
) -> dict[str, SVIResult]:
    """Compute the SVI for every municipality in the snapshot."""
    asset_risk = asset_risk or {}
    munis = list(snapshot.municipalities.values())

    # Cohort extremes for min-max normalisation
    emp_pc = [v for v in (_tourism_emp_per_1000(m) for m in munis) if v is not None]
    ageing = [m.pct_over_65 for m in munis if m.pct_over_65 is not None]
    decline = [(-m.pop_change_5y_pct) for m in munis if m.pop_change_5y_pct is not None]

    emp_lo, emp_hi = (min(emp_pc), max(emp_pc)) if emp_pc else (0.0, 0.0)
    age_lo, age_hi = (min(ageing), max(ageing)) if ageing else (0.0, 0.0)
    dec_lo, dec_hi = (min(decline), max(decline)) if decline else (0.0, 0.0)

    results: dict[str, SVIResult] = {}
    for m in munis:
        # DEP — dependencia turística
        dep = _mean([
            (m.pct_second_homes / 100.0) if m.pct_second_homes is not None else None,
            _minmax(_tourism_emp_per_1000(m), emp_lo, emp_hi),
        ])
        # DEM — fragilidad demográfica
        _decline = (-m.pop_change_5y_pct) if m.pop_change_5y_pct is not None else None
        dem = _mean([
            _minmax(m.pct_over_65, age_lo, age_hi),
            _minmax(_decline, dec_lo, dec_hi),
        ])
        # EXP — exposición al riesgo ambiental (from the municipality's assets)
        agg = asset_risk.get(m.ine_code)
        exp = agg.exposure() if agg else None

        comps: list[tuple[str, float, float]] = []
        if dep is not None:
            comps.append(("DEP", dep, W_DEP))
        if dem is not None:
            comps.append(("DEM", dem, W_DEM))
        if exp is not None:
            comps.append(("EXP", exp, W_EXP))

        if comps:
            wsum = sum(w for _, _, w in comps)
            svi = 100.0 * sum(v * w for _, v, w in comps) / wsum
        else:
            svi = 0.0

        community = (
            100.0 * exp * dep if (exp is not None and dep is not None) else None
        )

        results[m.ine_code] = SVIResult(
            ine_code=m.ine_code, name=m.name, province=m.province,
            svi=round(svi, 1),
            dep=round(dep, 3) if dep is not None else None,
            dem=round(dem, 3) if dem is not None else None,
            exp=round(exp, 3) if exp is not None else None,
            community_impact=round(community, 1) if community is not None else None,
            components_available=[c for c, _, _ in comps],
            completeness=m.completeness.value,
        )
    return results


# ── Local jobs at risk (data-backed) ────────────────────────────────────────────
@dataclass(frozen=True)
class JobsAtRisk:
    total: float                       # estimated tourism-linked jobs exposed
    by_municipality: list[tuple[str, float]]  # (name, jobs) sorted desc


def jobs_at_risk(
    snapshot: SocioeconomicSnapshot,
    asset_risk: dict[str, AssetRiskAgg],
) -> JobsAtRisk:
    """
    Estimate tourism-linked employment exposed to asset degradation:
        jobs_at_risk(muni) = tourism_employment(muni) · exposure(muni)

    Replaces the dashboard's hard-coded ``visitors / 2500`` heuristic with INE/
    ALMUDENA affiliation counts modulated by the municipality's real EXP.
    """
    rows: list[tuple[str, float]] = []
    for ine, agg in asset_risk.items():
        m = snapshot.municipalities.get(ine)
        if m is None or m.tourism_employment is None:
            continue
        jobs = m.tourism_employment * agg.exposure()
        if jobs > 0:
            rows.append((m.name, round(jobs, 1)))
    rows.sort(key=lambda t: t[1], reverse=True)
    return JobsAtRisk(total=round(sum(j for _, j in rows), 1), by_municipality=rows)
