# Nota metodológica — Rigor estadístico de la detección de tendencia y cuantificación de la incertidumbre

> **Propósito.** Texto de referencia para el capítulo de Metodología del TFM y para la interlocución técnica con OAPN. Documenta, componente a componente y con su cita, la cadena estadística que convierte la serie Sentinel-2 mensual del PNSG en afirmaciones de tendencia y en indicadores (EHS) acompañados de su intervalo de confianza. Es la contrapartida cuantitativa de la [nota de alcance temporal](nota_metodologica_temporalidad.md), que delimita *qué* territorio sostiene *qué* afirmación; esta nota detalla *cómo* se calcula cada afirmación de forma defendible frente a la crítica estadística estándar.

---

## 1. Principio rector

Cada número que el SNTO reporta a un gestor público debe (a) derivarse de un método cuyo supuesto no esté violado por los datos, y (b) llevar asociada una medida explícita de su incertidumbre. Un τ de Mann-Kendall calculado sobre una serie estacional, o un Environmental Health Score (EHS) sin banda de error, no son defendibles para decisión pública aunque el número sea correcto en apariencia. Esta nota describe las tres correcciones que materializan ese principio sobre datos reales del Parque Nacional Sierra de Guadarrama (PNSG).

---

## 2. Cadena de procesamiento (pipeline de tendencia)

```
serie NDVI mensual real (Sentinel-2, 2021–2026)
        │
        ▼  [2.1] descomposición armónica (2 componentes) → serie desestacionalizada
        │
        ▼  [2.2] (opcional) pre-whitening libre de tendencia (Yue-Pilon)
        │
        ▼  [2.3] Mann-Kendall con corrección de empates  →  τ, p, dirección
        │
        ▼  [2.4] pendiente de Sen + intervalo de confianza no paramétrico (Gilbert)
        │
        ▼  [2.5] Environmental Health Score + IC 95 % por bootstrap de bloques (Künsch)
```

Implementación: `src/time_series/{decomposition,mann_kendall,prewhitening,confidence}.py`, orquestada offline por `scripts/run_timeseries_analysis.py` (tendencia sobre serie real) y por `run_pipeline_a_timeseries.py` (EHS + IC).

---

## 3. Justificación de cada componente

### 3.1 Desestacionalización previa al test de tendencia

El test de Mann-Kendall asume observaciones intercambiables bajo la hipótesis nula. En una serie NDVI **mensual**, la fenología mediterránea (pico primaveral, valle estival) es una señal periódica dominante que viola ese supuesto: la autocorrelación estacional infla la varianza aparente del estadístico y, con ella, la tasa de falsos positivos. Por ello el test **no se aplica sobre la serie cruda**, sino sobre la serie desestacionalizada (observación menos componente estacional), obtenida por una descomposición armónica de dos componentes (armónico anual y semianual) con ajuste simultáneo de tendencia lineal. El ajuste simultáneo evita que el término de tendencia absorba fuga estacional. Dos armónicos explican ≥ 95 % de la varianza estacional en vegetación mediterránea (Julien & Sobrino, 2009); la fuerza estacional se cuantifica con el índice de Wang et al. (2006).

### 3.2 Mann-Kendall con corrección de empates

Se emplea el test de Mann-Kendall (Mann, 1945; Kendall, 1975), no paramétrico, resistente a valores atípicos y sensible a cualquier tendencia monótona (no solo lineal). La varianza del estadístico S incorpora la **corrección por empates** de Hipel & McLeod (1994) y el estadístico Z lleva corrección de continuidad. Una única implementación validada (`src/time_series/mann_kendall.py`) alimenta tanto el análisis como los tests, eliminando la duplicación previa que ponía en riesgo la reproducibilidad.

### 3.3 Pre-whitening libre de tendencia (Yue-Pilon)

Aun tras desestacionalizar, los residuos mensuales conservan persistencia de corto plazo (autocorrelación de lag-1) que sigue inflando la tasa de falsos positivos. Se aplica **Trend-Free Pre-Whitening** (Yue, Pilon, Phinney & Cavadias, 2002): se estima la tendencia con la pendiente de Sen, se elimina, se descuenta el componente AR(1) de los residuos y se restituye la tendencia antes del test. El orden «quitar tendencia → blanquear → restituir» es esencial: el blanqueado ingenuo eliminaría parte de la propia tendencia que se busca detectar (Yue & Wang, 2002). El pre-whitening se ofrece como paso opcional (`--prewhiten`) y solo se activa cuando el lag-1 supera el umbral de ruido blanco; se usa como **prueba de robustez**, no como transformación por defecto.

