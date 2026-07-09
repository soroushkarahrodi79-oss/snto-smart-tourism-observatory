# Nota metodológica — Alcance temporal de los indicadores y validez del análisis de tendencia

> **Propósito.** Texto de referencia para el capítulo de Metodología del TFM. Delimita con precisión qué afirma cada pipeline en función de su profundidad temporal, blinda la decisión de diseño frente a la crítica estadística más previsible (aplicación de Mann-Kendall sobre series cortas) y declara explícitamente las líneas de trabajo abiertas. La transparencia sobre el alcance es parte del valor metodológico del trabajo, no una concesión.

---

## 0. Actualización v1.1.0 (julio 2026) — leer primero

Esta nota se escribió cuando el SNTO solo tenía dos análisis temporales (ΔEHS
real de 2 escenas + Mann-Kendall demo sobre Pipeline B). **Desde v1.1.0 hay un
tercero:** una serie Sentinel-2 real 2021–2026 (Google Earth Engine) para 21
activos reales del PNSG, con Mann-Kendall calculado sobre esos datos reales.
La distinción central de este documento (raw MK ≠ tendencia estadísticamente
robusta) sigue vigente y de hecho ahora es *más* importante: el nuevo análisis
real se reporta explícitamente como **preliminar**, no confirmatorio, porque
corre sobre NDVI mensual crudo sin desestacionalizar ni corregir
autocorrelación serial. La corrección estadística completa (desestacionalización
+ Hamed-Rao + corrección de empates) es el objetivo de **v1.1.1**
(`research/statistical-rigor`). Las secciones siguientes se han actualizado
para reflejar esta tercera capa; el kit de defensa del tribunal (§7) incluye
las preguntas que este cambio hace previsibles.

## 1. El problema y la decisión de diseño

El SNTO integra tres análisis temporales de naturaleza distinta que **no deben confundirse**:

- **Contraste estacional intra-anual (ΔEHS)** — opera sobre el Pipeline A con datos Sentinel-2 reales del **Parque Nacional Sierra de Guadarrama (PNSG)**, territorio principal del observatorio (dos escenas: primavera y verano de un mismo ciclo). El método se validó previamente sobre la **Reserva de la Biosfera Sierra del Rincón**, que se conserva como piloto de calibración con datos reales propios.
- **Tendencia inter-anual real pero preliminar (v1.1.0)** — Mann-Kendall calculado sobre una serie Sentinel-2 mensual real 2021–2026 (GEE) para 21 activos reales del PNSG. Es un hallazgo empírico sobre territorio real, no una demostración de capacidad — pero su significancia estadística es **indicativa**, no confirmatoria, por las razones de §3.
- **Detección de tendencia inter-anual con rigor completo (Mann-Kendall + pendiente de Sen, desestacionalizado)** — opera sobre el Pipeline B, sobre series multi-anuales calibradas de demostración. Sigue siendo la referencia de lo que "rigor estadístico completo" significa en este sistema, hasta que la serie real del PNSG reciba la misma corrección (v1.1.1).

El test de Mann-Kendall es un contraste no paramétrico de tendencia monótona que **requiere una serie temporal de profundidad suficiente** para que el estadístico S y su varianza tengan potencia estadística; aplicado sobre dos observaciones carecería por completo de significado. Por ello, **el Pipeline A operacional (raster, 2 escenas) no aplica Mann-Kendall**: con dos escenas de un único año, hacerlo sería estadísticamente injustificable — esta parte del diseño no ha cambiado. Lo que sí ha cambiado es que ahora existe, en paralelo, una serie de 66 meses (21 activos) suficientemente profunda para que Mann-Kendall tenga sentido *como test* — el matiz de v1.1.0 no es de profundidad, sino de **desestacionalización y autocorrelación** (§3).

---

## 2. Qué afirma el Pipeline A: ΔEHS como señal de alerta temprana

El resultado temporal real para el PNSG es el **delta estacional del Environmental Health Score**:

```
ΔEHS = EHS_verano − EHS_primavera
ΔEHS > 0 → presión antrópica amplificando el estrés estacional (señal de alerta)
ΔEHS ≤ 0 → recuperación estacional dentro de lo esperable
```

Este indicador es **válido con dos observaciones** porque no pretende estimar una tendencia a largo plazo, sino **un contraste pareado entre dos estados fenológicos del mismo ciclo anual**. Su robustez metodológica descansa en dos pilares:

1. **Anclaje por percentiles de escena (P90/P10).** Cada EHS estacional se normaliza frente a la distribución real de píxeles válidos de su propia imagen, eliminando el sesgo por diferencias de iluminación, fenología o condiciones atmosféricas entre escenas. Esto hace que el delta sea comparable y atribuible a cambio de estado, no a artefacto radiométrico.
2. **Fundamento ecológico.** En ecosistemas montanos mediterráneos, la fenología sigue un patrón verde-primavera / sequía-verano predecible; una caída de salud vegetal **mayor de la esperable estacionalmente** en el corredor del sendero, y no en el fondo de paisaje, señala presión de uso, no clima (esta atribución la formaliza el módulo SCM mediante el Spatial Impact Gradient).

