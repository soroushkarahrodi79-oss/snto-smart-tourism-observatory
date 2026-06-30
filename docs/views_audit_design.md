# Auditoría de las 3 vistas del observatorio — diagnóstico y hoja de ruta (F10)

> **Propósito.** El observatorio sirve la misma evidencia a tres audiencias distintas
> (Técnica, Gestor, Auditoría científica) a través de un único `ViewProfile`
> (`src/platform/views.py`) consumido en `app.py`. F7 creó el selector; un commit
> posterior ("diferenciar de verdad las 3 vistas") añadió divulgación por capas
> real. Este documento audita **el estado actual** de esa diferenciación —qué
> cambia, qué no, y por qué— y propone fases concretas para optimizarla en
> próximas ramas. No incluye cambios de código: es el cierre de la Fase 1
> (auditoría) antes de tocar `app.py`.

---

## 0. Resumen ejecutivo

- Las 3 vistas están bien definidas como **datos** (`ViewProfile`, F7) y la
  diferenciación es real (no solo el banner), pero **incompleta**: de las 8
  pestañas del dashboard, solo **5 cambian contenido según la vista**; 3 quedan
  idénticas para Técnica/Gestor/Auditoría, incluida la pestaña que por nombre
  más debería variar (*8️⃣ Fundamento y Trazabilidad*).
- La lógica de modulación (`if _view.simplified / .technical / .audit`) está
  **dispersa en 10 puntos** de un archivo de ~3000 líneas, sin un contrato
  único ni tests que verifiquen que el render realmente difiere por vista.
- Existe un **segundo eje de "vista" no unificado**: el selector de capa del
  mapa (Gestión vs. Espectral) es independiente del selector de
  audiencia — un Gestor puede activar la capa espectral cruda y una
  Auditoría puede quedarse en la capa de gestión.
- Recomendación: cerrar primero el contrato (qué debe diferir y qué es
  intencionalmente común), luego consolidar el mecanismo, y solo después
  extender cobertura — en fases pequeñas, cada una en su propia rama desde
  `main`, siguiendo el patrón de commits por fase que ya usa el repo (F1, F7,
  F8, F9).

---

## 1. Qué son hoy las 3 vistas

Definidas en `src/platform/views.py` como `ViewProfile` (dataclass inmutable),
registradas en `_PROFILES` y expuestas vía `get_view()` / `view_modes()`.

| Vista | `ViewMode` | Audiencia | `confidence_detail` | Flags activos | Énfasis declarado |
|---|---|---|---|---|---|
| 🔬 Técnica | `TECNICA` | Equipo técnico/científico | `RAW` | `technical=True` | NDVI/NDMI, buffers, baselines, incertidumbre, píxeles válidos |
| 🧭 Gestor | `GESTOR` | Gestor del espacio/administración | `CONCISE` | `simplified=True` | Ranking, prioridad, presupuesto, acción recomendada |
| ⚖️ Auditoría científica | `TRIBUNAL` | Revisión metodológica/académica | `FULL` | `technical=True`, `audit=True` | Procedencia del dato, override conservador, fórmulas EHS/TPI/DCS, límites declarados |

Por defecto el sidebar arranca en **Auditoría** (`_default_view_idx` apunta a
`TRIBUNAL`), una decisión deliberada: es la vista más completa y la adecuada
para defensa metodológica/académica del observatorio.

---

## 2. Mecanismo técnico (cómo se aplica)

`ViewProfile` es la única fuente de verdad; `app.py` la consume en **10
puntos** (`grep -n "_view\."`):

1. Sidebar (L1370-1385): selector + caption de audiencia + resumen `shows`.
2. Tab 1 *Resumen Ejecutivo*: `simplified` → tarjeta "Acción prioritaria del
   territorio" (solo Gestor).
3. Tab 6 *Evolución Temporal*: `simplified` → una línea sin jerga;
   `technical` → estadística Mann-Kendall/DCS/SCM cruda.
4. Tab 5 *Impacto Socioeconómico*: `confidence_detail == FULL` → expander de
   procedencia y límites declarados (solo Auditoría).
5. Tab 2 *Diagnóstico Satelital*: `technical` controla si el expander
   metodológico arranca expandido por defecto.
6. Tab 2 *Diagnóstico Satelital* (bloque de sendas reales): `confidence_detail`
   en sus 3 niveles controla el grado de caveat sobre profundidad temporal.
