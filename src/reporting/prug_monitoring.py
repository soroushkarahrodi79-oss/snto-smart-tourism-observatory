"""PRUG monitoring roll-up (v3.0, institutional productization).

WHY
===
The roadmap's v3.0 milestone names a **CETS/PRUG reporting pack**
(``docs/roadmap/plan_v3_roadmap.md``), and the institutional dossier
(``docs/dossier_institucional_OAPN.md`` §3) states one of SNTO's stated aims to
the park's Dirección is *"apoyo al seguimiento del PRUG"*. The CETS surface
(``cets_readiness.py``, PR #123) covers the accreditation framework; this module
covers the other half: the park's own management instrument.

The **PRUG** (Plan Rector de Uso y Gestión) is the legal management plan of a
Spanish national park. Its backbone is a **zonificación** — every hectare is
assigned a management regime (Zona de Reserva, Uso Restringido, Uso Moderado,
Uso Especial), and the stricter the zone, the lower the tolerated human impact.
SNTO already carries that official OAPN zonification per trail
(``real_trails.RealTrail.prug_zone`` + ``prug_protection_weight``), joined to
the real Sentinel-2 environmental signal.

WHAT THIS REPORT DOES
=====================
It rolls up the **real** per-trail evidence **by PRUG management zone**, so a
manager reads the park through the same lens the plan is written in: which zone
is degrading, where the observed pressure contradicts the intended protection
level, and how the restoration budget distributes across the regimes.

The analytically useful signal is the **protection–pressure mismatch**: a trail
in a strictly protected zone (Uso Restringido) that is nonetheless losing health
is a stronger management flag than the same degradation in a Uso Especial zone,
because the plan promised the former more protection. That is exactly what the
existing ``priority_index = (100 − health) × protection_weight`` encodes, so the
roll-up aggregates it per zone rather than inventing a new metric.

HONESTY BOUNDARIES (carried verbatim from the dossier's own caveats)
====================================================================
* The zonification is real OAPN cartography and the EHS/ΔEHS/SCM are real
  Sentinel-2 signals, so the roll-up is ``EvidenceClass.REAL`` — **but** the
  current snapshot is a **two-scene seasonal ΔEHS**: an *early-warning*
  signal (``DecisionUse.PRIORITIZATION``), never a multi-year trend and never a
  compliance verdict on the plan.
* **No trail is field-validated** (campaign #26 pending): "degrada en zona
  protegida" flags *where to look*, it does not certify a management breach.
* The budget is the indicative TIS figure already shown on the dashboard; it is
  a planning estimate, not a committed cost.
* A territory without PRUG zonification (only PNSG carries it today) yields an
  ``available=False`` report — never a fabricated set of zones.
"""
from __future__ import annotations

from dataclasses import dataclass

from src._version import __version__
from src.platform.evidence import EvidenceClass

# PRUG management regimes ordered by protection level, strictest first — the
# order a plan is read in. Any zone the data carries that is not listed here
# (or the "outside zonification" bucket) is appended after these, so an OAPN
# cartography update cannot silently drop a zone from the report.
_ZONE_ORDER: tuple[str, ...] = (
    "Zona de Reserva",
    "Zona de Uso Restringido",
    "Zona de Uso Moderado",
    "Zona de Uso Especial",
    "Fuera de zonificación",
)

# A trail is counted as "degrading" when its health falls from spring to summer.
# In the health convention (100 = healthy), that is delta_health < 0. This
# mirrors ``RealTrail.is_degrading`` exactly rather than re-deriving a threshold.
_DEGRADING = "delta_health < 0"


@dataclass(frozen=True)
class ZoneRollup:
    """Aggregated real evidence for one PRUG management zone."""

    zone: str
    protection_weight: float | None
    n_trails: int
    length_km: float
    ehs_summer_mean: float | None
    n_degrading: int
    n_with_health: int
    scm_localized: int          # human-use signal (LOCALIZED_IMPACT)
    scm_mixed: int
    scm_landscape: int          # climate-scale signal (LANDSCAPE_DRIVEN)
    priority_index_mean: float | None
    budget_eur: float | None

    @property
    def degrading_share(self) -> float | None:
        """Fraction of health-bearing trails in this zone that are degrading."""
        if self.n_with_health == 0:
            return None
        return round(self.n_degrading / self.n_with_health, 4)


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _zone_sort_key(zone: str) -> tuple[int, str]:
    """Strictest-first order, with unknown zones appended alphabetically."""
    try:
        return (_ZONE_ORDER.index(zone), "")
    except ValueError:
        return (len(_ZONE_ORDER), zone)


