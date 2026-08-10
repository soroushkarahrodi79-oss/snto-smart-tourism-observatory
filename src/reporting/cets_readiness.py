"""CETS Fase I readiness / correspondence report (v3.0, institutional productization).

WHY
===
The roadmap's v3.0 milestone names an institutional reporting pack (CETS/PRUG,
OAPN dossier — ``docs/roadmap/plan_v3_roadmap.md``). The raw material already
exists as prose: ``docs/archive/CETS_Phase1_correspondence.md`` maps the Carta
Europea de Turismo Sostenible Fase I dossier onto SNTO modules. But that
document is **archived and stale in two ways**: it targets Sierra del Rincón
(no longer the active pilot) at SNTO ``v0.1.0``, and several of its gap findings
have since been closed — it calls the socioeconomic layer *"débil"* (the SVI
layer and its real time series now exist) and MITMA visitor-flow integration
*"prevista"* (it shipped in v2.2).

This module turns that frozen prose into a **live readiness report**: the
CETS↔SNTO mapping is declared here once, and each row's evidence state is
resolved against what the repository actually holds *right now* for the
requested territory. Re-running it after the field campaign, or for a second
park, yields a different — and still honest — answer without editing prose.

TWO ORTHOGONAL AXES, DELIBERATELY NOT ONE SCORE
===============================================
The archived document scored each row on a 1–5 "madurez" scale. This module
**does not reproduce that scale**: a single 1–5 number blends an editorial
judgement ("does SNTO even address this requirement?") with a factual one
("what class of evidence backs it today?"), and reads as a measurement when
only the second half is measurable. They are kept apart:

* :class:`Coverage` — *declared* editorial position on whether SNTO addresses
  the requirement at all (``CORE`` / ``PARTIAL`` / ``INSTRUMENTAL`` /
  ``OUT_OF_SCOPE``). Fixed in the tables below, traceable to the official
  Carta text; it does not change with data.
* :class:`~src.platform.evidence.EvidenceClass` — *computed* from live
  repository state (real Sentinel-2 trends on disk? a real MITMA snapshot? real
  multi-scale SCM zones? an SVI history? measured field plots?). This is
  ADR-004's canonical five-tier vocabulary, deliberately **not**
  ``temporal.manifest.DataStatus``: that one has no ``SIMULATED`` tier, so it
  would collapse a model-derived projection into ``SYNTHETIC`` alongside demo
  mocks — exactly the blurring ADR-004 forbids. Use
  ``evidence.from_data_status()`` if a ``DataStatus`` ever needs reconciling in.

WHAT THIS REPORT REFUSES TO DO
==============================
* It never marks any row *externally validated*. The satellite↔field agreement
  runner exists but the campaign (#26) has not run, so the strongest evidence
  class any row can reach is ``REAL`` (real observation), never a validation
  claim (ADR-003, ADR-004).
* It never hides the principles SNTO does **not** address. Principles 4, 6 and
  7 (visitor experience, tourism products, stakeholder training) are
  programmatic, outside a technical evidence system, and are emitted as
  ``OUT_OF_SCOPE`` rows. A readiness document that silently omitted them would
  overstate coverage — the specific failure mode this project's
  non-negotiables exist to prevent.
* It is a **preparation aid, not a submission**. The Fase I dossier is built by
  a Foro and a Grupo de Trabajo; SNTO instruments the candidacy, it does not
  constitute it. Every rendered artifact says so.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src._version import __version__
from src.platform.evidence import EvidenceClass

_ROOT = Path(__file__).resolve().parents[2]
_FIELD_CSV = (
    _ROOT / "clean_assets/field_validation/pnsg_field_observations_template.csv"
)


class Coverage(str, Enum):
    """Declared editorial position on how far SNTO addresses a requirement.

    Not computed and not a score — a four-way qualitative statement, fixed in
    this module's tables and unchanged by data availability.
    """

    CORE = "core"                  # SNTO's differential contribution
    PARTIAL = "partial"            # addressed, with a named limitation
    INSTRUMENTAL = "instrumental"  # SNTO feeds a human/organisational process
    OUT_OF_SCOPE = "out_of_scope"  # deliberately outside a technical system


_COVERAGE_LABELS: dict[Coverage, str] = {
    Coverage.CORE: "🟢 Núcleo",
    Coverage.PARTIAL: "🟡 Parcial",
    Coverage.INSTRUMENTAL: "🔵 Instrumental",
    Coverage.OUT_OF_SCOPE: "⚪ Fuera de alcance",
}

# Evidence-signal keys. Each row declares which live signal backs it; the
# resolver maps each signal to an EvidenceClass for the requested territory.
# ``None`` means "no data backs this row at all" — an organisational or
# out-of-scope requirement — which resolves to MISSING rather than pretending.
SIGNAL_SATELLITE = "satellite_trends"
SIGNAL_MOBILITY = "mobility"
SIGNAL_SOCIOECONOMIC = "socioeconomic"
SIGNAL_FIELD = "field_validation"
SIGNAL_CURATED = "curated_portfolio"
SIGNAL_FORECAST = "forecast"
# Causal attribution is backed by multi-scale zones, *not* by the trend series:
# without a real GEE zone export the SCM runs its α-decay simulation
# (``src.spatial_causality.analyzer.evidence_class_for_source`` → SIMULATED).
# Keeping this signal separate from SIGNAL_SATELLITE is what stops the report
# from inheriting the trend series' REAL status for a simulated inference.
SIGNAL_SCM_ZONES = "scm_zones"


@dataclass(frozen=True)
class _Requirement:
    """A CETS requirement and its declared SNTO correspondence."""

    key: str
    title: str
    snto_module: str
    indicator: str
    coverage: Coverage
    signal: str | None
    note: str


# ── Fase I dossier components (EUROPARC-España) ───────────────────────────────
# Terminology verified in docs/archive/CETS_Phase1_correspondence.md §0 against
# EUROPARC-España's published Fase I dossier structure.
_COMPONENTS: tuple[_Requirement, ...] = (
    _Requirement(
        key="diagnostico_conservacion",
        title="Diagnóstico — estado de conservación",
        snto_module="`src/platform/satellite_trends.py`, `src/metrics/`",
        indicator="EHS por activo (0–100) y tendencia Mann-Kendall NDVI/NDMI",
        coverage=Coverage.CORE,
        signal=SIGNAL_SATELLITE,
        note=(
            "Monitorización espectral objetiva; supera el estándar cualitativo "
            "habitual del diagnóstico de uso público."
        ),
    ),
    _Requirement(
        key="diagnostico_atribucion",
        title="Diagnóstico — atribución del impacto",
        snto_module="`src/spatial_causality/`",
        indicator="Clasificación LOCALIZED / LANDSCAPE / MIXED (Spatial Impact "
                  "Gradient)",
        coverage=Coverage.CORE,
        signal=SIGNAL_SCM_ZONES,
        note=(
            "Separa degradación por uso turístico de la climática — la pregunta "
            "que la Carta plantea y que un indicador agregado no responde."
        ),
    ),
    _Requirement(
        key="diagnostico_fiabilidad",
        title="Diagnóstico — fiabilidad de la evidencia",
        snto_module="`src/decision_confidence/`",
        indicator="DCS (5 dimensiones) con data-quality gate `can_act`",
        coverage=Coverage.CORE,
        signal=SIGNAL_SATELLITE,
        note=(
            "Ninguna recomendación de gasto se emite sobre evidencia "
            "insuficiente; la incertidumbre viaja con el dato."
        ),
    ),
    _Requirement(
        key="diagnostico_flujos",
        title="Diagnóstico — flujos de visitantes",
        snto_module="`src/mobility/`, `src/platform/pressure_capacity.py`",
        indicator="Presión de visitantes (MITMA) y capacidad LAC/ROS por activo",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_MOBILITY,
        note=(
            "Movilidad municipal real como *proxy*: no es un conteo de "
            "visitantes en puerta ni un aforo instrumentado por sendero."
        ),
    ),
    _Requirement(
        key="diagnostico_socioeconomico",
        title="Diagnóstico — contexto socioeconómico",
        snto_module="`src/socioeconomic/`",
        indicator="SVI (vulnerabilidad), impacto en comunidad, empleo en riesgo",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_SOCIOECONOMIC,
        note=(
            "Cubre vulnerabilidad y dependencia turística; **no** mide "
            "satisfacción residente ni gasto turístico, que la Carta también pide."
        ),
    ),
    _Requirement(
        key="estrategia_priorizacion",
        title="Estrategia — priorización territorial a 5 años",
        snto_module="`src/territorial/` (TPI)",
        indicator="Territorial Priority Index + 4 tiers de actuación",
        coverage=Coverage.CORE,
        signal=SIGNAL_CURATED,
        note=(
            "Ordena la cartera por urgencia y valor estratégico; la estrategia "
            "misma (objetivos políticos a 5 años) es del equipo gestor."
        ),
    ),
    _Requirement(
        key="estrategia_proyeccion",
        title="Estrategia — proyección de escenarios",
        snto_module="`src/forecasting/`",
        indicator="Proyección de tendencia con banda de incertidumbre",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_FORECAST,
        note=(
            "Proyección **simulada** por construcción (nunca observación): "
            "apoya la discusión del horizonte a 5 años, no lo predice."
        ),
    ),
    _Requirement(
        key="plan_accion_actuaciones",
        title="Plan de Acción — actuaciones medibles y coste",
        snto_module="`src/intervention/` (TIS), `src/reporting/territorial_brief.py`",
        indicator="Escenarios A–E, optimizador presupuestario, coste de no actuar",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_CURATED,
        note=(
            "Costes orientativos con base en licitación pública; requieren "
            "calibración local antes de comprometerse en un Plan de Acción."
        ),
    ),
    _Requirement(
        key="plan_accion_seguimiento",
        title="Mejora continua — seguimiento e informe periódico",
        snto_module="`app.py` (capa Gobernar), `src/reporting/`",
        indicator="Panel por capas de decisión + informes y exportaciones GIS",
        coverage=Coverage.CORE,
        signal=SIGNAL_SATELLITE,
        note=(
            "La Carta exige seguimiento periódico verificable; el observatorio "
            "es reejecutable y cada cifra lleva su clase de evidencia."
        ),
    ),
    _Requirement(
        key="plan_accion_validacion",
        title="Mejora continua — contraste con la realidad de campo",
        snto_module="`src/validation/` (agreement, cross-sensor)",
        indicator="Concordancia satélite↔campo (Spearman ρ, Cliff's δ)",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_FIELD,
        note=(
            "El runner está implementado y probado; **la campaña de campo "
            "(#26) no se ha ejecutado**, así que no hay concordancia medida."
        ),
    ),
    _Requirement(
        key="foro",
        title="Foro — marco colaborativo",
        snto_module="`src/platform/views.py` (3 vistas por audiencia)",
        indicator="Evidencia común segmentada por perfil (técnico/gestor/auditoría)",
        coverage=Coverage.INSTRUMENTAL,
        signal=SIGNAL_CURATED,
        note=(
            "El Foro es un requisito organizativo y político. SNTO es la "
            "infraestructura de evidencia del Foro, no el Foro."
        ),
    ),
    _Requirement(
        key="grupo_trabajo",
        title="Grupo de Trabajo — redacción del dosier",
        snto_module="`src/reporting/` (este informe incluido)",
        indicator="Artefactos descargables trazables y fechados",
        coverage=Coverage.INSTRUMENTAL,
        signal=SIGNAL_CURATED,
        note=(
            "Aporta material fuente citable al equipo redactor; la redacción y "
            "el compromiso institucional son humanos."
        ),
    ),
)

# ── The 10 principles of the Carta ────────────────────────────────────────────
# Principle wording paraphrased in short form; the verbatim official text is in
# docs/archive/CETS_Phase1_correspondence.md §2 (verified there against the
# Apéndice 1 of the EUROPARC/MITECO Spanish edition).
_PRINCIPLES: tuple[_Requirement, ...] = (
    _Requirement(
        key="p01_participacion",
        title="1 · Hacer partícipes a los implicados en el turismo",
        snto_module="`src/platform/views.py`",
        indicator="Informes segmentados por audiencia",
        coverage=Coverage.INSTRUMENTAL,
        signal=SIGNAL_CURATED,
        note="Alimenta la participación con evidencia común; no la sustituye.",
    ),
    _Requirement(
        key="p02_estrategia",
        title="2 · Elaborar y aplicar una estrategia y un plan de acción",
        snto_module="`src/territorial/`, `src/intervention/`, `src/forecasting/`",
        indicator="TPI + escenarios TIS + proyección con incertidumbre",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_CURATED,
        note="Instrumenta la priorización y el coste; no fija los objetivos.",
    ),
    _Requirement(
        key="p03_patrimonio",
        title="3 · Proteger y potenciar el patrimonio natural y cultural",
        snto_module="`src/metrics/`, `src/spatial_causality/`, `src/intervention/`",
        indicator="EHS + atribución causal + presupuesto de restauración",
        coverage=Coverage.CORE,
        signal=SIGNAL_SATELLITE,
        note="Aportación diferencial máxima del sistema.",
    ),
    _Requirement(
        key="p04_experiencia",
        title="4 · Ofrecer una experiencia turística de alta calidad",
        snto_module="—",
        indicator="—",
        coverage=Coverage.OUT_OF_SCOPE,
        signal=None,
        note=(
            "Satisfacción y calidad de la experiencia no se miden desde "
            "teledetección; requieren encuesta a visitantes."
        ),
    ),
    _Requirement(
        key="p05_informacion",
        title="5 · Informar bien a los visitantes",
        snto_module="`app.py` (panel institucional)",
        indicator="Panel con trazabilidad y clase de evidencia",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_SATELLITE,
        note=(
            "El panel sirve a gestores. Un portal público de transparencia está "
            "explícitamente diferido hasta que la evidencia sea auditable."
        ),
    ),
    _Requirement(
        key="p06_productos",
        title="6 · Promover productos turísticos específicos",
        snto_module="—",
        indicator="—",
        coverage=Coverage.OUT_OF_SCOPE,
        signal=None,
        note="Diseño de producto turístico: programático, no técnico.",
    ),
    _Requirement(
        key="p07_formacion",
        title="7 · Formación de las partes implicadas",
        snto_module="—",
        indicator="—",
        coverage=Coverage.OUT_OF_SCOPE,
        signal=None,
        note="Acción formativa/organizativa fuera del sistema de evidencia.",
    ),
    _Requirement(
        key="p08_calidad_vida",
        title="8 · Garantizar que el turismo no reduzca la calidad de vida local",
        snto_module="`src/socioeconomic/`",
        indicator="SVI + impacto en comunidad + empleo local en riesgo",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_SOCIOECONOMIC,
        note=(
            "Cubierto por vulnerabilidad y empleo con dato municipal real; "
            "sin encuesta de satisfacción residente."
        ),
    ),
    _Requirement(
        key="p09_economia_local",
        title="9 · Aumentar los beneficios para la economía local",
        snto_module="`src/socioeconomic/`, `src/intervention/`",
        indicator="Dependencia turística municipal + coste de restauración local",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_SOCIOECONOMIC,
        note="Sin medición de gasto turístico ni derrama económica directa.",
    ),
    _Requirement(
        key="p10_flujos",
        title="10 · Controlar y seguir los flujos de turistas",
        snto_module="`src/mobility/`, `src/platform/pressure_capacity.py`",
        indicator="Presión MITMA + capacidad de carga LAC/ROS",
        coverage=Coverage.PARTIAL,
        signal=SIGNAL_MOBILITY,
        note=(
            "Serie de movilidad municipal real como proxy espacio-temporal; "
            "no sustituye aforo instrumentado por sendero."
        ),
    ),
)


@dataclass(frozen=True)
class ReadinessRow:
    """One CETS requirement with its declared coverage and computed evidence."""

    key: str
    title: str
    snto_module: str
    indicator: str
    coverage: Coverage
    evidence_class: EvidenceClass
    evidence_note: str
    note: str


@dataclass(frozen=True)
class EvidenceSignals:
    """Live availability of each evidence source, resolved once per report."""

    satellite_real: bool
    mobility_real: bool
    socioeconomic_series: bool
    field_measured_plots: int
    # Real multi-scale GEE zone exports backing SCM causal attribution. Zero
    # means the α-decay simulation is what actually runs, so attribution must
    # not be reported as observed. Defaulted for callers predating this field.
    scm_real_zones: int = 0

    @property
    def field_validated(self) -> bool:
        """True only if real measured field plots exist (campaign #26 ran)."""
        return self.field_measured_plots > 0

    @property
    def scm_zones_real(self) -> bool:
        """True only if at least one real multi-scale zone export exists."""
        return self.scm_real_zones > 0


def resolve_signals(park: str) -> EvidenceSignals:
    """Inspect the repository for what actually backs a territory today.

    Every check is a real on-disk/state probe, never an assumption: a park
    without a committed Mann-Kendall JSON reports ``satellite_real=False``
    rather than inheriting PNSG's evidence.
    """
    # Imported lazily so a report build doesn't pull the analytical stack
    # unless it is actually asked for.
    from src.mobility.loader import mobility_snapshot_exists
    from src.platform.satellite_trends import summarize_trends
    from src.socioeconomic.series import svi_history_available

    try:
        satellite_real = summarize_trends(park=park).available
    except (OSError, ValueError):
        satellite_real = False

    return EvidenceSignals(
        satellite_real=satellite_real,
        mobility_real=mobility_snapshot_exists(),
        socioeconomic_series=svi_history_available(),
        field_measured_plots=count_measured_field_plots(),
        scm_real_zones=count_real_scm_zone_exports(),
    )


def count_real_scm_zone_exports(path: Path | None = None) -> int:
    """Number of real multi-scale GEE zone exports on disk.

    Mirrors ``src.spatial_causality.zone_loader``'s layout
    (``zones/<asset_id>.json``). Zero — the state today — means SCM attribution
    runs on the α-decay simulation, so the readiness report must classify it
    ``SIMULATED`` rather than inherit the trend series' ``REAL``.
    """
    zones_dir = path or (_ROOT / "src/spatial_causality/zones")
    if not zones_dir.is_dir():
        return 0
    return len(list(zones_dir.glob("*.json")))


def count_measured_field_plots(path: Path | None = None) -> int:
    """Number of field plots carrying at least one real measurement.

    The campaign template ships with plot coordinates but **blank measurement
    columns**, so a row's mere existence proves nothing. Only rows whose
    ``degradation_index()`` resolves (i.e. at least one of compaction / cover /
    erosion was actually recorded) count as measured.
    """
    csv_path = path or _FIELD_CSV
    if not csv_path.exists():
        return 0
    from src.validation.io import load_field_observations

    try:
        observations = load_field_observations(csv_path)
    except (OSError, ValueError):
        return 0
    return sum(1 for o in observations if o.degradation_index() is not None)


def _status_for_signal(
    signal: str | None, signals: EvidenceSignals
) -> tuple[EvidenceClass, str]:
    """Map a declared evidence signal to its live status plus a short reason.

    ``REAL`` is the ceiling: no branch returns a "validated" state, because the
    satellite↔field campaign (#26) has not run. Even with measured plots
    present, this function reports ``REAL`` and leaves the agreement verdict to
    ``src/validation/agreement.py``, which is the only place allowed to state it.
    """
    if signal is None:
        return (
            EvidenceClass.MISSING,
            "Sin fuente de dato: requisito organizativo o fuera de alcance.",
        )
    if signal == SIGNAL_SATELLITE:
        if signals.satellite_real:
            return (
                EvidenceClass.REAL,
                "Serie Sentinel-2 real comprometida en disco para este territorio.",
            )
        return (
            EvidenceClass.MISSING,
            "Sin serie de tendencia real para este territorio (plantilla GEE "
            "pendiente de validación por bioma).",
        )
    if signal == SIGNAL_MOBILITY:
        if signals.mobility_real:
            return (
                EvidenceClass.REAL,
                "Snapshot de movilidad municipal MITMA real disponible.",
            )
        return (EvidenceClass.MISSING, "Sin snapshot de movilidad real disponible.")
    if signal == SIGNAL_SOCIOECONOMIC:
        if signals.socioeconomic_series:
            return (
                EvidenceClass.REAL,
                "Serie socioeconómica municipal real (INE/ALMUDENA) con tendencia.",
            )
        return (
            EvidenceClass.CALIBRATED,
            "Solo snapshot socioeconómico curado, sin serie temporal.",
        )
    if signal == SIGNAL_FIELD:
        if signals.field_validated:
            return (
                EvidenceClass.REAL,
                f"{signals.field_measured_plots} parcelas de campo con medición "
                "real registrada; la concordancia debe calcularse aparte.",
            )
        return (
            EvidenceClass.MISSING,
            "Plantilla de campo sin mediciones: la campaña #26 no se ha ejecutado.",
        )
    if signal == SIGNAL_SCM_ZONES:
        if signals.scm_zones_real:
            return (
                EvidenceClass.REAL,
                f"{signals.scm_real_zones} exportaciones de zonas multiescala "
                "reales (GEE) respaldan la atribución causal.",
            )
        return (
            EvidenceClass.SIMULATED,
            "Sin exportaciones de zonas reales: la atribución causal se apoya "
            "en la simulación de decaimiento α, no en zonas observadas.",
        )
    if signal == SIGNAL_FORECAST:
        return (
            EvidenceClass.SIMULATED,
            "Proyección simulada por construcción; nunca observación.",
        )
    if signal == SIGNAL_CURATED:
        return (
            EvidenceClass.CALIBRATED,
            "Cartera curada por experto (aforo, importancia económica, "
            "accesibilidad): estimación de orden de magnitud.",
        )
    # Unknown signal key: fail honest rather than guess a status.
    return (EvidenceClass.MISSING, f"Señal de evidencia no reconocida: {signal!r}.")


def _build_rows(
    requirements: tuple[_Requirement, ...], signals: EvidenceSignals
) -> list[ReadinessRow]:
    rows: list[ReadinessRow] = []
    for req in requirements:
        status, reason = _status_for_signal(req.signal, signals)
        rows.append(
            ReadinessRow(
                key=req.key,
                title=req.title,
                snto_module=req.snto_module,
                indicator=req.indicator,
                coverage=req.coverage,
                evidence_class=status,
                evidence_note=reason,
                note=req.note,
            )
        )
    return rows


def build_cets_readiness(
    *,
    territory_name: str,
    park: str,
    report_date: str | None = None,
    signals: EvidenceSignals | None = None,
) -> dict:
    """Assemble the CETS Fase I readiness report for one territory.

    Args:
        territory_name: human-readable territory name for the header.
        park: ``satellite_trends`` park key used to probe real evidence.
        report_date: ISO date, or ``None`` when generation provenance is not
            recorded. Stored as ``None`` in the returned dict — never replaced
            by today's date. Markdown renderers translate ``None`` to
            "no registrada" at presentation time.
        signals: pre-resolved evidence signals (injected by tests); resolved
            from the repository when omitted.

    Returns:
        A JSON-serialisable dict. Counts are derived from the rows, so they can
        never disagree with the table a reader sees.
    """
    if signals is None:
        signals = resolve_signals(park)

    components = _build_rows(_COMPONENTS, signals)
    principles = _build_rows(_PRINCIPLES, signals)
    all_rows = components + principles

    coverage_counts: dict[str, int] = {c.value: 0 for c in Coverage}
    status_counts: dict[str, int] = {s.value: 0 for s in EvidenceClass}
    for row in all_rows:
        coverage_counts[row.coverage.value] += 1
        status_counts[row.evidence_class.value] += 1

    return {
        "metadata": {
            "report_date": report_date,
            "system": "Smart Natural Tourism Observatory (SNTO)",
            "version": __version__,
            "territory": territory_name,
            "park_key": park,
            "framework": "Carta Europea de Turismo Sostenible (CETS) — Fase I",
        },
        "scope_note": (
            "Documento de **preparación**, no un dosier de candidatura. La Fase I "
            "de la CETS acredita al espacio protegido a través de un Foro y un "
            "Grupo de Trabajo: SNTO instrumenta la candidatura con evidencia "
            "trazable, no la constituye ni la sustituye."
        ),
        "validation_note": (
            "Ninguna fila se declara validada externamente. El runner de "
            "concordancia satélite↔campo está implementado, pero la campaña de "
            "campo (#26) no se ha ejecutado: «tendencia satelital real» no "
            "equivale a «validado en campo» (ADR-003)."
        ),
        "signals": {
            "satellite_real": signals.satellite_real,
            "mobility_real": signals.mobility_real,
            "socioeconomic_series": signals.socioeconomic_series,
            "field_measured_plots": signals.field_measured_plots,
            "field_validated": signals.field_validated,
            "scm_real_zones": signals.scm_real_zones,
            "scm_zones_real": signals.scm_zones_real,
        },
        "summary": {
            "requirements_assessed": len(all_rows),
            "by_coverage": coverage_counts,
            "by_evidence_class": status_counts,
        },
        "components": [_row_dict(r) for r in components],
        "principles": [_row_dict(r) for r in principles],
    }


def _row_dict(row: ReadinessRow) -> dict:
    d = row.__dict__.copy()
    d["coverage"] = row.coverage.value
    d["evidence_class"] = row.evidence_class.value
    return d


def _render_table(rows: list[dict]) -> list[str]:
    cols = [
        "Requisito", "Módulo SNTO", "Indicador", "Cobertura", "Evidencia hoy", "Nota",
    ]
    lines = [
        "| " + " | ".join(cols) + " |",
        "|" + "|".join("---" for _ in cols) + "|",
    ]
    for r in rows:
        coverage = _COVERAGE_LABELS[Coverage(r["coverage"])]
        status = r["evidence_class"]
        lines.append(
            f"| {r['title']} | {r['snto_module']} | {r['indicator']} | "
            f"{coverage} | `{status}` | {r['note']} |"
        )
    return lines


def render_cets_readiness_markdown(report: dict) -> str:
    """Render the readiness report as an exportable Markdown document."""
    m = report["metadata"]
    s = report["summary"]
    sig = report["signals"]

    lines = [
        f"# Preparación de dosier CETS Fase I — {m['territory']}",
        "",
        f"**Marco:** {m['framework']}  ·  **Fecha:** "
        f"{m['report_date'] or 'no registrada'}  ·  "
        f"**SNTO** v{m['version']}",
        "",
        f"> {report['scope_note']}",
        "",
        f"> ⚠️ {report['validation_note']}",
        "",
        "## Estado de la evidencia disponible",
        "",
        f"- Serie satelital real (`{m['park_key']}`): "
        f"{'sí' if sig['satellite_real'] else 'no'}",
        f"- Movilidad real (MITMA): {'sí' if sig['mobility_real'] else 'no'}",
        f"- Zonas SCM multiescala reales: {sig['scm_real_zones']}"
        + (
            ""
            if sig["scm_zones_real"]
            else " — la atribución causal usa la simulación α"
        ),
        f"- Serie socioeconómica real: "
        f"{'sí' if sig['socioeconomic_series'] else 'no'}",
        f"- Parcelas de campo con medición: {sig['field_measured_plots']}"
        + ("" if sig["field_measured_plots"] else " — **campaña #26 pendiente**"),
        "",
        f"**Requisitos evaluados:** {s['requirements_assessed']}  ·  "
        + "  ·  ".join(
            f"{_COVERAGE_LABELS[Coverage(k)]}: {v}"
            for k, v in s["by_coverage"].items()
            if v
        ),
        "",
        "## 1 · Componentes del dosier Fase I",
        "",
    ]
    lines += _render_table(report["components"])
    lines += [
        "",
        "## 2 · Los 10 principios de la Carta",
        "",
    ]
    lines += _render_table(report["principles"])

    out_of_scope = [
        r for r in report["principles"] if r["coverage"] == Coverage.OUT_OF_SCOPE.value
    ]
    lines += [
        "",
        "## 3 · Límites declarados",
        "",
        (
            "Los siguientes principios quedan **deliberadamente fuera** del "
            "alcance de un sistema de evidencia teledetectada y deben cubrirse "
            "con actuaciones organizativas del Plan de Acción:"
        ),
        "",
    ]
    if out_of_scope:
        for r in out_of_scope:
            lines.append(f"- **{r['title']}** — {r['note']}")
    else:
        lines.append("- (ninguno)")
    lines += [
        "",
        (
            "_Informe de preparación generado por SNTO. No es un dosier de "
            "candidatura ni acredita cumplimiento; no sustituye la inspección de "
            "campo, la validación técnica local ni el contraste con "
            "EUROPARC-España._"
        ),
        "",
    ]
    return "\n".join(lines)