7. Tab 7 *Catálogo de Activos*: `simplified` → una línea de validación
   satelital; resto → fila de 4 métricas + párrafo; `audit` → expander extra
   de procedencia y límites.

Patrón de divulgación: **aditivo por capas** (todas ven el núcleo; cada
perfil suma o quita) — principio correcto y documentado en el docstring del
módulo. El problema no es el principio, es su aplicación incompleta y
repetida ad-hoc.

---

## 3. Matriz de cobertura real por pestaña (hallazgo central)

| # | Pestaña | ¿Modula por vista? | Qué cambia |
|---|---|---|---|
| 1 | Resumen Ejecutivo (KPIs) | ✅ Parcial | Tarjeta de acción prioritaria solo en Gestor |
| 2 | Diagnóstico Satelital y Mapa | ✅ Parcial | Expander metodológico auto-expandido en Técnica/Auditoría; caveat de confianza en 3 niveles |
| 3 | Priorización y Alertas (Portafolio TPI) | ❌ No | Idéntico en las 3 vistas |
| 4 | Simulador Financiero | ❌ No | Idéntico en las 3 vistas |
| 5 | Impacto Socioeconómico | ✅ Parcial | Expander de procedencia/límites solo en Auditoría |
| 6 | Evolución Temporal (Series Espectrales) | ✅ Sí | Resumen en lenguaje llano (Gestor) vs. estadística cruda (Técnica/Auditoría) |
| 7 | Catálogo de Activos y Auditoría | ✅ Sí | Una línea (Gestor) vs. 4 métricas + párrafo (resto) vs. + expander de procedencia (Auditoría) |
| 8 | Fundamento y Trazabilidad | ❌ No | Idéntico en las 3 vistas |

**3 de 8 pestañas (37%) no modulan en absoluto.** El caso más llamativo es la
pestaña 8, *Fundamento y Trazabilidad*: por nombre y propósito es la que más
debería reaccionar a `audit`/`confidence_detail`, y hoy muestra exactamente lo
mismo a las 3 audiencias.

---

## 4. Hallazgos de la auditoría

1. **Cobertura incompleta** (sección 3): 3 pestañas sin modulación, una de
   ellas (*Fundamento y Trazabilidad*) contradice el propósito declarado de
   la vista Auditoría.
2. **Segundo eje de vista no unificado.** El toggle del mapa
   (`map_mode` → `spectral_mode`, L2491-2540, `build_pydeck_deck` vs.
   `build_pydeck_deck_spectral`) es un control independiente del
   `ViewMode` de audiencia. Hoy nada ata "vista Técnica" a "capa espectral
   por defecto", aunque conceptualmente son la misma idea de "mostrar el dato
   crudo".
3. **Lógica dispersa, sin contrato.** Los 7 puntos de consumo repiten
   `if _view.simplified / .technical / .audit` con HTML/markdown inline en
   cada sitio. No hay un único lugar que declare "estas son las secciones que
   aporta cada pestaña por flag de vista", lo que aumenta el riesgo de drift
   al añadir una 9ª pestaña o un 4º perfil.
4. **Dos sistemas de modulación parcialmente redundantes.**
   `confidence_detail` (3 niveles: RAW/CONCISE/FULL) y los booleanos
   `technical`/`simplified`/`audit` se solapan conceptualmente pero se usan en
   pestañas distintas (confidence_detail solo en 2 de 8). No está
   documentado cuándo usar uno u otro al añadir una nueva sección.
5. **Sin tests de integración sobre la diferenciación.**
   `tests/unit/test_views.py` cubre el dataclass (5 tests: orden, flags,
   campos no vacíos) pero ningún test verifica que `app.py` realmente
   renderice contenido distinto por vista — la garantía actual es solo
   "verificado en vivo" según el mensaje de commit, no un test que falle si
   alguien rompe la modulación al editar `app.py`.
6. **Banner de Auditoría embebido como texto largo en Python.** El banner de
   `TRIBUNAL` (L89-100 de `views.py`) es un párrafo extenso de metodología
   (override conservador, resolución, ALMUDENA/INE) hard-codeado en el
   módulo, duplicando contenido que ya vive en
   `docs/informe_tecnico_limites.md` y `docs/baselines_uncertainty_design.md`.
   Riesgo de que ambas fuentes diverjan con el tiempo.

---

## 5. Principios de reorganización propuestos

- **Mantener `views.py` como fuente única de verdad** del perfil (correcto
  hoy); no introducir una segunda fuente de configuración de vistas.
