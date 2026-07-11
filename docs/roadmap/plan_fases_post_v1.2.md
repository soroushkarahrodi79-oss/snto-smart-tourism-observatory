# Plan de fases post-v1.2.0 — Consolidación y avance hacia v2.0

> **Estado:** aprobado como hoja de ruta operativa. Fecha: julio 2026.
> **Punto de partida:** `main` = v1.1.1 (`07801f8`); v1.2.0 lista en PRs #21 + #22
> (solo pendiente de datos GEE del piloto).
> **Método:** este plan se ha construido auditando *todas* las ramas del
> repositorio (13 remotas), los PRs abiertos, los issues (#9–#16) y la memoria
> del proyecto (`CLAUDE.md`, `docs/roadmap/`, `docs/ai-context/`).

---

## 1. Estado de partida verificado

### 1.1 Línea principal

| Versión | Estado | Contenido |
|---|---|---|
| v1.0.0 | ✅ En `main` (tag) | Prototipo científico PNSG, EHS, dashboard |
| v1.1.0 | ✅ En `main` (tag, PR #1) | Capa temporal Sentinel-2 real 2021–2026, Mann-Kendall preliminar |
| v1.1.1 | ✅ En `main` (tag, PRs #19/#20) | Rigor estadístico MK desestacionalizado + fix orden cronológico |
| **v1.2.0** | 🟡 **PRs #21 + #22 abiertos** | Multi-parque Red OAPN (código completo, datos del piloto pendientes) |

### 1.2 PRs abiertos (= v1.2.0)

- **PR #21** (`feature/v1.2.0-oapn-network-expansion-clean` → `main`): plantillas
  GEE de 15 parques + generador `build_gee_oapn_templates.py` + plan de piloto
  (`docs/v1.2.0_oapn_expansion_plan.md`). Aditivo, 552 tests verdes.
- **PR #22** (`feature/v1.2.0-oapn-integration`, *stacked* sobre #21):
  generalización multi-parque del flujo temporal (`--park`,
  `satellite_trends.load_asset_trends(park=…)`, selector de parque en Tab 6).
  561 tests verdes. **Retrocompatible por diseño**: default `park="pnsg"` →
  comportamiento byte-idéntico a v1.1.1.
- **Único bloqueo:** exportación manual GEE (CSV de Tablas de Daimiel y
  Monfragüe). No automatizable en CI (requiere cuenta Earth Engine + Drive).

### 1.3 Auditoría de ramas: veredicto por rama

| Rama | Ahead/Behind `main` | Veredicto |
|---|---|---|
| `feature/v1.2.0-oapn-network-expansion-clean` | 1 / 0 | **Mergear** (PR #21, primero) |
| `feature/v1.2.0-oapn-integration` | 2 / 0 | **Mergear** (PR #22, tras #21) |
| `research/statistical-rigor` | 15 / 13 | **Rescatar** por cherry-pick (Fase 2 → v1.3.0). Cortada de un `main` antiguo; su merge directo revertiría v1.1.x |
| `claude/tourism-observatory-views-audit-jyl38k` | 7 / 14 | **Gated**: toca `app.py` (+173 líneas); bloqueada por el non-negotiable "modularizar antes de evolucionar UI" (Fase 4). Sus docs (`views_audit_design.md`) rescatables antes como docs-only |
| `feature/v1.1.0-multiyear-trends` | 11 / 4 | **Borrar**: contenido mergeado vía PR #1 (commits duplicados por rebase) |
| `feature/v1.2.0-oapn-network-expansion` | 8 / 13 | **Borrar**: versión sucia sustituida por `-clean`; su merge revertiría la base estratégica y el rigor v1.1.1 |
| `fix/v1.1.1-statistical-rigor` | 1 / 2 | **Borrar**: mergeada como PR #19 |
| `docs/v1.1.0-status-sync` | 1 / 3 | **Borrar**: mergeada como PR #18 |
| `docs/v1.1.1-temporal-design-sync` | 1 / 1 | **Borrar**: mergeada como PR #20 |
| `docs/mermaid-architecture-diagrams` | 0 / 13 | **Borrar**: totalmente integrada |
| `docs/strategic-knowledge-base-2026` | — | **Borrar**: contenido ya en `main` (`ae4a139`); era el origen del contaminado PR #7 |
| `docs/strategic-knowledge-base-2026-clean` | 2 / 6 | **Borrar**: verificado con diff — `CLAUDE.md`, `docs/ai-context/` y `MASTER_STRATEGIC_INDEX.md` son idénticos en `main` |

### 1.4 Issues abiertos

- **Obsoletos** (referían al PR #1 pre-merge, ya integrado): #14 (conflicto
  README), #15 (CI en verde), #16 (validar assets/pins) → cerrar con nota de
  verificación.
- **Vigentes**, mapeados a fases de este plan: #9 (posicionamiento
  decision-intelligence), #10 (separación de evidencia), #11 (protocolo de
  validación), #12 (risk brief para dirección), #13 (estabilización de ramas —
  este plan es su ejecución).

---

## 2. Fase 0 — Cierre de v1.2.0 (inmediata)

**Objetivo:** convertir los PRs #21/#22 + los datos GEE en el release v1.2.0
etiquetado, sin comprometer la línea PNSG.

1. **Revisión humana y merge de PR #21** (plantillas + plan; aditivo, riesgo
   bajo). Al mergear, GitHub re-apunta PR #22 a `main` automáticamente.
2. **Revisión humana y merge de PR #22** (integración multi-parque). Verificar
   antes: CI verde, `available_parks() == ['pnsg']` (selector oculto sin
   datos), suite 561 tests.
3. **Exportación GEE (paso manual del propietario):** pegar
   `scripts/gee_templates_oapn/pn_tablas_daimiel.js` y `pn_monfrague.js` en
   [code.earthengine.google.com](https://code.earthengine.google.com) → Run →
   Tasks → descargar CSV de Drive a `clean_assets/timeseries/<key>_gee_timeseries.csv`.
4. **Ingestión y análisis** (rama `data/v1.2.0-pilot-ingest`):
   `python scripts/run_timeseries_analysis.py --input clean_assets/timeseries/<key>_gee_timeseries.csv --park <key>`
   → `mk_trends_<key>.json`. El selector de Tab 6 aparece solo al existir ≥2
   parques con datos.
5. **QA por bioma antes de marcar nada "validado"** (transparencia
   metodológica, non-negotiable):
   - *Tablas de Daimiel* (humedal): índice diagnóstico **NDMI**; revisar
     coherencia con la historia hídrica conocida del parque.
   - *Monfragüe* (dehesa): **NDVI/EVI**; revisar estacionalidad mediterránea y
     la capa ciclismo (columna `category`).
   - Cobertura nubosa/SCL, huecos de serie, nº de observaciones por mes.
6. **Release:** bump a `1.2.0` en `pyproject.toml` → `python scripts/sync_readme.py`
   → tag `v1.2.0` + release notes (qué es real, qué es piloto, qué queda
   "pendiente de validación" — los otros 13 parques).

**Definition of Done:** tag `v1.2.0` en `main`; 2 parques piloto visibles en
Tab 6 con datos reales y caveats; los 13 restantes etiquetados como plantillas
sin validar; suite de tests verde; versión sincronizada.

---

## 3. Fase 1 — Higiene de repositorio (misma semana que Fase 0)

**Objetivo:** que el repositorio refleje solo trabajo vivo; eliminar el riesgo
de merges accidentales de ramas obsoletas (una de ellas revertiría `main`).

1. Cerrar issues #14, #15, #16 con comentario de verificación (PR #1 mergeado,
   CI verde en `main`, assets validados en v1.1.x).
2. Borrar las 8 ramas marcadas **Borrar** en la tabla §1.3 (tras confirmar una
   última vez `git rev-list --count origin/main..<rama>` sobre contenido único).
3. Crear tickets para las Fases 2–4 (patrón de los issues #9–#13), de modo que
   cada fase tenga su unidad de seguimiento.
4. Actualizar `CLAUDE.md` (sección *Current Status* y *Next Recommended
   Actions*): v1.1 ya no es "PR #1 abierto"; el estado pasa a ser el de este
   plan.

---

## 4. Fase 2 — v1.3.0: Rigor estadístico consolidado

**Objetivo:** rescatar el trabajo científico de `research/statistical-rigor`
(el mayor activo no mergeado) y extenderlo al modo multi-parque. Cierra #11.

**Problema:** la rama está cortada de un `main` antiguo (13 behind) y parte de
su contenido (MK desestacionalizado, Yue-Pilon) ya llegó a `main` vía v1.1.1.
Un merge directo generaría conflictos y regresiones.

**Estrategia (mismo patrón que funcionó con la rama OAPN "-clean"):**

1. Crear `feature/v1.3.0-statistical-rigor-clean` desde `main` post-v1.2.0.
2. Cherry-pick de los commits únicos, en orden, resolviendo solapes con
   `src/time_series/mann_kendall.py` y `prewhitening.py` ya mergeados:
   - `fbb744a` — intervalo de confianza del EHS por bootstrap de bloques (FA-3)
   - `8545873` — nota de rigor estadístico (docs, FA-1..3)
   - `3939525` — detección de punto de cambio abrupto Pettitt (Fase B)
   - `4dc1cfb` — análisis de sensibilidad global del EHS, Morris (FC-1)
   - `426bb1c` — validación cruzada inter-sensor NDVI S2 vs MODIS (FC-2)
   - `6fb25ab` — unificación de la detección de tendencia en ambos pipelines
3. **Extensión multi-parque:** parametrizar los nuevos análisis con el mismo
   `park=<slug>` de v1.2.0, para que Pettitt/bootstrap/sensibilidad funcionen
   sobre los pilotos OAPN, no solo PNSG.
4. Tests: portar las suites de la rama (`test_changepoint`, `test_confidence`,
   `test_ehs_sensitivity`, `test_cross_sensor`, `test_prewhitening`) y añadir
   casos multi-parque.
5. Documentación: actualizar `docs/methodology/` y
   `docs/nota_metodologica_temporalidad.md` con los métodos incorporados y sus
   límites (no sobre-afirmar validez, non-negotiable).
6. PR único, revisión humana, merge, tag `v1.3.0`.

**Valor:** defensibilidad académica (TFM) + credibilidad institucional: cada
tendencia mostrada pasa a tener IC, punto de cambio y validación inter-sensor.

---

## 5. Fase 3 — v1.4.0: Pilot readiness institucional

**Objetivo:** completar los items de `v1.2.md` (roadmap estratégico) que la
v1.2.0 técnica no cubrió: convertir la evidencia en material usable por un
gestor de parque. Cierra #9, #10, #12 y avanza el protocolo de campo.

Orden recomendado (independientes entre sí, PRs pequeños):

1. **Risk brief director-grade** (#12): informe ligero exportable
   (estado ecológico → causa probable → confianza → prioridad → presupuesto).
   Base: `docs/product/personas.md`, `docs/reviews/2026/02-national-park-director.md`.
2. **Export GIS**: salida GeoJSON/GeoPackage de assets + tendencias + EHS para
   consumo en QGIS/ArcGIS. SNTO *se integra con* GIS, no lo reemplaza
   (posicionamiento estratégico).
3. **Separación de evidencia** (#10): etiquetado explícito
   real / calibrada / sintética / simulada en UI y en datos exportados;
   resolver la inversión de convención del EHS (ADR-004).
4. **Copy de posicionamiento** (#9): reencuadre "observatorio" →
   "capa de inteligencia para la decisión" en dashboard, README y
   product-vision. Sin rediseño de UI (eso es v2.0).
5. **Campaña de validación de campo**: ejecutar
   `docs/field_validation_protocol.md` sobre una muestra de assets PNSG +
   piloto; registrar resultados como evidencia de calibración.
6. Merge acumulado → tag `v1.4.0`: el release "listo para piloto de pago".

---

## 6. Fase 4 — Pre-v2.0: modularización de `app.py` (bloqueante)

**Objetivo:** eliminar el mayor riesgo arquitectónico antes de cualquier
evolución de UI. `app.py` está en **3.172 líneas** (creció desde ~2.890) y
concentra UI, orquestación, estado, copy y lógica de producto.

1. **Extracción incremental por tabs** a `src/ui/` (un PR por tab, sin cambio
   de comportamiento; los tests de contrato existentes como red de seguridad):
   `src/ui/tabs/tab1_*.py` … `tab6_temporal.py`, `src/ui/state.py`,
   `src/ui/copy.py` (textos), `src/ui/layout.py`.
2. Criterio de done: `app.py` < 300 líneas (solo composición y navegación);
   ningún test roto; el dashboard se comporta idéntico.
3. **Después** (y solo después), rescatar
   `claude/tourism-observatory-views-audit-jyl38k`: las vistas por audiencia
   (técnica/gestor/auditoría, F10), el helper `section()` y la telemetría
   opt-in encajan naturalmente sobre la estructura modular. Rebase o
   cherry-pick según el tamaño del conflicto con el `app.py` ya modularizado.
   - Su documento `docs/views_audit_design.md` puede rescatarse antes como
     PR docs-only si se necesita para diseño.

Esta fase no lleva número de release propio si no cambia comportamiento
(candidata a `v1.5.0` interna o directamente pre-releases `v2.0.0-alpha`).

---

## 7. Fase 5 — v2.0: fundamentos de producto

Según `docs/roadmap/v2.0.md`, y **solo tras** integrar Fases 0–4:

- Arquitectura modular consolidada (ya iniciada en Fase 4).
- Promoción del API FastAPI (hoy secundaria) a contrato versionado.
- Backend persistente, identidad/autorización, audit trail.
- Evolución mayor de UI por roles (director, analista, campo, informes,
  auditoría), sobre la especificación UX v2.0 ya mergeada (PR #17) y el
  trabajo de vistas rescatado en Fase 4.
- v3.0 (multi-parque enterprise, escala Red OAPN completa) queda fuera de este
  plan; sus 13 plantillas GEE ya están preparadas y esperan validación
  incremental parque a parque.

---

## 8. Principios de compatibilidad (invariantes de todas las fases)

1. **`park="pnsg"` como default intocable**: toda generalización multi-parque
   debe dejar el comportamiento PNSG byte-idéntico (patrón establecido en PR #22).
2. **Tags semver en cada release** (`v1.2.0`, `v1.3.0`, …) con
   `pyproject.toml` como fuente única de versión y `sync_readme.py --check-version`
   como guarda.
3. **No modificar `main` directamente**; todo por PR con aprobación humana.
4. **No mezclar PRs de documentación con cambios funcionales** (lección del
   PR #7 contaminado).
5. **No difuminar evidencia** real / calibrada / sintética / simulada; no
   sobre-afirmar validez científica antes de la validación (Fases 0.5 y 3).
6. **Nada de rediseño mayor de UI antes de completar la Fase 4**
   (modularización de `app.py`).
7. **Ramas muertas se borran**: una rama supersedida es un riesgo de reversión
   accidental, no un backup (el historial de git ya conserva los commits).

## Documentos relacionados

- [v1.2 (dirección estratégica)](v1.2.md) · [v2.0](v2.0.md) · [v3.0](v3.0.md)
- Plan técnico del piloto OAPN: `docs/v1.2.0_oapn_expansion_plan.md`
  (llega a `main` con el merge de PR #21)
- [Índice estratégico maestro](../../MASTER_STRATEGIC_INDEX.md)
- [Contexto para agentes IA](../ai-context/README.md)
