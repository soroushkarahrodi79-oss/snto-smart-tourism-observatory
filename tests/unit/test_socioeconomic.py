"""Unit tests for the socioeconomic layer (F9)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from etl_socioeconomic import parse_es_number
from src.socioeconomic.indicators import (
    AssetRiskAgg,
    aggregate_asset_risk,
    compute_svi,
    jobs_at_risk,
)
from src.socioeconomic.loader import SocioeconomicSnapshot, snapshot_exists, load_municipalities
from src.socioeconomic.mapping import (
    CROSSWALK_PATH, load_crosswalk, normalize_name, region_to_ine,
)
from src.socioeconomic.models import DataCompleteness, Municipality


# ── Number parsing (European format from the PDF-extracted fichas) ──────────────
@pytest.mark.parametrize("token,expected", [
    ("7.782", 7782.0),
    ("1.026.696", 1026696.0),
    ("18,90", 18.9),
    ("-3,23", -3.23),
    ("24.067", 24067.0),
    ("- - - ****", None),
    ("-", None),
    ("", None),
    ("..", None),  # decodes to 0.0? no -> '..' has no digits
])
def test_parse_es_number(token, expected):
    assert parse_es_number(token) == expected


def test_parse_es_number_double_dot_is_none():
    # INE uses ".." for suppressed values
    assert parse_es_number("..") is None


# ── Name normalisation handles the INE trailing-article convention ──────────────
@pytest.mark.parametrize("a,b", [
    ("Molinos, Los", "Los Molinos"),
    ("Boalo (El)", "El Boalo"),
    ("Rascafría", "RASCAFRIA"),
    ("Manzanares El Real", "Manzanares el Real"),
])
def test_normalize_name_equivalences(a, b):
    assert normalize_name(a) == normalize_name(b)


# ── Crosswalk + region resolution (raw file, ETL-only — skipped if absent) ──────
@pytest.mark.skipif(not CROSSWALK_PATH.exists(), reason="raw crosswalk CSV not in checkout")
def test_region_to_ine_resolves_pnsg_assets():
    rows = load_crosswalk()
    assert region_to_ine("Cercedilla", rows) == "28038"
    assert region_to_ine("Rascafría", rows) == "28120"
    assert region_to_ine("Manzanares El Real", rows) == "28082"
    # A non-PNSG municipality is not in the crosswalk
    assert region_to_ine("La Hiruela", rows) is None


# ── Asset-risk aggregation ──────────────────────────────────────────────────────
@dataclass
class _Asset:
    region: str
    ehs: float
    scm_classification: str
    tier: int
    visitor_capacity_annual: int


def test_aggregate_asset_risk_groups_by_municipality():
    assets = [
        _Asset("Cercedilla", ehs=39, scm_classification="LOCALIZED_IMPACT", tier=1, visitor_capacity_annual=85_000),
        _Asset("Cercedilla", ehs=53, scm_classification="LOCALIZED_IMPACT", tier=2, visitor_capacity_annual=35_000),
        _Asset("Rascafría", ehs=85, scm_classification="LANDSCAPE_DRIVEN", tier=4, visitor_capacity_annual=22_000),
    ]
    # Explicit name->INE map (snapshot-style) so the test needs no raw CSV.
    name_to_ine = {normalize_name("Cercedilla"): "28038", normalize_name("Rascafría"): "28120"}
    agg = aggregate_asset_risk(assets, name_to_ine=name_to_ine)
    assert set(agg) == {"28038", "28120"}
    cer = agg["28038"]
    assert cer.n_assets == 2
    assert cer.share_tier12 == 1.0
    assert cer.share_localized == 1.0
    assert cer.visitors_tier12 == 120_000
    # health deficit = mean((100-39)+(100-53))/100/2
    assert cer.mean_health_deficit == pytest.approx(((61 + 47) / 100) / 2)
    # healthy Tier-4 municipality has low exposure
    assert agg["28120"].exposure() < cer.exposure()


# ── SVI computation ─────────────────────────────────────────────────────────────
def _snapshot(munis: list[Municipality]) -> SocioeconomicSnapshot:
    return SocioeconomicSnapshot(
        schema_version="test", source_snapshot_date="test",
        n_municipalities=len(munis), n_full=0, n_demographic_only=0, sources={},
        municipalities={m.ine_code: m for m in munis},
    )


def _full_muni(ine, name, **kw) -> Municipality:
    base = dict(
        province="Madrid", pnsg_zone="PN", population=5000, population_year=2025,
        pop_change_5y_pct=0.0, pct_over_65=20.0, tourism_employment=300,
        pct_second_homes=40.0, completeness=DataCompleteness.FULL,
    )
    base.update(kw)
    return Municipality(ine_code=ine, name=name, **base)


def test_svi_components_and_weighting():
    munis = [
        _full_muni("A", "AltaDependencia", pct_second_homes=70.0, tourism_employment=600, pct_over_65=32.0, pop_change_5y_pct=-8.0),
        _full_muni("B", "BajaDependencia", pct_second_homes=33.0, tourism_employment=350, pct_over_65=15.0, pop_change_5y_pct=8.0),
    ]
    snap = _snapshot(munis)
    risk = {
        "A": AssetRiskAgg("A", 2, mean_health_deficit=0.6, share_localized=1.0, share_tier12=1.0, visitors_tier12=80_000),
        "B": AssetRiskAgg("B", 1, mean_health_deficit=0.1, share_localized=0.0, share_tier12=0.0, visitors_tier12=0),
    }
    svi = compute_svi(snap, risk)
    assert svi["A"].components_available == ["DEP", "DEM", "EXP"]
    # The fragile, degraded, tourism-dependent municipality scores higher
    assert svi["A"].svi > svi["B"].svi
    assert svi["A"].community_impact is not None
    assert 0 <= svi["A"].svi <= 100


def test_svi_partial_for_demographic_only_municipality():
    """A Segovia-style municipality (no ALMUDENA, no assets) still gets a DEM-only SVI."""
    seg = Municipality(
        ine_code="40194", name="Segovia", province="Segovia", pnsg_zone="PN",
        population=52000, population_year=2025, pop_change_5y_pct=-2.0,
        completeness=DataCompleteness.DEMOGRAPHIC_ONLY,
    )
    full = _full_muni("28038", "Cercedilla", pop_change_5y_pct=5.0)
    snap = _snapshot([seg, full])
    svi = compute_svi(snap, asset_risk={})
    # Segovia: only DEM available (no tourism DEP, no asset EXP)
    assert svi["40194"].components_available == ["DEM"]
    assert svi["40194"].community_impact is None
    assert svi["40194"].dep is None and svi["40194"].exp is None


def test_jobs_at_risk_uses_employment_and_exposure():
    munis = [_full_muni("A", "Aaa", tourism_employment=500)]
    snap = _snapshot(munis)
    risk = {"A": AssetRiskAgg("A", 1, mean_health_deficit=0.8, share_localized=1.0, share_tier12=1.0, visitors_tier12=50_000)}
    jr = jobs_at_risk(snap, risk)
    exp = risk["A"].exposure()
    assert jr.total == pytest.approx(round(500 * exp, 1))
    assert jr.by_municipality[0][0] == "Aaa"


# ── Integration with the real curated snapshot (if present) ─────────────────────
@pytest.mark.skipif(not snapshot_exists(), reason="run etl_socioeconomic.py first")
def test_real_snapshot_loads_and_covers_34_municipalities():
    snap = load_municipalities()
    assert snap.n_municipalities == 34
    assert snap.n_full == 15           # Madrid (ALMUDENA)
    assert snap.n_demographic_only == 19  # Segovia (padrón only)
    cer = snap.get("28038")
    assert cer is not None and cer.name == "Cercedilla"
    assert cer.tourism_employment == 510
    assert cer.completeness == DataCompleteness.FULL
