"""
SNTO — Audience view profiles (F7)
==================================
The same evidence serves three audiences with very different needs. The audit
recommended separating them explicitly:

  * Técnica   — NDVI/NDMI, buffers, baselines, uncertainty, valid pixels.
  * Gestor    — ranking, priority, budget, recommended action.
  * Auditoría — methodology, traceability, evidence, declared limits.

This module defines those view profiles as pure data so ``app.py`` can render a
single dataset through the right lens, with the right *confidence verbosity*,
instead of forcing one audience's framing on everyone.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ViewMode(str, Enum):
    TECNICA = "tecnica"
    GESTOR = "gestor"
    TRIBUNAL = "tribunal"


class ConfidenceDetail(str, Enum):
    RAW = "raw"          # show the underlying metrics, minimal hand-holding
    CONCISE = "concise"  # one-line actionable confidence flag
    FULL = "full"        # full caveat + methodology + traceability


@dataclass(frozen=True)
class ViewProfile:
    mode: ViewMode
    label: str
    icon: str
    audience: str
    emphasis: str
    confidence_detail: ConfidenceDetail
    banner: str
    # ── Política de divulgación por capas (F7) ────────────────────────────────
    # Controlan qué muestra cada vista, para que las tres difieran de verdad y no
    # solo en el banner. Principio aditivo: todas ven el núcleo; cada perfil suma
    # o quita capas.
    technical: bool = False  # NDVI/NDMI crudo, p-valores, componentes DCS, percentiles
    simplified: bool = False  # lenguaje llano, oculta jerga, decisión primero
    # procedencia, fechas de escena, override, validación cruzada, límites
    audit: bool = False
    shows: str = ""  # resumen de una línea de "qué cambia" (para el sidebar)


_PROFILES: dict[ViewMode, ViewProfile] = {
    ViewMode.TECNICA: ViewProfile(
        mode=ViewMode.TECNICA,
        label="Técnica",
        icon="🔬",
        audience="Equipo técnico / científico",
        emphasis="NDVI/NDMI, buffers, baselines, incertidumbre y píxeles válidos.",
        confidence_detail=ConfidenceDetail.RAW,
        banner="Vista técnica: índices espectrales, baselines y métricas de "
               "incertidumbre sin simplificar.",
        technical=True,
        shows="Añade p-valores Mann-Kendall, componentes DCS"
              " y notas espectrales abiertas.",
    ),
    ViewMode.GESTOR: ViewProfile(
        mode=ViewMode.GESTOR,
        label="Gestor",
        icon="🧭",
        audience="Gestor del espacio / administración",
        emphasis="Ranking de prioridad, presupuesto y acción recomendada.",
        confidence_detail=ConfidenceDetail.CONCISE,
        banner="Vista gestor: prioridad, presupuesto y acción — con el nivel de "
               "confianza resumido en una línea.",
        simplified=True,
        shows="Oculta la jerga estadística y añade"
              " la acción prioritaria del territorio.",
    ),
    ViewMode.TRIBUNAL: ViewProfile(
        mode=ViewMode.TRIBUNAL,
        label="Auditoría científica",
        icon="⚖️",
        audience="Revisión metodológica / auditoría científica",
        emphasis="Procedencia del dato (satélite vs. curado vs. socioeconómico), "
                 "política de override conservador,"
                 " fórmulas EHS/TPI/DCS y límites declarados.",
        confidence_detail=ConfidenceDetail.FULL,
        banner="Vista de auditoría: el EHS satelital procede de Sentinel-2 L2A (tile "
               "T30TVL, Pipeline A). Override conservador —"
               " el satélite solo sobreescribe "
               "el juicio experto cuando observa MÁS degradación; al alza no sustituye "
               "(la roca/canchal de alta montaña tiene poco NDVI por geología, no por "
               "turismo). La capa socioeconómica ALMUDENA/INE"
               " es completa en Madrid y solo "
               "demográfica en Segovia. Límites: resolución ~10-30 m,"
               " profundidad temporal "
               "del snapshot y sendas sin equivalente OSM"
               " (SIN_DATO). Cada cifra lleva su "
               "procedencia y nivel de confianza (DCS).",
        technical=True,
        audit=True,
        shows="Suma a la vista técnica la procedencia del dato,"
              " la validación cruzada y los límites declarados.",
    ),
}


def view_modes() -> list[ViewMode]:
    """Ordered list of view modes for a UI selector."""
    return [ViewMode.TECNICA, ViewMode.GESTOR, ViewMode.TRIBUNAL]


def get_view(mode: ViewMode | str) -> ViewProfile:
    """Return the ViewProfile for a mode (accepts the enum or its value)."""
    if isinstance(mode, str):
        mode = ViewMode(mode)
    return _PROFILES[mode]
