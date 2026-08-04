# Visitor Pressure Forecasting Lab: preparación científica del dato

## Pregunta y decisión

La pregunta original es si SNTO puede anticipar presión de visitantes en un lugar y
horizonte definidos con datos trazables y evaluación temporal reproducible. La
auditoría del repositorio respondió **Decisión C**: no existe todavía una serie
temporal real y científicamente defendible de presión de visitantes.

Los CSV de Sentinel-2 son observaciones ambientales; `annual_visitors` contiene
valores aleatorios sintéticos; `visitor_capacity_annual` es estático; el snapshot
MITMA no está incluido; los conteos de campo están vacíos; y las proyecciones
existentes están correctamente etiquetadas como `SIMULATED`. Por tanto, el estado
actual esperado es `INSUFFICIENT_EVIDENCE`. Esto es una salvaguarda, no un fallo.

> Visitor-pressure forecasting does not by itself establish ecological causality,
> carrying capacity or a Limits of Acceptable Change threshold.

> Environmental observations such as NDVI, NDMI, EVI and EHS are not observations
> of visitors and cannot substitute for visitor-pressure targets.

## Contrato y taxonomía

Cada registro conserva por separado el periodo medido (`timestamp`), cuándo se
produjo la observación (`observed_at`), cuándo estuvo disponible para análisis
(`available_at`) y el corte de información de una predicción futura (`data_cutoff`).
También exige ubicación, objetivo, valor, unidad, fuente, método de fuente, clase de
evidencia, indicador de calidad y, opcionalmente, intervalo de medida y metadatos.
Todas las fechas son conscientes de zona horaria.

Los objetivos no son intercambiables:

| Objetivo | Unidades permitidas |
|---|---|
| `visitor_count` | `persons` |
| `vehicle_count` | `vehicles` |
| `parking_occupancy` | `occupied_spaces`, `percentage` |
| `reservation_count` | `reservations` |
| `inbound_trips` | `trips` |
| `pedestrian_count` | `pedestrians` |

Los estados `OBSERVED`, `CALCULATED`, `ESTIMATED`, `SIMULATED` y `MISSING` se
mapean explícitamente a los ejes nativos `DataType` y `EvidenceClass`. Una
estimación no es un conteo directo; una fixture sintética conserva `SIMULATED`; un
valor ausente conserva `null`; y no se permite promocionar evidencia simulada,
estimada, calculada o ausente a `OBSERVED`.

## Validación, frecuencia y fuga temporal

La validación no corrige datos. Informa errores, advertencias e información con
códigos estables. Comprueba columnas, parsing, zonas horarias, procedencia,
objetivo–unidad, valores nulos/no numéricos/negativos, porcentajes, orden,
duplicados, unidades y evidencias mezcladas, frecuencia irregular, huecos,
constancia, valores anuales o únicos, profundidad, ciclos estacionales y número de
orígenes de backtesting. Los conteos exigen valores enteros; los porcentajes pueden
ser fraccionarios. Las series se evalúan por ubicación, objetivo y unidad antes de
producir la decisión agregada.

La frecuencia se infiere conservadoramente como horaria, diaria, semanal, mensual,
anual, irregular o desconocida, exponiendo intervalo mediano/mínimo/máximo y
periodos esperados ausentes. Un valor anual aislado y una secuencia estática repetida
no constituyen evidencia longitudinal.

Existe fuga temporal si el dato o su disponibilidad son posteriores a
`data_cutoff`. Tal caso es un error `TEMPORAL_LEAKAGE` y bloquea el backtesting. El
informe incluye cobertura, recuentos por ubicación/objetivo, resumen de evidencia y
la lista de incidentes de fuga. La igualdad con el cutoff es válida. Una revisión
histórica debe sustituir explícitamente su versión anterior y conservar trazabilidad
en el sistema fuente; dos versiones con la misma clave temporal se rechazan como
duplicadas.

## Decisión de readiness y salida

`audit_records`, `audit_rows` y `audit_csv` producen un `AuditResult` tipado y JSON
estable con esquema `1.0`. `generated_at` es el único metadato de ejecución y puede
inyectarse para obtener serialización determinista:

- `INVALID_DATASET`: errores críticos, incluida fuga;
- `INSUFFICIENT_EVIDENCE`: ausencia de datos reales, simulación, profundidad,
  ciclos u orígenes insuficientes, o valores únicos/estáticos;
- `PARTIALLY_READY`: evidencia real válida pero con advertencias de regularidad,
  huecos o mezcla declarada;
- `READY_FOR_BACKTESTING`: satisface la política explícita sin esos bloqueos.

Los defaults (30 observaciones, dos ciclos y cinco orígenes) son una política
provisional del experimento, no una verdad científica universal. Se configuran por
caso junto con el periodo estacional requerido.

## Fixture y reproducción

`tests/fixtures/visitor_pressure_synthetic.csv` tiene 21 observaciones diarias y un
patrón semanal determinista. Solo prueba el framework: vive fuera de los datos de
producción, nunca debe mostrarse en producto ni convertirse a `OBSERVED`, y su
auditoría debe devolver `INSUFFICIENT_EVIDENCE`. No puede sustentar afirmaciones de
producto ni demostraciones de una predicción real.

Desde la raíz y con el entorno del proyecto:

```powershell
.venv\Scripts\python.exe -m pytest tests/visitor_pressure -v
.venv\Scripts\python.exe -m pytest tests/visitor_pressure tests/unit/test_forecasting_projection.py tests/unit/test_forecasting_seasonal.py tests/unit/test_forecast_chart.py -v
.venv\Scripts\python.exe -m ruff check src/visitor_pressure tests/visitor_pressure
.venv\Scripts\python.exe -m mypy --follow-imports=skip src/visitor_pressure
.venv\Scripts\python.exe -m pre_commit run --all-files
```

## Especificación mínima para adquisición

Una futura serie debe identificar ubicación o acceso, objetivo y unidad estables,
intervalo consistente, timestamps, duración, autoridad de fuente, instrumento o
método, estado de evidencia, codificación de ausentes, cambios de instrumento,
historial de revisiones, `observed_at`, `available_at`, licencia/procedencia y
profundidad suficiente para el ciclo y horizonte pretendidos.

No se impone universalmente una duración de 18–24 meses. La estacionalidad semanal
requiere ciclos semanales repetidos; la anual requiere más de un ciclo anual y las
comparaciones robustas suelen beneficiarse de varios años. La frecuencia, la
estabilidad y el horizonte determinan la profundidad útil.

MITMA `inbound_trips`, si se ingiere en el futuro, representa movilidad municipal y
requiere calibración antes de interpretarse como presión turística. Se recomiendan
contadores de acceso, censos de campo protocolizados, sensores de aparcamiento y
reservas con trazabilidad, acuerdos de licencia y registro de calibraciones.

## Condiciones para modelar y limitaciones

SARIMAX o SVR solo podrán evaluarse después de aportar una serie real conforme al
contrato, resolver errores, superar una política contextual de profundidad/ciclos,
definir horizonte y particiones temporales con varios orígenes y acordar métricas y
baseline. La selección de algoritmo dependerá entonces del tamaño y estructura de
esa evidencia; este laboratorio no implementa ningún modelo.

La readiness solo habilita una evaluación retrospectiva. No demuestra calidad
predictiva ni causalidad, representatividad turística, capacidad de carga, umbrales
LAC o validez para decisiones operativas o comunicación pública.
