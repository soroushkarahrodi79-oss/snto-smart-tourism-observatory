# Nota metodológica — Alcance temporal de los indicadores y validez del análisis de tendencia

> **Propósito.** Texto de referencia para el capítulo de Metodología del TFM. Delimita con precisión qué afirma cada pipeline en función de su profundidad temporal, blinda la decisión de diseño frente a la crítica estadística más previsible (aplicación de Mann-Kendall sobre series cortas) y declara explícitamente las líneas de trabajo abiertas. La transparencia sobre el alcance es parte del valor metodológico del trabajo, no una concesión.

> **Nota de versión.** Esta nota fija el *alcance* (qué territorio sostiene qué afirmación). El *detalle cuantitativo* del método de tendencia e incertidumbre —desestacionalización, corrección de autocorrelación e intervalos de confianza— se documenta en la [nota de rigor estadístico](nota_metodologica_rigor_estadistico.md). Con la integración de la serie Sentinel-2 real multi-anual del PNSG (v1.1.0), la «línea de trabajo abierta» descrita en §5 pasa a estar parcialmente cubierta: consúltese la nota de rigor para el estado vigente de la detección de tendencia sobre datos reales.

---

## 0. Actualización v1.1.1 (julio 2026) — leer primero

Esta nota nació en v1.1.0, cuando el SNTO ya tenía tres análisis temporales
(ΔEHS real de 2 escenas + Mann-Kendall real pero preliminar sobre el PNSG +
Mann-Kendall demo con rigor completo sobre Pipeline B) y el hallazgo real del
PNSG se declaraba explícitamente **preliminar**: el test corría sobre NDVI
mensual crudo, sin desestacionalizar ni corregir autocorrelación serial.

**Desde v1.1.1, esa brecha está cerrada.** El Mann-Kendall real del PNSG corre
ahora sobre la serie **desestacionalizada** (descomposición armónica), con
**corrección de empates** en la varianza y **pendiente de Sen con intervalo de
confianza no paramétrico** (Gilbert 1987). Los 7 veredictos significativos
superan además una prueba de robustez de *pre-whitening* libre de tendencia
(Yue-Pilon 2002) frente a la autocorrelación serial, sin ningún cambio de
dirección. **De paso, v1.1.1 corrigió un bug de orden cronológico** presente
en el release público de v1.1.0 (`year`/`month` se ordenaban como texto —
"10","11" antes que "2"), que corrompía la serie mensual de los 21 activos; el
resultado aquí descrito ya incorpora esa corrección. Las secciones siguientes
se han actualizado; el kit de defensa del tribunal (§7) incluye las preguntas
que este cambio hace previsibles — incluida la de por qué se declara un bug
encontrado durante el propio proceso de rigor, en vez de callarlo.

## 1. El problema y la decisión de diseño

El SNTO integra tres análisis temporales de naturaleza distinta que **no deben confundirse**:

- **Contraste estacional intra-anual (ΔEHS)** — opera sobre el Pipeline A con datos Sentinel-2 reales del **Parque Nacional Sierra de Guadarrama (PNSG)**, territorio principal del observatorio (dos escenas: primavera y verano de un mismo ciclo). El método se validó previamente sobre la **Reserva de la Biosfera Sierra del Rincón**, que se conserva como piloto de calibración con datos reales propios.
- **Tendencia inter-anual real y corregida (v1.1.1)** — Mann-Kendall calculado sobre una serie Sentinel-2 mensual real 2021–2026 (GEE) para 21 activos reales del PNSG, desestacionalizada, con corrección de empates, IC de Sen y verificación de robustez frente a autocorrelación. Es un hallazgo empírico sobre territorio real, con el mismo nivel de rigor estadístico que antes solo demostraba el Pipeline B (§3).
- **Detección de tendencia inter-anual sobre datos de demostración (Mann-Kendall + pendiente de Sen, desestacionalizado)** — opera sobre el Pipeline B, sobre series multi-anuales calibradas. Sigue siendo útil como demostración arquitectónica del método sobre una serie de referencia con anomalías climáticas documentadas — pero, desde v1.1.1, ya no es la única capa con rigor estadístico completo: el PNSG real también lo tiene.

