"""Derived blocks of the OAPN institutional dossier (v3.0, productization).

WHY
===
``docs/dossier_institucional_OAPN.md`` is the document sent to the park's
Dirección and to EUROPARC — it sits on the outreach checklist
(``docs/kit_difusion.md``). It was written by hand at ``v1.0 (junio 2026)`` and
its figures drifted badly from the system they describe. Measured against the
live repository when this module was written:

===========================================  ==================  ==============
Dossier claim                                Live value          Drift
===========================================  ==================  ==============
"17 de 73 senderos" degrading                46 of 218           wrong base
SCM "27 localizados · 9 mixtos · 37 paisaje" 24 · 29 · 165       wrong
"Presupuesto indicativo ~205.000 €"          1.435.721 €         **7× under**
"474 tests automatizados"                    1008                wrong
CETS "Principio 10 de forma **directa**"     partial / missing   **overclaim**
===========================================  ==================  ==============

Two of those matter a great deal: a restoration budget understated sevenfold in
a document used to open an institutional conversation, and a claim of *direct*
coverage of CETS Principle 10 (visitor-flow management) at exactly the point
where the system has **no real data** — the MITMA mobility snapshot is not
ingested. That is the same overclaim corrected internally in the README and
CLAUDE.md, still live in the document that leaves the building.

WHAT THIS MODULE DOES
=====================
It rebuilds only the **derived** sections of the dossier from the same live
sources that already feed the CETS and PRUG reports, so the outward-facing
document cannot contradict the system again:

* §4 *Resultados* ← :func:`src.platform.real_trails.get_real_trails` and
  :func:`src.reporting.prug_monitoring.build_prug_monitoring`
* §5 *Madurez* ← :func:`src.reporting.cets_readiness.resolve_signals`
* §6 *Marco* ← :func:`src.reporting.cets_readiness.build_cets_readiness`, so the
  CETS coverage stated here **is** the declared mapping in that module rather
  than a prose duplicate that can drift away from it.

The editorial prose (the problem, the proposal, the asks, the contact) is *not*
generated: it is the author's institutional voice and stays hand-edited. Only
the blocks between the ``SNTO:AUTO`` markers are replaced (see
``scripts/build_dossier.py``).

HONESTY RULES (inherited from the CETS/PRUG surfaces)
=====================================================
* CETS coverage is reported at the level ``cets_readiness`` declares, annotated
  with the evidence class computed today — a principle whose evidence is
  ``missing`` is never described as directly covered.
* A two-scene ΔEHS is a **seasonal early warning**, never a multi-year trend.
* No trail is field-validated (campaign #26 pending); the budget is indicative.
* A territory with no real trails yields an explicit "no disponible" block
  rather than an invented figure.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src._version import __version__
from src.platform.evidence import EvidenceClass
from src.reporting.cets_readiness import Coverage

# Marker names for the replaceable blocks. The script pairs each with
# ``<!-- SNTO:AUTO:<name> -->`` / ``<!-- /SNTO:AUTO:<name> -->`` in the Markdown.
BLOCK_RESULTS = "resultados"
BLOCK_MATURITY = "madurez"
BLOCK_FRAMEWORK = "marco"

ALL_BLOCKS: tuple[str, ...] = (BLOCK_RESULTS, BLOCK_MATURITY, BLOCK_FRAMEWORK)

# CETS principles the dossier's framework section speaks to, in reading order.
_FRAMEWORK_PRINCIPLES: tuple[str, ...] = (
    "p03_patrimonio",
    "p10_flujos",
    "p01_participacion",
    "p02_estrategia",
)

# How a declared Coverage reads in institutional prose. Deliberately conservative:
# only CORE earns "de forma directa", so the dossier can never claim more than
# the CETS module declares.
_COVERAGE_PROSE: dict[Coverage, str] = {
    Coverage.CORE: "de forma directa",
    Coverage.PARTIAL: "de forma parcial",
    Coverage.INSTRUMENTAL: "de forma instrumental",
    Coverage.OUT_OF_SCOPE: "fuera del alcance del sistema",
}

# Evidence caveat appended when a principle's live evidence does not back the
# declared coverage — the specific failure this module exists to prevent.
_EVIDENCE_CAVEAT: dict[str, str] = {
    EvidenceClass.MISSING.value: "sin dato real hoy",
    EvidenceClass.SIMULATED.value: "hoy sobre simulación",
    EvidenceClass.SYNTHETIC.value: "hoy sobre datos de demostración",
    EvidenceClass.CALIBRATED.value: "sobre dato calibrado",
}


@dataclass(frozen=True)
class DossierFacts:
    """The live figures the dossier's derived sections state."""

    territory_name: str
    n_trails: int
    total_length_km: float
    n_degrading: int
    n_with_delta: int
    scm_localized: int
    scm_mixed: int
    scm_landscape: int
    budget_eur: float | None
    ehs_summer_mean: float | None
    priority_zone: str | None
    n_municipalities: int | None


