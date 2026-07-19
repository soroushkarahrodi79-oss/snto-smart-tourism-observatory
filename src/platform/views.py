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
    """Eje de *verbosidad de confianza* (cuánto caveat lleva una afirmación que
    las tres vistas muestran en alguna forma). Es independiente de las banderas
    booleanas de ``ViewProfile`` (``technical``/``simplified``/``audit``), que
    deciden SI una sección entera aparece. Regla práctica:

    * ¿Aparece o no una sección/bloque? → ``ViewProfile.section(...)``.
    * ¿Cuánto caveat lleva un dato de confianza que sí se muestra? → este enum.
    """
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
    personas: tuple[str, ...]
    home_layer: str
    home_module: str
    # ── Política de divulgación por capas (F7) ────────────────────────────────
    # Controlan qué muestra cada vista, para que las tres difieran de verdad y no
    # solo en el banner. Principio aditivo: todas ven el núcleo; cada perfil suma
    # o quita capas.
    technical: bool = False  # NDVI/NDMI crudo, p-valores, componentes DCS, percentiles
    simplified: bool = False  # lenguaje llano, oculta jerga, decisión primero
    # procedencia, fechas de escena, override, validación cruzada, límites
    audit: bool = False
    shows: str = ""  # resumen de una línea de "qué cambia" (para el sidebar)

    @property
    def home_path(self) -> str:
        """Visible IA path that opens first for this grouped audience."""
        return f"{self.home_layer.title()} → {self.home_module}"

    def section(
        self,
        *,
        technical: bool = False,
        simplified: bool = False,
        audit: bool = False,
    ) -> bool:
        """¿Debe esta vista renderizar una sección con estos requisitos?

        Punto único de decisión de la divulgación por capas (F7/F10): sustituye a
        leer ``self.technical`` / ``self.simplified`` / ``self.audit`` sueltos por
        toda la app, para que el contrato de cada sección quede explícito y
        testeable.

        * sin argumentos → ``True``: núcleo común a las tres vistas.
        * ``technical=True``  → solo vistas con detalle técnico (Técnica, Auditoría).
        * ``simplified=True`` → solo la vista en lenguaje llano (Gestor).
        * ``audit=True``      → solo la vista de auditoría (procedencia/límites).

        Varios ejes se combinan con OR inclusivo (se muestra si la vista satisface
        CUALQUIERA), coherente con el principio aditivo: cada perfil suma capas.
        Para el GRADO de caveat de confianza se usa ``confidence_detail``, no esto.
        """
        if not (technical or simplified or audit):
            return True
        return (
            (technical and self.technical)
            or (simplified and self.simplified)
            or (audit and self.audit)
        )


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
        personas=("Analista GIS / EO",),
        home_layer="diagnosticar",
        home_module="Diagnóstico espacial",
        technical=True,
        shows="Abre el diagnóstico espacial y añade p-valores Mann-Kendall, "
              "componentes DCS y notas espectrales.",
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
        personas=(
            "Dirección del parque",
            "Gestión de destino",
            "Decisión pública",
        ),
        home_layer="decidir",
        home_module="Panorama ejecutivo",
        simplified=True,
        shows="Abre el panorama ejecutivo, oculta jerga estadística y prioriza "
              "la acción del territorio.",
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
        # Banner deliberadamente conciso: la metodología detallada (procedencia,
        # fórmulas, cobertura ALMUDENA/INE, resolución, override) vive en la
        # capa «Gobernar → Metodología y auditoría» (src/platform/methodology.py) y en
        # los docs de diseño. El banner solo enuncia el contrato y remite, para no
        # duplicar —y que diverja— el texto canónico.
        banner="Vista de auditoría: cada cifra lleva su procedencia (satélite "
               "Sentinel-2 / dato curado / socioeconómico) y su confianza (DCS), con "
               "override conservador (el satélite solo agrava, nunca relaja el juicio "
               "experto). Fundamento, fórmulas y límites declarados en "
               "«Gobernar → Metodología y auditoría» y en "
               "docs/informe_tecnico_limites.md, "
               "docs/baselines_uncertainty_design.md y "
               "docs/socioeconomic_integration_design.md.",
        personas=("Revisión científica", "Auditoría / evaluación"),
        home_layer="gobernar",
        home_module="Metodología y auditoría",
        technical=True,
        audit=True,
        shows="Abre metodología y suma procedencia, validación cruzada y "
              "límites declarados.",
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