- **Formalizar el contrato por pestaña**: un registro declarativo (tabla o
  pequeño helper, p. ej. `view.show(section_key)`) en vez de `if` repetidos,
  para que añadir una pestaña obligue a declarar explícitamente su
  comportamiento por vista (o marcarla deliberadamente como "común a las
  3", como ya lo son Portafolio TPI y Simulador Financiero por razones
  financieras válidas).
- **Decidir explícitamente, no por omisión**, qué pestañas son
  intencionalmente comunes (cifras financieras objetivas no deberían cambiar
  por audiencia) frente a cuáles deberían modular y hoy no lo hacen
  (*Fundamento y Trazabilidad*).
- **Unificar o documentar el segundo eje** (mapa espectral): o se ata por
  defecto a `technical`, o se documenta como eje ortogonal intencional.
- **Enlazar, no duplicar, el texto metodológico largo**: el banner de
  Auditoría debería referenciar/derivar de los docs de diseño existentes en
  vez de mantener su propia copia.
- **Cerrar con un test de contrato** (p. ej. `streamlit.testing.v1.AppTest`)
  que falle si una pestaña marcada como "debe modular" deja de hacerlo.

---

## 6. Fases y pasos para optimizar

Cada fase = una rama propia desde `main` y, preferiblemente, un commit/PR
enfocado — el mismo patrón que F1/F7/F8/F9 en el historial del repo.

### Fase 1 — Auditoría (este documento) ✅
Cerrada en esta rama (`claude/tourism-observatory-views-audit-jyl38k`).
Sin cambios de código; solo diagnóstico y decisión.

**Decisión de producto (resuelta).** *Fundamento y Trazabilidad* **sí debe
modular por vista**. Implementado en esta rama como primer entregable de la
Fase 4 (ver más abajo): Gestor recibe un resumen de fiabilidad de una pantalla;
Técnica, el detalle metodológico completo con licencias plegadas; Auditoría,
todo visible incluidas fuentes y licencias.

### Fase 2 — Consolidar el mecanismo de modulación ✅
Cerrada en esta rama.
- **Helper único**: `ViewProfile.section(*, technical=False, simplified=False,
  audit=False) -> bool` en `views.py`. Sustituye los ~10 `if _view.simplified /
  .technical / .audit` dispersos en `app.py` por una sola API documentada y
  testeable; sin args devuelve `True` (núcleo común). Sin cambio de
  comportamiento visible. (El nombre es `section()` y no `shows()` porque el
  dataclass ya tiene un campo `shows: str`.)
- **`confidence_detail` documentado**: su docstring en `views.py` deja explícita
  la regla — `section()` decide SI aparece una sección; `confidence_detail`
  (RAW/CONCISE/FULL) decide CUÁNTO caveat lleva un dato de confianza que las tres
  vistas muestran en alguna forma. Son ejes distintos.
- **Tests de contrato**:
  - Unitarios (`tests/unit/test_views.py`): 6 tests de `section()` (núcleo
    común, cada eje, OR inclusivo).
  - Integración (`tests/integration/test_view_modulation.py`): `AppTest` levanta
    la app real y verifica que (a) las tres vistas renderizan sin excepción,
    (b) el resumen ejecutivo y los planes "acción primero" aparecen solo en
    Gestor, (c) cada vista muestra su propio banner y no el de las otras, y
    (d) **las cifras financieras son idénticas entre audiencias**. Robusto
    frente a la contaminación global del stub de `pydeck` de `test_map_layers`.

### Fase 3 — Unificar el segundo eje (mapa espectral)
- Decidir y documentar la relación entre `ViewMode` y `map_mode`
  (¿la vista Técnica/Auditoría preselecciona la capa espectral por defecto,
  dejando el toggle como override manual?).

### Fase 4 — Extender cobertura real
- **✅ *Fundamento y Trazabilidad* (pestaña 8) — hecho en esta rama.**
  Modulación por audiencia:
  - **Gestor**: `render_executive_summary()` — resumen de fiabilidad de una
    pantalla (cuántas variables se miden vs. se modelan, en lenguaje llano) +
    los 4 caveats que cambian una decisión; el detalle denso queda plegado en
    un expander.
  - **Técnica**: fundamento + matriz de trazabilidad + multiplicadores
    inline; fuentes y licencias plegadas (asunto de publicación, secundario
    para el perfil técnico).
  - **Auditoría**: todo visible, con fuentes y licencias desplegadas
    (requisito de defensa/publicación).
  - Verificado con `AppTest`: el contenido renderizado difiere entre las tres
    vistas. Test de contrato `test_plain_summary_covers_every_data_type`
    blinda que cada `DataType` tenga su versión llana.
