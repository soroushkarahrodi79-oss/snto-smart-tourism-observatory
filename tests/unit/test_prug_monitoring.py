"""Contracts for the PRUG monitoring roll-up (v3.0, institutional pack).

The non-negotiables under test:

* A territory without PRUG zonification yields ``available=False`` with a
  reason — never a fabricated set of zones (only PNSG carries the cartography).
* Zones are ordered strictest-protection-first (the order a plan is read in),
  and an unknown zone from a cartography update is appended, not dropped.
* The "priority zone" headline follows the plan's own protection hierarchy: the
  most-protected zone that is *nonetheless* degrading, never a hard-coded name.
* Real OAPN cartography × real Sentinel-2 signal is ``EvidenceClass.REAL``, but
  the rendered artifact always carries the seasonal-not-trend, not-field-
  validated caveats.

Deterministic cases run against synthetic ``RealTrail`` datasets injected via a
monkeypatched ``get_real_trails``; a couple of live checks run against the real
committed PNSG trails, mirroring the ``real_trails`` test convention.
"""
from __future__ import annotations

import json

import pytest

from src.platform.evidence import EvidenceClass
from src.platform.real_trails import RealTrail, RealTrailDataset
from src.reporting import prug_monitoring
from src.reporting.prug_monitoring import (
    build_prug_monitoring,
    render_prug_monitoring_markdown,
)

_GEOM = {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}


def _trail(
    trail_id: int,
    *,
    health_summer: float | None,
    delta_health: float | None,
    zone: str | None,
    weight: float | None,
    scm_class: str | None = "LANDSCAPE_DRIVEN",
    budget_eur: float | None = 1000.0,
    priority_index: float | None = None,
) -> RealTrail:
    return RealTrail(
        trail_id=trail_id,
        name=f"Senda {trail_id}",
        length_km=2.0,
        health_spring=None,
        health_summer=health_summer,
        delta_health=delta_health,
        scm_class=scm_class,
        budget_eur=budget_eur,
        geometry=_GEOM,
        prug_zone=zone,
        prug_protection_weight=weight,
        priority_index=priority_index,
    )


def _dataset(trails: list[RealTrail], *, available: bool = True) -> RealTrailDataset:
    return RealTrailDataset(
        territory_key="pnsg",
        available=available,
        trails=trails,
        summary={"territory_name": "Parque de Prueba"},
    )


@pytest.fixture
def patch_trails(monkeypatch):
    def _install(dataset: RealTrailDataset) -> None:
        monkeypatch.setattr(
            prug_monitoring, "get_real_trails", lambda _key: dataset, raising=False
        )
        # Lazy import inside build_prug_monitoring resolves from the module, so
        # patch there; also patch the source in case of direct import.
        monkeypatch.setattr(
            "src.platform.real_trails.get_real_trails",
            lambda _key: dataset,
            raising=True,
        )

    return _install


# ── Honest absence ───────────────────────────────────────────────────────────

def test_unavailable_dataset_reports_not_available(patch_trails) -> None:
    patch_trails(_dataset([], available=False))
    report = build_prug_monitoring("pnsg")
    assert report["available"] is False
    assert "zones" not in report
    assert report["reason"]


def test_dataset_without_prug_zonification_is_not_available(patch_trails) -> None:
    # Trails exist but none carries a PRUG zone/weight (e.g. Sierra del Rincón).
    trails = [
        _trail(1, health_summer=80.0, delta_health=-2.0, zone=None, weight=None)
    ]
    patch_trails(_dataset(trails))
    report = build_prug_monitoring("pnsg")
    assert report["available"] is False
    assert "no se inventan zonas" in report["reason"].lower()


def test_markdown_of_unavailable_report_states_the_reason(patch_trails) -> None:
    patch_trails(_dataset([], available=False))
    md = render_prug_monitoring_markdown(build_prug_monitoring("pnsg"))
    assert "Sin zonificación PRUG" in md


# ── Zone ordering and completeness ───────────────────────────────────────────

def test_zones_are_ordered_strictest_protection_first(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=90.0, delta_health=1.0,
               zone="Zona de Uso Especial", weight=0.25),
        _trail(2, health_summer=90.0, delta_health=1.0,
               zone="Zona de Uso Restringido", weight=0.75),
        _trail(3, health_summer=90.0, delta_health=1.0,
               zone="Zona de Uso Moderado", weight=0.5),
    ]
    patch_trails(_dataset(trails))
    zones = [z["zone"] for z in build_prug_monitoring("pnsg")["zones"]]
    assert zones == [
        "Zona de Uso Restringido",
        "Zona de Uso Moderado",
        "Zona de Uso Especial",
    ]