def _rollup_one_zone(zone: str, trails: list) -> ZoneRollup:
    healths = [t.health_summer for t in trails if t.health_summer is not None]
    prio = [t.priority_index for t in trails if t.priority_index is not None]
    budgets = [t.budget_eur for t in trails if t.budget_eur is not None]
    weights = {
        t.prug_protection_weight
        for t in trails
        if t.prug_protection_weight is not None
    }
    return ZoneRollup(
        zone=zone,
        # One weight per zone by construction; if the cartography ever disagrees
        # we surface None rather than pick one silently.
        protection_weight=next(iter(weights)) if len(weights) == 1 else None,
        n_trails=len(trails),
        length_km=round(sum(t.length_km for t in trails), 1),
        ehs_summer_mean=_mean(healths),
        n_degrading=sum(1 for t in trails if t.is_degrading),
        n_with_health=len(healths),
        scm_localized=sum(1 for t in trails if t.scm_class == "LOCALIZED_IMPACT"),
        scm_mixed=sum(1 for t in trails if t.scm_class == "MIXED"),
        scm_landscape=sum(1 for t in trails if t.scm_class == "LANDSCAPE_DRIVEN"),
        priority_index_mean=_mean(prio),
        budget_eur=round(sum(budgets), 2) if budgets else None,
    )


def build_prug_monitoring(
    dashboard_key: str,
    *,
    report_date: str | None = None,
) -> dict:
    """Assemble the PRUG-zone monitoring roll-up for a territory.

    Returns a JSON-serialisable dict. ``available`` is ``False`` (with an
    explicit reason) when the territory carries no real trails or no PRUG
    zonification — the report never fabricates zones for a park that lacks them.

    Args:
        dashboard_key: dashboard territory key (e.g. ``"pnsg"``).
        report_date: ISO date, or ``None`` when generation provenance is not
            recorded. Stored as ``None`` in the returned dict — never replaced
            by today's date. Markdown renderers translate ``None`` to
            "no registrada" at presentation time.
    """

    # Imported lazily: real-trail loading pulls Pipeline-A outputs off disk.
    from src.platform.real_trails import get_real_trails

    dataset = get_real_trails(dashboard_key)
    metadata = {
        "report_date": report_date,
        "system": "Smart Natural Tourism Observatory (SNTO)",
        "version": __version__,
        "territory_key": dashboard_key,
        "instrument": "Plan Rector de Uso y Gestión (PRUG) — seguimiento",
    }

    if not dataset.available or not dataset.trails:
        return {
            "metadata": metadata,
            "available": False,
            "reason": (
                "El territorio no tiene sendas reales cargadas (Pipeline A): "
                "sin ellas no hay seguimiento PRUG posible."
            ),
        }
    # A territory "has PRUG" when its trails carry the OAPN zone label — checked
    # directly, not via ``dataset.has_prug`` (which keys on ``priority_index``,
    # present only when both health and protection weight exist). A zone
    # assignment without a computable priority index is still a real zone.
    if not any(t.prug_zone for t in dataset.trails):
        return {
            "metadata": metadata,
            "available": False,
            "reason": (
                "Las sendas de este territorio no llevan zonificación PRUG "
                "(hoy solo el PNSG la tiene). No se inventan zonas."
            ),
        }

    metadata["territory"] = dataset.summary.get("territory_name", dashboard_key)

    # Provenance of the Sentinel-2 signal behind the ΔEHS. ``EvidenceClass.REAL``
    # (below) is the *trust tier* of the derived signal and stays correct; this
    # block qualifies, separately, whether the raw source scenes and their
    # sensor/date metadata can be verified in this environment. It never changes
    # priority_index, ΔEHS, thresholds or management logic.
    from src.platform.provenance import snapshot_provenance

    _snapshot = snapshot_provenance(dashboard_key)
    if _snapshot.scene_refs:
        _scene_note = "Escenas fuente: " + " · ".join(
            f"{r.sensor_id} ({r.acquisition_date})" for r in _snapshot.scene_refs
        )
    else:
        _scene_note = (
            "Escenas fuente Sentinel-2 (sensor/fecha) no verificables en este "
            "entorno; señal derivada real pero procedencia local incompleta y no "
            "reproducible localmente."
        )
    provenance = {
        "raw_scenes_available": _snapshot.raw_scenes_available,
        "provenance_complete": _snapshot.provenance_complete,
        "locally_reproducible": _snapshot.locally_reproducible,
        "scene_references": [
            {"sensor_id": r.sensor_id, "acquisition_date": r.acquisition_date}
            for r in _snapshot.scene_refs
        ],
        "note": _scene_note,
    }

    grouped: dict[str, list] = {}
    for trail in dataset.trails:
        grouped.setdefault(trail.prug_zone or "Fuera de zonificación", []).append(
            trail
        )

    zones = [
        _rollup_one_zone(zone, trails)
        for zone, trails in sorted(
            grouped.items(), key=lambda kv: _zone_sort_key(kv[0])
        )
    ]

    total_budget = sum(z.budget_eur for z in zones if z.budget_eur is not None)
    total_degrading = sum(z.n_degrading for z in zones)

    # The management headline: the strictest-protected zone that is nonetheless
    # degrading, if any. Uses the declared protection weight, so it tracks the
    # plan's own hierarchy rather than a hard-coded zone name.
    flagged = [
        z for z in zones if z.protection_weight is not None and z.n_degrading > 0
    ]
    flagged.sort(key=lambda z: z.protection_weight or 0.0, reverse=True)
    priority_zone = flagged[0].zone if flagged else None

    return {
        "metadata": metadata,
        "available": True,
        "evidence_class": EvidenceClass.REAL.value,
        "provenance": provenance,
        "evidence_note": (
            "Zonificación PRUG (cartografía oficial OAPN) cruzada con señal "
            "Sentinel-2 real (EHS/ΔEHS/SCM). El ΔEHS de dos escenas es una "
            "**alerta temprana estacional**, no una tendencia plurianual ni un "
            "veredicto de cumplimiento del Plan; ninguna senda está validada en "
            "campo (campaña #26 pendiente); el presupuesto es orientativo."
        ),
        "mismatch_note": (
            "«Índice de prioridad» = (100 − salud) × peso de protección: pondera "
            "el deterioro por el nivel de protección que el PRUG asigna a la "
            "zona. Un deterioro en Uso Restringido pesa más que el mismo "
            "deterioro en Uso Especial — señala dónde mirar primero, no un "
            "incumplimiento."
        ),
        "summary": {
            "n_zones": len(zones),
            "n_trails": sum(z.n_trails for z in zones),
            "total_length_km": round(sum(z.length_km for z in zones), 1),
            "n_degrading": total_degrading,
            "total_indicative_budget_eur": (
                round(total_budget, 2) if total_budget else None
            ),
            "priority_zone": priority_zone,
        },
        "zones": [_zone_dict(z) for z in zones],
    }


