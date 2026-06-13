# Protocolo de validación de campo y pseudo-validación (F5)

> **Propósito.** El sistema produce un EHS satelital muy elaborado, pero muchas
> de sus constantes son expert-based. La mejora de mayor impacto que señaló el
> audit es **demostrar que el EHS satelital correlaciona con la degradación
> observada en el terreno**. Esta fase entrega la *estructura* para hacerlo —
> esquema de datos de campo, diseño de muestreo control-impacto y métricas de
> concordancia— de modo que una campaña mínima (o una pseudo-validación) pueda
> ejecutarse y reportarse de forma defendible. **No es una campaña ya realizada.**

---

## 1. Qué se mide en campo

Por cada parcela georreferenciada (`src/validation/field.py::FieldObservation`):

| Variable | Instrumento / método | Campo |
|---|---|---|
| Compactación del suelo | Penetrómetro de bolsillo (MPa) | `soil_compaction_mpa` |
| Cobertura vegetal | Estimación visual en cuadrante (%) | `veg_cover_pct` |
| Erosión visible | Clase 0–3 (ninguna→severa) | `erosion_class` |
| Anchura real del sendero | Cinta métrica (m) | `trail_width_m` |
| Afluencia | Conteo / contador automático | `visitor_count` |
| Foto georreferenciada | Móvil con GPS | `photo_ref` |
| Estrato | Hábitat / banda de altitud | `stratum` |

El **índice de degradación de campo** (`degradation_index()`, 0–100, convenio de
estrés) combina con igual peso la compactación normalizada, el déficit de
cobertura (100 − cobertura) y la erosión escalada. Así es comparable contra el
score de estrés satelital.

## 2. Diseño control-impacto (BACI)

El muestreo sigue un diseño **Before-After-Control-Impact** simplificado a
**Control-Impact** en el primer ciclo (sin línea base temporal todavía):

- **Parcelas de impacto** — sobre el corredor del sendero (0–`distance_to_trail_m`
  bajo, `is_control=False`).
- **Parcelas de control** — lejos del sendero, en el **mismo estrato** (hábitat,
  altitud, orientación), `is_control=True`. Son la referencia de "qué es sano
  para este hábitat", coherente con los baselines estratificados de F4 y con la
  zona *landscape* del SCM (que actúa como control espacial interno).

La regla de emparejamiento control↔impacto por estrato evita confundir el efecto
del sendero con diferencias de hábitat.

## 3. Métricas de concordancia (`src/validation/agreement.py`)

1. **Correlación satélite↔terreno** — `validate_satellite_vs_field(pairs)` calcula
   la **correlación de Spearman** entre el estrés satelital y el índice de
   degradación de campo en parcelas co-localizadas. ρ ≥ 0,6 ⇒ *"el satélite sigue
   la degradación observada"*; es la evidencia que eleva el EHS de "demo" a
   "indicador validado".
2. **Contraste control-impacto** — `control_impact_contrast(impacto, control)`
   reporta la diferencia de medias y el **tamaño de efecto de Cliff (δ)** entre
   parcelas impactadas y de control. δ ≥ 0,474 (Romano et al. 2006) ⇒ efecto
   grande: el corredor está claramente más degradado que su control.

Ambas son funciones puras (Spearman y Cliff's δ implementados sin SciPy), con
tests en `tests/unit/test_validation.py`.

## 4. Pseudo-validación (sin campaña de campo)

Mientras no haya datos de penetrómetro, se puede pseudo-validar usando puntos de
control **satelitales** lejos del sendero (la zona *landscape* del SCM) como
proxy de control, y contrastándolos contra el corredor (zona *core*). El mismo
`control_impact_contrast` aplica sustituyendo el índice de campo por el estrés
satelital por zona. Esto demuestra el gradiente de impacto con los datos ya
disponibles, a la espera de la verdad-terreno.

## 5. Tamaño muestral mínimo y límites

- Mínimo **3 parcelas co-localizadas** para una Spearman con sentido (el módulo
  lo exige; por debajo devuelve "insuficiente").
- Un primer ciclo Control-Impact **no** sostiene afirmaciones temporales (eso lo
  da la serie 2021–2026 de F2). La validación de campo confirma la *relación*
  satélite↔degradación, no la *tendencia*.
- La campaña ideal: ≥ 15–20 parcelas impacto + ≥ 15–20 control, estratificadas,
  con fotos y coordenadas, en la ventana fenológica de la escena satelital usada.

---

*Documento de protocolo · SNTO · F5 validación · territorio principal PNSG.*