### 3.4 Intervalo de confianza de la pendiente de Sen

La magnitud de la tendencia se estima con la pendiente de Sen (Sen, 1968) —mediana de las pendientes por pares, robusta a atípicos— y se acompaña de su **intervalo de confianza no paramétrico exacto** (Gilbert, 1987, §16.4.2), estándar en análisis de tendencias ambientales (USGS, US-EPA). El intervalo es determinista y consciente de empates: dados N′ pares y la varianza corregida Var(S), los límites son los estadísticos de orden de las pendientes en los rangos M₁ = (N′−C)/2 y M₂+1 = (N′+C)/2, con C = z₁₋α/₂·√Var(S).

### 3.5 Intervalo de confianza del EHS por bootstrap de bloques

El EHS es un indicador compuesto (nivel base, tendencia, anomalía, recuperación, estabilidad) sin forma cerrada para su varianza. Su incertidumbre se estima por **bootstrap de bloques móviles** (Künsch, 1989): se remuestrean bloques contiguos de observaciones —preservando la dependencia serial de corto plazo que un bootstrap i.i.d. destruiría— y se recalcula el EHS en cada réplica. Dos decisiones de diseño garantizan la validez:

1. **Se remuestrean observaciones completas, no valores NDVI sueltos**, de modo que los canales correlacionados NDVI/NDMI/EVI de cada mes permanecen alineados en cada réplica. Esto es imprescindible en el modo *dense-canopy*, donde el nivel base se calcula con EVI en lugar de NDVI saturado.
2. **El cálculo del EHS es una única función** (`_ehs_from_observations`) compartida por la estimación puntual y el bootstrap, de forma que el intervalo queda centrado exactamente en la computación que cuantifica.

El generador aleatorio se siembra de forma determinista a partir del identificador del activo (`crc32`), de modo que el intervalo es **reproducible** entre ejecuciones —requisito para un dato que alimenta informes institucionales.

---

## 4. Resultado sobre datos reales del PNSG

Aplicada la cadena a la serie Sentinel-2 real 2021–2026 de los 21 activos del PNSG, y corregido de paso un error de ordenación cronológica que barajaba los meses (`"10","11"` antes que `"2"`) y corrompía toda serie:

- **6 activos** presentan reverdecimiento monótono significativo (p < 0,05), coherente con la recuperación posterior a la sequía de 2022 que las medias anuales confirman de forma independiente. Esta señal estaba **oculta** por el error de ordenación previo.
- **1 activo** (Maliciosa-Porrones) mantiene una degradación significativa, con IC 95 % de la pendiente de Sen enteramente por debajo de cero (≈ [−0,00053, −0,00026] NDVI/mes): es la única alerta de degradación del portafolio, en continuidad con el diagnóstico de la v1.1.0.
- **Prueba de robustez:** los **7 veredictos significativos sobreviven al pre-whitening de Yue-Pilon sin excepción** (0 cambios de dirección), pese a que la corrección de autocorrelación se activa en 5 de los 21 activos. Las tendencias no son, por tanto, artefactos de persistencia serial.

> Alcance honesto (coherente con la [nota de temporalidad](nota_metodologica_temporalidad.md)): la **tendencia y su IC de Sen** se computan sobre datos reales del PNSG. El **IC del EHS** está implementado y verificado end-to-end sobre datos sintéticos (218 senderos, anchura media de IC ≈ 10 puntos); su ejecución sobre los activos reales del PNSG requiere una corrida completa vía Google Earth Engine (credenciales de cuenta de servicio), y se declara como paso de ejecución pendiente, no como carencia de método.

---

## 5. Trazabilidad y reproducibilidad

