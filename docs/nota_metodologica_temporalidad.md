# Nota metodológica — Alcance temporal de los indicadores y validez del análisis de tendencia

> **Propósito.** Texto de referencia para el capítulo de Metodología del TFM. Delimita con precisión qué afirma cada pipeline en función de su profundidad temporal, blinda la decisión de diseño frente a la crítica estadística más previsible (aplicación de Mann-Kendall sobre series cortas) y declara explícitamente las líneas de trabajo abiertas. La transparencia sobre el alcance es parte del valor metodológico del trabajo, no una concesión.

---

## 1. El problema y la decisión de diseño

El SNTO integra dos análisis temporales de naturaleza distinta que **no deben confundirse**:

- **Contraste estacional intra-anual (ΔEHS)** — opera sobre el Pipeline A con datos Sentinel-2 reales del **Parque Nacional Sierra de Guadarrama (PNSG)**, territorio principal del observatorio (dos escenas: primavera y verano de un mismo ciclo). El método se validó previamente sobre la **Reserva de la Biosfera Sierra del Rincón**, que se conserva como piloto de calibración con datos reales propios.
- **Detección de tendencia inter-anual (Mann-Kendall + pendiente de Sen)** — opera sobre el Pipeline B, sobre series multi-anuales calibradas de demostración.

El test de Mann-Kendall es un contraste no paramétrico de tendencia monótona que **requiere una serie temporal de profundidad suficiente** para que el estadístico S y su varianza tengan potencia estadística; aplicado sobre dos observaciones carecería por completo de significado. Por ello, **el Pipeline A no aplica Mann-Kendall**: con dos escenas de un único año, hacerlo sería estadísticamente injustificable. La decisión de diseño es deliberada: cada pipeline emite únicamente el tipo de inferencia que su profundidad temporal sostiene.

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

## 3. Qué afirma el Pipeline B: Mann-Kendall como capacidad demostrada

La capacidad de detección de tendencia inter-anual del sistema **se demuestra sobre el Pipeline B**, donde la profundidad temporal (series multi-anuales) sí lo justifica. En este pipeline, el análisis se aplica sobre la serie desestacionalizada (residuos de la descomposición armónica de dos armónicas), con umbral de significación p < 0,05 y la pendiente de Sen como estimador robusto.

Es crucial el matiz de presentación: **Mann-Kendall es una capacidad arquitectónica del SNTO demostrada en datos de calibración, no un hallazgo empírico sobre el PNSG.** Afirmar lo contrario sería atribuir a un territorio real una conclusión derivada de datos sintéticos. La separación arquitectónica de los dos pipelines (datos reales vs. demostración) materializa esta honestidad en el propio código.

---

## 4. Frontera de afirmaciones (tabla de honestidad)

| Afirmación | Pipeline A (real, PNSG · calibración Rincón) | Pipeline B (demo, Villuercas) |
|---|---|---|
| Estado de salud ambiental por activo (EHS) | ✅ Sí, con datos Sentinel-2 reales | ✅ Sí, con datos calibrados |
| Señal de alerta estacional (ΔEHS) | ✅ Sí — resultado real | ✅ Sí |
| Atribución causal espacial (SCM/SIG) | ✅ Sí, desde rásteres reales | 🟡 Simulada desde una observación |
| Tendencia inter-anual (Mann-Kendall/Sen) | ❌ No — profundidad insuficiente | ✅ Sí — capacidad demostrada |
| Anomalías inter-anuales / sequía | ❌ No | ✅ Sí |

> Regla de lectura: el SNTO **nunca** atribuye al PNSG una conclusión que solo el Pipeline B puede sostener. La columna izquierda es lo defendible como hallazgo; la derecha, lo defendible como capacidad del sistema.

---

## 5. Línea de trabajo abierta (declarada, no oculta)

La integración de la serie multi-anual real 2021–2026 para el PNSG vía **Google Earth Engine** (`src/ingestion/gee_adapter.py`, ya implementado) es la vía para elevar el Pipeline A a detección de tendencia con datos reales. Está pendiente de credenciales de cuenta de servicio y tiempo de cómputo. Su integración **convertiría el ΔEHS estacional en una serie sobre la que Mann-Kendall sería estadísticamente robusto**, cerrando la única brecha temporal del sistema sobre territorio real. Se declara como trabajo en curso, no como carencia: la arquitectura ya está preparada para recibir esa serie sin refactorización.

---

## 6. Kit de defensa — preguntas previsibles del tribunal

**P: «Aplicas Mann-Kendall con un año de datos. ¿No es eso estadísticamente nulo?»**
R: Correcto, y por eso el Pipeline A no lo aplica. Sobre el PNSG el resultado temporal es el ΔEHS estacional, un contraste pareado válido con dos escenas. Mann-Kendall se demuestra como capacidad del sistema sobre el Pipeline B, donde la profundidad temporal lo justifica. La separación es una decisión de diseño explícita en el código.

**P: «¿Por qué debería creer un delta calculado con solo dos imágenes?»**
R: Porque no afirma una tendencia, sino un cambio de estado entre dos puntos fenológicos del mismo ciclo, normalizado por percentiles de escena para eliminar el sesgo radiométrico, y atribuido espacialmente por el SCM. Su fiabilidad se reporta de forma explícita mediante el Decision Confidence Score, que degrada cualquier recomendación si la cobertura temporal es insuficiente (data quality gate).

**P: «Entonces, ¿el sistema realmente funciona en el PNSG o solo en la demo?»**
R: El diagnóstico de estado (EHS), la señal de alerta (ΔEHS) y la atribución causal (SCM/SIG) funcionan con datos reales en el PNSG. La reconstrucción histórica multi-anual y la detección de tendencia se demuestran en el Pipeline B. La frontera está documentada y es deliberada.

**P: «¿Qué falta para tener tendencia real en el PNSG?»**
R: Únicamente la serie GEE 2021–2025. El adaptador está implementado; falta credencial y ejecución. No requiere rediseño, solo datos.

**P: «¿No es esto una limitación grave del trabajo?»**
R: Es una limitación de alcance temporal de los datos de entrada, no del método. El método de detección de tendencia está implementado y validado; lo que se acota es sobre qué territorio se afirma un hallazgo frente a una capacidad. Esa distinción es precisamente lo que da rigor al trabajo.

---

*Documento de apoyo al TFM sobre gobernanza inteligente y transición regenerativa en espacios naturales protegidos. Territorio principal: Parque Nacional Sierra de Guadarrama; piloto de calibración metodológica: Reserva de la Biosfera Sierra del Rincón · SNTO v0.1.0 · junio 2026.*
