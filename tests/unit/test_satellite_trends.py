"""Tests del cargador de tendencias satelitales reales (v1.1.0).

Cubren ``src/platform/satellite_trends.py`` — el módulo que el dashboard usa en
runtime para la Pestaña 6 (Evolución Temporal). A diferencia de la simulación de
``charts.build_time_series_chart``, aquí se parsea el JSON Mann-Kendall *real*
producido offline por ``scripts/run_timeseries_analysis.py``.

Estilo del repo: ``monkeypatch`` / ``tmp_path``, fixtures JSON diminutas en
memoria, sin red ni dependencias nuevas.
"""
from __future__ import annotations

import json
import tracemalloc
from pathlib import Path

import pytest

import src.platform.satellite_trends as st_mod
from src.platform.satellite_trends import (
    DEFAULT_PARK,
    AssetTrend,
    TrendSummary,
    _category_from_id,
    available_parks,
    find_trend,
    load_asset_trends,
    park_label,
    summarize_trends,
)

# ── Fixtures JSON (esquema real de mk_trends_pnsg.json) ─────────────────────────

def _record(
    *,
    tau: float,
    p_approx: float,
    trend: str,
    annual: dict[str, float],
    partial: list[str] | None = None,
    worst: str | None = "2022",
    best: str | None = "2024",
    n_obs: int = 60,
    ndvi_min: float = 0.32,
    ndvi_max: float = 0.48,
) -> dict:
    """Un registro per-activo con las claves exactas del pipeline real."""
    return {
        "n_observations": n_obs,
        "mann_kendall_ndvi": {
            "tau": tau, "z": 2.0, "p_approx": p_approx, "trend": trend, "n": n_obs,
        },
        "mann_kendall_ndmi": {
            "tau": 0.0, "z": 0.0, "p_approx": 0.9, "trend": "no trend", "n": n_obs,
        },
        "annual_mean_ndvi": annual,
        "partial_years": partial or [],
        "worst_ndvi_year": worst,
        "best_ndvi_year": best,
        "ndvi_range": {"min": ndvi_min, "max": ndvi_max},
    }