def test_unknown_zone_is_appended_not_dropped(patch_trails) -> None:
    """A cartography update introducing a new zone must still be reported."""
    trails = [
        _trail(1, health_summer=90.0, delta_health=1.0,
               zone="Zona de Uso Restringido", weight=0.75),
        _trail(2, health_summer=90.0, delta_health=1.0,
               zone="Zona Nueva Desconocida", weight=0.9),
    ]
    patch_trails(_dataset(trails))
    zones = [z["zone"] for z in build_prug_monitoring("pnsg")["zones"]]
    assert "Zona Nueva Desconocida" in zones
    # Known zone comes first; the unknown one is appended after the known order.
    assert zones[0] == "Zona de Uso Restringido"
    assert zones[-1] == "Zona Nueva Desconocida"


# ── The protection–pressure mismatch headline ────────────────────────────────

def test_priority_zone_is_most_protected_zone_that_degrades(patch_trails) -> None:
    trails = [
        # Most protected, but healthy/improving → must NOT be the priority zone.
        _trail(1, health_summer=95.0, delta_health=2.0,
               zone="Zona de Uso Restringido", weight=0.75),
        # Less protected, but degrading → this is the flag.
        _trail(2, health_summer=60.0, delta_health=-8.0,
               zone="Zona de Uso Moderado", weight=0.5),
    ]
    patch_trails(_dataset(trails))
    report = build_prug_monitoring("pnsg")
    assert report["summary"]["priority_zone"] == "Zona de Uso Moderado"


def test_priority_zone_prefers_stricter_protection(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=70.0, delta_health=-3.0,
               zone="Zona de Uso Restringido", weight=0.75),
        _trail(2, health_summer=70.0, delta_health=-3.0,
               zone="Zona de Uso Moderado", weight=0.5),
    ]
    patch_trails(_dataset(trails))
    report = build_prug_monitoring("pnsg")
    assert report["summary"]["priority_zone"] == "Zona de Uso Restringido"


def test_no_priority_zone_when_nothing_degrades(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=95.0, delta_health=3.0,
               zone="Zona de Uso Restringido", weight=0.75),
    ]
    patch_trails(_dataset(trails))
    report = build_prug_monitoring("pnsg")
    assert report["summary"]["priority_zone"] is None


# ── Aggregation correctness ──────────────────────────────────────────────────

def test_degrading_uses_the_same_convention_as_real_trail(patch_trails) -> None:
    """delta_health < 0 is degrading; >= 0 is not; None does not count."""
    trails = [
        _trail(1, health_summer=80.0, delta_health=-1.0,
               zone="Zona de Uso Moderado", weight=0.5),
        _trail(2, health_summer=80.0, delta_health=0.0,
               zone="Zona de Uso Moderado", weight=0.5),
        _trail(3, health_summer=80.0, delta_health=None,
               zone="Zona de Uso Moderado", weight=0.5),
    ]
    patch_trails(_dataset(trails))
    zone = build_prug_monitoring("pnsg")["zones"][0]
    assert zone["n_degrading"] == 1
    assert zone["n_trails"] == 3


def test_degrading_share_ignores_health_less_trails(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=80.0, delta_health=-1.0,
               zone="Zona de Uso Moderado", weight=0.5),
        _trail(2, health_summer=None, delta_health=None,
               zone="Zona de Uso Moderado", weight=0.5),
    ]
    patch_trails(_dataset(trails))
    zone = build_prug_monitoring("pnsg")["zones"][0]
    assert zone["n_with_health"] == 1
    assert zone["degrading_share"] == 1.0


def test_protection_weight_is_none_when_a_zone_carries_conflicting_weights(
    patch_trails,
) -> None:
    """Defensive: a cartography glitch must not silently pick one weight."""
    trails = [
        _trail(1, health_summer=80.0, delta_health=1.0,
               zone="Zona de Uso Moderado", weight=0.5),
        _trail(2, health_summer=80.0, delta_health=1.0,
               zone="Zona de Uso Moderado", weight=0.9),
    ]
    patch_trails(_dataset(trails))
    zone = build_prug_monitoring("pnsg")["zones"][0]
    assert zone["protection_weight"] is None


def test_summary_totals_agree_with_the_zone_rows(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=80.0, delta_health=-1.0,
               zone="Zona de Uso Restringido", weight=0.75, budget_eur=100.0),
        _trail(2, health_summer=70.0, delta_health=-2.0,
               zone="Zona de Uso Moderado", weight=0.5, budget_eur=200.0),
    ]
    patch_trails(_dataset(trails))
    report = build_prug_monitoring("pnsg")
    s = report["summary"]
    assert s["n_trails"] == sum(z["n_trails"] for z in report["zones"])
    assert s["n_degrading"] == sum(z["n_degrading"] for z in report["zones"])
    assert s["total_indicative_budget_eur"] == 300.0


# ── Evidence honesty ─────────────────────────────────────────────────────────

