# Baselines estratificados e incertidumbre — diseño (F4)

> **Propósito.** Elevar el rigor científico del EHS en dos frentes que el audit
> señaló: (1) comparar cada sendero contra lo que es *sano para su estrato*
> (hábitat, altitud, orientación) en vez de contra toda la escena, y (2) hacer
> el ranking **defendible bajo perturbación** de los pesos expertos. Esta fase
> entrega el **framework y la metodología** (módulos puros y testados) y declara
> con honestidad qué datos faltan para activarlo sobre todos los píxeles reales.

---

## 1. Por qué el baseline de escena no basta

El EHS operacional ancla cada sendero a los percentiles **de toda la escena**
(P90 sano / P10 suelo) sobre los píxeles de vegetación de fondo
(`calculate_delta_ehs._compute_scene_baselines`). Es robusto frente a la deriva
radiométrica entre imágenes, pero tiene una debilidad conocida:

> Si una sequía deprime **todo** el paisaje, el "P90 sano" también baja. Un
> sendero regionalmente estresado puede parecer sano *relativo a su entorno
> igualmente estresado*. El baseline de escena puede **normalizar de más** y
> ocultar el estrés regional.

**Solución (F4):** baselines **estratificados**. Cada sendero se compara con el
P90/P10 de su propio estrato ecológico, no con el de la escena entera.

## 2. Framework: `src/risk_engine/baselines.py`

`compute_stratified_baselines(values, strata, p_base_pct, p_floor_pct, min_pixels)`
produce:

- `pooled` — baseline de escena (siempre disponible; comportamiento actual).
- `by_stratum` — P90/P10 por etiqueta de estrato.
- **Regla de fallback explícita y defendible:** un estrato con menos de
  `min_pixels` (por defecto 100, igual que la guarda de escena) **toma prestado
  el baseline pooled** (`fell_back=True`) en lugar de un percentil inestable.
- `for_stratum(label)` devuelve el baseline del estrato, o el pooled si la
  etiqueta es desconocida / None.

Es **agnóstico de la fuente**: el llamador aporta pares `(valor, etiqueta)`. Esto
deja el punto de integración limpio para cuando el ráster de estratos esté
alineado a la rejilla de la escena.

## 3. Qué datos faltan (declarado, no oculto)

| Estratificador | Dato necesario | Estado |
|---|---|---|
| Hábitat / vegetación | Capa Natura 2000 / vegetación rasterizada a la escena | KML de vegetación PNSG disponible (`SistemasNaturales_…_vegetacion.kml`); falta rasterizar y alinear |
| Altitud (banda) | DEM (MDT25 IGN o Copernicus DEM) | **No presente** en el repo |
| Orientación / pendiente | Derivadas del DEM (aspect, slope) | Depende del DEM |
| Litología / bioclima | Cartografía edafológica / bioclimática | No integrada |

El único categórico ya disponible por sendero es la **zona PRUG** (PNSG), que
sirve como primer estratificador operativo. La estratificación por altitud y
orientación es la mejora de mayor impacto y queda **bloqueada por la ausencia de
un DEM** — es una tarea de datos, no de método.

---

## 4. Incertidumbre y robustez: `src/analysis/sensitivity.py`

Muchas constantes son expert-based (pesos EHS `W_NDVI = W_NDMI = 0.5`, pesos
TPI…). Un ranking solo es defendible si es **estable** bajo perturbación
razonable de esos pesos. El módulo lo cuantifica con funciones puras:

- `deficit` / `stress_score` — replican la fórmula operacional para que la
  sensibilidad use el modelo real.
- `weight_band(d_ndvi, d_ndmi, w_min, w_max)` — rango del score al barrer el
  reparto NDVI/NDMI. Si `d_ndvi == d_ndmi`, el `spread` es 0 (los pesos no
  importan); cuanto más difieren, mayor la banda de confianza.
- `ranking_stability(items, top_n, w_min, w_max)` — por ítem, el rango de rango
  a través de la malla de pesos, y la bandera **`robust_top_n`**: cierto solo si
  el *peor* rango del ítem sigue dentro del top-N para **todos** los pesos. Esto
  responde literalmente a *"si el peso NDVI varía de 0,4 a 0,6, ¿sigue este
  sendero en el top-3?"*.
- `monte_carlo_ci(d_ndvi, d_ndmi, w_ndvi, sigma, n)` — propaga ruido gaussiano
  sobre los déficits a un **intervalo de confianza** del score (P5/P50/P95).

### Ejemplo (de los tests)

Dos sendas que se intercambian según el peso:
`ndvi_heavy=(0.80, 0.30)` y `ndmi_heavy=(0.30, 0.80)` con pesos en `[0.3, 0.7]`
→ ninguna es líder robusta (`robust_top_n=False`, rango 1↔2). En cambio
`dominant=(0.95, 0.92)` mantiene rango 1 en toda la malla → `robust_top_n=True`.

---

## 5. Integración pendiente (siguiente paso, fuera de F4)

Para correr la sensibilidad sobre **cada sendero real** hay que persistir sus
déficits por índice (`d_ndvi`, `d_ndmi`) o `avg_ndvi/avg_ndmi` + baselines en la
salida del Pipeline A (hoy el CSV solo guarda EHS/ΔEHS/SCM/presupuesto). Es una
adición pequeña a `calculate_delta_ehs` / `run_pipeline_a_filemode`. Una vez
persistidos, `ranking_stability` produce directamente la columna "ranking
robusto" para el dashboard (F3) y los informes.

---

*Documento de diseño · SNTO · F4 baselines + incertidumbre · territorio principal PNSG.*