def _write_json(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "mk_trends.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


_ANNUAL = {"2021": 0.39, "2022": 0.36, "2023": 0.41, "2024": 0.42,
           "2025": 0.41, "2026": 0.44}


# ── load_asset_trends: mapeo de campos ──────────────────────────────────────────

def test_load_maps_schema_fields(tmp_path):
    payload = {
        "pnsg_escalada_penalara": _record(
            tau=0.191, p_approx=0.0316, trend="increasing",
            annual=_ANNUAL, partial=["2026"], worst="2022", best="2024",
            n_obs=60, ndvi_min=0.3277, ndvi_max=0.4779,
        )
    }
    trends = load_asset_trends(_write_json(tmp_path, payload))
    assert len(trends) == 1
    a = trends[0]
    assert isinstance(a, AssetTrend)
    assert a.asset_id == "pnsg_escalada_penalara"
    assert a.category == "escalada"            # _category_from_id
    assert a.n_observations == 60
    assert a.tau == pytest.approx(0.191)
    assert a.p_value == pytest.approx(0.0316)  # p_approx → p_value
    assert a.trend == "increasing"
    assert a.annual_mean_ndvi["2022"] == pytest.approx(0.36)
    assert a.partial_years == ["2026"]
    assert a.worst_year == "2022"
    assert a.best_year == "2024"
    assert a.ndvi_min == pytest.approx(0.3277)
    assert a.ndvi_max == pytest.approx(0.4779)


def test_load_missing_file_returns_empty(tmp_path):
    assert load_asset_trends(tmp_path / "does_not_exist.json") == []


@pytest.mark.parametrize("asset_id,expected", [
    ("pnsg_escalada_penalara", "escalada"),
    ("pnsg_vuelo_libre_el_nevero", "vuelo"),
    ("solo", "otro"),            # sin separador → 'otro'
])
def test_category_from_id(asset_id, expected):
    assert _category_from_id(asset_id) == expected


def test_explicit_category_column_preferred_over_id(tmp_path):
    """OAPN (v1.2.0): la columna `category` gana sobre el parseo del id.

    El id multi-token `pn_tablas_daimiel_senderismo_...` rompería el parseo
    posicional (`parts[1]` → 'tablas'); con `category` explícita se lee tal cual.
    """
    rec = _record(tau=0.1, p_approx=0.3, trend="no trend", annual=_ANNUAL)
    rec["category"] = "senderismo"
    payload = {"pn_tablas_daimiel_senderismo_la_isla_del_pan_001": rec}
    a = load_asset_trends(_write_json(tmp_path, payload))[0]
    assert a.category == "senderismo"          # no 'tablas' (parts[1])


def test_missing_category_falls_back_to_id(tmp_path):
    payload = {"pnsg_escalada_penalara": _record(
        tau=0.1, p_approx=0.3, trend="no trend", annual=_ANNUAL)}
    a = load_asset_trends(_write_json(tmp_path, payload))[0]
    assert a.category == "escalada"            # sin columna → _category_from_id


# ── Multi-parque (v1.2.0 Red OAPN): resolución por slug + descubrimiento ────────

def test_load_resolves_park_slug(tmp_path, monkeypatch):
    monkeypatch.setattr(st_mod, "_ANALYSIS_DIR", tmp_path)
    (tmp_path / "mk_trends_pn_monfrague.json").write_text(
        json.dumps({"pn_monfrague_ciclismo_x_0": _record(
            tau=0.2, p_approx=0.3, trend="no trend", annual=_ANNUAL)}),
        encoding="utf-8",
    )
    # sin `path`, se resuelve por park → mk_trends_pn_monfrague.json
    trends = load_asset_trends(park="pn_monfrague")
    assert len(trends) == 1 and trends[0].asset_id == "pn_monfrague_ciclismo_x_0"
    # un parque inexistente → lista vacía (no revienta)
    assert load_asset_trends(park="pn_inexistente") == []


def test_available_parks_lists_pnsg_first(tmp_path, monkeypatch):
    monkeypatch.setattr(st_mod, "_ANALYSIS_DIR", tmp_path)
    for slug in ("pn_monfrague", "pnsg", "pn_tablas_daimiel"):
        (tmp_path / f"mk_trends_{slug}.json").write_text("{}", encoding="utf-8")
    parks = available_parks()
    assert parks[0] == DEFAULT_PARK                       # PNSG siempre primero
    assert set(parks) == {"pnsg", "pn_monfrague", "pn_tablas_daimiel"}
    assert parks[1:] == ["pn_monfrague", "pn_tablas_daimiel"]  # resto alfabético


def test_available_parks_empty_when_dir_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(st_mod, "_ANALYSIS_DIR", tmp_path / "nope")
    assert available_parks() == []


def test_summarize_by_park(tmp_path, monkeypatch):
    monkeypatch.setattr(st_mod, "_ANALYSIS_DIR", tmp_path)
    (tmp_path / "mk_trends_pn_tablas_daimiel.json").write_text(
        json.dumps({"pn_tablas_daimiel_senderismo_x_0": _record(
            tau=-0.3, p_approx=0.01, trend="decreasing", annual=_ANNUAL)}),
        encoding="utf-8",
    )
    s = summarize_trends(park="pn_tablas_daimiel")
    assert s.available is True and s.n_degrading == 1


@pytest.mark.parametrize("slug,expected", [
    ("pnsg", "Sierra de Guadarrama (PNSG)"),
    ("pn_monfrague", "Monfragüe"),
    ("pn_desconocido", "pn_desconocido"),      # fallback al slug
])
def test_park_label(slug, expected):
    assert park_label(slug) == expected


# ── AssetTrend: propiedades derivadas ───────────────────────────────────────────

def _trend(**kw) -> AssetTrend:
    base = dict(
        asset_id="pnsg_x_y", category="x", n_observations=60, tau=0.0,
        p_value=0.5, trend="no trend", annual_mean_ndvi={"2021": 0.4},
        partial_years=[], worst_year="2022", best_year="2024",
        ndvi_min=0.3, ndvi_max=0.5,
    )
    base.update(kw)
    return AssetTrend(**base)


def test_significant_boundary():
    assert _trend(p_value=0.0499).significant is True
    assert _trend(p_value=0.05).significant is False    # estricto: p < 0.05


def test_is_alert_requires_significant_decrease():
    assert _trend(trend="decreasing", p_value=0.01).is_alert is True
    assert _trend(trend="decreasing", p_value=0.20).is_alert is False  # no signif.
    assert _trend(trend="increasing", p_value=0.01).is_alert is False


@pytest.mark.parametrize("trend,label", [
    ("increasing", "↗ mejora"),
    ("decreasing", "↘ degradación"),
    ("no trend", "→ estable"),
    ("garbage", "→ estable"),       # fallback
])
def test_trend_es_labels(trend, label):
    assert _trend(trend=trend).trend_es == label


# ── summarize_trends: roll-up de portafolio ─────────────────────────────────────

def test_summarize_missing_file_unavailable(tmp_path):
    summary = summarize_trends(tmp_path / "missing.json")
    assert isinstance(summary, TrendSummary)
    assert summary.available is False
    assert summary.assets == []


def test_summarize_counts_and_signals(tmp_path):
    # partial_years es global (idéntico en todos los activos del pipeline real).
    payload = {
        # degradación significativa → alerta
        "pnsg_a_deg": _record(tau=-0.3, p_approx=0.01, trend="decreasing",
                              annual=_ANNUAL, partial=["2026"], worst="2022"),
        # mejora significativa
        "pnsg_b_imp": _record(tau=0.3, p_approx=0.02, trend="increasing",
                              annual=_ANNUAL, partial=["2026"], worst="2022"),
        # decreasing pero NO significativo → cuenta como estable
        "pnsg_c_ns": _record(tau=-0.1, p_approx=0.40, trend="decreasing",
                             annual=_ANNUAL, partial=["2026"], worst="2023"),
        # no trend → estable
        "pnsg_d_flat": _record(tau=0.0, p_approx=0.90, trend="no trend",
                              annual=_ANNUAL, partial=["2026"], worst="2022"),
    }
    s = summarize_trends(_write_json(tmp_path, payload))
    assert s.available is True
    assert s.n_degrading == 1      # solo el significativo
    assert s.n_improving == 1
    assert s.n_stable == 2         # ns-decreasing + no-trend
    assert s.worst_year_global == "2022"   # 3 de 4 activos
    assert s.partial_years == ["2026"]     # global, tomado de assets[0]
    # alerts = decreasing & significant
    assert [a.asset_id for a in s.alerts] == ["pnsg_a_deg"]
    # orden: alertas primero, luego p ascendente
    assert s.assets[0].asset_id == "pnsg_a_deg"
    assert s.assets[1].asset_id == "pnsg_b_imp"   # p=0.02 antes que 0.40/0.90


# ── find_trend: emparejamiento difuso nombre→asset_id ───────────────────────────

@pytest.fixture
def _assets() -> list[AssetTrend]:
    return [
        _trend(asset_id="pnsg_escalada_penalara"),
        _trend(asset_id="pnsg_vuelo_libre_el_nevero"),
    ]


def test_find_trend_unicode_and_accents(_assets):
    m = find_trend("Peñalara", _assets)
    assert m is not None and m.asset_id == "pnsg_escalada_penalara"


def test_find_trend_multitoken(_assets):
    m = find_trend("El Nevero", _assets)
    assert m is not None and m.asset_id == "pnsg_vuelo_libre_el_nevero"


def test_find_trend_short_tokens_only_returns_none(_assets):
    # tokens de ≤3 chars se descartan → sin tokens utilizables
    assert find_trend("el", _assets) is None


def test_find_trend_no_match(_assets):
    assert find_trend("Montaña Inexistente", _assets) is None


# ── Benchmark de memoria (Fase 2): el cargador no debe inflarse ─────────────────

def test_loader_memory_bounded(tmp_path):
    """Carga 30 activos × 6 años bajo tracemalloc y fija un techo generoso.

    Bloquea regresiones que metan estructuras O(N²) o copias de rasters en el
    camino de runtime de la Pestaña 6 (hoy ~decenas de KB para 21 activos).
    """
    payload = {
        f"pnsg_cat{i}_asset{i}": _record(
            tau=0.1, p_approx=0.3, trend="no trend", annual=_ANNUAL,
        )
        for i in range(30)
    }
    path = _write_json(tmp_path, payload)

    tracemalloc.start()
    trends = load_asset_trends(path)
    summary = summarize_trends(path)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert len(trends) == 30
    assert summary.available is True
    peak_mb = peak / (1024 * 1024)
    # Techo holgado: el payload real (21 activos) ocupa muy por debajo de esto.
    assert peak_mb < 25.0, f"pico de memoria {peak_mb:.2f} MB excede el límite"
