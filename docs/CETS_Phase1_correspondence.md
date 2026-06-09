# Tabla de correspondencia CETS Fase I ↔ SNTO

**Reserva de la Biosfera Sierra del Rincón** · Candidatura a la Fase I de la Carta Europea de Turismo Sostenible (CETS)

> **Propósito.** Este documento mapea cada componente y principio de la Fase I de la CETS contra el módulo del SNTO que lo responde, el indicador cuantitativo que genera y su nivel de madurez actual. Es la columna vertebral argumentativa que conecta el sistema técnico (SNTO) con el marco de acreditación europeo (CETS / EUROPARC).

---

## 0. Terminología oficial (verificada con EUROPARC-España)

La **Fase I de la CETS** acredita al **espacio natural protegido** (la acreditación de empresas turísticas es la Fase II). El dosier de candidatura de la Fase I se compone de:

| Componente oficial | Descripción (EUROPARC-España) |
|---|---|
| **Diagnóstico** | Análisis del uso público y el turismo en el ámbito de actuación, según objetivos y exigencias de la CETS |
| **Estrategia** | Estrategia a cinco años basada en el diagnóstico |
| **Plan de Acción** | Programa de actuaciones a cinco años de todas las entidades participantes |
| **Foro** | Marco colaborativo (formal o informal) donde se elabora la candidatura |
| **Grupo de Trabajo** | Equipo encargado de la redacción del dosier de candidatura |

El compromiso CETS exige **mejora continua mediante seguimiento e informe periódico de resultados** sobre impacto ambiental, satisfacción del visitante, desempeño económico y calidad de vida local.

**Leyenda de madurez (1–5):**
`1` Conceptual · `2` Prototipo / simulado · `3` Funcional sobre datos demo · `4` Operacional con datos reales · `5` Validado externamente / en producción

---

## 1. Correspondencia con los componentes del dosier Fase I

| Componente CETS Fase I | Módulo SNTO que lo responde | Indicador concreto que genera | Evidencia / archivo | Madurez |
|---|---|---|---|---|
| **Diagnóstico** — estado de conservación | `etl_raster_processor` + `calculate_delta_ehs` | EHS operacional por activo (0–100), NDVI/NDMI reales Sentinel-2 | `clean_S2_NDVI.tif`, `calculate_delta_ehs.py` | **4** |
| **Diagnóstico** — atribución del impacto | SCM (`src/spatial_causality/`) | Clasificación LOCALIZED / LANDSCAPE / MIXED vía Spatial Impact Gradient (SIG) | `run_scm_operational.py` | **4** |
| **Diagnóstico** — fiabilidad de la evidencia | DCS (`src/decision_confidence/`) | Decision Confidence Score con data quality gate | `assessor.py`, 22 tests | **4** |
| **Estrategia** — priorización territorial | TPI (`src/territorial/`) | Territorial Priority Index + sistema de 4 tiers | `run_phase5_report.py` | **4** (demo) |
| **Estrategia** — compromiso de huella ecológica | `tis_engine` (modelo financiero-ecológico) | Presupuesto de restauración €/activo con factor causal | `tis_engine.py` | **3** |
| **Plan de Acción** — actuaciones medibles a 5 años | TIS + escenarios (`src/intervention/`) | 5 escenarios A–E, simulación de impacto, optimizador presupuestario | `run_phase6_report.py` | **3** (demo) |
| **Plan de Acción** — coste de no actuar | Análisis contrafactual (`src/intervention/`) | Trayectorias EHS a 3 años, coste de inacción | `run_phase6_report.py` | **3** (demo) |
| **Foro / Grupo de Trabajo** — evidencia compartida | Platform Phase 7 (5 perfiles de stakeholder) | Informe ejecutivo de 10 secciones segmentado por perfil | `run_phase7_report.py` | **2** |
| **Mejora continua** — madurez del destino | Modelo de madurez 5 niveles (Phase 7) | Nivel de madurez del destino (autoevaluación) | `src/platform/` | **3** |
| **Seguimiento e informe periódico** — transparencia | Dashboard Azure + capa de explicabilidad | Dashboard público 10 KPIs + traza de decisión (elegido/rechazado/por qué/confianza) | `app.py`, Azure Container Apps | **4** |

---

## 2. Correspondencia con los 10 principios de la Carta