def collect_facts(dashboard_key: str = "pnsg") -> DossierFacts | None:
    """Gather the live figures for a territory, or ``None`` if it has no trails.

    Every number comes from an existing loader; nothing is recomputed here, so
    the dossier and the dashboard cannot disagree.
    """
    from src.platform.real_trails import get_real_trails
    from src.reporting.prug_monitoring import build_prug_monitoring

    dataset = get_real_trails(dashboard_key)
    if not dataset.available or not dataset.trails:
        return None

    s = dataset.summary
    prug = build_prug_monitoring(dashboard_key)
    priority_zone = (
        prug["summary"]["priority_zone"] if prug.get("available") else None
    )

    # Socioeconomic coverage is optional context; absence degrades to None.
    n_municipalities: int | None
    try:
        from src.socioeconomic.loader import load_municipalities

        n_municipalities = load_municipalities().n_municipalities
    except (OSError, ValueError, ImportError):
        n_municipalities = None

    return DossierFacts(
        territory_name=s.get("territory_name", dashboard_key),
        n_trails=int(s.get("n_trails", len(dataset.trails))),
        total_length_km=float(s.get("total_length_km", 0.0)),
        n_degrading=int(s.get("n_degrading_positive_delta", 0)),
        n_with_delta=int(s.get("n_with_valid_delta", 0)),
        scm_localized=int(s.get("scm_localized", 0)),
        scm_mixed=int(s.get("scm_mixed", 0)),
        scm_landscape=int(s.get("scm_landscape", 0)),
        budget_eur=s.get("total_budget_eur"),
        ehs_summer_mean=s.get("ehs_summer_mean"),
        priority_zone=priority_zone,
        n_municipalities=n_municipalities,
    )


def _render_results(facts: DossierFacts | None) -> str:
    if facts is None:
        return (
            "> ⚠️ Sin sendas reales cargadas para este territorio: no se publican "
            "resultados hasta que el Pipeline A produzca su salida."
        )

    budget = (
        f"{facts.budget_eur:,.0f} €".replace(",", ".")
        if facts.budget_eur
        else "pendiente de estimar"
    )
    lines = [
        f"- **{facts.n_degrading} de {facts.n_with_delta} senderos** muestran "
        "deterioro estacional activo (ΔEHS de degradación).",
        f"- Clasificación causal SCM: **{facts.scm_localized} localizados** "
        f"(señal de uso) · **{facts.scm_mixed} mixtos** · "
        f"**{facts.scm_landscape} a escala de paisaje** (señal climática).",
        f"- **Presupuesto indicativo de intervención: {budget}**, modulado por el "
        "factor causal de cada tramo.",
    ]
    if facts.ehs_summer_mean is not None:
        lines.append(
            f"- Salud ecológica media en verano: **{facts.ehs_summer_mean:.1f}/100** "
            f"sobre {facts.total_length_km:,.0f} km analizados.".replace(",", ".")
        )
    if facts.priority_zone:
        lines.append(
            f"- Zona PRUG de atención prioritaria (mayor protección con deterioro "
            f"activo): **{facts.priority_zone}**."
        )
    if facts.n_municipalities:
        lines.append(
            f"- Cobertura socioeconómica: **{facts.n_municipalities} municipios** "
            "del entorno del Parque."
        )
    return "\n".join(lines)


