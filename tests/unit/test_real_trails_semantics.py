"""F1 — Semántica de salud en el puente Pipeline A → observatorio.

Blinda que RealTrail expone SALUD (no estrés): health_* y delta_health en
convenio 0=crítico, 100=sano, con delta_health > 0 ⇒ la salud mejora.
"""
from __future__ import annotations

from src.platform.real_trails import (
    SCM_ATTRIBUTION_CAVEAT,
    SCM_ATTRIBUTION_LABEL,
    RealTrail,
    RealTrailDataset,
    build_real_trails_geojson,
    get_real_trails,
)


def _trail(name: str, spring: float, summer: float, **kw) -> RealTrail:
    return RealTrail(
        trail_id=kw.get("trail_id", 1),
        name=name,
        length_km=kw.get("length_km", 1.0),
        health_spring=spring,
        health_summer=summer,
        delta_health=round(summer - spring, 4),
        scm_class=kw.get("scm_class"),
        budget_eur=kw.get("budget_eur"),
        geometry=kw.get("geometry", {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}),
    )


def test_is_degrading_uses_health_delta_sign():
    worsening = _trail("A", spring=80.0, summer=60.0)   # salud cae 20
    improving = _trail("B", spring=60.0, summer=72.0)   # salud sube 12
    assert worsening.delta_health == -20.0
    assert worsening.is_degrading is True
    assert improving.delta_health == 12.0
    assert improving.is_degrading is False


def test_priority_label_tracks_summer_health():
    critical = _trail("C", spring=40.0, summer=20.0)    # salud < 30
    healthy = _trail("D", spring=82.0, summer=88.0)     # salud >= 75
    assert critical.priority_label == "Crítica"
    assert healthy.priority_label == "Mínima"


def test_ranked_by_priority_puts_lowest_health_first():
    ds = RealTrailDataset(
        territory_key="t", available=True,
        trails=[_trail("alta", 80, 85), _trail("baja", 30, 25), _trail("media", 60, 55)],
        summary={},
    )
    order = [t.name for t in ds.ranked_by_priority()]
    assert order == ["baja", "media", "alta"]


def test_top_degrading_returns_most_negative_health_delta_first():
    ds = RealTrailDataset(
        territory_key="t", available=True,
        trails=[_trail("leve", 70, 66), _trail("grave", 80, 50), _trail("mejora", 50, 60)],
        summary={},
    )
    top = ds.top_degrading(n=2)
    assert [t.name for t in top] == ["grave", "leve"]


def test_geojson_exposes_health_keys_not_stress():
    ds = RealTrailDataset("t", True, [_trail("X", 70, 65)], {})
    fc = build_real_trails_geojson(ds)
    props = fc["features"][0]["properties"]
    assert "health_summer" in props and "delta_health" in props
    assert "ehs_summer" not in props


def test_pnsg_real_output_is_in_health_convention_if_present():
    """Smoke de integración: si la salida real de PNSG existe, toda la salud
    debe caer en [0, 100] y el signo de delta_health ser coherente."""
    ds = get_real_trails("pnsg")
    if not ds.available:
        return  # pipeline no ejecutado en este entorno; no es un fallo
    for t in ds.trails:
        if t.health_summer is not None:
            assert 0.0 <= t.health_summer <= 100.0
        if (t.health_summer is not None and t.health_spring is not None
                and t.delta_health is not None):
            assert abs(t.delta_health - (t.health_summer - t.health_spring)) < 0.05


# ── I-4 (Phase 0.5H) — SCM attribution caveat and stored-value invariance ─────

def test_scm_attribution_caveat_states_model_not_causal():
    """The canonical caveat must name the model provenance without claiming
    causal validation, and without falsely calling the live data simulated."""
    text = SCM_ATTRIBUTION_CAVEAT.lower()
    assert "modelo" in text
    assert "sentinel-2" in text
    assert "causa confirmada" in text or "medici" in text  # causal-denial present
    assert "simulad" not in text  # the underlying observations are real


def test_scm_attribution_label_is_not_simulated_or_bare_real():
    label = SCM_ATTRIBUTION_LABEL.lower()
    assert "simulad" not in label
    assert label.strip() != "real"


def test_scm_label_es_stored_values_unchanged():
    """I-4 changes only display wording; the stored SCM classification values
    (LOCALIZED_IMPACT / MIXED / LANDSCAPE_DRIVEN / None) must not change."""
    for cls in ("LOCALIZED_IMPACT", "MIXED", "LANDSCAPE_DRIVEN", None):
        t = _trail("X", 70, 65, scm_class=cls)
        assert t.scm_class == cls


def test_scm_label_es_mixed_avoids_causal_wording():
    """'MIXED' must not render as an unqualified 'Causa mixta' — that phrasing
    reads as a confirmed cause. The stored class itself is unaffected."""
    t = _trail("X", 70, 65, scm_class="MIXED")
    assert t.scm_class == "MIXED"
    assert "causa" not in t.scm_label_es.lower()