| # | Principio CETS (EUROPARC) | ¿Lo aborda el SNTO? | Módulo / indicador SNTO | Madurez |
|---|---|---|---|---|
| 1 | **Cooperación** entre todos los actores | 🟡 Instrumental | Informes segmentados por 5 perfiles de stakeholder (alimenta el foro, no lo sustituye) | **2** |
| 2 | **Elaboración de la Estrategia y Plan de Acción** | 🟢 Sí | TPI + escenarios TIS A–E + contrafactual | **3** |
| 3 | **Protección y valorización del patrimonio natural y cultural** | 🟢 Núcleo | EHS + SCM + presupuesto de restauración causal | **4** |
| 4 | **Satisfacción del visitante / calidad de la experiencia** | 🔴 No | — (fuera del alcance del sistema actual) | **1** |
| 5 | **Información y sensibilización** | 🟡 Parcial | Dashboard público como herramienta de transparencia ciudadana | **3** |
| 6 | **Productos turísticos específicos del espacio protegido** | 🔴 No | — (programático, no técnico) | **1** |
| 7 | **Formación** | 🔴 No | — (programático) | **1** |
| 8 | **Mantenimiento de la calidad de vida local** | 🟡 Débil | Proxy de presión humana geo-based (sin indicador socioeconómico directo) | **2** |
| 9 | **Beneficios para la economía local** | 🟡 Débil | Modelo de coste de restauración (licitación pública local); sin medición de gasto turístico | **2** |
| 10 | **Gestión de los flujos de visitantes** | 🟢 Sí | KPI-6 (capacidad de visitantes en riesgo), proxy de presión, integración MITMA prevista | **3** |

---

## 3. Análisis de brechas (transparencia metodológica)

- **🟢 Fortaleza máxima — Diagnóstico y protección del patrimonio (principio 3):** el SNTO *es* el sistema de monitorización ambiental objetivo que la Fase I exige, y supera el estándar habitual (cualitativo) con indicadores espectrales reales y atribución causal del impacto. Aquí el proyecto aporta valor diferencial real.
- **🟡 Brecha de gobernanza (componente Foro / principio 1):** el Foro permanente es un requisito **organizativo y político**, no técnico. El SNTO lo *alimenta* con evidencia objetiva, pero no lo constituye. Posicionamiento honesto para el TFM: *"el SNTO es la infraestructura de evidencia del Foro, no el Foro"*. → Declarar como actuación del Plan de Acción.
- **🟡 Brecha socioeconómica (principios 8 y 9):** la CETS exige indicadores socioeconómicos (empleo, satisfacción residente, gasto turístico). El SNTO es fuerte en lo ambiental y débil aquí. → Proponer MITMA + encuestas a residentes como línea de desarrollo.
- **🔴 Principios programáticos (4, 6, 7):** satisfacción del visitante, productos turísticos y formación quedan deliberadamente fuera del alcance del sistema; son acciones humanas/organizativas. → Reconocer explícitamente el límite del sistema técnico.
- **🔴 Dependencia crítica — validación externa:** ningún nivel de madurez 4 se consolida sin contraste con EUROPARC-España y el equipo gestor de la Reserva de la Biosfera. Es la condición para que la candidatura sea creíble y no autoproclamada.

---

## 4. Síntesis de madurez

| Bloque CETS | Cobertura SNTO | Madurez media |
|---|---|---|
| Monitorización ambiental (Diagnóstico) | Completa | **4** |
| Atribución de huella ecológica | Completa | **4** |
| Priorización y Plan de Acción | Demostrada (datos sintéticos) | **3** |
| Gobernanza / Foro | Instrumental | **2** |
| Socioeconómico | Débil | **2** |
| Transparencia / seguimiento | Operacional y pública | **4** |

> **Conclusión para la defensa.** El SNTO responde de forma fuerte y diferencial a los requisitos de **monitorización objetiva** y **minimización de la huella ecológica** de la Fase I — los dos pilares más exigentes técnicamente. Las brechas (gobernanza, socioeconómico, principios programáticos) no son fallos del sistema, sino el límite natural entre una **infraestructura de evidencia** y un **proceso de acreditación participativo**: el SNTO instrumenta la candidatura, no la reemplaza.

---

## Fuentes

- [Fase I CETS — EUROPARC-España](http://www.redeuroparc.org/actividades/carta-europea-turismo-sostenible/fase-i-cets)
- [Carta Europea de Turismo Sostenible — EUROPARC-España](https://redeuroparc.org/carta-europea-turismo-sostenible/)
- [The European Charter for Sustainable Tourism in Protected Areas — EUROPARC Federation](https://www.europarc.org/sustainable-tourism/)

*Documento generado para el TFM "Gobernanza Inteligente y Transición Regenerativa en la Reserva de la Biosfera Sierra del Rincón" · SNTO v0.1.0 · junio 2026. La terminología oficial de la CETS debe cotejarse con el Manual de EUROPARC-España antes de la entrega definitiva.*