def _render_maturity(signals: dict) -> str:
    # The exact test count is deliberately NOT stated here. It changes with every
    # PR that adds a test, which would make the CI freshness check fail on
    # unrelated work — a guard that cries wolf gets ignored. README carries the
    # live number (badge + §8); this document states the qualitative fact.
    tests = (
        "- Suite de tests automatizados **verde** en cada cambio, con CI/CD "
        "separado del despliegue (el conteo vivo está en el README del "
        "repositorio)."
    )

    def _yes_no(flag: bool) -> str:
        return "sí" if flag else "**aún no**"

    return "\n".join(
        [
            tests,
            "- Desplegado en la nube (Azure Container Apps), panel con cuatro capas "
            "de decisión y tres vistas por audiencia.",
            "- Etiquetado de procedencia visible en cada dato: **real / calibrado / "
            "simulado / sintético**.",
            "- Estado de las vías de dato real (comprobado en vivo): serie satelital "
            f"{_yes_no(signals['satellite_real'])} · movilidad MITMA "
            f"{_yes_no(signals['mobility_real'])} · zonas SCM multiescala "
            f"{_yes_no(signals['scm_zones_real'])} · serie socioeconómica "
            f"{_yes_no(signals['socioeconomic_series'])}.",
            f"- Parcelas de campo con medición registrada: "
            f"**{signals['field_measured_plots']}** — la campaña de validación "
            "(#26) sigue pendiente, por lo que **no se afirma validación de campo**.",
            "- Documentación completa: arquitectura, whitepaper, protocolo de "
            "validación de campo, límites técnicos.",
        ]
    )


def _principle_sentence(principle: dict) -> str:
    coverage = Coverage(principle["coverage"])
    prose = _COVERAGE_PROSE[coverage]
    caveat = _EVIDENCE_CAVEAT.get(principle["evidence_class"])
    # Strip the leading "N · " numbering from the module's title for prose flow.
    title = principle["title"]
    label = title.split("·", 1)[1].strip() if "·" in title else title
    number = title.split("·", 1)[0].strip() if "·" in title else "?"
    sentence = f"**Principio {number}** ({label}): cubierto {prose}"
    if caveat:
        sentence += f" — {caveat}"
    return sentence + "."


def _render_framework(cets_report: dict) -> str:
    by_key = {p["key"]: p for p in cets_report["principles"]}
    lines = [
        "El SNTO se diseña en sintonía con los marcos europeos de reporte de "
        "espacios protegidos (Natura 2000 / EUROPARC / SISMOTUR) y con la **Carta "
        "Europea de Turismo Sostenible (CETS)**. La cobertura declarada por "
        "principio, con la evidencia que la respalda hoy:",
        "",
    ]
    for key in _FRAMEWORK_PRINCIPLES:
        principle = by_key.get(key)
        if principle is not None:
            lines.append(f"- {_principle_sentence(principle)}")
    lines += [
        "",
        "La correspondencia completa con los componentes del dosier de la Fase I y "
        "los 10 principios —incluidos los que quedan **fuera del alcance** de un "
        "sistema de evidencia teledetectada— se genera desde el propio observatorio "
        "(módulo «Informes y exportaciones»).",
    ]
    return "\n".join(lines)


def build_dossier_blocks(dashboard_key: str = "pnsg") -> dict[str, str]:
    """Build every replaceable block of the dossier, keyed by marker name.

    Deterministic for a given repository state: the same inputs always render the
    same Markdown, which is what lets ``scripts/build_dossier.py --check`` act as
    a CI freshness gate without false alarms.

    Args:
        dashboard_key: territory key to describe (``"pnsg"`` today).

    Returns:
        ``{block_name: markdown}`` for every name in :data:`ALL_BLOCKS`.
    """
    # build_cets_readiness() already resolves the live evidence signals, so the
    # maturity block reads them off its report rather than probing disk twice.
    from src.reporting.cets_readiness import build_cets_readiness

    facts = collect_facts(dashboard_key)
    cets_report = build_cets_readiness(
        territory_name=facts.territory_name if facts else dashboard_key,
        park=dashboard_key,
    )

    return {
        BLOCK_RESULTS: _render_results(facts),
        BLOCK_MATURITY: _render_maturity(cets_report["signals"]),
        BLOCK_FRAMEWORK: _render_framework(cets_report),
    }


def dossier_version_line(today: date | None = None) -> str:
    """The dossier's version/date line, tracking the live package version."""
    stamp = (today or date.today()).isoformat()
    return (
        f"**Dossier institucional · generado desde SNTO v{__version__} · "
        f"{stamp}**"
    )
