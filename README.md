<div align="center">

# 🏔 SNTO — Smart Nature Tourism Observatory

**Capa de inteligencia para la decisión en espacios naturales protegidos.** Código abierto, para uso académico.

De la teledetección Sentinel-2 a la decisión de inversión pública: indicadores ambientales calibrados, atribución causal de la degradación y priorización presupuestaria sobre el **Parque Nacional Sierra de Guadarrama (PNSG)**, primer territorio de la Red de Parques Nacionales (OAPN) integrado.

> SNTO **no reemplaza** a ArcGIS, Google Earth Engine, Sentinel Hub, Tableau ni Power BI: se sitúa **por encima** de las plataformas GIS, de observación de la Tierra y de BI, y traduce su señal en decisiones de conservación defendibles (riesgo de presión de visitantes, prioridad e inversión, con nivel de confianza).

[![Tests](https://img.shields.io/badge/tests-1059%20passing-brightgreen)](#8-tests)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.12-blue)](https://www.python.org/)
[![CI](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/ci.yml/badge.svg)](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/ci.yml)
[![Deploy](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/deploy-azure-container-apps.yml/badge.svg)](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/deploy-azure-container-apps.yml)
[![Deploy target](https://img.shields.io/badge/deploy-Azure%20Container%20Apps-0078D4?logo=microsoftazure&logoColor=white)](#7-despliegue)
[![Status](https://img.shields.io/badge/estado-investigaci%C3%B3n%20activa-blue)](#1-estado-del-proyecto)
[![License](https://img.shields.io/badge/uso-acad%C3%A9mico-lightgrey)](LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20818269-1682D4?logo=zenodo&logoColor=white)](https://doi.org/10.5281/zenodo.20818269)

**🔴 [Dashboard en vivo](https://snto-observatory.happyground-be027676.swedencentral.azurecontainerapps.io/)** · 📄 [Whitepaper](WHITEPAPER_SNTO_Architecture_Blueprint.md) · 🏗 [Arquitectura](ARCHITECTURE.md)

</div>

---

## 🎯 El problema en una frase

La mayoría de los espacios naturales protegidos gestionan el impacto del turismo de forma **reactiva**: actúan cuando la degradación ya es visible. El SNTO transforma ese paradigma en **gobernanza regenerativa proactiva** — detecta el estrés ecológico desde el satélite antes de que sea irreversible, distingue si la causa es el uso turístico o el clima, y traduce cada hallazgo en una **prioridad de inversión con presupuesto y nivel de confianza**.

> **Para evaluadores y revisores:** este repositorio es un proyecto de investigación académica de la **Universidad Complutense de Madrid (UCM)**: un observatorio que evalúa el estado de senderos y enclaves de turismo natural por teledetección satelital, detecta zonas de riesgo de degradación y prioriza la intervención con fórmulas financieras. Demuestra un pipeline geoespacial real sobre el **Parque Nacional Sierra de Guadarrama** (218 senderos analizados con cartografía oficial OAPN) y un sistema completo de inteligencia territorial de 7 fases, con capas de **andamiaje temporal (serie 2021–2026), trazabilidad/confianza del dato, baselines estratificados, incertidumbre del ranking y validación de campo**. **1059 tests, CI separado del deploy, dos pipelines arquitectónicamente desacoplados.** La gobernanza se alinea con los marcos europeos de reporte de espacios protegidos (Natura 2000 / EUROPARC / SISMOTUR), validada inicialmente sobre la Reserva de la Biosfera Sierra del Rincón como piloto de calibración.

> **Estado de versión:** [`v2.0.0`](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/releases/tag/v2.0.0) es la última release estable; `main` está en `v2.1.0.dev0` (marcador de desarrollo, no una release final). v2.0.0 consuma la visión v2.0 del roadmap (arquitectura modular + backend persistente + evolución de UI por roles). Se apoya en los cimientos ya publicados en v1.5.0 — la **modularización de `app.py`** (#27: de ~3.170 a ~285 líneas, UI extraída a `src/ui/`), las **vistas por audiencia** (#28: Técnica/Gestor/Auditoría con cifras financieras invariantes) y los **fundamentos del backend persistente** (Fase 5, ADR-011: persistencia SQLAlchemy+Alembic, API `/api/v2`, ciclo de vida, auditoría; producción sobre Azure PostgreSQL desde el cutover 2026-07-18) — y añade la **evolución de UI por roles** (Fase 6): la información se reorganiza en **cuatro capas de decisión** (Decidir · Diagnosticar · Evidenciar · Gobernar) con *home* por audiencia, el **activo como página**, triaje de alertas en «Acciones Urgentes», y los módulos de simulación, presión/capacidad, confianza, proveniencia, informes/exportaciones y configuración territorial. Ningún cambio relaja la separación de evidencia ni afirma validación de campo (campaña #26 aún pendiente). En `main` (sin nueva release estable todavía) ya han aterrizado además los primeros hitos post-v2.0: **v2.1** (activación y gobernanza — deploy gateado por CI, CI endurecido, `DataStatus` de la capa curada), **v2.2** (profundidad analítica — forecasting `SIMULATED` y capacidad LAC/ROS operativos; las vías de dato real —movilidad MITMA, zonas SCM, serie SVI— implementadas con puerta de disponibilidad pero **aún sin dato ingerido**), la **puerta de validación v2.5** (runner de concordancia y captura de parcelas; la campaña de campo sigue pendiente) y los primeros cimientos de **v3.0** (identidad y multi-tenancy, aprovisionamiento, registro territorial editable y autorización de escritura en `/api/v2`; SSO/Entra ID sigue pendiente).

---

## 📸 Vista del dashboard

<div align="center">

![Dashboard ejecutivo SNTO](docs/screenshot-dashboard.png)

_Shell de 4 capas de decisión (Fase 6, v2.0) — Decidir · Diagnosticar · Evidenciar · **Gobernar**, aquí en la vista **Auditoría científica** sobre «Metodología y auditoría», con la puerta de validación satélite↔campo (v2.5) y el panel de alertas activas del PNSG. Desplegado en Azure Container Apps (Sweden Central)._

</div>

---

## 📑 Índice

1. [Estado del proyecto](#1-estado-del-proyecto)
2. [Arquitectura: dos pipelines](#2-arquitectura-dos-pipelines)
3. [Capacidades técnicas implementadas](#3-capacidades-técnicas-implementadas)
4. [Stack tecnológico](#4-stack-tecnológico)
5. [Estructura del repositorio](#5-estructura-del-repositorio)
6. [Orden de ejecución](#6-orden-de-ejecución)
7. [Despliegue](#7-despliegue)
8. [Tests](#8-tests)
9. [Honestidad sobre limitaciones](#9-honestidad-sobre-limitaciones)
10. [Fundamento científico](#10-fundamento-científico)
11. [Fuentes y licencias de datos](#11-fuentes-y-licencias-de-datos)
12. [Licencia / uso académico](#12-licencia--uso-académico)

---

## 1. Estado del proyecto

| Componente | Territorio | Estado |
|---|---|---|
| **Pipeline A — Geoespacial** | **Parque Nacional Sierra de Guadarrama (PNSG)** — territorio principal | ✅ Operacional con datos Sentinel-2 reales (2 escenas: primavera 2026 + verano 2025); **218 senderos** con cartografía oficial OAPN |
| **Capa temporal Sentinel-2 real (v1.1.1)** | PNSG — 21 activos reales | ✅ Real 2021–2026 (GEE); Mann-Kendall **desestacionalizado y verificado con Yue-Pilon** (ver §9) |
| **Expansión Red OAPN — piloto de replicabilidad (v1.2.0)** | Tablas de Daimiel (humedal, 5 activos) + Monfragüe (dehesa, 21 activos) | ✅ Series Sentinel-2 reales 2021–2026 validadas y en el selector de Tab 6; 13 parques restantes preparados como plantillas GEE, pendientes de validación por bioma |
| **Rigor estadístico (v1.3.0)** | PNSG + pilotos OAPN | ✅ Punto de cambio abrupto (Pettitt), IC 95% del EHS por bootstrap de bloques, sensibilidad global (Morris) y validación cruzada inter-sensor NDVI (Sentinel-2 vs MODIS); ver [nota metodológica](docs/nota_metodologica_rigor_estadistico.md) |
| **Integración para decisión y validación (v1.4.0)** | PNSG + pilotos OAPN | ✅ Risk brief directivo, exportación GIS, vocabulario y gating de evidencia, y herramientas de validación de campo; la campaña de campo permanece pendiente |
| **Pipeline A — Calibración metodológica** | Reserva de la Biosfera Sierra del Rincón (Madrid) | ✅ Piloto de validación del método (escenas reales propias) |
| **Pipeline B — Inteligencia territorial (7 fases)** | Villuercas-Ibores-Jara Geopark (Extremadura) | ✅ Demostración funcional completa sobre 20 activos sintéticos calibrados |
| **Capa socioeconómica (ALMUDENA / INE)** | PNSG — 34 municipios | ✅ SVI + impacto en comunidad + empleos en riesgo, integrado en el dashboard |
| **Arquitectura modular del dashboard (Fase 4, #27)** | — | ✅ `app.py` de ~3.170 → ~285 líneas (solo composición); UI extraída a `src/ui/` (`layout.py`, `render_helpers.py`, `render_widgets.py`, un módulo por pestaña en `src/ui/tabs/`) |
| **Vistas por audiencia (#28)** | — | ✅ Técnica / Gestor / Auditoría con divulgación por capas (`ViewProfile.section()`), pestaña Fundamento modulada, telemetría local opt-in; cifras financieras idénticas entre vistas (verificado) |
| **Backend persistente (Fase 5, v1.5.0, ADR-011)** | — | ✅ `src/persistence/` (SQLAlchemy 2.0 + Alembic, repositorios tipados), `/api/v2` de lectura+escritura, máquinas de estado de ciclo de vida, rastro de auditoría y auth mínima por API-key; **producción sobre Azure PostgreSQL** (cutover 2026-07-18). El `/api/v2` existe como código + tests, aún no desplegado como servicio |
| **UI por roles (Fase 6, v2.0.0)** | — | ✅ 4 capas de decisión (Decidir · Diagnosticar · Evidenciar · Gobernar), *home* por audiencia, activo-como-página, triaje de alertas; **14 módulos** analíticos (`src/ui/navigation.py`) |
| **v2.1 — Activación y gobernanza** (`main`, `2.1.0.dev0`) | — | ✅ deploy gateado por CI verde (ADR-009) + runbook de rollback, CI endurecido (cobertura, `mypy`, job Postgres real), `DataStatus` máquina-legible en la capa curada |
| **v2.2 — Profundidad analítica** (`main`, dev) | PNSG | ✅ **forecasting** (proyección con banda de incertidumbre, siempre `SIMULATED`) y marco de capacidad de carga **LAC/ROS** operativos sobre el proxy curado. 🟡 Las **tres vías de dato real** (movilidad MITMA, zonas SCM multiescala, serie temporal SVI) están **implementadas con su puerta de disponibilidad**, pero **ninguna tiene aún el dato ingerido**: sin él el sistema mantiene, etiquetado, el comportamiento curado/simulado previo |
| **v2.5 — Puerta de validación** (`main`, dev, en curso) | PNSG | 🟡 runner de concordancia satélite↔campo (Spearman / Cliff's δ) listo y con superficie de estado; **la campaña de campo (#26) sigue pendiente** — sin ella no se afirma validación |
| **v3.0 — Identidad y multi-tenancy** (`main`, dev, parcial) | — | 🟡 modelos `Organization`/`User`/`UserRole`, política `authz.py`, servicio de aprovisionamiento `tenancy.py`, `Territory.org_id` (aditivo, nulable) y gate de autorización en los 5 endpoints de escritura de `/api/v2`. **Latente hasta que existan `User` reales** — el modelo actual de API-key compartida no cambia. SSO/Entra ID y geometría PostGIS pendientes |
| **v3.0 — Benchmarking Red OAPN** (`main`, dev) | Red OAPN | ✅ roll-up comparativo entre parques (`src/benchmarking/oapn_rollup.py`) **solo sobre los 3 parques con serie de tendencia real comprometida** (PNSG, Monfragüe, Tablas de Daimiel); las 13 plantillas GEE sin validar se reportan como recuento pendiente, nunca agregadas a una cifra de red |
| **v3.0 — Preparación de dosier CETS Fase I** (`main`, dev) | PNSG | ✅ correspondencia CETS↔SNTO (`src/reporting/cets_readiness.py`) con la clase de evidencia de cada requisito **resuelta en vivo**; cobertura declarada y evidencia calculada se mantienen separadas, `real` es el techo (nunca afirma validación) y los principios fuera de alcance (4, 6, 7) se publican, no se ocultan. Material de preparación para un Foro / Grupo de Trabajo, **no un dosier de candidatura** |
| **v3.0 — Seguimiento del PRUG por zonas** (`main`, dev) | PNSG | ✅ agrega la evidencia real de las 218 sendas por **zona de gestión oficial OAPN** (`src/reporting/prug_monitoring.py`): estado ambiental, deterioro estacional y desajuste protección↔presión por zona (Uso Restringido / Moderado / Especial). Evidencia `real` (cartografía OAPN × Sentinel-2) pero **alerta temprana estacional, no tendencia plurianual ni veredicto de cumplimiento del Plan**; sin validación de campo (#26) |
| **v3.0 — Dossier institucional automatizado** (`main`, dev) | PNSG | ✅ las secciones de datos del dossier que se envía a OAPN/EUROPARC se **generan** desde las fuentes vivas (`src/reporting/institutional_dossier.py` + `scripts/build_dossier.py`); CI falla si las cifras publicadas dejan de coincidir con el sistema. La prosa institucional sigue editándose a mano |
| **v3.0 — Paquete de piloto (A07)** (`main`, dev) | — | 🟡 [`docs/product/pilot-package.md`](docs/product/pilot-package.md): alcance, entregables, hitos y criterios de aceptación **cerrados y verificados** contra el sistema; las 7 decisiones comerciales/jurídicas quedan como huecos `🔲` para el responsable — un test verifica que **no aparece ninguna cifra económica inventada** |
| **v3.0 — Contrato OpenAPI publicado** (`main`, dev) | — | ✅ [`docs/api/openapi.json`](docs/api/openapi.json) (OpenAPI 3.1, 21 rutas, 38 esquemas) generado desde el código y verificado en CI, con [guía de integración](docs/api/README.md). Habilita evaluar la integración GIS/BI (ADR-008) **sin desplegar**: el despliegue sigue gobernado por ADR-012 |
| **Cliente móvil** (`mobile/`, Expo + TypeScript) | PNSG | ✅ Fase 1 (ADR-013) shell nativo sobre fixtures sintéticas + Fase 2 (ADR-014) repositorio HTTP real sobre `/api/v2`; **por defecto en modo sintético** salvo `EXPO_PUBLIC_SNTO_USE_REMOTE_API=true`. CI propia, desacoplada de la de Python |
| **Dashboard ejecutivo** | PNSG | ✅ Desplegado en Azure Container Apps (scale-to-zero); sirve el shell de 4 capas |
| **CI/CD** | — | ✅ GitHub Actions → CI verde **gatea** el deploy → ACR build → roll Container App |
| **Tests** | — | ✅ 1058 passing, 1 skipped, 0 regresiones (suite verde, ver §8) |

El Pipeline A produce indicadores ambientales reales: el **PNSG** es el territorio principal del observatorio y la **Reserva de la Biosfera Sierra del Rincón** se conserva como piloto de calibración metodológica (valida el método sobre un segundo territorio con datos reales). El Pipeline B demuestra el sistema de gobernanza de extremo a extremo. Ambos pipelines están diseñados para integrarse cuando el Pipeline A disponga de series temporales multi-anuales reales. Desde v1.2.0, el método se ha replicado con éxito en un piloto de dos biomas contrastados de la **Red de Parques Nacionales (OAPN)** (Tablas de Daimiel, Monfragüe); el resto de la Red queda preparado como plantillas GEE para fases posteriores.

---

## 2. Arquitectura: dos pipelines

### Convención de scores: salud vs estrés

SNTO usa dos direcciones de score 0-100 y no deben mezclarse:

- **Health Score / EHS de observatorio:** 0 = crítico, 100 = saludable. Es el
  convenio usado por dashboard, TPI, tiers y comunicación ejecutiva.
- **Stress Score / EHS operacional legacy:** 0 = sin estrés, 100 = máxima
  degradación. Es el convenio que aún almacenan las columnas legacy
  `ehs_spring`, `ehs_summer` y `delta_ehs` producidas por Pipeline A.

La conversión oficial vive en `src.metrics.semantics`:
`health = 100 - stress`. Esta separación evita que una métrica alta signifique
"excelente" en una parte del sistema y "crítico" en otra.

### Infografía del Flujo de Datos Arquitectónico

```mermaid
graph TD
%% Estilos de los nodos principales
classDef ingesta fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
classDef bd fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
classDef dcs fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
classDef dash fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

%% --- CAPA DE INGESTA Y PROCESAMIENTO (Pipeline A y B) ---
subgraph Ingesta["1. Capa de Ingesta (Parallel Processing)"]
    A1[Pipeline A: Imág. Satelitales] -->|API STAC / COG| A2[Sentinel-2 L2A]
    A2 -->|Cálculo Vectorizado| A3(Índices NDVI / NDMI)
    
    B1[Pipeline B: Socio-Económico] -->|MultiYearAdapter| B2(Datos Estadísticos: INE)
    B2 -->|Normalización| B3(Variables ALMUDENA)
end

%% --- CAPA DE ALMACENAMIENTO Y GOBERNANZA (PostGIS & DCS) ---
subgraph Almacenamiento["2. Capa de Datos y Gobernanza"]
    A3 & B3 -->|src/platform/enrichment.py| C[Enrichment Pipeline]
    C -->|Override Conservador| D[(PostGIS DB: TerritorialAsset)]
    
    %% Sistema de Control Dinámico (DCS)
    D -->|Lectura de Estado| E{DCS Gate: can_act?}
    E -->|False: Datos Insuficientes| E1[Modo Bloqueo / Logs]
end

%% --- CAPA DE NEGOCIO Y VISUALIZACIÓN (Dashboard) ---
subgraph Presentacion["3. Capa de Negocio y Presentación"]
    E -->|True: Validación Exitosa| F[Streamlit Dashboard]
    
    %% Vistas del Dashboard
    F --> G[1. Vista Científica: PyDeck Diagnostic Map]
    F --> H[2. Vista de Negocio: Executive Summary]
    
    %% Entregables finales
    G --> I[Análisis de Riesgo y Degradación]
    H --> J[Plan de Acción y Presupuestos TRAGSA]
end

%% Aplicación de clases visuales
class A1,A2,A3,B1,B2,B3,C ingesta;
class D bd;
class E,E1 dcs;
class F,G,H,I,J dash;
```

> **Nota honesta:** `USE_MOCK_DATA` en `.env.example` controla únicamente el Pipeline A. El Pipeline B consume el `MultiYearAdapter` directamente; sus 20 activos son sintéticos, calibrados con anomalías climáticas documentadas, no datos satelitales reales.

---

## 3. Capacidades técnicas implementadas

- **EHS operacional** calibrado por percentiles de escena (P90 → referencia sana, P10 → suelo degradado) sobre la distribución real de píxeles de cada imagen Sentinel-2, por estación e índice (NDVI, NDMI).
- **SCM operacional** que calcula el Spatial Impact Gradient (SIG) directamente desde los rásteres Sentinel-2 reales (zonas core 0–50 m / near 50–200 m / landscape 200–1000 m en EPSG:25830) y clasifica LOCALIZED_IMPACT / LANDSCAPE_DRIVEN / MIXED — es decir, **separa la degradación causada por el uso turístico de la causada por el clima**.
- **DCS (Decision Confidence Score)** de 5 dimensiones (Data Quality, Temporal Robustness, Spatial Consistency, Model Stability, Signal Strength) con **data quality gate**: `can_act = False` si DQ < 10/25 o TR < 12/25. Ninguna recomendación de gasto se emite sobre evidencia insuficiente.
- **Análisis multi-anual:** test de Mann-Kendall (Sen's slope), descomposición armónica estacional, detección de anomalías inter-anuales y eventos de sequía.
- **TPI (Territorial Priority Index)** para ranking de activos y asignación de recursos en 4 tiers (atención inmediata → promoción activa).
- **TIS — escenarios de intervención** con simulación de impacto, optimizador de presupuesto y análisis contrafactual (coste de no actuar).
- **Panorama de decisión ejecutivo** (Fase 6.3): 3–4 cifras de decisión al frente y los 10 KPIs territoriales reubicados a la capa *Diagnosticar*; modelo de madurez de destino de 5 niveles y perfiles de stakeholders.
- **Backend persistente + API operacional** (Fase 5, ADR-011) — `src/persistence/` (SQLAlchemy 2.0 + Alembic, repositorios tipados, ciclo de vida validado, rastro de auditoría) y `src/api/v2/` de lectura+escritura con auth mínima. Producción sobre Azure PostgreSQL; el `/api/v2` es código + tests, aún no desplegado como servicio.
- **UI por roles en 4 capas** (Fase 6) — `src/ui/navigation.py`: Decidir · Diagnosticar · Evidenciar · Gobernar, con *home* por audiencia, activo-como-página y triaje de alertas (14 módulos).
- **Forecasting** (v2.2) — `src/forecasting/`: proyección de tendencia con banda de incertidumbre y proyección estacional; **cada salida lleva `EvidenceClass.SIMULATED`** (nunca observación), y una superficie de "Proyección de tendencia" en *Diagnosticar*.
- **Capacidad de carga LAC/ROS + vía de movilidad real** (v2.2) — `src/platform/pressure_capacity.py` + `src/platform/lac_ros.py`: clasificación ROS, estándar de *Limits of Acceptable Change* sobre el EHS y capacidad al estándar, calculados sobre el **proxy curado** `visitor_capacity_annual` (rango de planificación, no un límite medido). `src/mobility/` aporta el **cruce real de zonas MITMA** (4 de 6 zonas resueltas) y la ruta de ingesta (`etl_mobility.py`); **el snapshot de viajes aún no se ha generado**, así que hoy no hay dato de movilidad real en el sistema. Cuando exista, la cifra municipal se adjunta como **contexto**, nunca sustituye al proxy del activo: un recuento municipal de viajes no es aforo de sendero.
- **Identidad y multi-tenancy** (v3.0, parcial) — `src/persistence/` añade `Organization`/`User`/`UserRole`, una política de autorización pura (`services/authz.py`), aprovisionamiento de organizaciones y territorios (`services/tenancy.py`) y un gate de escritura en `/api/v2` (`api/v2/authz_gate.py`). Diseño **aditivo y latente**: sin filas `User` reales el comportamiento actual (API-key compartida, territorio `pnsg` sin propietario) no cambia. Ver [`ADR-002`](docs/decisions/ADR-002.md) / [`ADR-005`](docs/decisions/ADR-005.md).
- **Preparación de dosier CETS Fase I** (v3.0) — `src/reporting/cets_readiness.py`: mapea los componentes del dosier de la Fase I de la **Carta Europea de Turismo Sostenible** y sus 10 principios contra los módulos del SNTO, resolviendo la **clase de evidencia de cada requisito contra el estado real del repositorio** (¿hay serie satelital comprometida? ¿snapshot de movilidad? ¿parcelas de campo medidas?). Mantiene dos ejes deliberadamente separados: la **cobertura** es una posición editorial declarada e independiente del dato, y la **evidencia** se calcula. `real` es el techo — nunca emite una afirmación de validación — y los principios que el sistema **no** aborda (4 experiencia, 6 productos, 7 formación) se publican explícitamente. Es material de preparación, no un dosier: la Fase I la construyen un Foro y un Grupo de Trabajo.
- **Contrato de integración OpenAPI** (v3.0, ADR-008) — `scripts/export_openapi.py` → [`docs/api/openapi.json`](docs/api/openapi.json): el contrato **OpenAPI 3.1** completo (21 rutas, 38 esquemas) generado desde la propia aplicación y verificado en CI, de modo que nunca describa una API que el código ya no implementa. Permite a un equipo técnico generar cliente y valorar el encaje con su GIS/BI **antes de decidir desplegar**; publicar el contrato **no** despliega nada — ADR-012 sigue gobernando eso, y la [guía de integración](docs/api/README.md) lo dice explícitamente.
- **Dossier institucional automatizado** (v3.0) — `src/reporting/institutional_dossier.py` + `scripts/build_dossier.py`: el documento que se envía a la Dirección del Parque y a EUROPARC (`docs/dossier_institucional_OAPN.md`) tenía cifras congeladas desde junio 2026 —entre ellas un presupuesto de restauración **7× infraestimado** y una afirmación de cobertura CETS del Principio 10 que el sistema no respalda—. Ahora sus secciones de resultados, madurez y marco se **regeneran desde las mismas fuentes vivas** que alimentan los informes CETS y PRUG (marcadores `SNTO:AUTO`), y `python scripts/build_dossier.py --check` **falla en CI** si las cifras publicadas dejan de coincidir. La prosa institucional (problema, peticiones, contacto) sigue siendo del autor y no se toca.
- **Seguimiento del PRUG por zonas** (v3.0) — `src/reporting/prug_monitoring.py`: lee el parque a través de su propio instrumento de gestión, el **Plan Rector de Uso y Gestión**, agregando la evidencia real de las 218 sendas por **zona de gestión oficial OAPN** (Uso Restringido / Moderado / Especial). Surface el **desajuste protección↔presión**: un deterioro en una zona de mayor protección pesa más (`índice = (100−salud) × peso de protección`) — señala dónde mirar primero, no un incumplimiento. Cartografía OAPN × señal Sentinel-2 real ⇒ evidencia `real`, pero **alerta temprana estacional** (ΔEHS de dos escenas), nunca una tendencia plurianual ni un veredicto de cumplimiento del Plan, y sin validación de campo (#26). Degrada honestamente a «no disponible» para territorios sin zonificación.
- **Benchmarking de la Red OAPN** (v3.0) — `src/benchmarking/oapn_rollup.py`: comparación entre parques construida **solo sobre los parques con tendencia real comprometida en disco** (PNSG, Monfragüe, Tablas de Daimiel). Las 13 plantillas GEE pendientes de QA por bioma se reportan como recuento explícito, **nunca agregadas a una cifra de red** — no se fabrica una señal que la evidencia no sostiene.
- **Capa temporal Sentinel-2 real (v1.1.0, estadística corregida en v1.1.1)** — `src/platform/satellite_trends.py` + `clean_assets/timeseries/`: serie mensual NDVI/NDMI real 2021–2026 (GEE) para 21 activos reales del PNSG, con tendencia Mann-Kendall por activo surgida en el panel "Tendencias satelitales reales" (pestaña Series Temporales). El test corre sobre la serie **desestacionalizada** (descomposición armónica), con **corrección de empates**, **pendiente de Sen + IC 95%** y verificación de robustez frente a autocorrelación (**pre-whitening Yue-Pilon**). Ver [docs/nota_metodologica_temporalidad.md](docs/nota_metodologica_temporalidad.md).
- **Andamiaje temporal declarativo** — `src/temporal/`: especificación declarativa de la serie (`PNSG_5Y` = 72 meses), **gate de validez Mann-Kendall** (qué inferencia sostiene cada profundidad: ΔEHS estacional vs tendencia) y **manifiesto de procedencia** por periodo — ruta de código separada de la capa anterior, aún sin activar con datos reales. Ver [docs/temporal_series_design.md](docs/temporal_series_design.md).
- **Trazabilidad y confianza del dato** — `src/platform/provenance.py`: etiquetas visibles **dato real / calibrado / sintético**, fechas de escena reales, cobertura y *caveats* de confianza en el dashboard.
- **Baselines estratificados + incertidumbre** — `src/risk_engine/baselines.py` (P90/P10 por estrato ecológico con fallback) y `src/analysis/sensitivity.py` (banda de pesos, **ranking robusto** y Monte-Carlo). Ver [docs/baselines_uncertainty_design.md](docs/baselines_uncertainty_design.md).
- **Validación de campo / pseudo-validación** — `src/validation/`: esquema de observación de campo y métricas de concordancia satélite↔terreno (Spearman, contraste control-impacto BACI). Ver [docs/field_validation_protocol.md](docs/field_validation_protocol.md).
- **Dashboard de 3 vistas** (`src/platform/views.py`): técnica / gestor / auditoría científica, con la verbosidad de confianza adaptada a cada audiencia.
- **Capa socioeconómica (ALMUDENA / INE)** — `src/socioeconomic/`: cruza el dato municipal real (padrón INE + Banco de Datos ALMUDENA de la Comunidad de Madrid) con el riesgo ambiental de los activos por municipio. Calcula el **SVI (Socioeconomic Vulnerability Index)** = 0,40·dependencia turística + 0,30·fragilidad demográfica + 0,30·exposición ambiental, el **impacto en la comunidad** (riesgo × dependencia económica) y los **empleos locales en riesgo** respaldados por datos (afiliación a hostelería × exposición). Snapshot curado de 34 municipios del PNSG (15 con economía ALMUDENA + 19 solo demografía, lado Segovia). Ver [docs/socioeconomic_integration_design.md](docs/socioeconomic_integration_design.md).

---

## 4. Stack tecnológico

- **Lenguaje:** Python ≥ 3.12
- **Geoespacial:** rasterio, rasterstats, shapely, geopandas
- **Datos:** Sentinel-2 SR L2A (Copernicus); Google Earth Engine (`gee_adapter.py` implementado, credenciales no incluidas)
- **Base de datos:** PostgreSQL / PostGIS (EPSG:25830 — ETRS89 / UTM 30N)
- **API / dashboard:** FastAPI, uvicorn, Streamlit, pydeck (Deck.gl — sustituye a folium)
- **Persistencia:** SQLAlchemy 2.0 + Alembic (PostgreSQL en producción, SQLite en dev/CI)
- **Modelado / análisis:** NumPy, pydantic; capa de forecasting propia (`src/forecasting/`)
- **Test / calidad:** pytest, pytest-cov, ruff
- **Infra:** Docker · Azure Container Apps · GitHub Actions (CI/CD)

---

## 5. Estructura del repositorio

```
snto-smart-tourism-observatory/
├── README.md
├── ARCHITECTURE.md
├── WHITEPAPER_SNTO_Architecture_Blueprint.md
├── requirements.txt / pyproject.toml / .env.example
│
├── Pipeline A (scripts geoespaciales)
│   ├── etl_raster_processor.py
│   ├── etl_vector_cleaner.py
│   ├── etl_raster_intersection.py
│   ├── calculate_delta_ehs.py
│   ├── run_scm_operational.py
│   ├── tis_engine.py
│   └── db_production_seeder.py
│
├── Pipeline B (informes por fase)
│   ├── run_phase3_report.py
│   ├── run_phase4_report.py
│   ├── run_phase5_report.py
│   ├── run_phase6_report.py
│   └── run_phase7_report.py
│
├── app.py                      # dashboard / entrada Streamlit
│
├── src/
│   ├── ingestion/              # adaptadores: GEE, mock, calibrado, multi-anual
│   ├── features/               # índices espectrales (NDVI, NDMI)
│   ├── geospatial/             # geometría y agregación zonal
│   ├── time_series/            # Mann-Kendall, descomposición, anomalías, volatilidad
│   ├── risk_engine/            # EHS, componentes de riesgo, presión humana, scorer
│   ├── spatial_causality/      # SCM / Spatial Impact Gradient
│   ├── decision_confidence/    # DCS + data quality gate
│   ├── territorial/            # TPI, portfolio, presupuesto, asignación (Phase 5)
│   ├── intervention/           # impacto, escenarios, TIS, reporter (Phase 6)
│   ├── platform/               # dashboard, madurez, stakeholders, provenance, views (Phase 7 + F3/F7)
│   ├── temporal/               # serie 2021-2026: spec, gate Mann-Kendall, manifiesto (F2)
│   ├── analysis/               # sensibilidad de pesos / ranking robusto / Monte-Carlo (F4)
│   ├── validation/             # esquema de campo + concordancia satélite-terreno (F5)
│   ├── metrics/                # semántica de scores salud/estrés (F1)
│   ├── calibration/            # validador y calibración
│   ├── alerts/                 # motor de alertas
│   ├── ranking/                # ranker de activos
│   ├── reporting/              # constructor de informes
│   ├── api/                    # FastAPI (routers: evaluate, ranking, alerts)
│   ├── assets/                 # modelos de activos
│   └── config/                 # constants.py, logging_setup.py, run_context.py
│
├── tests/
│   ├── unit/                   # EHS, DCS, Mann-Kendall, scorer, TIS, ...
│   ├── integration/            # API, pipeline Phase 1, cálculo SIG del SCM
│   └── calibration/            # validador, agregación
│
└── data/
    ├── raw_assets/             # rásteres y vectores de entrada
    └── clean_assets/           # GeoTIFFs y GeoJSON listos para producción
```

---

## 6. Orden de ejecución

### Pipeline A — geoespacial (orden correcto)

```bash
python etl_raster_processor.py      # 1. NDVI/NDMI desde Sentinel-2 L2A
python etl_vector_cleaner.py        # 2. limpieza/reproyección de vectores
python etl_raster_intersection.py   # 3. zonal stats por sendero (buffer 50 m)
python calculate_delta_ehs.py       # 4. EHS estacional + Delta EHS
python run_scm_operational.py       # 5. SIG y clasificación SCM
python tis_engine.py                # 6. priority_score + presupuesto causal
```

### Pipeline B — inteligencia territorial (independiente)

```bash
python run_phase3_report.py   # validación y calibración
python run_phase4_report.py   # reconstrucción multi-anual
python run_phase5_report.py   # inteligencia territorial
python run_phase6_report.py   # escenarios de intervención
python run_phase7_report.py   # plataforma estratégica completa
```

### Instalación local

```bash
pip install -r requirements.txt
cp .env.example .env

# Pipeline A: configurar PostgreSQL/PostGIS y, para datos reales,
# Google Earth Engine (ver src/ingestion/gee_adapter.py).
# USE_MOCK_DATA=true por defecto.

streamlit run app.py          # lanzar el dashboard en local
```

---

## 7. Despliegue

**CI separado del deploy.** El workflow [`ci.yml`](.github/workflows/ci.yml) (lint de módulos mantenidos + import smoke + suite pytest) es la puerta de salud del código y corre en cada `push` y `pull_request` a `main`, **independiente de Azure**. El despliegue [`deploy-azure-container-apps.yml`](.github/workflows/deploy-azure-container-apps.yml) se dispara por `workflow_run` **solo si CI concluye con éxito** (o por dispatch manual): nunca se despliega sobre tests en rojo.

El dashboard se despliega en **Azure Container Apps** con `scale-to-zero` (coste ≈ 0 €/mes en Azure for Students). Tras pasar CI, el deploy reconstruye la imagen en Azure Container Registry (ACR) y actualiza el Container App.

```bash
# Bootstrap único de los recursos Azure:
bash deploy/azure-bootstrap.sh

# Después, el despliegue es automático en cada push a main.
```

Secrets requeridos en GitHub (`Settings ▸ Secrets and variables ▸ Actions`): `AZURE_CREDENTIALS`, `ACR_NAME`. Ver cabecera de [`.github/workflows/deploy-azure-container-apps.yml`](.github/workflows/deploy-azure-container-apps.yml) para el detalle.

> **🔴 Dashboard en vivo:** https://snto-observatory.happyground-be027676.swedencentral.azurecontainerapps.io/

---

## 8. Tests

```bash
pytest --tb=short
```

- **1058 passing, 1 skipped, 0 regresiones, suite verde** (1059 tests recogidos — el badge refleja el total recogido).
- **CI (`ci.yml`)** ejecuta además `ruff` bloqueante sobre los módulos mantenidos (F0–F7), `ruff` informativo sobre el resto (deuda de lint en reducción), import smoke y `py_compile` de los entry points.

---

## 9. Honestidad sobre limitaciones

Esta sección es deliberada: la transparencia metodológica es parte del valor académico del proyecto.

- **Pipeline A — profundidad temporal operacional:** el EHS/ΔEHS operacional (percentiles P90/P10 por escena) sigue anclado en 2 imágenes Sentinel-2 reales (primavera 2026 + verano 2025, un único ciclo anual); el **ΔEHS estacional** (señal de alerta temprana) es válido con dos escenas y no cambia con v1.1.0.
- **Pipeline B — naturaleza de los datos:** opera sobre 20 activos sintéticos calibrados con anomalías documentadas de AEMET / Copernicus. La calibración no sustituye a una validación con datos satelitales reales multi-anuales.
- **Baselines EHS por hábitat:** el **framework** de baselines estratificados ya existe (`src/risk_engine/baselines.py`, con fallback a percentil de escena), pero la estratificación operativa por altitud/orientación requiere un **DEM aún no integrado** y el EHS operacional usa hoy percentiles de escena. Es una brecha de datos, no de método.
- **Serie temporal 2021–2026 (v1.1.0, estadística corregida v1.1.1):** la ingesta real vía Google Earth Engine está hecha para 21 activos reales del PNSG (`clean_assets/timeseries/`, panel "Tendencias satelitales reales" en la pestaña Series Temporales). El test **Mann-Kendall corre sobre la serie desestacionalizada** (descomposición armónica de 2 componentes), con **corrección de empates** en la varianza y **pendiente de Sen con intervalo de confianza no paramétrico**. Los 7 veredictos significativos superan además una prueba de robustez de *pre-whitening* libre de tendencia (Yue-Pilon 2002) sin ningún cambio de dirección. v1.1.1 también corrigió un bug de orden cronológico (year/month se ordenaban como texto: "10" antes que "2"), presente en el release público v1.1.0, que corrompía la serie mensual de los 21 activos. Detalle completo y kit de defensa del tribunal en [docs/nota_metodologica_temporalidad.md](docs/nota_metodologica_temporalidad.md). Nota: esta capa sigue siendo independiente del andamiaje declarativo `src/temporal/` (spec + `trend_gate` + manifiesto), que continúa sin activar con datos reales — son dos rutas de código distintas.
- **Validación de campo:** el esquema y las métricas de concordancia (`src/validation/`) están listos; **falta la campaña de terreno** (penetrómetro, parcelas, control) o, en su defecto, la pseudo-validación con puntos de control satelitales.
- **Las tres vías de dato real de v2.2 están construidas pero sin ingerir.** Cada una tiene su puerta de disponibilidad y, mientras esté vacía, el sistema mantiene —etiquetado— el comportamiento curado o simulado anterior; ninguna cifra se inventa, pero **tampoco hay hoy dato real de estas tres fuentes**:
  - **Movilidad MITMA:** el cruce real de zonas está comprometido (`src/mobility/reference/`, 4 de 6 zonas resueltas) y la ruta de ingesta existe (`etl_mobility.py`), pero `src/mobility/snapshot/mobility.json` no se ha generado → la capacidad de carga usa el proxy curado `visitor_capacity_annual`.
  - **Zonas SCM multiescala:** `real_zones_exist()` está implementado, pero no hay exportaciones en `src/spatial_causality/zones/` → la atribución causal sigue empleando la simulación de decaimiento α.
  - **Serie temporal SVI:** se requieren ≥2 snapshots datados para una tendencia y solo se distribuye `2026-06` → no hay tendencia socioeconómica real.

  El estado de estas puertas se puede comprobar en cualquier momento con `src.reporting.cets_readiness.resolve_signals()`, que es la fuente de verdad de esta sección.
- **Costes unitarios de restauración (15,50 €/m):** calibrados con tarifas TRAGSA 2023; la cita de la resolución oficial por partida está pendiente de cierre y debe tratarse como estimación de orden de magnitud hasta entonces.
- **Capa económica = análisis prospectivo:** los ingresos, empleos proxy y el ratio coste-beneficio de la pestaña *Impacto Socioeconómico* son **escenarios condicionales** sobre `visitor_capacity_annual` (atributo curado) y parámetros de literatura — no economía observada ni predicción. Su naturaleza se etiqueta en la interfaz.

> **Auditoría de defensibilidad académica:** la clasificación completa de cada variable (Observada / Calculada / Estimada / Simulada), la matriz de trazabilidad, el inventario de multiplicadores con su sensibilidad, el diagnóstico de vulnerabilidades y el banco de preguntas de tribunal están en [`docs/defensibilidad_academica.md`](docs/defensibilidad_academica.md), y son consultables en vivo en la pestaña **8 · Fundamento y Trazabilidad** del observatorio.

---

## 10. Fundamento científico

El SNTO se apoya en una cadena causal documentada: **pisoteo recreativo → compactación del suelo → estrés hídrico → firma espectral medible** (caída de NDVI y NDMI). La compactación reduce la macroporosidad un 15–40 %, suprimiendo la disponibilidad de agua en zona radicular con independencia del clima.

Referencias clave: Roovers et al. (2004); Pickering & Mount (2010); Marion & Leung (2001); Cole & Monz (2002); Duxbury et al. (2021); Sheldon (2020).

Marco regulatorio español aplicable: Ley 42/2007 (Patrimonio Natural y Biodiversidad), Ley 26/2007 (Responsabilidad Medioambiental), TRAGSA Tarifas 2023.

El detalle completo está en el [Whitepaper](WHITEPAPER_SNTO_Architecture_Blueprint.md).

---

## 11. Fuentes y licencias de datos

Atribución obligatoria de cada fuente (también consultable en vivo en la pestaña **8 · Fundamento y Trazabilidad** del observatorio):

| Fuente | Proveedor | Licencia / condiciones | Atribución requerida |
|---|---|---|---|
| Sentinel-2 L2A (NDVI/NDMI) | ESA / Copernicus | Datos abiertos Copernicus (uso libre con atribución) | *Contiene datos Copernicus Sentinel-2 modificados (2025–2026)* |
| Cartografía de sendas y zonificación PRUG | OAPN (Red de Parques Nacionales) | Reutilización institucional con cita | *Cartografía oficial OAPN — Parque Nacional Sierra de Guadarrama* |
| Cartografía complementaria | OpenStreetMap | Open Database License (ODbL) | *© OpenStreetMap contributors* |
| Padrón municipal, EOATR | INE | Datos abiertos INE (reutilización con cita) | *Instituto Nacional de Estadística (INE)* |
| Economía municipal (hostelería, renta) | ALMUDENA — Comunidad de Madrid | Banco de Datos Municipal y Zonal (reutilización con cita) | *ALMUDENA, Instituto de Estadística de la Comunidad de Madrid* |

El **código** se distribuye para **uso académico y de investigación**. Los **datos** pertenecen a sus respectivos proveedores y conservan sus licencias; este proyecto solo los reutiliza con la atribución indicada.

---

## 12. Licencia / uso académico

Proyecto de investigación académica desarrollado en la **Universidad Complutense de Madrid (UCM)**. Supervisión académica: Carmen Mínguez · Susana Ramírez García (REGENERA).

El código se distribuye para uso académico y de investigación con atribución. Ver [`LICENSE`](LICENSE). Los datos pertenecen a sus respectivos proveedores y conservan sus licencias (ver §11).

### Cómo citar
**DOI permanente — todas las versiones (Zenodo):** [10.5281/zenodo.20818269](https://doi.org/10.5281/zenodo.20818269)

**DOI de la release estable v2.0.0:** [10.5281/zenodo.21472647](https://doi.org/10.5281/zenodo.21472647)

Fichero de cita: [`CITATION.cff`](CITATION.cff) · Contribuciones: [`CONTRIBUTING.md`](CONTRIBUTING.md)

### Qué se publica y cuándo

La política de publicación es **de dos pistas** y está documentada en
[`docs/PUBLICATION_STRATEGY.md`](docs/PUBLICATION_STRATEGY.md):

- **Pista A — artefactos de software:** siguen a las releases de código y se
  publican ya (Zenodo por tag, notas de release en
  [`docs/releases/`](docs/releases/), material de difusión en
  [`docs/kit_difusion.md`](docs/kit_difusion.md)).
- **Pista B — afirmaciones científicas:** siguen a la **evidencia**, no al
  código, y permanecen **congeladas hasta que la campaña de campo (#26) se
  ejecute**. Ninguna publicación de Pista A afirma validación satélite↔campo.

---

## Cliente móvil — Fase 1 + Fase 2

`mobile/` contiene una aplicación nativa Expo SDK 57 para iOS y Android.
**Fase 1** (ADR-013) implementó navegación tipada, estados de carga/error,
tokens visuales, el contrato de repositorio y una costura HTTP exclusivamente
`GET`. **Fase 2** (ADR-014) añade un repositorio HTTP real (`MobileHttpRepository`)
sobre el contrato de lectura de `/api/v2` (territorios, activos con centroide
de mapa, alertas por territorio) — construido y probado contra `fetch`
mockeado, **sin necesitar `/api/v2` desplegado**.

**Sigue por defecto en modo sintético**: todas las pantallas usan fixtures
locales marcadas como `synthetic` salvo que se active explícitamente
`EXPO_PUBLIC_SNTO_USE_REMOTE_API=true` — configurar solo la URL del API no
basta. Ninguna pantalla incorpora todavía autenticación, mapas, persistencia
offline, recursos Azure ni operaciones de escritura.

Consulte [`mobile/README.md`](mobile/README.md) para ejecutar y validar el
cliente, [`ADR-013`](docs/decisions/ADR-013-mobile-client.md) para el límite
arquitectónico de Fase 1, y [`ADR-014`](docs/decisions/ADR-014-mobile-read-api-contract.md)
para el contrato de lectura de Fase 2.

---

<div align="center">
<sub>SNTO v2.1.0.dev0 · Python ≥ 3.12 · 1059 tests passing · julio 2026</sub>
</div>