def test_available_report_is_real_evidence(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=80.0, delta_health=-1.0,
               zone="Zona de Uso Moderado", weight=0.5),
    ]
    patch_trails(_dataset(trails))
    report = build_prug_monitoring("pnsg")
    assert report["evidence_class"] == EvidenceClass.REAL.value


def test_evidence_note_carries_seasonal_and_validation_caveats(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=80.0, delta_health=-1.0,
               zone="Zona de Uso Moderado", weight=0.5),
    ]
    patch_trails(_dataset(trails))
    note = build_prug_monitoring("pnsg")["evidence_note"]
    assert "alerta temprana" in note
    assert "#26" in note
    assert "cumplimiento" in note  # explicitly not a compliance verdict


def test_report_is_json_serialisable(patch_trails) -> None:
    trails = [
        _trail(1, health_summer=80.0, delta_health=-1.0,
               zone="Zona de Uso Moderado", weight=0.5, priority_index=10.0),
    ]
    patch_trails(_dataset(trails))
    json.dumps(build_prug_monitoring("pnsg"), ensure_ascii=False)


# ── Sentinel-2 provenance qualified separately from EvidenceClass (PR 0.5.2) ──

def _zoned_trails() -> list[RealTrail]:
    return [
        _trail(1, health_summer=80.0, delta_health=-1.0,
               zone="Zona de Uso Moderado", weight=0.5),
    ]


def _force_snapshot(monkeypatch, snapshot) -> None:
    """Pin the lazily-imported ``snapshot_provenance`` used inside the report."""
    monkeypatch.setattr(
        "src.platform.provenance.snapshot_provenance",
        lambda _key: snapshot,
        raising=True,
    )


def test_provenance_block_lists_paired_scenes_in_state_a(patch_trails, monkeypatch):
    from src.platform.provenance import SceneReference, SnapshotProvenance
    from src.temporal import DataStatus, TrendReadiness

    snap = SnapshotProvenance(
        status=DataStatus.REAL, derived_output_available=True,
        raw_scenes_available=True, provenance_complete=True,
        locally_reproducible=True, n_scenes=2,
        scene_dates=["2025-08-10", "2026-04-10"],
        scene_refs=[SceneReference("S2A", "2025-08-10"),
                    SceneReference("S2B", "2026-04-10")],
        readiness=TrendReadiness.SEASONAL_ONLY,
        mann_kendall_justified=False, seasonal_delta_valid=True,
        inference_label="…", caveat="…",
    )
    patch_trails(_dataset(_zoned_trails()))
    _force_snapshot(monkeypatch, snap)
    report = build_prug_monitoring("pnsg")
    # EvidenceClass stays REAL; provenance is qualified separately.
    assert report["evidence_class"] == EvidenceClass.REAL.value
    prov = report["provenance"]
    assert prov["raw_scenes_available"] is True
    assert prov["provenance_complete"] is True
    assert prov["locally_reproducible"] is True
    assert {(r["sensor_id"], r["acquisition_date"]) for r in prov["scene_references"]} == {
        ("S2A", "2025-08-10"), ("S2B", "2026-04-10"),
    }
    md = render_prug_monitoring_markdown(report)
    assert "S2A" in md and "2025-08-10" in md


def test_provenance_block_degrades_in_state_b(patch_trails, monkeypatch):
    from src.platform.provenance import SnapshotProvenance
    from src.temporal import DataStatus

    snap = SnapshotProvenance(
        status=DataStatus.REAL, derived_output_available=True,
        raw_scenes_available=False, provenance_complete=False,
        locally_reproducible=False, n_scenes=None,
        scene_dates=[], scene_refs=[], readiness=None,
        mann_kendall_justified=False, seasonal_delta_valid=False,
        inference_label="…", caveat="…",
    )
    patch_trails(_dataset(_zoned_trails()))
    _force_snapshot(monkeypatch, snap)
    report = build_prug_monitoring("pnsg")
    # Still REAL-derived, but provenance flagged incomplete / not reproducible.
    assert report["evidence_class"] == EvidenceClass.REAL.value
    prov = report["provenance"]
    assert prov["raw_scenes_available"] is False
    assert prov["provenance_complete"] is False
    assert prov["locally_reproducible"] is False
    assert prov["scene_references"] == []
    md = render_prug_monitoring_markdown(report)
    assert "no verificables en este entorno" in md
    assert "no reproducible localmente" in md


# ── Live checks against the real committed PNSG trails ───────────────────────

def test_live_pnsg_report_is_available_and_real() -> None:
    report = build_prug_monitoring("pnsg")
    assert report["available"] is True
    assert report["evidence_class"] == EvidenceClass.REAL.value
    assert report["summary"]["n_trails"] > 0


def test_live_pnsg_priority_zone_is_a_real_prug_zone() -> None:
    report = build_prug_monitoring("pnsg")
    pz = report["summary"]["priority_zone"]
    # Whatever the data says today, it must be one of the zones the report emits.
    assert pz in {z["zone"] for z in report["zones"]}