El test de Mann-Kendall es un contraste no paramétrico de tendencia monótona que **requiere una serie temporal de profundidad suficiente** para que el estadístico S y su varianza tengan potencia estadística; aplicado sobre dos observaciones carecería por completo de significado. Por ello, **el Pipeline A operacional (raster, 2 escenas) no aplica Mann-Kendall**: con dos escenas de un único año, hacerlo sería estadísticamente injustificable — esta parte del diseño no ha cambiado. La serie de 66 meses (21 activos) sí tiene la profundidad necesaria, y desde v1.1.1 recibe además el tratamiento estadístico correcto (§3).

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

## 3. Qué afirma la capa real del PNSG (v1.1.1): Mann-Kendall corregido

Desde **v1.1.0**, el SNTO ingiere una serie Sentinel-2 mensual real 2021–2026
(fuente `GEE:S2_SR_HARMONIZED`) para **21 activos reales del PNSG**
(`scripts/extract_gee_timeseries_pnsg.py` → `clean_assets/timeseries/` →
`src/platform/satellite_trends.py`), servida en el panel "Tendencias
satelitales reales" del dashboard. Con 66 observaciones mensuales por activo,
la serie tiene **profundidad suficiente** para que el estadístico de
Mann-Kendall tenga potencia estadística — a diferencia del ΔEHS de 2 escenas.

En v1.1.0 el test corría directamente sobre el **NDVI mensual crudo**, sin dos
correcciones estándar en climatología/teledetección (desestacionalización y
autocorrelación), por lo que el resultado se declaraba preliminar. **Desde
v1.1.1, el pipeline (`scripts/run_timeseries_analysis.py`) aplica la cadena
completa**, implementada en `src/time_series/{decomposition,mann_kendall,
prewhitening,confidence}.py`:

1. **Desestacionalización.** El NDVI de un ecosistema de montaña mediterráneo
   tiene un ciclo estacional muy marcado (pico en mayo, mínimo en
   enero–febrero). El test corre sobre la serie **desestacionalizada**
   (descomposición armónica de 2 componentes con ajuste simultáneo de
   tendencia, Julien & Sobrino 2009), no sobre la serie cruda — la fenología
   ya no contamina el supuesto de monotonía.
2. **Corrección de empates.** La varianza del estadístico S incorpora la
   corrección por empates de Hipel & McLeod (1994), en vez de la fórmula
   simplificada que usaba v1.1.0.
3. **Pendiente de Sen + intervalo de confianza.** La magnitud de la tendencia
   se reporta con su IC 95% no paramétrico exacto (Gilbert 1987), no como un
   único valor sin incertidumbre.
4. **Prueba de robustez frente a autocorrelación.** *Trend-Free Pre-Whitening*
   (Yue-Pilon 2002, flag `--prewhiten`): se estima la tendencia, se descuenta
   la persistencia de lag-1 de los residuos y se restituye la tendencia antes
   de repetir el test. Los **7 veredictos significativos del PNSG sobreviven
   sin excepción** (0 cambios de dirección), pese a que el pre-whitening se
   activa en 5 de los 21 activos (lag-1 significativo).

**Hallazgo adicional:** al reordenar correctamente la serie para desestacionalizar,
se detectó y corrigió un bug de v1.1.0 — `year`/`month` se ordenaban como texto
(`"10","11"` antes que `"2"`), corrompiendo la cronología. Corregido el orden y
aplicada la cadena completa, **6 activos muestran ahora un reverdecimiento
monótono significativo** (antes solo 1 lo mostraba, oculto por el bug), coherente
con la recuperación posterior a la sequía de 2022 que las medias anuales
confirman de forma independiente. Maliciosa-Porrones sigue siendo la única
alerta de degradación, con IC 95% de la pendiente de Sen enteramente por
debajo de cero (≈ [−0,00050, −0,00023] NDVI/mes).

Con esta cadena, el hallazgo sobre el PNSG es empírico, real, y tiene el mismo
rigor estadístico que antes solo demostraba el Pipeline B sobre datos
sintéticos (§4) — con la diferencia de que aquí los datos son observaciones
reales, no una serie de demostración.

---

## 4. Qué afirma el Pipeline B: Mann-Kendall como demostración arquitectónica

