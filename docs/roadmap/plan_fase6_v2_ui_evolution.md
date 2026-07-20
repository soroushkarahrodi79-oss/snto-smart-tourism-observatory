# Fase 6 — v2.0 role-based UI evolution (plan)

> **Estado (2026-07-20): ✅ COMPLETA en código.** Todos los pasos de §4
> (6.0–6.7f) están mergeados en `main` (PRs #75–#89); las tres decisiones de
> §2 quedaron resueltas e implementadas por sus recomendaciones conservadoras.
> Ver §7 para lo que queda fuera del alcance del plan (pase visual del
> propietario y corte de release).

## 0. Qué NO es esta fase

- No es una reescritura visual completa en un solo PR. Cada paso de §4 es un
  PR pequeño, individualmente revisado, **sin auto-merge** — mismo patrón que
  Fase 4 y Fase 5.
- No resuelve las decisiones de producto de §2 por su cuenta. A diferencia de
  Fase 5 (donde las 3 decisiones abiertas eran técnicas y las resolví yo por
  delegación explícita), las de esta fase son decisiones de **producto y
  navegación** — le corresponden al propietario.
- No implementa nada hasta que este documento se apruebe (mergeado como PR
  docs-only), igual que `plan_fase5_v2_foundations.md` precedió a la
  implementación de Fase 5.
- No relaja la separación de evidencia (real/calibrada/sintética/simulada) ni
  el gating de decisión de ADR-004 "por pulido visual" — non-negotiable
  explícito en `docs/ux/ui-evolution-v2-spec.md` §12.

## 1. Estado real verificado

### 1.1 La puerta "Pre-v2" (spec §11, §15) está cerrada

La especificación UX v2.0 (`docs/ux/ui-evolution-v2-spec.md`) condicionaba la
implementación a tres prerrequisitos técnicos — los tres están cumplidos:

| Prerrequisito | Estado |
|---|---|
| Modularización de `app.py` | ✅ Fase 4 (#27): ~3.170 → ~285 líneas |
| Backend persistente (ADR-006) | ✅ Fase 5 (ADR-011, #61–#70): SQLAlchemy+Alembic, `/api/v2`, ciclo de vida validado, auditoría, auth mínima; Postgres en producción desde 2026-07-18 |
| Identidad/roles (precedente) | ✅ #28: vistas por audiencia Técnica/Gestor/Auditoría, `ViewProfile.section()` |

`ADR-007` (fija la evolución de UI en v2.0, después de modularizar) queda
satisfecho. **La especificación §15 autoriza explícitamente empezar la
implementación una vez cerrada esta puerta.**

### 1.2 Corrección de numeración de fases

`docs/roadmap/plan_fases_post_v1.2.md` §7 titulaba **"Fase 5 — v2.0:
fundamentos de producto"** agrupando persistencia *y* evolución de UI en un
solo bloque aspiracional. Lo que se ejecutó como "Fase 5" (ADR-011, #61–#70)
cubrió únicamente los fundamentos de backend. La evolución de UI por roles —
la otra mitad de ese §7 original — se numera aquí como **Fase 6**, para que
el histórico de PRs y el roadmap queden trazables sin ambigüedad. (Este
documento actualiza esa sección en el mismo PR.)

### 1.3 Brecha entre la spec y lo ya construido

La spec (escrita antes de Fase 5) asumía que "Urgent actions" llegaría
**después** de esta puerta como estado local efímero, nunca simulando
persistencia (§6, nota bajo la tabla de prioridad). En la práctica, Fase 5.9
ya construyó una primera versión **contra el backend persistente real** —
por delante de lo que la spec previó, no por detrás. Pero es un corte
mínimo: lee alertas abiertas ordenadas por `risk_score` y permite un avance
de ciclo de vida. Brecha frente al módulo P1 completo que describe la spec
§6 ("Urgent actions"):

| Requisito P1 (spec §6) | Estado actual (`tab_urgent_actions.py`) |
|---|---|
| Cola ordenada por severidad×confianza | Solo por `risk_score` descendente; no hay score de confianza (DCS) todavía en el modelo `Alert` |
| Asignar / escalar / descartar con motivo | Solo "avanzar un estado"; no hay descarte con motivo ni asignación a persona |
| Estado de verificación de campo por alerta | No enlaza con `FieldVerification` (existe el modelo desde Fase 5.6, sin usar aquí) |
| Tarjeta de activo con acción y estado | Tarjeta mínima; no enlaza a "activo como página" (no existe todavía, ver §2.3) |
| Falsos positivos registrados | No existe ese estado en `AlertStatus` (`open/assigned/escalated/dismissed` sí cubre "dismissed", falta el motivo) |

Este cierre de brecha es el contenido natural del primer paso de
implementación (§4, paso 6.2).

### 1.4 Mapeo de las 9 tabs actuales a las 4 capas de IA

La spec reemplaza las tabs por 4 capas navegables — **Decidir · Diagnosticar
· Evidenciar · Gobernar** (§5). Mapeo de lo que ya existe:

| Tab actual | Capa IA destino | Nota |
|---|---|---|
| 1️⃣ Resumen Ejecutivo (KPIs) | Decidir → "Panorama de decisión ejecutivo" | De 10 KPIs a 3–4 cifras de decisión (spec §10.1); 6 migran a Diagnosticar |
| 9️⃣ Acciones Urgentes | Decidir → "Urgent actions" | Ya construida (Fase 5.9); necesita el cierre de brecha de §1.3 |
| 4️⃣ Simulador Financiero | Decidir → "Simulador de presupuesto" (P2) | — |
| 5️⃣ Impacto Socioeconómico | Decidir → "Impacto socioeconómico" (P3) | — |
| 2️⃣ Diagnóstico Satelital y Mapa | Diagnosticar → "Diagnóstico espacial" | — |
| 7️⃣ Catálogo de Activos y Auditoría | Diagnosticar → "Catálogo de activos/sendas" | Se convierte en página por activo, ver §2.3 |
| 3️⃣ Priorización y Alertas (Portafolio TPI) | Diagnosticar → "Presión y capacidad de carga" (P2) | — |
| 6️⃣ Evolución Temporal (Series Espectrales) | Evidenciar → "Evidencia satelital" | — |
| 8️⃣ Fundamento y Trazabilidad | Gobernar → "Metodología y auditoría" | Ya es, en esencia, este módulo hoy |

Ningún módulo P1 se construye desde cero: **todos ya tienen un antecesor
funcional**. El trabajo real de Fase 6 es reestructurar la navegación,
aplicar las reglas del sistema de diseño (spec §7–9), completar los enlaces
de "activo como página", y cerrar la brecha de Urgent Actions — no
inventar funcionalidad nueva de análisis.

## 2. Decisiones abiertas (requieren al propietario)

> **Estado: las tres decisiones quedaron RESUELTAS e implementadas por sus
> recomendaciones conservadoras.** 2.1 → opción A, tabs agrupadas por capa
> (`src/ui/navigation.py`, PR #80). 2.2 → opción A, las 3 vistas absorben las
> 6 personas (`ViewProfile` extendido con `home_layer`, PR #82). 2.3 → patrón
> `st.session_state` compatible con 2.1-A (`src/ui/asset_detail.py`, PR #81).
> El texto original se conserva a continuación como registro de la decisión.

A diferencia de Fase 5, estas son decisiones de producto/UX, no de
ingeniería — no las resuelvo por mi cuenta.

### 2.1 Mecanismo de navegación por capas

La spec pide 4 capas navegables reemplazando las tabs (§5, §10.2). Streamlit
soporta multi-página nativa (`st.navigation`/`st.Page`, en las versiones
recientes de la línea `1.35–1.x` que ya usa el proyecto) además del patrón
actual de `st.tabs()` con estado condicional. Opciones:

- **A. Mantener `st.tabs()`**, reagrupadas en 4 grupos visuales dentro de la
  misma página — cambio mínimo, sin URLs por capa, sin romper el patrón
  actual de `render_tab_x()`.
- **B. Migrar a `st.navigation`/páginas nativas** — URLs reales por capa
  (`/decidir`, `/diagnosticar`, …), más alineado con "página por activo"
  (§2.3), pero un cambio arquitectónico mayor sobre `src/ui/`.

**Recomendación (no decisión):** empezar con A para los primeros pasos de
implementación (bajo riesgo, reversible), evaluar B solo si "activo como
página" (P1, spec §10.4) lo exige de verdad.

### 2.2 Mecanismo de home page por persona

La spec define 6 personas (§4) pero el sistema hoy tiene 3 `ViewMode`
(Técnica/Gestor/Auditoría). Opciones:

- **A. Las 3 vistas actuales absorben las 6 personas** por agrupación (p. ej.
  Gestor cubre Director + Decisor público + Gestor de destino) — cambio
  aditivo sobre `ViewProfile`, sin tocar el enum.
- **B. Extender a un enum de 6 personas** — más fiel a la spec, pero rompe
  compatibilidad con `test_view_modulation.py` y con el contrato
  `ViewProfile.section()` que ya usan 8 tabs.

**Recomendación (no decisión):** A para v2.0 P1; B queda para cuando (si)
haga falta distinguir Director de Decisor público en la práctica.

### 2.3 "Activo como página" — enrutamiento

Spec §10.4: "el 80% de los enlaces del producto aterrizan ahí". Requiere
decidir si es una URL real (depende de 2.1-B) o un patrón de
`st.session_state` con un id de activo seleccionado (compatible con 2.1-A).
Bloqueado por 2.1.

## 3. Esquema — de spec a artefactos concretos

No se introduce esquema de datos nuevo: la spec vive sobre los recursos ya
persistidos en Fase 5 (`ManagedAsset`, `Alert`, `Recommendation`,
`FieldVerification`, `Intervention`). Lo nuevo en esta fase es:

- `src/ui/layers/` (o el nombre que 2.1 determine) — agrupación de tabs por
  capa IA, sin nuevo estado de dominio.
- Extensión de `AlertStatus`/`Alert` si el cierre de brecha de Urgent
  Actions (§1.3) lo requiere — **resuelto en 6.2a sin cambio de esquema**: el
  triaje reutiliza el `AlertStatus` y el campo `reason` ya existentes, y la
  confianza sale del `Recommendation.confidence` ya modelado. Ninguna
  migración Alembic fue necesaria.
- Ningún cambio a `src/persistence/` fuera de eso.

## 4. Pasos de implementación

| Paso | Contenido | Riesgo | Bloqueado por |
|---|---|---|---|
| 6.0 | **✅** Este documento (docs-only) + corrección de numeración en `plan_fases_post_v1.2.md` | Ninguno | — |
| 6.1 | **✅ (PR #78)** Reglas del sistema de diseño (spec §7–9) aplicadas *in situ* a las tabs existentes: jerarquía tipográfica, precedencia de paleta, tarjetas de evidencia sin acento en Diagnosticar/Evidenciar. Sin reestructurar navegación. | Bajo — solo CSS/presentación, mismo patrón que `render_helpers.py` | Ninguno |
| 6.2a | **✅ Backend de triaje de alertas** (`alert_triage.py`: máquina de estados assign/escalate/dismiss-with-reason, auditada; `POST /api/v2/alerts/{id}/triage`; `UrgentAction` enriquecida con `confidence` del top recommendation y `field_verified`). **Sin cambio de esquema**: reutiliza `Alert.status`/`reason`, `Recommendation.confidence`, `FieldVerification`. Falsos positivos = dismiss con motivo. | Medio — `src/persistence` + `/api/v2/alerts` | Ninguno |
| 6.2b | **✅ Wiring UI del triaje** en la pestaña «Acciones Urgentes»: botones Asignar/Escalar/Descartar (con input de motivo obligatorio para descartar), y muestra de `confianza N%` (sin decimales espurios, spec §8) + badge de verificación de campo. Escrituras in-process con actor `ui`, vía `triage_alert`. Cubierto por AppTest (controles presentes) + tests de servicio para el comportamiento. **Recomendable un vistazo visual del propietario** (`streamlit run app.py`, pestaña 9). | Medio — `src/ui/tabs/` | 6.2a |
| 6.3 | **✅ (PR #79)** Panorama de decisión ejecutivo: de 10 KPIs a 3–4 cifras de decisión + reubicación de las 6 restantes a Diagnosticar | Medio — toca `app.py`/`tab_kpis.py` | Ninguno |
| 6.4 | **✅ (PR #80)** Reagrupación de navegación en las 4 capas IA (implementa la decisión de §2.1 → opción A, `src/ui/navigation.py`) | Alto — toca `app.py` y la navegación completa | ~~§2.1~~ resuelto |
| 6.5 | **✅ (PR #81)** Activo como página (implementa la decisión de §2.3 → enrutado por `st.session_state`, `src/ui/asset_detail.py` + `asset_navigation.py`) | Alto — nueva superficie de navegación | ~~§2.1, §2.3~~ resueltos |
| 6.6 | **✅ (PR #82)** Home pages por persona (implementa la decisión de §2.2 → opción A: las 3 vistas absorben las 6 personas, `ViewProfile.home_layer`) | Medio-Alto | ~~§2.2~~ resuelto |
| 6.7a | **✅ Simulador de escenarios v2**: tres carteras anuales comparables (esencial / plan / refuerzo), supuestos editables de coste y eficacia, costes como horquilla redondeada, delta de riesgo evitado y composición por Tier en paleta índigo. Reutiliza el optimizador TIS/DCS existente y etiqueta todos los resultados como simulados. | Medio — `src/intervention/planning.py` + `src/ui/tabs/tab_simulator.py` | Ninguno |
| 6.7b | **✅ Presión y capacidad de carga**: TPI estacional explícitamente estimado, capacidad operativa como horquilla condicionada por EHS/DCS, y atribución turismo-vs-clima en lenguaje de hipótesis SCM con aviso «correlación ≠ causa». Conserva la matriz territorial previa y corrige sus etiquetas para no presentar el proxy anual como aforo observado. | Medio — `src/platform/pressure_capacity.py` + `src/ui/tabs/tab_portfolio.py` | Ninguno |
| 6.7c | **✅ Confianza e incertidumbre**: superficie DCS por activo con soporte para componentes exactos persistidos, decomposición honesta, tornado de sensibilidad estructural, recomendaciones para elevar confianza y mapa de brechas. Mientras el dashboard conserve solo el total DCS, muestra intervalos matemáticamente posibles y «propagación pendiente»; nunca reparte el total de forma heurística. | Medio — `src/platform/confidence_explain.py` + `src/ui/tabs/tab_confidence.py` | Ninguno |
| 6.7d | **✅ Proveniencia y linaje**: registro por dato para cada activo con valor, fuente, naturaleza epistémica, clase de evidencia, fecha disponible y transformaciones hasta TPI/acción. Aplica degradación a la entrada más débil y declara que el runtime aún no persiste timestamps/huellas de ejecución por valor; nunca sustituye la fecha faltante por la fecha del informe. | Medio — `src/platform/lineage.py` + `src/ui/tabs/tab_provenance.py` | Ninguno |
| 6.7e | **✅ Informes y exportaciones** (spec §6, "Reports / exports"): módulo de la capa Gobernar que empaqueta lo ya calculado en dos artefactos descargables y etiquetados por evidencia — (1) **resumen ejecutivo del panel** (Markdown/JSON) sobre la cartera de decisión real del dashboard vía `src/reporting/territorial_brief.py`, y (2) **capa GIS (GeoJSON)** del conjunto de monitorización satelital real (geometría OAPN + tendencia Sentinel-2 + `evidence_level`) reutilizando `src/reporting/gis_export.py`. Son **dos conjuntos de activos distintos** y la UI los etiqueta con su procedencia para no confundirlos; nada se inventa (campos ausentes → «pendiente») y no se afirma validación de campo (#26). No reusa `build_risk_brief` porque su descomposición de componentes del `risk_engine` no existe en el modelo territorial (evitar fabricar evidencia). `src/ui/tabs/tab_reports.py`, capa Gobernar. | Medio — `src/ui/` | Ninguno |
| 6.7f | **✅ Configuración territorial** (spec §6 P3, "prepare multi-park without overpromising"): registro de territorios de solo-lectura con estado de validación honesto por territorio (PNSG piloto activo; 2 pilotos de tendencia OAPN v1.2; 13 plantillas GEE sin validar) + umbrales operativos de solo-lectura. **Ningún territorio se marca validado en campo** (la campaña #26 sigue pendiente); no se ofrece alta/edición ni tenencia multi-parque (v3.0). `src/platform/territory_registry.py` + `src/ui/tabs/tab_config.py`, capa Gobernar. | Medio — `src/ui/` | Ninguno |

Cada paso: rama desde `main`, tests, PR individual, **sin auto-merge**,
verificación manual (`streamlit run app.py`) cuando toque `src/ui/` — mismo
patrón que Fase 4 y Fase 5.

## 5. Verificación por paso

- `python -m pytest -q` en verde, incluyendo
  `tests/integration/test_view_modulation.py` (cifras financieras invariantes
  entre vistas) sin regresión.
- Smoke test manual (`streamlit run app.py`) para cualquier paso que toque
  `src/ui/`, mismo patrón usado en Fase 4/5.9.
- `ruff check` limpio sobre los módulos nuevos, añadidos a la zona
  bloqueante de CI desde el principio.
- AA de accesibilidad como criterio de aceptación (spec §11) — a definir el
  checklist concreto en el paso 6.1.

## 6. Relación con el resto del roadmap

Continúa `docs/ux/ui-evolution-v2-spec.md` (spec completa) y cierra la
"Fase 5 — v2.0: fundamentos de producto" original de
`plan_fases_post_v1.2.md` §7 (renumerada aquí como Fase 6 para el tramo de
UI). v3.0 (multi-parque enterprise, spec §11) queda fuera de este plan.

## 7. Próximos pasos

> **Estado: Fase 6 COMPLETA en código (PRs #75–#89, todos los pasos 6.0–6.7f
> mergeados).** Trabajo repartido entre dos agentes: Codex del propietario
> (6.1, 6.3–6.6, 6.7a–d, ramas `codex/*`) y Claude Code (6.0, 6.2a/b, 6.7e,
> 6.7f). El borrador 6.7e de Codex quedó fuera del remoto y fue supersedido
> por el PR #89.

Queda, ya fuera del alcance de este plan:

1. **Pase visual del propietario** sobre las 4 capas × 3 vistas
   (`streamlit run app.py` o el Container App tras reconstruir la imagen).
2. Corte de la siguiente release cuando el propietario dé el visto bueno
   (bump desde `1.6.0.dev0`, `scripts/sync_readme.py`, tag).
3. Los frentes operativos del roadmap: campaña de validación de campo (#26)
   y vigilancia del trigger de despliegue del API (ADR-012).
