"""
Territory registry for the Gobernar layer (Fase 6.7f — configuración territorial).

Pure logic (no Streamlit) so it is unit-testable and reused by
``src/ui/tabs/tab_config.py``. It assembles a **read-only** view of the
territories SNTO knows about and, crucially, their **validation state** — so
the configuration surface prepares multi-park *without overpromising* it
(project non-negotiable; ``docs/ux/ui-evolution-v2-spec.md`` §6 marks this
module P3, "prepare multi-park without overpromising", and ADR-004 forbids
claiming scientific validity before field validation).

Grounded in what actually exists in the repo:
- the two configured territories in ``src/ui/layout._TERRITORY_CONFIG`` (PNSG
  active, Sierra del Rincón archived), and
- the OAPN GEE template set under ``scripts/gee_templates_oapn/`` (15 parks),
  of which two (Tablas de Daimiel, Monfragüe) have real validated *trend*
  series from the v1.2 replicability pilot and the rest are unvalidated
  templates pending per-biome QA.

**No territory is marked field-validated** — the PNSG ground-truth campaign
(#26) is still pending, so "real satellite trend" is never conflated with
"field-validated".
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ValidationState(str, Enum):
    """How much any given territory has actually been validated. Ordered weak→strong."""

    TEMPLATE_UNVALIDATED = "template_unvalidated"
    CALIBRATION_ARCHIVED = "calibration_archived"
    TREND_PILOT = "trend_pilot"  # real Sentinel-2 trend series, NOT field-validated
    ACTIVE_PILOT = "active_pilot"  # main case study; field validation still pending


_STATE_LABEL: dict[ValidationState, str] = {
    ValidationState.TEMPLATE_UNVALIDATED: "Plantilla · sin validar",
    ValidationState.CALIBRATION_ARCHIVED: "Calibración · archivada",
    ValidationState.TREND_PILOT: "Piloto de tendencia · sin validación de campo",
    ValidationState.ACTIVE_PILOT: "Piloto activo · validación de campo pendiente",
}


@dataclass(frozen=True)
class TerritoryProfile:
    """One territory's registry row — descriptive, never a live-tenancy claim."""

    slug: str
    name: str
    biome: str
    state: ValidationState
    note: str

    @property
    def state_label(self) -> str:
        return _STATE_LABEL[self.state]

    @property
    def field_validated(self) -> bool:
        """Always False today — the #26 campaign has not been collected."""
        return False


# The two territories wired into the running app (mirrors _TERRITORY_CONFIG).
_CONFIGURED = (
    TerritoryProfile(
        slug="pnsg",
        name="Parque Nacional Sierra de Guadarrama",
        biome="Alta montaña mediterránea",
        state=ValidationState.ACTIVE_PILOT,
        note=(
            "Territorio principal del observatorio. Sentinel-2 real (218 sendas, "
            "cartografía OAPN). La campaña de validación de campo (#26) está "
            "pendiente: la tendencia satelital es real, no un aval de campo."
        ),
    ),
    TerritoryProfile(
        slug="snr",
        name="Reserva de la Biosfera Sierra del Rincón",
        biome="Montaña media / robledal",
        state=ValidationState.CALIBRATION_ARCHIVED,
        note=(
            "Piloto de calibración del método (escenas reales propias). "
            "Archivado: se conserva en código y datos, ya no es el piloto activo."
        ),
    ),
)

# OAPN replicability set — real trend pilots (v1.2) + unvalidated templates.
# Slugs mirror scripts/gee_templates_oapn/*.js so the registry never invents
# a park that has no template on disk.
_TREND_PILOT_SLUGS = ("tablas_daimiel", "monfrague")
_OAPN_TEMPLATE_SLUGS = (
    "aiguestortes", "cabaneros", "cabrera", "donana", "garajonay",
    "islas_atlanticas", "ordesa", "picos_europa", "sierra_nevada",
    "sierra_nieves", "taburiente", "teide", "timanfaya",
)
_OAPN_NAMES: dict[str, tuple[str, str]] = {
    "tablas_daimiel": ("Tablas de Daimiel", "Humedal manchego"),
    "monfrague": ("Monfragüe", "Dehesa mediterránea"),
    "aiguestortes": ("Aigüestortes i Estany de Sant Maurici", "Alta montaña pirenaica"),
    "cabaneros": ("Cabañeros", "Bosque mediterráneo / raña"),
    "cabrera": ("Archipiélago de Cabrera", "Marítimo-terrestre"),
    "donana": ("Doñana", "Marismas / dunas"),
    "garajonay": ("Garajonay", "Laurisilva"),
    "islas_atlanticas": ("Islas Atlánticas de Galicia", "Marítimo-terrestre"),
    "ordesa": ("Ordesa y Monte Perdido", "Alta montaña pirenaica"),
    "picos_europa": ("Picos de Europa", "Alta montaña atlántica"),
    "sierra_nevada": ("Sierra Nevada", "Alta montaña mediterránea"),
    "sierra_nieves": ("Sierra de las Nieves", "Pinsapar mediterráneo"),
    "taburiente": ("Caldera de Taburiente", "Pinar canario"),
    "teide": ("Teide", "Alta montaña volcánica"),
    "timanfaya": ("Timanfaya", "Volcánico / badlands"),
}


def _oapn_profiles() -> tuple[TerritoryProfile, ...]:
    profiles: list[TerritoryProfile] = []
    for slug in _TREND_PILOT_SLUGS:
        name, biome = _OAPN_NAMES[slug]
        profiles.append(
            TerritoryProfile(
                slug=slug,
                name=name,
                biome=biome,
                state=ValidationState.TREND_PILOT,
                note=(
                    "Piloto de replicabilidad v1.2: series Sentinel-2 reales "
                    "2021–2026 con QA por bioma. Sin validación de campo."
                ),
            )
        )
    for slug in _OAPN_TEMPLATE_SLUGS:
        name, biome = _OAPN_NAMES[slug]
        profiles.append(
            TerritoryProfile(
                slug=slug,
                name=name,
                biome=biome,
                state=ValidationState.TEMPLATE_UNVALIDATED,
                note=(
                    "Plantilla GEE preparada; alertas pendientes de auditoría de "
                    "máscara SCL por bioma. No presentar como territorio operativo."
                ),
            )
        )
    return tuple(profiles)


def territory_profiles() -> tuple[TerritoryProfile, ...]:
    """All known territories, strongest validation state first."""
    everything = _CONFIGURED + _oapn_profiles()
    order = {
        ValidationState.ACTIVE_PILOT: 0,
        ValidationState.TREND_PILOT: 1,
        ValidationState.CALIBRATION_ARCHIVED: 2,
        ValidationState.TEMPLATE_UNVALIDATED: 3,
    }
    return tuple(sorted(everything, key=lambda p: (order[p.state], p.name)))


@dataclass(frozen=True)
class RegistrySummary:
    total: int
    active: int
    trend_pilots: int
    templates: int
    field_validated: int  # always 0 until the #26 campaign is collected


def registry_summary() -> RegistrySummary:
    profiles = territory_profiles()
    return RegistrySummary(
        total=len(profiles),
        active=sum(1 for p in profiles if p.state is ValidationState.ACTIVE_PILOT),
        trend_pilots=sum(
            1 for p in profiles if p.state is ValidationState.TREND_PILOT
        ),
        templates=sum(
            1 for p in profiles if p.state is ValidationState.TEMPLATE_UNVALIDATED
        ),
        field_validated=sum(1 for p in profiles if p.field_validated),
    )