El Pipeline B aplica la misma cadena estadística (desestacionalización +
Mann-Kendall + pendiente de Sen) sobre series multi-anuales **calibradas**,
no observadas — construidas con anomalías climáticas documentadas
(AEMET/Copernicus) para demostrar la arquitectura del sistema con un
territorio de referencia.

Desde v1.1.1, el matiz de presentación cambia respecto a versiones anteriores
de esta nota: **el Pipeline B ya no es la única capa con rigor estadístico
completo** — el PNSG real lo tiene también (§3). El Pipeline B conserva su
valor como demostración reproducible del método sobre una serie con anomalías
conocidas de antemano (útil para validar que el pipeline detecta lo que se
sabe que debería detectar), pero la afirmación de tendencia sobre territorio
real ya no depende de él.

---

## 5. Frontera de afirmaciones (tabla de honestidad)

| Afirmación | Pipeline A — raster (real, 2 escenas) | Pipeline A — serie temporal (real, PNSG, v1.1.1) | Pipeline B (demo, Villuercas) |
|---|---|---|---|
| Estado de salud ambiental por activo (EHS) | ✅ Sí, con datos Sentinel-2 reales | — | ✅ Sí, con datos calibrados |
| Señal de alerta estacional (ΔEHS) | ✅ Sí — resultado real | — | ✅ Sí |
| Atribución causal espacial (SCM/SIG) | ✅ Sí, desde rásteres reales | — | 🟡 Simulada desde una observación |
| Tendencia inter-anual (Mann-Kendall/Sen) | ❌ No — profundidad insuficiente | ✅ **Sí, rigor completo** — real, desestacionalizada, corrección de empates, IC de Sen, robustez Yue-Pilon | ✅ Sí — rigor completo, sobre datos de demostración |
| Anomalías inter-anuales / sequía | ❌ No | 🟡 Señal cruzada observada (2022 peor año en la mayoría de activos), no test formal | ✅ Sí |

> Regla de lectura: el SNTO **nunca** presenta una inferencia con más confianza estadística de la que su método soporta. Desde v1.1.1, la serie real del PNSG y el Pipeline B comparten el mismo rigor estadístico en la detección de tendencia; la diferencia que queda es la naturaleza del dato (observación real vs. demostración calibrada), no el método.

---

## 6. Línea de trabajo abierta (declarada, no oculta)

**Hecho (v1.1.0):** integración de la serie multi-anual real 2021–2026 para 21 activos del PNSG vía **Google Earth Engine**, ingerida en `clean_assets/timeseries/`.

**Hecho (v1.1.1):** corrección estadística completa de esa serie —desestacionalización, corrección de empates, IC de Sen, verificación de robustez Yue-Pilon— para que la tendencia real del PNSG alcance el mismo rigor que el Pipeline B. De paso, corrección del bug de orden cronológico detectado durante este trabajo (§0, §3).

**Abierto (sin versión asignada):** el andamiaje declarativo `src/temporal/`
(spec + `trend_gate.py` + manifiesto de procedencia) sigue sin conectarse a
esta serie real — es una ruta de código independiente, diseñada antes de que
existiera la capa de v1.1.0/v1.1.1, y su integración es una tarea de
arquitectura, no de rigor estadístico. `src/time_series/confidence.py` incluye
además un bootstrap de bloques móviles (Künsch 1989) como primitiva genérica
reutilizable, probada con ejemplos sintéticos — pero **no está conectada al
EHS**: calcular el intervalo de confianza del EHS compuesto de los 218
senderos reales del PNSG es una iniciativa futura separada, no parte de este
alcance.

---

## 7. Kit de defensa — preguntas previsibles del tribunal

**P: «Aplicas Mann-Kendall con un año de datos. ¿No es eso estadísticamente nulo?»**
R: Correcto para el Pipeline A raster (2 escenas), que por eso no lo aplica — ahí el resultado temporal es el ΔEHS estacional. Pero existe una serie separada de 66 observaciones mensuales (21 activos del PNSG, 2021–2026 real vía GEE), con profundidad suficiente para que el test tenga potencia estadística — y desde v1.1.1 el cálculo también está correctamente especificado (siguiente pregunta).

