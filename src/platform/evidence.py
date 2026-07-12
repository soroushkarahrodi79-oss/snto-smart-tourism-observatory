"""
SNTO — Canonical evidence-class vocabulary and decision gating (ADR-004, #10).

WHY
===
Multiple reviews flagged mixed evidence classes as a scientific, product and
adoption risk, and ADR-004 made evidence class a *first-class* concept that
must be separated in data, UI, reports and documentation — never blurred. The
project already labels provenance in two places:

  * ``src/temporal/manifest.DataStatus`` — the trust tier of a temporal datum
    (``real`` / ``calibrated`` / ``synthetic`` / ``missing``);
  * ``src/platform/methodology.DataType`` — the epistemic nature of a *variable*
    (``Observada`` / ``Calculada`` / ``Estimada`` / ``Simulada``).

Those are two useful but different axes, and neither on its own states the four
provenance tiers ADR-004 names (real / calibrated / **synthetic** /
**simulated**) nor *what decisions each tier may support*. This module supplies
the single canonical provenance vocabulary and the gating matrix ADR-004's
"Next Steps" asks for: which evidence class can back monitoring, prioritisation,
intervention and public reporting.

It is pure logic (no Streamlit) so the dashboard, reports and the GIS/risk
exporters can all read the *same* labels, colours and rules. The gating matrix
is deliberately conservative — a proposed institutional policy, open to owner
review — because overstating certainty is the failure mode ADR-004 guards
against.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.platform.methodology import DataType
from src.temporal.manifest import DataStatus


class EvidenceClass(str, Enum):
    """The canonical provenance tier of a value (ADR-004's four classes + gap).

    ``MISSING`` is the honest sentinel for *absence* of evidence — it is not a
    tier that supports any decision, it records that no datum exists.
    """
    REAL = "real"              # direct Sentinel-2 / official observation
    CALIBRATED = "calibrated"  # literature/expert-calibrated reconstruction
    SIMULATED = "simulated"    # scenario / counterfactual (Pipeline B, simulator)
    SYNTHETIC = "synthetic"    # mock / demo data for system demonstration
    MISSING = "missing"        # expected datum absent — not evidence


class DecisionUse(str, Enum):
    """The kinds of decision an evidence class may (or may not) support."""
    MONITORING = "monitoring"            # observe / contextualise state
    PRIORITIZATION = "prioritization"    # where to look first (early warning)
    INTERVENTION = "intervention"        # commit budget / order field action
    PUBLIC_REPORTING = "public_reporting"  # institutional / public communication


@dataclass(frozen=True)
class EvidenceDescriptor:
    """Everything the UI, reports and gating need for one evidence class."""
    evidence: EvidenceClass
    emoji: str
    label: str
    color: str
    definition: str
    caveat: str
    allowed_uses: frozenset[DecisionUse]


# Conservative gating policy (ADR-004 Next Steps). Rationale per class lives in
# ``definition``/``caveat`` and in docs/methodology/evidence-classes.md.
_DESCRIPTORS: dict[EvidenceClass, EvidenceDescriptor] = {
    EvidenceClass.REAL: EvidenceDescriptor(
        EvidenceClass.REAL, "🛰️", "Dato satelital real", "#0F6E56",
        "Observación directa Sentinel-2 L2A / cartografía oficial.",
        "Apta para diagnóstico, alerta y decisión, con su nivel de confianza.",
        frozenset({
            DecisionUse.MONITORING, DecisionUse.PRIORITIZATION,
            DecisionUse.INTERVENTION, DecisionUse.PUBLIC_REPORTING,
        }),
    ),
    EvidenceClass.CALIBRATED: EvidenceDescriptor(
        EvidenceClass.CALIBRATED, "📐", "Dato calibrado por experto", "#B7791F",
        "Reconstrucción calibrada con literatura / anomalías AEMET-Copernicus.",
        "No es observación directa: sirve para orientar dónde mirar, no para "
        "ordenar gasto ni comunicar como hecho sin validar antes.",
        frozenset({DecisionUse.MONITORING, DecisionUse.PRIORITIZATION}),
    ),
    EvidenceClass.SIMULATED: EvidenceDescriptor(
        EvidenceClass.SIMULATED, "🎛️", "Escenario simulado", "#5B21B6",
        "Escenario / contrafactual del simulador (Pipeline B): un '¿y si?', "
        "no el estado actual del territorio.",
        "Solo para explorar escenarios. No es evidencia del estado real: no "
        "usar para monitorización, priorización, gasto ni reporte público.",
        frozenset(),
    ),
    EvidenceClass.SYNTHETIC: EvidenceDescriptor(
        EvidenceClass.SYNTHETIC, "🧪", "Demo sintética", "#A32D2D",
        "Datos generados para demostrar el sistema.",
        "NO usar para ninguna decisión real: solo demostración.",
        frozenset(),
    ),
    EvidenceClass.MISSING: EvidenceDescriptor(
        EvidenceClass.MISSING, "—", "Sin dato", "#9E9E9E",
        "Periodo o activo sin observación válida.",
        "Ausencia de evidencia: se declara como null, nunca se rellena.",
        frozenset(),
    ),
}

# UI/report display order: strongest tier first, absence last.
_ORDER: tuple[EvidenceClass, ...] = (
    EvidenceClass.REAL, EvidenceClass.CALIBRATED, EvidenceClass.SIMULATED,
    EvidenceClass.SYNTHETIC, EvidenceClass.MISSING,
)

# DataStatus (temporal layer) has no SIMULATED tier; it maps 1:1 otherwise.
_FROM_DATA_STATUS: dict[DataStatus, EvidenceClass] = {
    DataStatus.REAL: EvidenceClass.REAL,
    DataStatus.CALIBRATED: EvidenceClass.CALIBRATED,
    DataStatus.SYNTHETIC: EvidenceClass.SYNTHETIC,
    DataStatus.MISSING: EvidenceClass.MISSING,
}

# DataType is an orthogonal axis (epistemic operation, not raw provenance). Only
# the unambiguous ends are mapped; ``Calculada`` inherits its tier from inputs
# and is intentionally left unmapped rather than blurred into one class.
_FROM_DATA_TYPE: dict[DataType, EvidenceClass] = {
    DataType.OBSERVED: EvidenceClass.REAL,
    DataType.ESTIMATED: EvidenceClass.CALIBRATED,
    DataType.SIMULATED: EvidenceClass.SIMULATED,
}


def descriptor(evidence: EvidenceClass) -> EvidenceDescriptor:
    """Canonical descriptor (emoji, label, colour, caveat, uses) for a class."""
    return _DESCRIPTORS[evidence]


def legend() -> list[EvidenceDescriptor]:
    """Descriptors in canonical display order — the single UI/report legend."""
    return [_DESCRIPTORS[e] for e in _ORDER]


def from_data_status(status: DataStatus) -> EvidenceClass:
    """Reconcile a temporal-layer ``DataStatus`` to the canonical class."""
    return _FROM_DATA_STATUS[status]


def from_data_type(dtype: DataType) -> EvidenceClass | None:
    """Reconcile a methodology ``DataType`` to a canonical class.

    Returns ``None`` for ``DataType.CALCULATED`` (``Calculada``): a calculated
    variable inherits the tier of its inputs, so collapsing it to a single class
    would blur evidence — the caller must resolve it from the actual inputs.
    """
    return _FROM_DATA_TYPE.get(dtype)


def supports(evidence: EvidenceClass, use: DecisionUse) -> bool:
    """Whether ``evidence`` may back a decision of type ``use`` (the gate)."""
    return use in _DESCRIPTORS[evidence].allowed_uses


def gating_matrix() -> dict[EvidenceClass, dict[DecisionUse, bool]]:
    """Full evidence-class × decision-use permission matrix (for docs/tables)."""
    return {
        e: {u: supports(e, u) for u in DecisionUse}
        for e in _ORDER
    }
