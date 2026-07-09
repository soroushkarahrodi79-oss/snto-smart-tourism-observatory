# Defensibilidad académica del SNTO — Anexo de la memoria del TFM

**Proyecto:** Smart Nature Tourism Observatory (SNTO)
**Caso de estudio:** Parque Nacional de la Sierra de Guadarrama (PNSG)
**Fecha del anexo:** 2026-06-15 · **Actualizado:** 2026-07-09 (v1.1.0 — ver Adenda al final del §4, V6, y hoja de ruta §7)
**Propósito:** documentar con rigor qué se mide, qué se calcula, qué se estima y qué se
simula en el observatorio; trazar cada indicador y multiplicador a su fuente; declarar
las limitaciones; y dotar a la defensa de un guion frente a preguntas de tribunal.

> Principio rector: **no ocultar, exponer.** El SNTO combina un núcleo satelital real
> con una capa socioeconómica mixta (datos oficiales + modelo proxy). La defensibilidad
> no depende de que todo sea observado, sino de que **cada cifra esté etiquetada por su
> naturaleza** y de que el sistema nunca presente un escenario como una observación.

Este anexo se sincroniza con el registro de código `src/platform/methodology.py`
(matriz `TRACEABILITY` y `MULTIPLIERS`), que alimenta la pestaña *8 · Fundamento y
Trazabilidad* del propio observatorio.

---

## 1. Clasificación epistémica de las variables (tarea 2)

Cuatro categorías, según la **naturaleza del dato** (eje distinto al de *procedencia*
satélite/calibrado/sintético que ya gestiona `src/platform/provenance.py`):

| Tipo | Definición | Ejemplos en SNTO |
|---|---|---|
| **Observada** | Medición directa de un instrumento o registro oficial. | NDVI/NDMI (Sentinel-2), población (INE), empleo hostelería (ALMUDENA), trazas OAPN/OSM. |
| **Calculada** | Determinista a partir de variables observadas, con fórmula explícita. | EHS, ΔEHS, SIG/SCM, risk_score, DCS, TPI, SVI, empleos en riesgo (KPI tira). |
| **Estimada** | Proxy de literatura o atributo curado, sin medición directa. | `visitor_capacity_annual`, €22,50/visitante, 2.500 visitantes/empleo, costes €. |
| **Simulada** | Escenario, contrafactual o serie de demostración. | Ingresos/empleos proxy en riesgo, ratio coste-beneficio, declive contrafactual, Mann-Kendall sobre Pipeline B (demo, datos sintéticos). |

**Recuento aproximado:** ~7 Observadas · ~10 Calculadas · ~3 Estimadas · ~6 Simuladas.
La capa de mayor riesgo académico es la **Simulada/Estimada** del modelo económico, hoy
etiquetada explícitamente como tal en la interfaz. **Nota v1.1.0:** el Mann-Kendall real
del PNSG (21 activos, GEE, ver fila añadida en §2) NO es Simulada — es Calculada sobre
datos Observados reales — pero se etiqueta con **confianza Baja / preliminar** porque el
test aún no está desestacionalizado ni corregido por autocorrelación. No confundir esta
capa con el Mann-Kendall demo de Pipeline B, que sigue siendo Simulada.

---

## 2. Matriz de trazabilidad (tarea 3)