**P: «Tu serie del PNSG tiene un ciclo estacional NDVI muy marcado. ¿Cómo sabes que tu p-valor no es solo estacionalidad disfrazada de tendencia?»**
R: Porque el test ya no corre sobre la serie cruda. Desde v1.1.1, `scripts/run_timeseries_analysis.py` desestacionaliza primero (descomposición armónica de 2 componentes, Julien & Sobrino 2009) y aplica Mann-Kendall sobre los residuos de esa descomposición, con corrección de empates en la varianza (Hipel & McLeod 1994). La fenología ya no puede inflar la significancia porque se resta antes del test.

**P: «Aun desestacionalizando, queda autocorrelación de corto plazo. ¿La controláis?»**
R: Sí, mediante *Trend-Free Pre-Whitening* (Yue-Pilon 2002): se estima la tendencia con la pendiente de Sen, se descuenta la persistencia de lag-1 de los residuos y se restituye la tendencia antes de repetir el test — el orden importa, porque un blanqueado ingenuo eliminaría parte de la propia tendencia (Yue & Wang, 2002). Es la prueba de robustez, no la transformación por defecto: se activa flag `--prewhiten` y solo se aplica cuando el lag-1 es significativo (5 de 21 activos). Los 7 veredictos significativos del PNSG la superan sin excepción, sin un solo cambio de dirección.

**P: «¿Por qué la pendiente de Sen y no una regresión lineal simple?»**
R: Porque es no paramétrica y robusta a valores atípicos (relevante ante picos de sequía) y admite un intervalo de confianza exacto (Gilbert 1987, §16.4.2) que reportamos junto al punto estimado, en vez de un único valor sin incertidumbre.

**P: «¿Por qué debería creer un delta calculado con solo dos imágenes?»**
R: Porque no afirma una tendencia, sino un cambio de estado entre dos puntos fenológicos del mismo ciclo, normalizado por percentiles de escena para eliminar el sesgo radiométrico, y atribuido espacialmente por el SCM. Su fiabilidad se reporta de forma explícita mediante el Decision Confidence Score, que degrada cualquier recomendación si la cobertura temporal es insuficiente (data quality gate).

**P: «Entonces, ¿el sistema realmente funciona en el PNSG o solo en la demo?»**
R: El diagnóstico de estado (EHS), la señal de alerta (ΔEHS), la atribución causal (SCM/SIG) y, desde v1.1.1, una tendencia interanual con rigor estadístico completo funcionan con datos reales en el PNSG. El Pipeline B conserva su valor como demostración arquitectónica sobre una serie con anomalías conocidas de antemano, pero ya no es la única capa con ese nivel de rigor.

**P: «Encontrasteis un bug de orden cronológico mientras hacíais el trabajo de rigor estadístico. ¿No es eso una señal de que el resultado de v1.1.0 no era fiable?»**
R: Es exactamente la señal contraria: el bug se descubrió y se corrigió *porque* se aplicó el escrutinio metodológico, no a pesar de él — el propio proceso de auditar el rigor estadístico expuso un defecto de implementación que un análisis menos riguroso habría dejado pasar. Se declara explícitamente aquí, en el JSON de salida (`clean_assets/README.md`) y en las notas de versión, en vez de silenciarlo. El resultado de v1.1.0 (1 activo en degradación significativa, sin más contexto) no era el hallazgo correcto — el de v1.1.1 (7 veredictos significativos, 6 de ellos reverdecimiento oculto por el bug) sí lo es, y está respaldado por la cadena estadística completa más la prueba de robustez.

**P: «¿No es esto una limitación grave del trabajo?»**
R: Ya no es una limitación de método — el Mann-Kendall real del PNSG tiene hoy el mismo rigor que el Pipeline B. Lo que queda declarado como trabajo futuro (intervalo de confianza del EHS compuesto sobre los 218 senderos reales, integración del andamiaje declarativo `src/temporal/`) se documenta explícitamente en §6, no se descubre en la defensa.

---

*Documento de apoyo al TFM sobre gobernanza inteligente y transición regenerativa en espacios naturales protegidos. Territorio principal: Parque Nacional Sierra de Guadarrama; piloto de calibración metodológica: Reserva de la Biosfera Sierra del Rincón · SNTO v1.1.1 · actualizado julio 2026.*