**El ΔEHS se presenta, por tanto, como una instantánea de alerta temprana, no como una tendencia validada.** Es exactamente lo que un sistema de monitorización para gestión adaptativa necesita en su primer ciclo: una señal accionable, con su nivel de confianza (DCS) explícito.

---

## 3. Qué afirma la nueva capa real (v1.1.0): Mann-Kendall preliminar sobre el PNSG

Desde **v1.1.0**, el SNTO ingiere una serie Sentinel-2 mensual real 2021–2026
(fuente `GEE:S2_SR_HARMONIZED`) para **21 activos reales del PNSG**
(`scripts/extract_gee_timeseries_pnsg.py` → `clean_assets/timeseries/` →
`src/platform/satellite_trends.py`), servida en el panel "Tendencias
satelitales reales" del dashboard. Con 66 observaciones mensuales por activo,
la serie tiene **profundidad suficiente** para que el estadístico de
Mann-Kendall tenga potencia estadística — a diferencia del ΔEHS de 2 escenas.

**Pero profundidad suficiente no equivale a inferencia confirmatoria.** El
cálculo actual (`scripts/run_timeseries_analysis.py`) corre Mann-Kendall
directamente sobre el **NDVI mensual crudo**, sin dos correcciones estándar en
climatología/teledetección:

1. **Desestacionalización.** El NDVI de un ecosistema de montaña mediterráneo
   tiene un ciclo estacional muy marcado (pico en mayo, mínimo en
   enero–febrero). Un test de tendencia monótona aplicado sobre una serie con
   estacionalidad no removida puede detectar significancia que refleja el
   patrón estacional repetido, no una tendencia interanual real.
2. **Autocorrelación serial.** Observaciones mensuales consecutivas de NDVI
   están correlacionadas entre sí (la vegetación de un mes se parece a la del
   mes anterior). El cálculo actual de varianza de Mann-Kendall (`var_s = n(n−1)(2n+5)/18`)
   asume independencia; con autocorrelación positiva, esto **infla la
   significancia** (p-valores más bajos de lo que corresponde).

Por eso los resultados (τ, p, y los recuentos de activos en degradación/mejora)
se etiquetan explícitamente como **preliminares/indicativos** en el dashboard,
en `clean_assets/README.md` y aquí. Son un hallazgo empírico real sobre el
PNSG — no una demostración de capacidad sobre datos sintéticos como el
Pipeline B — pero con un nivel de confianza estadística menor del que un
Mann-Kendall correctamente especificado tendría. La corrección
(desestacionalización vía medias anuales o descomposición STL + corrección de
autocorrelación de Hamed-Rao + corrección de empates) es el objetivo de
**v1.1.1** (`research/statistical-rigor`).

---

## 4. Qué afirma el Pipeline B: Mann-Kendall con rigor estadístico completo

La capacidad de detección de tendencia inter-anual **con la corrección estadística completa** se demuestra sobre el Pipeline B, donde la profundidad temporal (series multi-anuales calibradas) lo justifica. En este pipeline, el análisis se aplica sobre la serie desestacionalizada (residuos de la descomposición armónica de dos armónicas), con umbral de significación p < 0,05 y la pendiente de Sen como estimador robusto.

Es crucial el matiz de presentación: **Mann-Kendall con rigor completo es una capacidad arquitectónica del SNTO demostrada en datos de calibración; el hallazgo empírico sobre el PNSG (§3) existe, pero con ese mismo rigor aún pendiente.** El Pipeline B sigue siendo la referencia de lo que "corrección estadística completa" significa en este sistema, hasta que la serie real del PNSG la reciba en v1.1.1.

---

## 5. Frontera de afirmaciones (tabla de honestidad)

| Afirmación | Pipeline A — raster (real, 2 escenas) | Pipeline A — serie temporal (real, PNSG, v1.1.0) | Pipeline B (demo, Villuercas) |
|---|---|---|---|
| Estado de salud ambiental por activo (EHS) | ✅ Sí, con datos Sentinel-2 reales | — | ✅ Sí, con datos calibrados |
| Señal de alerta estacional (ΔEHS) | ✅ Sí — resultado real | — | ✅ Sí |
| Atribución causal espacial (SCM/SIG) | ✅ Sí, desde rásteres reales | — | 🟡 Simulada desde una observación |
| Tendencia inter-anual (Mann-Kendall/Sen) | ❌ No — profundidad insuficiente | 🟡 **Preliminar** — real, sin desestacionalizar/autocorrelación (v1.1.0) | ✅ Sí — rigor completo, capacidad demostrada |
| Anomalías inter-anuales / sequía | ❌ No | 🟡 Señal cruzada observada (2022 peor año en la mayoría de activos), no test formal | ✅ Sí |