| Variable | Fuente | Fórmula / regla | Confianza | Tipo | Código |
|---|---|---|---|---|---|
| NDVI | Sentinel-2 L2A B4/B8 | `(NIR−RED)/(NIR+RED)` | Alta | Observada | `src/features/spectral.py` |
| NDMI | Sentinel-2 L2A B8/B11 | `(NIR−SWIR)/(NIR+SWIR)` | Alta | Observada | `src/features/spectral.py` |
| Geometría de sendas | OAPN + OSM | trazas vectoriales | Alta | Observada | `data/raw_assets/vector_data/` |
| Fechas de escena | productos `.SAFE` | parseo del nombre | Alta | Observada | `provenance.py:detect_scene_dates` |
| EHS estacional (PNSG) | percentiles P90/P10 de escena | `100·(1−D)` | Alta | Calculada | `calculate_delta_ehs.py` |
| ΔEHS | EHS_verano − EHS_primavera | resta pareada | Alta | Calculada | `calculate_delta_ehs.py` |
| EHS multi-componente | serie NDVI/NDMI | `100·(1−Σ pesos·riesgos)` | Media | Calculada | `src/risk_engine/ehs.py` |
| SIG / SCM | rásters por zona | `(NDVI_land−NDVI_core)/NDVI_land` | Alta | Calculada | `src/spatial_causality/analyzer.py` |
| risk_score | componentes eco/HP/vuln | `0.40·eco+0.30·HP+0.30·vuln` | Media | Calculada | `src/risk_engine/scorer.py` |
| DCS | calidad+robustez+coherencia | `Σ subscores ≤ 100` | Media | Calculada | `src/decision_confidence/assessor.py` |
| TPI | EHS+alerta+DCS+estrategia+causa | suma ponderada (0–100) | Media | Calculada | `src/territorial/tpi.py` |
| Tier (1–4) | reglas TPI/EHS/DCS/tendencia | umbrales heurísticos | Media | Calculada | `src/territorial/tpi.py` |
| Población, %≥65, Δpob | INE Padrón | conteo censal | Alta | Observada | `etl_socioeconomic.py` |
| Empleo hostelería | ALMUDENA | conteo afiliación | Alta | Observada | `etl_socioeconomic.py` |
| SVI | ALMUDENA/INE + exposición | `100·(0.40·DEP+0.30·DEM+0.30·EXP)` | Media | Calculada | `src/socioeconomic/indicators.py` |
| Empleos locales en riesgo (KPI) | empleo × exposición | `empleo·exposición` | Media | Calculada | `indicators.py:compute_jobs_at_risk` |
| `visitor_capacity_annual` | atributo curado | valor asignado | Baja | Estimada | definición de activos |
| Ingresos pot. en riesgo | proxy | `visitantes·€22,50·factor` | Baja | Simulada | `app.py` tab 5 |
| Empleos expuestos (proxy) | proxy | `(visitantes/2500)·factor` | Baja | Simulada | `app.py` tab 5 |
| Ratio coste-beneficio | proxy | `ingresos_esc/coste` | Baja | Simulada | `app.py` tab 5 |
| Impacto de intervención | modelo | `ΔEHS=18·headroom·causa·conf` | Baja | Simulada | `src/intervention/impact.py` |
| Declive contrafactual | modelo | `2–5 EHS/año·f(EHS,SCM)` | Baja | Simulada | `src/intervention/scenarios.py` |
| Mann-Kendall (demo) | serie calibrada 60 m | test no paramétrico | Baja | Simulada | `src/time_series/mann_kendall.py` |
| Mann-Kendall real PNSG (v1.1.0) | NDVI mensual Sentinel-2 real 2021–2026 (GEE), 21 activos | test no paramétrico, **sin desestacionalizar/autocorrelación** | Baja (preliminar) | Calculada | `scripts/run_timeseries_analysis.py`, `src/platform/satellite_trends.py` |
| Presupuesto restauración | TRAGSA × longitud × SCM | `m·15,50€·factor` | Media | Estimada | `tis_engine.py` |

---

## 3. Inventario de multiplicadores (tarea 5)

Origen · justificación · comportamiento matemático · sensibilidad. (Versión viva en
`src/platform/methodology.py::MULTIPLIERS`, también visible en la pestaña 8.)

| Multiplicador | Valor | Origen | Comportamiento | Sensibilidad |
|---|---|---|---|---|
| Pesos riesgo (eco/HP/vuln) | 0.40/0.30/0.30 | Elicitación experta | Combinación convexa → [0,1] | **Media** |
| Umbrales de alerta | 0.85/0.70/0.50 | Heurística calibrada (sin cita externa) | Función escalón sobre risk_score | **Alta** |
| Pesos EHS | 0.30/0.25/0.25/0.10/0.10 | Elicitación + literatura | Convexa → EHS∈[0,100] | Media |
| Gasto/visitante | €22,50 | MITECO 2023 | Factor lineal sobre ingresos | **Alta** |
| Visitantes/empleo | 2.500 | Proxy ecoturismo (sin cita dura) | Divisor lineal | **Alta** |
| Factores de cierre por tier | 1.00/0.40/0.05/0.00 | Supuesto de política | Multiplicador [0,1] | **Crítica** |
| Riesgo residual con fondos | 0.15 | Supuesto | Multiplicador sobre factor cierre | Media |
| Coste restauración | €35.000 | Estimación / TRAGSA | Constante aditiva | Media |
| ΔEHS máx restauración | 18.0 | Tope de modelo | Cota superior | Media |
| Factores causales SCM | 1.0/0.5/0.0 | "Quien contamina paga" | Multiplicador presupuesto | Media |
| Tasas de declive contrafactual | 2–5 EHS/año | Supuesto | Decremento anual con feedback | **Alta** |
| Coste unitario lineal | 15,50 €/m | TRAGSA 2023 | Factor lineal | Media |

