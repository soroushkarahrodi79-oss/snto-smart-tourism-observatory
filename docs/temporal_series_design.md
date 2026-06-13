# Diseño de la serie temporal multi-anual (2021–2026) — PNSG

> **Propósito.** Estructurar, científica y técnicamente, el salto del SNTO desde
> una instantánea estacional (dos escenas) a una **serie temporal real de cinco
> años** sobre el Parque Nacional Sierra de Guadarrama. Este documento define el
> *contrato* (qué serie, con qué cadencia y calidad), la *regla de inferencia*
> (qué afirmación sostiene cada profundidad temporal) y la *trazabilidad*
> (manifiesto de procedencia). **No describe una ingesta ya realizada:** la serie
> aún no se ha descargado; aquí se fija el andamiaje (F2 del roadmap) que la hará
> reproducible y defendible cuando se ejecute vía Google Earth Engine.

---

## 1. Estado de partida y objetivo

| | Hoy (real) | Objetivo F2 → ingesta |
|---|---|---|
| Profundidad | 2 escenas (primavera 2026 + verano 2025) | 72 composiciones mensuales 2021–2026 |
| Inferencia válida | ΔEHS estacional (contraste pareado) | Tendencia inter-anual (Mann-Kendall + Sen) |
| Territorio | PNSG (73 sendas OAPN) | PNSG (ampliable a OAPN) |
| Tile Sentinel-2 | T30TVL | T30TVL |

El objetivo **no** es más complejidad, sino convertir una *capacidad demostrada*
(Mann-Kendall sobre datos de calibración del Pipeline B) en un *hallazgo real*
sobre territorio (PNSG), cerrando la brecha temporal #2 del audit.

---

## 2. El contrato: `SeriesSpec`

La serie se declara de forma única en `src/temporal/series_spec.py`. La
especificación de referencia es:

```python
PNSG_5Y = SeriesSpec(
    territory_key="pnsg",
    start_year=2021, end_year=2026,   # 6 años naturales → 72 meses
    cadence=Cadence.MONTHLY,
    s2_tile="T30TVL",
    indices=("NDVI", "NDMI", "EVI"),
    min_valid_pixel_pct=0.30,
    collection="COPERNICUS/S2_SR_HARMONIZED",
)
```

Decisiones de diseño:

- **Cadencia mensual.** El revisit de Sentinel-2 A+B (~5 días) permite una
  composición *mediana mensual* robusta a nubes residuales. La cadencia mensual
  preserva la señal fenológica (verde-primavera / sequía-verano) que el módulo
  de descomposición armónica necesita para desestacionalizar antes de estimar
  tendencia. La cadencia estacional (`Cadence.SEASONAL`, 4 periodos/año) se
  ofrece como alternativa agregada para territorios con alta nubosidad.
- **Ventana 2021–2026.** Seis ciclos anuales completos garantizan, tras
  desestacionalización, profundidad suficiente para una tendencia robusta
  (ver §3). 2021 es el primer año con la colección armonizada estable.
- **Colección armonizada.** `S2_SR_HARMONIZED` normaliza los cambios de baseline
  de procesado (PB < 4.00 vs ≥ 4.00), evitando un salto radiométrico artificial
  a mitad de serie que Mann-Kendall interpretaría como tendencia falsa.
- **Suelo de calidad (`min_valid_pixel_pct = 0.30`).** Una composición mensual
  con < 30 % de píxeles libres de nube se trata como **hueco**, no como
  observación. Coherente con `_MIN_VALID_PIX_PCT` del `GEEAdapter`.

`SeriesSpec.periods()` enumera los 72 periodos esperados; es la base contra la
que se mide la cobertura real (§4).

---

## 3. La regla de inferencia: `trend_gate`

`src/temporal/trend_gate.py` codifica como componente reutilizable la regla ya
argumentada en `nota_metodologica_temporalidad.md`: **cada análisis emite solo la
inferencia que su profundidad temporal sostiene.** El gate mapea la longitud
*efectiva* de la serie (observaciones válidas, no periodos esperados) a un nivel:

| Nivel | n efectivo | ΔEHS pareado | Mann-Kendall | Lectura |
|---|---|---|---|---|
| `INSUFFICIENT` | n < 2 | ❌ | ❌ | Sin inferencia temporal |
| `SEASONAL_ONLY` | 2 ≤ n < 4 | ✅ | ❌ | **Estado real actual de PNSG** |
| `TREND_EMERGING` | 4 ≤ n < 10 | ✅ | ⚠️ computable, infra-potenciado | Tendencia con cautela explícita |
| `TREND_ROBUST` | n ≥ 10 | ✅ | ✅ | Tendencia defendible como hallazgo |

Umbrales (no son números mágicos):

- **`MK_MIN_N = 4`.** Por debajo, el estadístico S de Mann-Kendall y su varianza
  no están bien definidos; `mann_kendall_test` ya devuelve `no_trend` para n < 4.
- **`MK_ROBUST_N = 10`.** La aproximación normal de S se considera adecuada a
  partir de ~10 observaciones (Hipel & McLeod 1994). Entre 4 y 10 el test es
  computable pero infra-potenciado → se reporta con cautela.
- **`SEASONAL_CYCLES_MIN = 3`.** Para datos mensuales con fuerte estacionalidad,
  la tendencia debe estimarse sobre la **serie de residuos desestacionalizada**
  (descomposición armónica) abarcando ≥ 3 ciclos anuales antes de tratarse como
  hallazgo empírico firme. El gate recomienda esto explícitamente; no lo
  sobrescribe en silencio.

Así, el dashboard y los informes consultan una única fuente de verdad antes de
etiquetar un resultado como "tendencia" frente a "señal estacional".

---

## 4. La trazabilidad: `SeriesManifest`

`src/temporal/manifest.py` produce un registro auditable de *qué* periodos
pueblan la serie y *cuán fiable* es cada uno — exactamente la metadata que el
audit exige por resultado: píxeles válidos, nubosidad, fecha, método de
composición, fuente y bandera real/calibrado/sintético.

- Se construye con `build_manifest_from_observations(spec, observations)`: cada
  `AssetObservation` se mapea a un `PeriodRecord`; los periodos esperados por la
  spec pero ausentes se marcan `present=False` → **la cobertura nunca se
  sobreestima**.
- `DataStatus` (`real` / `calibrated` / `synthetic` / `missing`) se infiere del
  `data_source` y se mostrará literalmente en el dashboard (F3).
- Métricas agregadas: `coverage()` (presentes / esperados), `gaps()`,
  `dominant_status()`. Serializa a JSON reproducible por ejecución.

Este manifiesto es el puente natural hacia **F3 (capa de calidad de dato
visible)**: el dashboard leerá `pipeline_a_ts_manifest.json` para etiquetar
cobertura y confianza sin afirmaciones infundadas.

---

## 5. Integración y siguiente paso

`run_pipeline_a_timeseries.py` queda parametrizado por territorio (por defecto
PNSG) y consume `PNSG_5Y` para el rango de años; tras la ingesta emite el
manifiesto y aplica el gate por sendero. En modo `--dry-run` (datos sintéticos)
todo el andamiaje es verificable sin conexión a GEE.

**Lo único que falta para tendencia real en PNSG es la ejecución con
credenciales GEE** — el andamiaje (contrato, gate, manifiesto) ya está montado y
probado. La ingesta efectiva es trabajo posterior, no parte de F2.

---

*Documento de diseño · SNTO · andamiaje temporal F2 · territorio principal PNSG.*