- **✅ *Portafolio TPI* (pestaña 3) y *Simulador Financiero* (pestaña 4) —
  hecho en esta rama.** Vista "acción primero" para Gestor, con la condición
  firme de que **las cifras financieras son idénticas entre audiencias**:
  - *Portafolio TPI*: para Gestor, un **Plan de acción prioritario**
    (`_render_action_first`) lidera la pestaña — activos Tier 1-2 por TPI con su
    acción recomendada y el coste del mejor escenario TIS (mismas cifras que el
    resto de vistas); la matriz analítica queda debajo. Técnica/Auditoría
    conservan el orden actual (matriz primero).
  - *Simulador Financiero*: para Gestor, un resumen en lenguaje llano tras el
    slider (qué financia el presupuesto, qué entra/sale frente a la base de
    €100K) **antes** de los KPIs; los KPIs y la asignación —que no están
    condicionados por vista— se muestran idénticos a todas las audiencias.
  - Verificado con `AppTest`: los paneles de acción solo aparecen en Gestor y el
    conjunto de cifras financieras (`st.metric` + tarjetas de presupuesto) es
    idéntico en las tres vistas.
- **✅ Banner de Auditoría (`TRIBUNAL`) — hecho en esta rama.** El párrafo
  metodológico largo embebido en `views.py` (tile T30TVL, cobertura
  ALMUDENA/INE, resolución, override, SIN_DATO) se ha sustituido por un banner
  conciso que enuncia el contrato (cada cifra con procedencia + confianza DCS,
  override conservador) y **remite** a la pestaña «Fundamento y Trazabilidad»
  (`methodology.py`) y a `docs/informe_tecnico_limites.md`,
  `docs/baselines_uncertainty_design.md` y
  `docs/socioeconomic_integration_design.md` como fuente canónica. Así el detalle
  vive en un único lugar y no diverge. Verificado con `AppTest`.

**Estado de la Fase 4: completa.** Las tres pestañas que no modulaban
(*Fundamento y Trazabilidad*, *Portafolio TPI*, *Simulador Financiero*) ya lo
hacen, y el banner de Auditoría dejó de duplicar la metodología. Quedan las
Fases 2 (consolidar el mecanismo en un helper único + tests de contrato), 3
(unificar el eje del mapa espectral con `ViewMode`) y 5 (medición).

### Fase 5 — Cierre y medición
- Si el observatorio tiene usuarios reales, instrumentar qué vista se usa más
  (telemetría simple) para priorizar dónde profundizar el detalle.
- Actualizar `README.md`/whitepaper si cambia el contrato público de las
  vistas.

---

## 7. Cómo seguir esto en ramas separadas

- Esta rama solo contiene la auditoría (sin tocar `app.py` ni `views.py`).
- Cada fase siguiente debe abrir su propia rama desde `main` actualizado
  (p. ej. `claude/views-f10-2-contrato`, `claude/views-f10-3-mapa-espectral`,
  `claude/views-f10-4-cobertura`), con su propio commit descriptivo y, si
  aplica, PR — para mantener cada cambio pequeño, revisable y reversible de
  forma independiente, en línea con cómo se han ido cerrando F1/F7/F8/F9.
- No combinar fases en una sola rama: el contrato (Fase 2) debe quedar
  estable antes de extender cobertura (Fase 4), o el helper nuevo tendría que
  rehacerse sobre código que ya cambió.

---

## 8. Quick wins vs. decisiones de producto

| Acción | Tipo | Bloqueada por |
|---|---|---|
| Helper único de modulación (Fase 2) | Quick win técnico | Nada — se puede empezar ya |
| Test de contrato por vista (Fase 2) | Quick win técnico | Nada |
| Enlazar banner de Auditoría a docs existentes (Fase 4) | Quick win técnico | Nada |
| Modular *Fundamento y Trazabilidad* | Requiere decisión | Confirmar si debe variar o es intencionalmente completa siempre |
| Unificar mapa espectral con `ViewMode` | Requiere decisión | Confirmar si el toggle debe seguir siendo manual independiente |
| Modular *Portafolio TPI* / *Simulador Financiero* | Requiere decisión | Confirmar que las cifras financieras deben permanecer idénticas entre audiencias |