> Regla de lectura: el SNTO **nunca** presenta una inferencia con más confianza estadística de la que su método soporta. El Pipeline B sigue siendo lo defendible con rigor completo; la serie real del PNSG (v1.1.0) es un hallazgo empírico genuino pero explícitamente preliminar hasta v1.1.1.

---

## 6. Línea de trabajo abierta (declarada, no oculta)

**Hecho (v1.1.0):** la integración de la serie multi-anual real 2021–2026 para 21 activos del PNSG vía **Google Earth Engine** está completa e ingerida (`clean_assets/timeseries/`), con Mann-Kendall calculado y surgido en el dashboard.

**Abierto (v1.1.1, `research/statistical-rigor`):** la corrección estadística de esa serie —desestacionalización (medias anuales o STL), corrección de autocorrelación serial (Hamed-Rao) y corrección de empates— para que la tendencia real del PNSG alcance el mismo rigor que hoy solo demuestra el Pipeline B. Se declara como trabajo en curso, no como carencia oculta: los datos y el pipeline de cálculo ya existen: falta el método estadístico correcto, no una nueva ingesta.

---

## 7. Kit de defensa — preguntas previsibles del tribunal

**P: «Aplicas Mann-Kendall con un año de datos. ¿No es eso estadísticamente nulo?»**
R: Correcto para el Pipeline A raster (2 escenas), que por eso no lo aplica — ahí el resultado temporal es el ΔEHS estacional. Pero desde v1.1.0 existe una serie separada de 66 observaciones mensuales (21 activos del PNSG, 2021–2026 real vía GEE), con profundidad suficiente para que el test tenga potencia estadística. Ahí la limitación ya no es de profundidad — es que el cálculo aún no está desestacionalizado ni corregido por autocorrelación (ver siguiente pregunta).

**P: «Tu serie real del PNSG tiene un ciclo estacional NDVI muy marcado. ¿Cómo sabes que tu p-valor no es solo estacionalidad disfrazada de tendencia?»**
R: No lo sabemos con la confianza que un Mann-Kendall bien especificado daría — y por eso lo declaramos explícitamente. El cálculo actual (`scripts/run_timeseries_analysis.py`) corre sobre NDVI mensual crudo, sin desestacionalizar y sin corregir autocorrelación serial (ambas inflan la significancia). El dashboard, `clean_assets/README.md` y esta nota etiquetan el resultado como **preliminar/indicativo**, no confirmatorio. La corrección (desestacionalización + Hamed-Rao) es el objetivo declarado de v1.1.1, ya con rama de trabajo abierta (`research/statistical-rigor`).

**P: «¿Por qué debería creer un delta calculado con solo dos imágenes?»**
R: Porque no afirma una tendencia, sino un cambio de estado entre dos puntos fenológicos del mismo ciclo, normalizado por percentiles de escena para eliminar el sesgo radiométrico, y atribuido espacialmente por el SCM. Su fiabilidad se reporta de forma explícita mediante el Decision Confidence Score, que degrada cualquier recomendación si la cobertura temporal es insuficiente (data quality gate).

**P: «Entonces, ¿el sistema realmente funciona en el PNSG o solo en la demo?»**
R: El diagnóstico de estado (EHS), la señal de alerta (ΔEHS), la atribución causal (SCM/SIG) y, desde v1.1.0, una tendencia interanual preliminar funcionan con datos reales en el PNSG. Lo que el Pipeline B sigue demostrando en exclusiva es la **versión con rigor estadístico completo** de esa tendencia. La frontera está documentada y es deliberada.

**P: «¿Qué falta para tener una tendencia real y estadísticamente robusta en el PNSG?»**
R: Ya no falta la ingesta — eso está hecho desde v1.1.0. Falta aplicar a esa serie real la misma corrección estadística (desestacionalización + autocorrelación) que ya se aplica en el Pipeline B. Es trabajo de método sobre datos existentes, no una nueva recolección.

**P: «¿No es esto una limitación grave del trabajo?»**
R: Es una limitación de rigor estadístico sobre un método ya implementado y datos ya disponibles, declarada explícitamente en el propio dashboard — no una carencia oculta descubierta por el tribunal. Que el sistema muestre un resultado preliminar etiquetado como tal, en vez de ocultarlo o sobreclamarlo, es precisamente el tipo de honestidad metodológica que este documento defiende.

---

*Documento de apoyo al TFM sobre gobernanza inteligente y transición regenerativa en espacios naturales protegidos. Territorio principal: Parque Nacional Sierra de Guadarrama; piloto de calibración metodológica: Reserva de la Biosfera Sierra del Rincón · SNTO v1.1.0 · actualizado julio 2026.*