Los marcados **Alta/Crítica** son los que más condicionan los resultados económicos y
deben recalibrarse con datos de campo antes de cualquier uso operativo real.

---

## 4. Diagnóstico de vulnerabilidades (tareas 9 y 10)

Para cada una: **riesgo → mitigación → respuesta de defensa**.

### V1 — Lenguaje de economía realizada sobre un modelo condicional · **CRÍTICA**
- **Riesgo:** etiquetas como "Ingresos en Riesgo", "ROI", "Coste de No Actuar" inducen a
  leer un escenario como pérdida observada o predicción.
- **Mitigación (implementada):** sustitución a lenguaje prospectivo ("Ingresos potencialmente
  en riesgo — escenario", "Ratio coste-beneficio", "Exposición económica") + chip
  `MODELO PROSPECTIVO` + expander de fundamento en la propia pestaña.
- **Defensa:** «La pestaña responde a una pregunta condicional explícita —*¿qué valor
  estaría expuesto si…?*—. La interfaz marca cada cifra como escenario; en ningún punto
  se afirma una pérdida observada ni una predicción.»

### V2 — `visitor_capacity_annual` es un atributo curado, no observado · **CRÍTICA**
- **Riesgo:** ingresos y empleos proxy cascadean de un valor no medido, dando apariencia
  de cuantificación empírica.
- **Mitigación (implementada):** clasificado **Estimada** en la matriz; expanders en tabs 4
  y 5 lo declaran como parámetro de planificación; los resultados derivados se marcan
  **Simulada**.
- **Defensa:** «Es un parámetro de planificación, no un aforo. Por eso todo lo que deriva
  de él se presenta como cobertura de escenario, no como afluencia real. El núcleo de
  decisión (EHS/ΔEHS/SCM) no depende de este parámetro.»

### V3 — Multiplicadores sin cita en superficie · **ALTA**
- **Riesgo:** umbrales (0.85/0.70/0.50), costes y deltas parecen arbitrarios.
- **Mitigación (implementada):** tabla de multiplicadores con origen/justificación/sensibilidad
  en la pestaña 8 y en este anexo; los heurísticos se declaran como "calibrados sobre el
  sandbox, ajustables tras validación".
- **Defensa:** «Distinguimos pesos con respaldo de literatura (EHS) de heurísticas de
  calibración (umbrales de alerta). Estas últimas se declaran como tales y son parámetros
  de gobernanza, no leyes físicas.»

### V4 — Proxy económico sin intervalo de sensibilidad · **ALTA**
- **Riesgo:** €22,50 y 2.500 visitantes/empleo presentados como punto único.
- **Mitigación (implementada):** documentada la sensibilidad lineal (±20%→±20%); recomendada
  banda baja/medio/alto como mejora P2.
- **Defensa:** «El modelo es deliberadamente transparente y lineal: su sensibilidad es
  trivial de comunicar. No pretende precisión, sino orden de magnitud comparativo.»

### V5 — Falta de superficie única de fundamento/trazabilidad · **MEDIA**
- **Mitigación (implementada):** pestaña 8 *Fundamento y Trazabilidad* + expanders in situ.
- **Defensa:** «Toda la trazabilidad es accesible desde la propia herramienta, no solo en
  la memoria.»

### V6 — Mann-Kendall demo junto a hallazgos reales · **MEDIA** (actualizado v1.1.0)
- **Estado original (pre-v1.1.0):** la matriz marcaba el test como **Simulada (demo
  Pipeline B)** exclusivamente; el PNSG solo reportaba ΔEHS. Ya no es el estado actual.
- **Estado actual (v1.1.0):** el PNSG **sí tiene** una tendencia Mann-Kendall real (21
  activos, serie GEE 2021–2026, 66 observaciones/activo — profundidad suficiente para
  el test). El riesgo se desplaza: ya no es "¿por qué aplicas MK sobre 2 escenas?" sino
  "¿tu MK real está desestacionalizado y corregido por autocorrelación?" — y la
  respuesta honesta es **no, todavía no**.
- **Mitigación (implementada):** el resultado se etiqueta explícitamente **preliminar /
  indicativo** en el dashboard (panel "Tendencias satelitales reales"), en
  `clean_assets/README.md` y en `docs/nota_metodologica_temporalidad.md` (reescrito
  v1.1.0, incluye nueva pregunta de tribunal sobre estacionalidad/autocorrelación). La
  corrección estadística completa (desestacionalización + Hamed-Rao + corrección de
  empates) es el objetivo declarado de **v1.1.1** (`research/statistical-rigor`).
- **Defensa:** «Con 2 escenas, una tendencia inter-anual sería estadísticamente
  injustificable — por eso el Pipeline A raster no la aplica. Pero desde v1.1.0 existe una
  serie separada de 66 meses reales del PNSG, suficientemente profunda para Mann-Kendall.
  La declaramos preliminar porque aún no está desestacionalizada ni corregida por
  autocorrelación — el Pipeline B sigue siendo la referencia de rigor completo hasta que
  esa corrección llegue a la serie real (v1.1.1). Preferimos mostrar un resultado
  preliminar etiquetado como tal a ocultarlo o sobreclamarlo.»

### V7 — "Deuda ecológica acumulada (€)" · **BAJA**
- **Riesgo:** reencuadra la necesidad de conservación como obligación financiera observada.
- **Mitigación:** documentado como coste estimado de mitigación (no deuda contable);
  candidata a renombrar a "Coste estimado de mitigación pendiente".
- **Defensa:** «Es la suma de costes de intervención recomendados para Tier 1+2, no un
  pasivo contable.»

---

## 5. Banco de preguntas de tribunal y respuestas modelo

1. **«¿Los empleos en riesgo son empleos reales perdidos?»**
   No. El KPI de la tira ejecutiva procede de afiliación **real** ALMUDENA/INE ponderada
   por exposición ambiental: es un indicador de **sensibilidad** (Calculada). Las cifras de
   la pestaña 5 son un **escenario** proxy, etiquetado como tal. Ninguna es empleo perdido
   observado.

2. **«¿De dónde sale el gasto de €22,50 por visitante?»**
   Del Informe de turismo de naturaleza de MITECO (2023). Es una **estimación de literatura**,
   declarada como tipo *Estimada*, con sensibilidad lineal documentada.

3. **«¿Por qué el umbral de alerta crítica es 0.85 y no otro?»**
   Es una **heurística calibrada** sobre la muestra de control, no una ley física. Se declara
   como parámetro de gobernanza ajustable tras validación de campo.

4. **«Con solo dos imágenes, ¿cómo justifica una tendencia temporal?»** *(actualizado v1.1.0)*
   El Pipeline A raster (2 escenas) reporta únicamente **ΔEHS estacional** (contraste
   pareado válido con 2 escenas) y no aplica Mann-Kendall — eso no ha cambiado. Pero desde
   v1.1.0 existe una serie separada, real, de 66 observaciones mensuales (21 activos del
   PNSG, GEE 2021–2026), con profundidad suficiente para Mann-Kendall. Ahí la limitación ya
   no es de profundidad: el test corre sobre NDVI mensual crudo, sin desestacionalizar ni
   corregir autocorrelación serial, así que el resultado se etiqueta **preliminar**, no
   confirmatorio. El Pipeline B sigue siendo la referencia de rigor estadístico completo
   hasta que esa corrección llegue a la serie real (v1.1.1). Ver
   `docs/nota_metodologica_temporalidad.md` §3 y §7 para el desarrollo completo.

5. **«¿`visitor_capacity_annual` es un aforo medido?»**
   No, es un **atributo curado** de planificación. Por eso ingresos/empleos derivados se
   marcan *Simulada/Estimada* y se presentan como cobertura de escenario.

6. **«¿No es la capa socioeconómica demasiado parcial?»**
   ALMUDENA solo cubre Madrid; los municipios de Segovia tienen SVI parcial (solo demografía).
   Está **declarado** en la interfaz y en el SVI mediante renormalización de pesos. Es contexto
   de enriquecimiento, no afirmación causal.

7. **«¿Qué pasaría si sus multiplicadores estuvieran mal?»**
   El núcleo de diagnóstico (EHS/ΔEHS/SCM) es independiente de los multiplicadores económicos.
   Estos solo afectan a la capa de *priorización presupuestaria*, que es comparativa entre
   activos, no una cuantificación absoluta.

8. **«¿Esto es una predicción?»**
   No. Es **análisis prospectivo**: dado un estado satelital observado, explora escenarios
   condicionales ("si no se interviene…"). No emite predicciones probabilísticas de futuro.

---

## 6. Puntuación de defendibilidad académica (0–10)

| Dimensión | Antes | Después | Comentario |
|---|---|---|---|
| Rigor del núcleo satelital | 8.5 | 8.5 | Sentinel-2 real, EHS anclado por percentiles, override conservador. |
| Honestidad temporal | 8.0 | 8.0 | Mantenida tras v1.1.0: nuevo hallazgo real (MK PNSG) etiquetado preliminar en vez de sobreclamado; ΔEHS vs. MK demo vs. MK real-preliminar, las tres fronteras declaradas. |
| Trazabilidad en superficie | 4.0 | 8.5 | Matriz + multiplicadores + código citados. |
| Lenguaje económico | 3.0 | 8.0 | Sustituido a prospectivo + chips de escenario. |
| Documentación de supuestos | 5.0 | 8.5 | Inventario de multiplicadores con sensibilidad. |
| Transparencia de datos | 7.5 | 8.5 | Observada/Calculada/Estimada/Simulada explícita. |

**Puntuación global: 6.0 → ~8.0 / 10.** El núcleo era ya defendible; el salto proviene de
**etiquetar y trazar** la capa de modelo en lugar de presentarla con lenguaje de observación.

---

## 7. Hoja de ruta: de "demo tecnológica" a "prototipo científico defendible" (tarea 8)

1. **(Hecho)** Etiquetado prospectivo + chips de escenario en la capa económica.
2. **(Hecho)** Superficie única de Fundamento/Trazabilidad/Limitaciones (pestaña 8 + expanders).
3. **(Hecho)** Inventario auditable de multiplicadores con sensibilidad.
4. **(P2)** Banda de sensibilidad bajo/medio/alto en el proxy económico (sin cambiar defaults):
   convierte un parámetro fijo en un análisis de incertidumbre explícito.
5. **(Hecho — v1.1.0)** Ingerir la serie 2021–2026 vía Google Earth Engine para 21 activos
   reales del PNSG y surgir Mann-Kendall real en el dashboard, en paralelo al demo de
   Pipeline B. Etiquetado explícitamente **preliminar** (ver V6).
6. **(P2 — v1.1.1, `research/statistical-rigor`)** Corregir estadísticamente la serie real
   del PNSG: desestacionalización (medias anuales o STL) + corrección de autocorrelación
   (Hamed-Rao) + corrección de empates, para que la tendencia real alcance el mismo rigor
   que hoy solo demuestra el Pipeline B. Este es ahora el ítem de mayor riesgo académico
   pendiente en la capa temporal.
7. **(P2)** Validación de campo (protocolo en `docs/field_validation_protocol.md`) para
   recalibrar umbrales de alerta y costes con evidencia.
8. **(P3)** Estratificar baselines por elevación/orientación (DEM) para robustecer el EHS.

> Estado actual del prototipo: **defendible como TFM** siempre que la defensa use la pestaña
> *8 · Fundamento y Trazabilidad* (o la vista *Auditoría*) y este anexo como soporte, y que se
> verbalice la distinción entre el **núcleo observado/calculado**, la **tendencia real
> preliminar del PNSG (v1.1.0)** y la **capa simulada** de escenarios económicos y del
> Mann-Kendall demo de Pipeline B.