- **Esquema aditivo.** El JSON de tendencia (`mk_trends_pnsg.json`) es un superconjunto del esquema histórico: conserva las claves que consume el dashboard y añade `sens_slope`, `sens_slope_ci`, `deseasonalised`, `prewhitened`, `lag1_autocorr` y `method` como procedencia. Ningún consumidor previo se rompe.
- **Determinismo.** Tanto el IC de Sen (analítico) como el IC del EHS (bootstrap con semilla derivada del activo) son reproducibles bit a bit.
- **Cobertura de test.** La cadena está cubierta por pruebas unitarias (`tests/unit/test_{mann_kendall,decomposition,prewhitening,confidence}.py`), incluida la preservación del emparejamiento de canales en el bootstrap.
- **Reejecución.** `python scripts/run_timeseries_analysis.py [--prewhiten]` regenera la tendencia; `python run_pipeline_a_timeseries.py --ehs-bootstrap N` produce el EHS con su IC.

---

## 6. Kit de defensa — preguntas previsibles

**P: «Mann-Kendall sobre NDVI mensual: ¿no viola el supuesto de independencia por la estacionalidad?»**
R: Sí, y por eso no se aplica sobre la serie cruda. El test corre sobre la serie desestacionalizada (descomposición armónica de dos componentes), de modo que la fenología no contamina el estadístico. La regla está documentada y codificada.

**P: «Aun desestacionalizando, queda autocorrelación. ¿La controláis?»**
R: Sí, mediante pre-whitening libre de tendencia (Yue-Pilon, 2002), que descuenta la persistencia de lag-1 sin eliminar la tendencia. Se usa como prueba de robustez: los siete veredictos significativos del PNSG la superan sin cambiar.

**P: «¿Por qué la pendiente de Sen y no una regresión OLS?»**
R: Porque es no paramétrica y robusta a atípicos (relevante ante picos de sequía), y admite un intervalo de confianza exacto (Gilbert, 1987) que reportamos, en lugar de un único valor.

**P: «Un EHS es un número compuesto. ¿Cómo sé si es fiable?»**
R: Cada EHS se acompaña de un IC 95 % por bootstrap de bloques que preserva la dependencia temporal y el emparejamiento espectral. La anchura del intervalo es, en sí misma, una medida de fiabilidad accionable para el gestor.

**P: «¿Es reproducible lo que entregáis a la Administración?»**
R: Sí. Los intervalos son deterministas (semilla derivada del activo), el esquema de salida es aditivo y la cadena está cubierta por tests. Otra persona con el mismo CSV obtiene el mismo resultado.

---

## 7. Referencias

- Gilbert, R.O. (1987). *Statistical Methods for Environmental Pollution Monitoring*, §16.4.2. Van Nostrand Reinhold.
- Hipel, K.W. & McLeod, A.I. (1994). *Time Series Modelling of Water Resources and Environmental Systems*. Elsevier.
- Julien, Y. & Sobrino, J.A. (2009). The Yearly Land Cover Dynamics (YLCD) method. *Remote Sensing of Environment*, 113, 329–334.
- Kendall, M.G. (1975). *Rank Correlation Methods*, 4.ª ed. Griffin, Londres.
- Künsch, H.R. (1989). The jackknife and the bootstrap for general stationary observations. *Annals of Statistics*, 17(3), 1217–1241.
- Mann, H.B. (1945). Nonparametric tests against trend. *Econometrica*, 13(3), 245–259.
- Sen, P.K. (1968). Estimates of the regression coefficient based on Kendall's tau. *Journal of the American Statistical Association*, 63, 1379–1389.
- Wang, X., Smith, K. & Hyndman, R. (2006). Characteristic-based clustering for time series data. *Data Mining and Knowledge Discovery*, 13, 335–364.
- Yue, S., Pilon, P., Phinney, B. & Cavadias, G. (2002). The influence of autocorrelation on the ability to detect trend in hydrological series. *Hydrological Processes*, 16, 1807–1829.
- Yue, S. & Wang, C.Y. (2002). Applicability of prewhitening to eliminate the influence of serial correlation on the Mann-Kendall test. *Water Resources Research*, 38(6).

---

*Documento de apoyo al TFM sobre gobernanza inteligente y transición regenerativa en espacios naturales protegidos. Territorio principal: Parque Nacional Sierra de Guadarrama. Complementa a `nota_metodologica_temporalidad.md` (alcance) con el detalle cuantitativo (rigor). Rama de I+D `research/statistical-rigor`.*
