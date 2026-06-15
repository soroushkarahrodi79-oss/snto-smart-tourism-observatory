"""
SNTO — Fundamento metodológico, trazabilidad e incertidumbre (defensa académica)
================================================================================
Convierte en una **fuente de verdad única** la clasificación de cada variable del
observatorio y el inventario de multiplicadores del modelo, para que la app y el
anexo de defensa (`docs/defensibilidad_academica.md`) no se desincronicen.

Responde directamente a las tareas de la auditoría de defensibilidad de TFM:

  * Tarea 2 — clasificar cada variable como Observada / Calculada / Estimada / Simulada.
  * Tarea 3 — matriz Variable / Fuente / Fórmula / Confianza / Tipo.
  * Tarea 5 — multiplicadores: origen, justificación, comportamiento, sensibilidad.
  * Tareas 4 y 7 — secciones y `st.expander` de Fundamento, Trazabilidad y Limitaciones.

Eje de clasificación (``DataType``) vs. eje de procedencia (``provenance.DataStatus``):
son **complementarios**. ``DataStatus`` dice de *dónde* viene el dato (satélite real /
calibrado / sintético); ``DataType`` dice *qué naturaleza epistémica* tiene la variable
(se mide, se calcula, se estima por proxy, o se simula como escenario). Un tribunal
necesita las dos lecturas.

La parte de datos (``TRACEABILITY``, ``MULTIPLIERS``) es **pura** (sin Streamlit), por lo
que `tests/test_methodology.py` la valida sin levantar la app. Los `render_*` importan
Streamlit/pandas de forma perezosa y se llaman desde `app.py`.

Los valores citados reflejan las constantes reales del código en el momento de escribir
(`src/config/constants.py`, `src/risk_engine/ehs.py`, `src/territorial/tpi.py`,
`src/intervention/impact.py`, `src/socioeconomic/indicators.py`, y el modelo proxy
económico embebido en `app.py`, tab 5). No se reescriben aquí: se documentan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ── Ejes de clasificación ─────────────────────────────────────────────────────
class DataType(str, Enum):
    """Naturaleza epistémica de una variable (tarea 2 de la auditoría)."""
    OBSERVED = "Observada"      # medición directa (satélite, padrón, cartografía oficial)
    CALCULATED = "Calculada"    # determinista a partir de observadas (EHS, ΔEHS, SVI, SIG)
    ESTIMATED = "Estimada"      # proxy / parámetro de literatura o atributo curado
    SIMULATED = "Simulada"      # escenario / contrafactual / serie demo (Pipeline B)

    @property
    def label(self) -> str:
        """Etiqueta visible (alias de ``value``; existe para legibilidad en la app)."""
        return self.value


class Confidence(str, Enum):
    HIGH = "Alta"
    MEDIUM = "Media"
    LOW = "Baja"


@dataclass(frozen=True)
class TraceRow:
    """Una fila de la matriz de trazabilidad."""
    variable: str
    source: str        # fuente / origen del dato
    formula: str       # fórmula o regla (texto compacto)
    confidence: Confidence
    dtype: DataType
    location: str = ""  # file:símbolo donde vive el cálculo (trazabilidad al código)
    note: str = ""


@dataclass(frozen=True)
class Multiplier:
    """Un multiplicador / coeficiente / constante del modelo (tarea 5)."""
    name: str
    value: str
    origin: str          # de dónde sale el número
    justification: str   # por qué es razonable
    behavior: str        # comportamiento matemático
    sensitivity: str     # qué pasa si se mueve
    location: str = ""   # file donde está la constante


# ══════════════════════════════════════════════════════════════════════════════
# MATRIZ DE TRAZABILIDAD  (tarea 3) — agrupada por capa
# ══════════════════════════════════════════════════════════════════════════════
TRACEABILITY: list[TraceRow] = [
    # ── Capa de observación satelital (núcleo real) ──────────────────────────
    TraceRow(
        "NDVI", "Sentinel-2 L2A (ESA Copernicus) B4/B8",
        "(NIR − RED) / (NIR + RED)", Confidence.HIGH, DataType.OBSERVED,
        "src/features/spectral.py", "Índice espectral medido por píxel (~10 m).",
    ),
    TraceRow(
        "NDMI", "Sentinel-2 L2A B8/B11",
        "(NIR − SWIR) / (NIR + SWIR)", Confidence.HIGH, DataType.OBSERVED,
        "src/features/spectral.py", "Humedad del dosel; resolución ~20 m remuestreada.",
    ),
    TraceRow(
        "Geometría de sendas", "OAPN (cartografía oficial) + OpenStreetMap",
        "trazas vectoriales", Confidence.HIGH, DataType.OBSERVED,
        "data/raw_assets/vector_data/hiking_trails.geojson",
        "73 sendas reales del PNSG.",
    ),
    TraceRow(
        "Fechas de escena", "Nombres de producto .SAFE Sentinel-2",
        "parseo S2[AB]_MSIL2A_YYYYMMDD", Confidence.HIGH, DataType.OBSERVED,
        "src/platform/provenance.py:detect_scene_dates", "No hardcodeadas.",
    ),

    # ── Capa de cálculo ecológico (determinista sobre observadas) ────────────
    TraceRow(
        "EHS estacional (PNSG)", "Percentiles P90/P10 de la escena (sin buffer de senda)",
        "100·(1 − D); D = déficit ponderado NDVI/NDMI", Confidence.HIGH, DataType.CALCULATED,
        "calculate_delta_ehs.py:_trail_stress_score",
        "Anclaje por percentiles de la propia escena. Convención salud (alto=sano).",
    ),
    TraceRow(
        "ΔEHS (cambio estacional)", "EHS_verano − EHS_primavera",
        "resta pareada", Confidence.HIGH, DataType.CALCULATED,
        "calculate_delta_ehs.py",
        "Contraste pareado: válido con 2 escenas. NO es tendencia inter-anual.",
    ),
    TraceRow(
        "EHS multi-componente (Pipeline B / research)",
        "Serie NDVI/NDMI",
        "100·(1 − [0.30·base + 0.25·trend + 0.25·anom + 0.10·recov + 0.10·estab])",
        Confidence.MEDIUM, DataType.CALCULATED,
        "src/risk_engine/ehs.py",
        "Pesos por elicitación experta (suman 1). En PNSG real solo aplica el modo "
        "estacional; este modo multi-año opera sobre serie calibrada (demo).",
    ),
    TraceRow(
        "SIG / clasificación SCM", "Rásters reales por zona (core/near/landscape)",
        "(NDVI_landscape − NDVI_core) / NDVI_landscape", Confidence.HIGH, DataType.CALCULATED,
        "src/spatial_causality/analyzer.py",
        "Atribución localizada vs. de paisaje desde píxeles reales.",
    ),
    TraceRow(
        "Riesgo (risk_score)", "Componentes eco / presión / vulnerabilidad",
        "0.40·eco + 0.30·HP + 0.30·vuln", Confidence.MEDIUM, DataType.CALCULATED,
        "src/risk_engine/scorer.py", "Pesos de elicitación (suman 1).",
    ),
    TraceRow(
        "DCS (confianza de decisión)", "Calidad dato + robustez temporal + coherencia",
        "Σ subscores (máx 100: DQ25+TR25+SC20+MS15+SS15)", Confidence.MEDIUM, DataType.CALCULATED,
        "src/decision_confidence/assessor.py", "Gate que frena decisiones con poca evidencia.",
    ),
    TraceRow(
        "TPI (prioridad territorial)", "EHS + alerta + DCS + valor estratégico + causalidad",
        "urgencia(0-40)+evidencia(0-25)+estrategia(0-20)+causalidad(0-15)",
        Confidence.MEDIUM, DataType.CALCULATED,
        "src/territorial/tpi.py", "Índice compuesto; cortes de tier son heurísticos.",
    ),
    TraceRow(
        "Tier (1-4)", "Reglas sobre TPI/EHS/DCS/tendencia",
        "umbrales: p.ej. Tier 4 si EHS≥75 ∧ risk≤0.35 ∧ DCS≥55", Confidence.MEDIUM, DataType.CALCULATED,
        "src/territorial/tpi.py", "Capa de estrategia de inversión, NO escala de riesgo.",
    ),

    # ── Capa socioeconómica real (observada / calculada) ─────────────────────
    TraceRow(
        "Población, % ≥65, Δ población", "INE Padrón Municipal",
        "conteo censal directo", Confidence.HIGH, DataType.OBSERVED,
        "etl_socioeconomic.py", "34 municipios PNSG (Madrid + Segovia).",
    ),
    TraceRow(
        "Empleo en hostelería (afiliados SS)", "ALMUDENA (Banco de Datos Municipal, C. Madrid)",
        "conteo de afiliación", Confidence.HIGH, DataType.OBSERVED,
        "etl_socioeconomic.py", "Solo 15 municipios de Madrid (ALMUDENA no cubre Segovia).",
    ),
    TraceRow(
        "SVI (vulnerabilidad socioeconómica)", "ALMUDENA/INE + exposición de activos",
        "100·(0.40·DEP + 0.30·DEM + 0.30·EXP)", Confidence.MEDIUM, DataType.CALCULATED,
        "src/socioeconomic/indicators.py", "Pesos renormalizados sobre componentes disponibles.",
    ),
    TraceRow(
        "Empleos locales en riesgo (KPI tira)", "Empleo ALMUDENA × exposición ambiental",
        "empleo_hostelería · exposición", Confidence.MEDIUM, DataType.CALCULATED,
        "src/socioeconomic/indicators.py:compute_jobs_at_risk",
        "Indicador de SENSIBILIDAD respaldado por dato real. No es empleo perdido observado.",
    ),

    # ── Capa de modelo prospectivo / proxy económico (estimada / simulada) ───
    TraceRow(
        "visitor_capacity_annual", "Atributo curado del activo (no aforo medido)",
        "valor asignado", Confidence.LOW, DataType.ESTIMATED,
        "definición de activos (app.py / run_phase5_report.py)",
        "⚠️ NO es un conteo real de visitantes. De él cascadean ingresos y empleos proxy.",
    ),
    TraceRow(
        "Ingresos potencialmente en riesgo (escenario)", "Modelo proxy de gasto turístico",
        "visitantes · €22.50 · factor_riesgo_cierre", Confidence.LOW, DataType.SIMULATED,
        "app.py tab 5 (modelo económico)",
        "ESCENARIO condicional al supuesto de cierre preventivo. No es pérdida observada.",
    ),
    TraceRow(
        "Empleos expuestos (proxy)", "Modelo proxy",
        "(visitantes / 2500) · factor_riesgo_cierre", Confidence.LOW, DataType.SIMULATED,
        "app.py tab 5", "Distinto del KPI 'empleos en riesgo' respaldado por ALMUDENA.",
    ),
    TraceRow(
        "Ratio coste-beneficio (escenario)", "Modelo proxy",
        "ingresos_escenario / coste_intervención", Confidence.LOW, DataType.SIMULATED,
        "app.py tab 5", "Indicador comparativo de escenario, no un ROI financiero realizado.",
    ),
    TraceRow(
        "Impacto de intervención (ΔEHS, ΔRiesgo)", "Modelo de respuesta a restauración",
        "ΔEHS = 18·headroom·causalidad·confianza", Confidence.LOW, DataType.SIMULATED,
        "src/intervention/impact.py", "Topes de modelo; pendientes de validación de campo.",
    ),
    TraceRow(
        "Declive contrafactual", "Modelo de no-intervención",
        "2–5 EHS/año · f(EHS, SCM, tendencia)", Confidence.LOW, DataType.SIMULATED,
        "src/intervention/scenarios.py", "Tasas asumidas; escenario, no proyección observada.",
    ),
    TraceRow(
        "Tendencia Mann-Kendall (demo)", "Serie calibrada 60 meses (Pipeline B)",
        "test no paramétrico de Mann-Kendall", Confidence.LOW, DataType.SIMULATED,
        "src/time_series/mann_kendall.py",
        "Demuestra CAPACIDAD del sistema; NO es hallazgo inter-anual del PNSG real "
        "(ver docs/nota_metodologica_temporalidad.md).",
    ),
    TraceRow(
        "Presupuesto de restauración (€)", "Coste unitario TRAGSA × longitud × factor SCM",
        "longitud_m · 15.50 €/m · factor_causal", Confidence.MEDIUM, DataType.ESTIMATED,
        "tis_engine.py / src/territorial/allocator.py",
        "Orden de magnitud (tarifa TRAGSA 2023); pendiente de cierre tarifario oficial.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# INVENTARIO DE MULTIPLICADORES  (tarea 5)
# ══════════════════════════════════════════════════════════════════════════════
MULTIPLIERS: list[Multiplier] = [
    Multiplier(
        "Pesos de riesgo (ecológico / presión / vulnerabilidad)", "0.40 / 0.30 / 0.30",
        "Elicitación experta (no fuente externa publicada).",
        "Suman 1; prioriza la señal ecológica sobre presión y vulnerabilidad.",
        "Combinación lineal convexa: el resultado siempre ∈ [0,1].",
        "Media: ±0.10 en un peso reordena alertas en la frontera, no el grueso del ranking.",
        "src/config/constants.py / src/risk_engine/scorer.py",
    ),
    Multiplier(
        "Umbrales de alerta (crítica / urgente / preventiva)", "0.85 / 0.70 / 0.50",
        "Heurística calibrada sobre el sandbox; sin cita física externa.",
        "Definen bandas de acción sobre risk_score; ajustables tras validación de campo.",
        "Función escalón sobre risk_score continuo.",
        "Alta: desplazarlos cambia directamente el recuento de activos Tier 1/2.",
        "src/config/constants.py",
    ),
    Multiplier(
        "Pesos EHS (baseline/trend/anomaly/recovery/stability)", "0.30/0.25/0.25/0.10/0.10",
        "Elicitación experta apoyada en literatura (Pellizzaro 2007, Lloret 2012, "
        "Fernández-Manso 2016).",
        "Suman 1; equilibran nivel, dinámica y estabilidad de la serie.",
        "Combinación convexa → EHS ∈ [0,100].",
        "Media: el modo dosel denso (NDVI≥0.80) ya reasigna pesos para evitar saturación.",
        "src/risk_engine/ehs.py",
    ),
    Multiplier(
        "Gasto medio diario por visitante", "€22.50",
        "MITECO / Informe de turismo de naturaleza 2023.",
        "Gasto en restauración/comercio local por visitante-día.",
        "Factor lineal: escala todos los 'ingresos en riesgo' proporcionalmente.",
        "Alta: ±20% → ±20% en todos los ingresos del escenario. Es un parámetro, no una medición.",
        "app.py tab 5 (_SPEND_PER_VISITOR_EUR)",
    ),
    Multiplier(
        "Visitantes por empleo (directo+indirecto)", "2.500",
        "Proxy para ecoturismo rural (sin cita dura publicada).",
        "Nº de visitantes anuales que sostienen 1 empleo equivalente.",
        "Divisor lineal: empleos = visitantes / 2500.",
        "Alta: ±20% → ∓20% en empleos vinculados/expuestos del proxy.",
        "app.py tab 5 (_VISITORS_PER_JOB)",
    ),
    Multiplier(
        "Factores de riesgo de cierre por tier", "Tier1=1.00 / Tier2=0.40 / Tier3=0.05 / Tier4=0.00",
        "Supuesto de política de gestión (cierre preventivo).",
        "Fracción de afluencia/ingresos afectada si el activo se degrada sin fondos.",
        "Multiplicador acotado [0,1] sobre ingresos y empleos del escenario.",
        "Crítica: define la MAGNITUD del riesgo económico. Tier1=1.00 es el caso peor (cierre total).",
        "app.py tab 5 (_CLOSURE_RISK_FACTOR)",
    ),
    Multiplier(
        "Riesgo residual con fondos (Tier 1)", "0.15",
        "Supuesto: riesgo durante el periodo de restauración.",
        "Reduce el factor de cierre cuando el activo SÍ recibe presupuesto.",
        "Multiplicador 0.15 sobre el factor de cierre base.",
        "Media: amortigua los ingresos en riesgo de los activos financiados.",
        "app.py tab 5 (effective_risk)",
    ),
    Multiplier(
        "Coste de restauración (intervención de campo)", "€35.000",
        "Estimación de planificación / tarifas TRAGSA.",
        "Coste único de una intervención física de restauración.",
        "Constante aditiva al presupuesto; denominador del ratio coste-beneficio.",
        "Media: escala el presupuesto total y el ratio de escenario.",
        "src/intervention/impact.py / src/territorial/allocator.py",
    ),
    Multiplier(
        "ΔEHS máximo por restauración", "18.0",
        "Tope de modelo (mejor caso de recuperación).",
        "Mejora máxima de EHS atribuible a una restauración ideal.",
        "Cota superior: ΔEHS = 18·headroom·causalidad·confianza ≤ 18.",
        "Media: escala la componente ambiental del TIS.",
        "src/intervention/impact.py (_MAX_DELTA_EHS)",
    ),
    Multiplier(
        "Factores causales SCM (localizado/mixto/paisaje)", "1.0 / 0.5 / 0.0",
        "Principio 'quien contamina paga' aplicado a presupuesto local.",
        "Modula cuánto presupuesto local justifica la causa (turismo vs. clima).",
        "Multiplicador [0,1] sobre el presupuesto de restauración.",
        "Media: paisaje (clima) → 0 presupuesto local; localizado → presupuesto íntegro.",
        "src/config/constants.py (SCM_*_FACTOR)",
    ),
    Multiplier(
        "Tasas de declive contrafactual", "2–5 EHS/año",
        "Supuesto de modelo (no observado en el PNSG).",
        "Velocidad de degradación si no se interviene, según EHS/SCM/tendencia.",
        "Decremento anual modulado por estado y con aceleración por realimentación.",
        "Alta: gobierna la magnitud del 'coste de no actuar' a varios años. Es un escenario.",
        "src/intervention/scenarios.py",
    ),
    Multiplier(
        "Coste unitario de restauración lineal", "15.50 €/m",
        "Tarifa TRAGSA 2023 (orden de magnitud).",
        "Coste por metro de senda restaurada (Pipeline A operacional).",
        "Factor lineal sobre longitud × factor causal SCM.",
        "Media: pendiente de cierre tarifario oficial; afecta presupuesto PNSG real.",
        "tis_engine.py",
    ),
]


# ── Validación de integridad (consumida por los tests) ────────────────────────
@dataclass
class IntegrityReport:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_registry() -> IntegrityReport:
    """Comprueba invariantes de la matriz y los multiplicadores.

    Garantiza que ninguna fila quede sin clasificar y que las afirmaciones de
    'pesos que suman 1' del propio registro sean coherentes con lo que se afirma.
    """
    errors: list[str] = []
    for r in TRACEABILITY:
        if not r.variable or not r.source or not r.formula:
            errors.append(f"Fila incompleta: {r.variable!r}")
        if not isinstance(r.confidence, Confidence):
            errors.append(f"Confianza inválida en {r.variable!r}")
        if not isinstance(r.dtype, DataType):
            errors.append(f"Tipo inválido en {r.variable!r}")
    for m in MULTIPLIERS:
        for f_name in ("name", "value", "origin", "justification", "behavior", "sensitivity"):
            if not getattr(m, f_name):
                errors.append(f"Multiplicador con campo vacío '{f_name}': {m.name!r}")
    # Coherencia de los conjuntos de pesos que afirmamos convexos.
    convex_sets = {
        "Riesgo (eco/HP/vuln)": (0.40, 0.30, 0.30),
        "EHS normal": (0.30, 0.25, 0.25, 0.10, 0.10),
        "SVI (DEP/DEM/EXP)": (0.40, 0.30, 0.30),
        "TIS (ENV/ECON/EVID)": (0.55, 0.30, 0.15),
    }
    for name, weights in convex_sets.items():
        if abs(sum(weights) - 1.0) > 1e-9:
            errors.append(f"Pesos no suman 1 en {name}: {sum(weights)}")
    return IntegrityReport(ok=not errors, errors=errors)


def counts_by_type() -> dict[str, int]:
    """Recuento de variables por tipo de dato (para el resumen de la pestaña)."""
    out: dict[str, int] = {}
    for r in TRACEABILITY:
        out[r.dtype.label] = out.get(r.dtype.label, 0) + 1
    return out


# ══════════════════════════════════════════════════════════════════════════════
# RENDERERS STREAMLIT  (tareas 4 y 7) — import perezoso para mantener el módulo testeable
# ══════════════════════════════════════════════════════════════════════════════
_TYPE_COLOR = {
    "Observada": "#0F6E56",   # verde — medición directa
    "Calculada": "#185FA5",   # azul  — determinista
    "Estimada":  "#B7791F",   # ámbar — proxy/parámetro
    "Simulada":  "#A32D2D",   # rojo  — escenario/contrafactual
}


def scenario_badge(label: str = "ESCENARIO", detail: str = "") -> str:
    """HTML de un chip ámbar reutilizable para marcar cifras de modelo/escenario."""
    extra = f' <span style="font-weight:400;opacity:0.85">· {detail}</span>' if detail else ""
    return (
        '<span style="display:inline-block;padding:2px 9px;border-radius:10px;'
        'background:#5a3d0a;color:#FFD98A;font-size:0.70rem;font-weight:700;'
        f'letter-spacing:0.04em;vertical-align:middle">🧪 {label}{extra}</span>'
    )


def type_badge(dtype_label: str) -> str:
    """HTML de un chip de color para el tipo de dato (Observada/Calculada/...)."""
    color = _TYPE_COLOR.get(dtype_label, "#6b7280")
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:9px;'
        f'background:{color};color:white;font-size:0.68rem;font-weight:600">'
        f'{dtype_label}</span>'
    )


def render_fundamento() -> None:
    """Sección A — Fundamento metodológico."""
    import streamlit as st

    st.markdown("#### A · Fundamento metodológico")
    st.markdown(
        "El SNTO operacionaliza el marco **LAC (Limits of Acceptable Change)**: en lugar "
        "de buscar un imposible 'impacto cero', define indicadores medibles, fija umbrales "
        "de cambio aceptable y prioriza la intervención donde se superan. La señal primaria "
        "es **teledetección real** (Sentinel-2 L2A); el resto de capas la contextualizan."
    )
    st.markdown(
        "**Arquitectura de dos pipelines (deliberada y declarada):**\n\n"
        "- **Pipeline A — real (PNSG):** NDVI/NDMI de Sentinel-2 sobre las sendas reales "
        "(OAPN/OSM). Produce **EHS estacional** y **ΔEHS** (primavera vs. verano). Con dos "
        "escenas, el contraste pareado estacional es válido; una **tendencia inter-anual NO** "
        "lo es, y por eso el sistema **no la afirma** para el PNSG.\n"
        "- **Pipeline B — demostración:** serie calibrada (60 meses) sobre activos sintéticos. "
        "Sirve para **demostrar la capacidad** (Mann-Kendall, contrafactuales), nunca como "
        "hallazgo empírico de un territorio real."
    )
    st.info(
        "🛰️ **Principio de override conservador:** el satélite solo sobreescribe el juicio "
        "experto cuando observa **más** degradación, nunca al alza — la roca y el canchal de "
        "alta montaña tienen poco NDVI por geología, no por turismo. Evita falsos positivos "
        "de degradación.",
        icon="🛰️",
    )
    st.caption(
        "Detalle temporal en `docs/nota_metodologica_temporalidad.md`. "
        "Anexo de defensa completo en `docs/defensibilidad_academica.md`."
    )


def render_traceability_matrix() -> None:
    """Sección B — Trazabilidad de indicadores (matriz filtrable)."""
    import pandas as pd
    import streamlit as st

    st.markdown("#### B · Trazabilidad de indicadores")
    st.caption(
        "Cada variable del observatorio clasificada por **naturaleza del dato**. "
        "Filtra para ver qué es medición directa y qué es modelo."
    )

    counts = counts_by_type()
    ccols = st.columns(4)
    for col, key in zip(ccols, ["Observada", "Calculada", "Estimada", "Simulada"]):
        with col:
            st.markdown(
                f'<div class="kpi-card" style="border-left:4px solid {_TYPE_COLOR[key]};">'
                f'<div class="kpi-meta">{key}</div>'
                f'<div class="kpi-value" style="color:{_TYPE_COLOR[key]};font-size:1.4rem">'
                f'{counts.get(key, 0)}</div></div>',
                unsafe_allow_html=True,
            )
    st.write("")

    options = ["Todas"] + ["Observada", "Calculada", "Estimada", "Simulada"]
    sel = st.radio("Filtrar por tipo de dato", options, horizontal=True, index=0,
                   key="trace_type_filter")
    rows = [r for r in TRACEABILITY if sel == "Todas" or r.dtype.label == sel]
    df = pd.DataFrame([{
        "Variable": r.variable,
        "Fuente": r.source,
        "Fórmula / regla": r.formula,
        "Confianza": r.confidence.value,
        "Tipo": r.dtype.label,
        "Ubicación en código": r.location,
        "Nota": r.note,
    } for r in rows])
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(
        "**Observada** = medición directa · **Calculada** = determinista desde observadas · "
        "**Estimada** = proxy/parámetro o atributo curado · **Simulada** = escenario/contrafactual. "
        "La 'Ubicación en código' permite auditar cada cifra contra su fuente."
    )


def render_multiplier_table() -> None:
    """Tabla de multiplicadores con origen, justificación, comportamiento y sensibilidad."""
    import pandas as pd
    import streamlit as st

    st.markdown("##### Multiplicadores y constantes del modelo")
    st.caption(
        "Inventario auditable de cada coeficiente. La columna **sensibilidad** indica el "
        "efecto de moverlo: los marcados *Alta/Crítica* son los que más condicionan los "
        "resultados y deben recalibrarse con datos de campo."
    )
    df = pd.DataFrame([{
        "Multiplicador": m.name,
        "Valor": m.value,
        "Origen": m.origin,
        "Justificación": m.justification,
        "Comportamiento": m.behavior,
        "Sensibilidad": m.sensitivity,
        "Ubicación": m.location,
    } for m in MULTIPLIERS])
    st.dataframe(df, width="stretch", hide_index=True)


@dataclass(frozen=True)
class DataSource:
    name: str
    provider: str
    license: str
    attribution: str
    use_in_snto: str


DATA_SOURCES: list[DataSource] = [
    DataSource(
        "Sentinel-2 L2A (NDVI/NDMI)", "ESA / Copernicus",
        "Copernicus open data (uso libre con atribución)",
        "Contiene datos Copernicus Sentinel-2 modificados (2025–2026)",
        "Cálculo del EHS, ΔEHS y SCM sobre las sendas reales del PNSG.",
    ),
    DataSource(
        "Cartografía de sendas / zonificación", "OAPN (Red de Parques Nacionales)",
        "Reutilización institucional con cita de la fuente",
        "Cartografía oficial OAPN — Parque Nacional Sierra de Guadarrama",
        "Geometría de las 73 sendas y zonificación PRUG.",
    ),
    DataSource(
        "Cartografía complementaria", "OpenStreetMap",
        "Open Database License (ODbL)",
        "© OpenStreetMap contributors",
        "Trazas y puntos de interés donde no hay cobertura OAPN.",
    ),
    DataSource(
        "Padrón, EOATR (demografía y turismo)", "INE",
        "Datos abiertos INE (reutilización con cita)",
        "Instituto Nacional de Estadística (INE)",
        "Población, envejecimiento, despoblación y ocupación turística.",
    ),
    DataSource(
        "Economía municipal (hostelería, renta)", "ALMUDENA — Comunidad de Madrid",
        "Banco de Datos Municipal y Zonal (reutilización con cita)",
        "ALMUDENA, Instituto de Estadística de la Comunidad de Madrid",
        "Empleo en hostelería y componentes del SVI (solo lado Madrid).",
    ),
]


def render_data_sources() -> None:
    """Sección de fuentes de datos y licencias (requisito de publicación)."""
    import pandas as pd
    import streamlit as st

    st.markdown("#### D · Fuentes de datos y licencias")
    st.caption(
        "Atribución obligatoria de cada fuente para la publicación oficial del observatorio."
    )
    df = pd.DataFrame([{
        "Fuente": s.name,
        "Proveedor": s.provider,
        "Licencia / condiciones": s.license,
        "Atribución requerida": s.attribution,
        "Uso en SNTO": s.use_in_snto,
    } for s in DATA_SOURCES])
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(
        "El código se distribuye para **uso académico y de investigación** (UCM). "
        "Los datos pertenecen a sus respectivos proveedores y conservan sus licencias."
    )


def render_limitations() -> None:
    """Sección C — Limitaciones e incertidumbre."""
    import streamlit as st

    st.markdown("#### C · Limitaciones e incertidumbre")
    st.markdown(
        "- **Resolución espacial:** Sentinel-2 ~10 m (NDVI) / ~20 m (NDMI). Por debajo de "
        "ese tamaño, los procesos quedan por debajo del píxel.\n"
        "- **Profundidad temporal (PNSG real):** snapshot de 2 escenas (primavera/verano). "
        "Válido para ΔEHS estacional; **no** para tendencia inter-anual.\n"
        "- **Cobertura socioeconómica:** ALMUDENA solo cubre la Comunidad de Madrid; los "
        "municipios del lado de Segovia tienen SVI parcial (solo fragilidad demográfica).\n"
        "- **Modelo económico = escenario:** ingresos, empleos proxy y ratio coste-beneficio "
        "son **simulaciones condicionales** sobre `visitor_capacity_annual` (atributo curado, "
        "no aforo medido) y parámetros de literatura. **No son economía observada.**\n"
        "- **Multiplicadores pendientes de validación de campo:** umbrales de alerta, tasas de "
        "declive y costes son heurísticos/estimados; se declaran como tales en la tabla inferior.\n"
        "- **Desfase temporal entre capas:** socioeconómico (padrón 2025 / renta 2023) vs. "
        "satélite (2025-26): es contexto de enriquecimiento, no una afirmación causal."
    )
    st.warning(
        "Las cifras del modelo económico (pestaña *Impacto Socioeconómico*) responden a la "
        "pregunta *«¿cuánto valor turístico estaría expuesto SI un activo crítico se degrada "
        "hasta requerir cierre?»*. Son **análisis prospectivo**, no predicción ni observación.",
        icon="⚠️",
    )
    st.divider()
    render_multiplier_table()