def _zone_dict(zone: ZoneRollup) -> dict:
    d = zone.__dict__.copy()
    d["degrading_share"] = zone.degrading_share
    return d


def render_prug_monitoring_markdown(report: dict) -> str:
    """Render the PRUG monitoring roll-up as an exportable Markdown document."""
    m = report["metadata"]
    lines = [
        f"# Seguimiento del PRUG por zonas — {m.get('territory', m['territory_key'])}",
        "",
        f"**Instrumento:** {m['instrument']}  ·  **Fecha:** {m['report_date'] or 'no registrada'}  ·  "
        f"**SNTO** v{m['version']}",
        "",
    ]

    if not report.get("available"):
        lines += [
            f"> ⚠️ {report['reason']}",
            "",
            "_Sin zonificación PRUG no se genera el seguimiento por zonas._",
            "",
        ]
        return "\n".join(lines)

    s = report["summary"]
    lines += [
        f"> {report['evidence_note']}",
        "",
        f"> {report['mismatch_note']}",
        "",
    ]
    _prov = report.get("provenance")
    if _prov:
        lines += [f"> **Procedencia Sentinel-2:** {_prov['note']}", ""]
    lines += [
        "## Panorama",
        "",
        f"- Zonas PRUG con sendas: **{s['n_zones']}**",
        f"- Sendas analizadas: **{s['n_trails']}** ({s['total_length_km']} km)",
        f"- Sendas con deterioro estacional: **{s['n_degrading']}**",
    ]
    if s["priority_zone"]:
        lines.append(
            f"- Zona de atención prioritaria (más protegida con deterioro "
            f"activo): **{s['priority_zone']}**"
        )
    if s["total_indicative_budget_eur"]:
        lines.append(
            f"- Presupuesto orientativo total: "
            f"**{s['total_indicative_budget_eur']:,.0f} €**"
        )
    lines += ["", "## Estado por zona de gestión (más protegida primero)", ""]

    cols = [
        "Zona PRUG", "Peso protección", "Sendas", "km", "EHS verano medio",
        "Deteriorándose", "SCM uso / mixto / clima", "Índice prioridad medio",
        "Coste orientativo (€)",
    ]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "|".join("---" for _ in cols) + "|")
    for z in report["zones"]:
        weight = (
            f"{z['protection_weight']:.2f}"
            if z["protection_weight"] is not None
            else "—"
        )
        ehs = (
            f"{z['ehs_summer_mean']:.1f}/100"
            if z["ehs_summer_mean"] is not None
            else "sin dato"
        )
        share = z["degrading_share"]
        degr = (
            f"{z['n_degrading']}/{z['n_with_health']}"
            + (f" ({share:.0%})" if share is not None else "")
        )
        scm = f"{z['scm_localized']} / {z['scm_mixed']} / {z['scm_landscape']}"
        prio = (
            f"{z['priority_index_mean']:.1f}"
            if z["priority_index_mean"] is not None
            else "—"
        )
        budget = (
            f"{z['budget_eur']:,.0f}" if z["budget_eur"] is not None else "—"
        )
        lines.append(
            f"| {z['zone']} | {weight} | {z['n_trails']} | {z['length_km']:.0f} | "
            f"{ehs} | {degr} | {scm} | {prio} | {budget} |"
        )

    lines += [
        "",
        (
            "_Seguimiento orientativo generado por SNTO sobre cartografía oficial "
            "OAPN y señal Sentinel-2 real. Alerta temprana estacional, no "
            "tendencia plurianual ni veredicto de cumplimiento del Plan; no "
            "sustituye la inspección de campo ni la validación técnica local._"
        ),
        "",
    ]
    return "\n".join(lines)
