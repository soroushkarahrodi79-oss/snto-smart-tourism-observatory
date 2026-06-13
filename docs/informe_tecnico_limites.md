# Informe técnico — supuestos, límites y trazabilidad

> **Propósito.** Registro consolidado y honesto de qué asume el SNTO, qué afirma
> y qué no, y cómo se puede auditar cada resultado. Es el documento que acompaña
> a la defensa: un sistema de decisión pública vale tanto por su trazabilidad
> como por su score. Territorio principal: **Parque Nacional Sierra de
> Guadarrama (PNSG)**.

---

## 1. Frontera de afirmaciones (qué se puede defender)

| Afirmación | ¿Defendible hoy? | Sobre qué dato |
|---|---|---|
| Estado de salud ambiental por sendero (EHS) | ✅ Sí | Sentinel-2 L2A real, PNSG (73 sendas OAPN) |
| Señal de alerta estacional (ΔEHS primavera→verano) | ✅ Sí | 2 escenas reales (2025-08-10 / 2026-04-10) |
| Atribución causal espacial (SCM/SIG core vs landscape) | ✅ Sí | Rásteres reales |
| Presupuesto de restauración por sendero | 🟡 Orden de magnitud | Tarifas TRAGSA 2023 (cita por partida pendiente) |
| Tendencia inter-anual (Mann-Kendall) sobre PNSG | ❌ No | Requiere serie 2021–2026 (no ingerida) |
| Correlación EHS satelital ↔ degradación de campo | ❌ No | Requiere campaña de campo (framework listo) |
| Tendencia como **capacidad del sistema** | ✅ Sí | Demostrada en Pipeline B (datos calibrados) |

Regla de lectura: el SNTO **nunca** atribuye al PNSG una conclusión que solo el
Pipeline B (demo) puede sostener. El `trend_gate` (F2) codifica esta frontera.

## 2. Supuestos y constantes expert-based

Constantes razonables pero no validadas con datos externos; su sensibilidad se
analiza en `src/analysis/sensitivity.py` (F4).

| Constante | Valor | Fuente / estado |
|---|---|---|
| Pesos EHS `W_NDVI` / `W_NDMI` | 0,5 / 0,5 | Expert; ranking robusto verificable con `ranking_stability` |
| Percentiles de baseline `P_BASE` / `P_FLOOR` | P90 / P10 de escena | Expert; mejora = baselines estratificados (F4) |
| Umbrales SCM `SIG` | 0,07 / 0,15 | Calibrados de literatura (Pickering, Marion); pendientes de calibración local (BACI) |
| Buffer de sendero | 50 m | Estándar; anchura real por sendero mejoraría precisión |
| Coste unitario restauración | 15,50 €/m | TRAGSA 2023; cita oficial por partida pendiente |
| Decaimiento espacial SCM `alpha_core` | 0,12 | Literatura de pisoteo (5–20 % reducción NDVI) |

## 3. Límites por tipo (datos vs método)

**Brechas de datos (no de método):**
- **Serie temporal real 2021–2026** — andamiaje montado (`src/temporal/`); falta ingesta GEE (credenciales + cómputo).
- **DEM** — necesario para estratificar baselines por altitud/orientación (F4). No presente.
- **Cartografía de hábitat rasterizada** — KML de vegetación PNSG disponible; falta rasterizar a la rejilla de escena.
- **Verdad-terreno** — esquema y métricas listas (`src/validation/`); falta campaña (penetrómetro, parcelas, control).
- **Déficits NDVI/NDMI por sendero** — no se persisten en la salida del Pipeline A; bloquea correr `ranking_stability` sobre cada sendero real.

**Límites de método (declarados):**
- Confusión espectral sequía↔pisoteo (el SCM mitiga, no elimina).
- ΔEHS con 2 escenas es contraste pareado, no tendencia.
- Pipeline B opera sobre datos sintéticos calibrados, no observación real.

## 4. Trazabilidad (cómo auditar un resultado)

| Nivel | Mecanismo | Artefacto |
|---|---|---|
| Procedencia del dato | `src/platform/provenance.py` + `DataStatus` | Badge real/calibrado/sintético en dashboard |
| Cobertura temporal y huecos | `src/temporal/manifest.py` | `pipeline_a_ts_manifest.json` |
| Validez de inferencia | `src/temporal/trend_gate.py` | Tier SEASONAL_ONLY / TREND_* |
| Reproducibilidad de ejecución | `src/config/run_context.py` | `run_context.json` (git sha, timestamp, params) |
| Confianza de decisión | DCS de 5 dimensiones + data quality gate | `can_act` |
| Semántica de score | `src/metrics/semantics.py` | health = 100 − stress (única conversión) |

## 5. Convenio semántico (anti-confusión)

Dos direcciones 0–100 que **no** deben mezclarse, con conversión canónica única
en `src/metrics/semantics.py`:

- **Health Score** — 0 crítico, 100 sano (dashboard, TPI, tiers, comunicación).
- **Stress / Degradation Score** — 0 sin estrés, 100 degradado (columnas legacy
  `ehs_*` del Pipeline A, índice de degradación de campo).
- **ΔStress > 0 ⇒ empeora**; equivalentemente **ΔHealth < 0 ⇒ empeora**.

## 6. Niveles de confianza para uso

| Uso | Requisito mínimo |
|---|---|
| Exploración / priorización (dónde mirar) | EHS + SCM reales (disponible) |
| Alerta temprana estacional | ΔEHS + DCS `can_act=True` (disponible) |
| Decisión de inversión formal | + validación de campo y/o serie multi-anual (pendiente) |
| Afirmación de tendencia | Serie 2021–2026 con `trend_gate` ≥ TREND_ROBUST (pendiente) |

---

*Informe técnico de apoyo · SNTO · territorio principal PNSG · junio 2026. Ver
también `docs/temporal_series_design.md`, `docs/baselines_uncertainty_design.md`
y `docs/field_validation_protocol.md`.*
