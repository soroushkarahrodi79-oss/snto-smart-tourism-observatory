<div align="center">

# 🏔 SNTO — Smart Natural Tourism Observatory

**Inteligencia territorial de código abierto para la gobernanza regenerativa de destinos de turismo natural.**

De la teledetección Sentinel-2 a la decisión de inversión pública: indicadores ambientales calibrados, atribución causal de la degradación y priorización presupuestaria sobre el **Parque Nacional Sierra de Guadarrama (PNSG)**, primer territorio de la Red de Parques Nacionales (OAPN) integrado en el observatorio.

[![Tests](https://img.shields.io/badge/tests-454%20passing-brightgreen)](#8-tests)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.12-blue)](https://www.python.org/)
[![CI](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/ci.yml/badge.svg)](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/ci.yml)
[![Deploy](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/deploy-azure-container-apps.yml/badge.svg)](https://github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory/actions/workflows/deploy-azure-container-apps.yml)
[![Deploy target](https://img.shields.io/badge/deploy-Azure%20Container%20Apps-0078D4?logo=microsoftazure&logoColor=white)](#7-despliegue)
[![Status](https://img.shields.io/badge/estado-investigaci%C3%B3n%20activa-blue)](#1-estado-del-proyecto)
[![License](https://img.shields.io/badge/uso-acad%C3%A9mico-lightgrey)](#11-licencia--uso-acad%C3%A9mico)

**🔴 [Dashboard en vivo](https://snto-observatory.happyground-be027676.swedencentral.azurecontainerapps.io/)** · 📄 [Whitepaper](WHITEPAPER_SNTO_Architecture_Blueprint.md) · 🏗 [Arquitectura](ARCHITECTURE.md)

</div>

---

## 🎯 El problema en una frase

La mayoría de los espacios naturales protegidos gestionan el impacto del turismo de forma **reactiva**: actúan cuando la degradación ya es visible. El SNTO transforma ese paradigma en **gobernanza regenerativa proactiva** — detecta el estrés ecológico desde el satélite antes de que sea irreversible, distingue si la causa es el uso turístico o el clima, y traduce cada hallazgo en una **prioridad de inversión con presupuesto y nivel de confianza**.

> **Para evaluadores y revisores:** este repositorio es un proyecto de investigación académica de la **Universidad Complutense de Madrid (UCM)**: un observatorio que evalúa el estado de senderos y enclaves de turismo natural por teledetección satelital, detecta zonas de riesgo de degradación y prioriza la intervención con fórmulas financieras. Demuestra un pipeline geoespacial real sobre el **Parque Nacional Sierra de Guadarrama** (73 senderos analizados con cartografía oficial OAPN) y un sistema completo de inteligencia territorial de 7 fases, con capas de **andamiaje temporal (serie 2021–2026), trazabilidad/confianza del dato, baselines estratificados, incertidumbre del ranking y validación de campo**. **454 tests, CI separado del deploy, dos pipelines arquitectónicamente desacoplados.** La gobernanza se alinea con los marcos europeos de reporte de espacios protegidos (Natura 2000 / EUROPARC / SISMOTUR), validada inicialmente sobre la Reserva de la Biosfera Sierra del Rincón como piloto de calibración.

---

## 📸 Vista del dashboard

<div align="center">

![Dashboard ejecutivo SNTO](docs/screenshot-dashboard.png)

_Dashboard ejecutivo con 10 KPIs territoriales, mapa folium de activos y modelo de madurez de destino de 5 niveles. Desplegado en Azure Container Apps (Sweden Central)._

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
11. [Licencia / uso académico](#11-licencia--uso-académico)

---

## 1. Estado del proyecto

| Componente | Territorio | Estado |
|---|---|---|
| **Pipeline A — Geoespacial** | **Parque Nacional Sierra de Guadarrama (PNSG)** — territorio principal | ✅ Operacional con datos Sentinel-2 reales (2 escenas: primavera 2026 + verano 2025); **73 senderos** con cartografía oficial OAPN |
| **Pipeline A — Calibración metodológica** | Reserva de la Biosfera Sierra del Rincón (Madrid) | ✅ Piloto de validación del método (escenas reales propias) |
| **Pipeline B — Inteligencia territorial (7 fases)** | Villuercas-Ibores-Jara Geopark (Extremadura) | ✅ Demostración funcional completa sobre 20 activos sintéticos calibrados |
| **Dashboard ejecutivo** | PNSG | ✅ Desplegado en Azure Container Apps (scale-to-zero) |
| **CI/CD** | — | ✅ GitHub Actions → ACR build → roll Container App |
| **Tests** | — | ✅ 454 passing, 0 regresiones (suite verde, ver §8) |

El Pipeline A produce indicadores ambientales reales: el **PNSG** es el territorio principal del observatorio y la **Reserva de la Biosfera Sierra del Rincón** se conserva como piloto de calibración metodológica (valida el método sobre un segundo territorio con datos reales). El Pipeline B demuestra el sistema de gobernanza de extremo a extremo. Ambos pipelines están diseñados para integrarse cuando el Pipeline A disponga de series temporales multi-anuales reales. El observatorio se expandirá a más espacios de la **Red de Parques Nacionales (OAPN)** en fases posteriores.

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

### Pipeline A — Geoespacial de producción (datos reales)

```
Sentinel-2 L2A (ZIP, primavera + verano)
        │
        ▼
etl_raster_processor.py      → extrae B04/B08/B11, recorta, calcula NDVI/NDMI
        │
        ▼
etl_vector_cleaner.py        → reproyecta y filtra 7 capas vectoriales a la AOI
        │
        ▼
etl_raster_intersection.py   → buffer 50 m por sendero, zonal stats (rasterstats)
        │
        ▼
calculate_delta_ehs.py       → EHS estacional anclado a percentiles de escena
        │                       (P90/P10), Delta EHS primavera→verano
        ▼
run_scm_operational.py       → SIG calculado desde rásteres reales →
        │                       clasificación LOCALIZED / LANDSCAPE / MIXED
        ▼
tis_engine.py                → priority_score + presupuesto con factor causal
        │
        ▼
        PostGIS (production_hiking_trails)
```

**Produce:** EHS operacional calibrado por percentiles reales de escena (P90/P10 sobre la distribución de píxeles de cada imagen), Delta EHS estacional, clasificación SCM espacial calculada desde SIG real, y presupuesto de restauración modulado por factor causal.

### Pipeline B — Inteligencia territorial (7 fases, demostración)

```
MultiYearAdapter (series temporales calibradas con anomalías
inter-anuales documentadas de AEMET / Copernicus)
        │
        ▼
run_phase3_report.py   → validación y calibración (caso Masatrigo)
        ▼
run_phase4_report.py   → reconstrucción histórica multi-anual
        ▼
run_phase5_report.py   → inteligencia territorial (TPI, portfolio, 20 activos)
        ▼
run_phase6_report.py   → escenarios de intervención (TIS) + contrafactual
        ▼
run_phase7_report.py   → plataforma estratégica (dashboard 10 KPIs, 5 perfiles)
```

**Produce:** EHS histórico, detección de tendencias (Mann-Kendall), descomposición armónica, DCS con data quality gate, TPI territorial, escenarios de intervención (TIS), análisis contrafactual y un informe ejecutivo de 10 secciones para 5 perfiles de stakeholders.

> **Nota honesta:** `USE_MOCK_DATA` en `.env.example` controla únicamente el Pipeline A. El Pipeline B consume el `MultiYearAdapter` directamente; sus 20 activos son sintéticos, calibrados con anomalías climáticas documentadas, no datos satelitales reales.

---

## 3. Capacidades técnicas implementadas

- **EHS operacional** calibrado por percentiles de escena (P90 → referencia sana, P10 → suelo degradado) sobre la distribución real de píxeles de cada imagen Sentinel-2, por estación e índice (NDVI, NDMI).
- **SCM operacional** que calcula el Spatial Impact Gradient (SIG) directamente desde los rásteres Sentinel-2 reales (zonas core 0–50 m / near 50–200 m / landscape 200–1000 m en EPSG:25830) y clasifica LOCALIZED_IMPACT / LANDSCAPE_DRIVEN / MIXED — es decir, **separa la degradación causada por el uso turístico de la causada por el clima**.
- **DCS (Decision Confidence Score)** de 5 dimensiones (Data Quality, Temporal Robustness, Spatial Consistency, Model Stability, Signal Strength) con **data quality gate**: `can_act = False` si DQ < 10/25 o TR < 12/25. Ninguna recomendación de gasto se emite sobre evidencia insuficiente.
- **Análisis multi-anual:** test de Mann-Kendall (Sen's slope), descomposición armónica estacional, detección de anomalías inter-anuales y eventos de sequía.
- **TPI (Territorial Priority Index)** para ranking de activos y asignación de recursos en 4 tiers (atención inmediata → promoción activa).
- **TIS — escenarios de intervención** con simulación de impacto, optimizador de presupuesto y análisis contrafactual (coste de no actuar).
- **Dashboard ejecutivo** de 10 KPIs, modelo de madurez de destino de 5 niveles y 5 perfiles de stakeholders.
- **Andamiaje temporal (serie 2021–2026)** — `src/temporal/`: especificación declarativa de la serie (`PNSG_5Y` = 72 meses), **gate de validez Mann-Kendall** (qué inferencia sostiene cada profundidad: ΔEHS estacional vs tendencia) y **manifiesto de procedencia** por periodo. Ver [docs/temporal_series_design.md](docs/temporal_series_design.md).
- **Trazabilidad y confianza del dato** — `src/platform/provenance.py`: etiquetas visibles **dato real / calibrado / sintético**, fechas de escena reales, cobertura y *caveats* de confianza en el dashboard.
- **Baselines estratificados + incertidumbre** — `src/risk_engine/baselines.py` (P90/P10 por estrato ecológico con fallback) y `src/analysis/sensitivity.py` (banda de pesos, **ranking robusto** y Monte-Carlo). Ver [docs/baselines_uncertainty_design.md](docs/baselines_uncertainty_design.md).
- **Validación de campo / pseudo-validación** — `src/validation/`: esquema de observación de campo y métricas de concordancia satélite↔terreno (Spearman, contraste control-impacto BACI). Ver [docs/field_validation_protocol.md](docs/field_validation_protocol.md).
- **Dashboard de 3 vistas** (`src/platform/views.py`): técnica / gestor / auditoría científica, con la verbosidad de confianza adaptada a cada audiencia.

---

## 4. Stack tecnológico

- **Lenguaje:** Python ≥ 3.12
- **Geoespacial:** rasterio, rasterstats, shapely, geopandas
- **Datos:** Sentinel-2 SR L2A (Copernicus); Google Earth Engine (`gee_adapter.py` implementado, credenciales no incluidas)
- **Base de datos:** PostgreSQL / PostGIS (EPSG:25830 — ETRS89 / UTM 30N)
- **API / dashboard:** FastAPI, uvicorn, Streamlit, folium
- **Modelado / análisis:** NumPy, pydantic
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

- **454 passing, 0 regresiones, suite verde.**
- El antiguo fallo legacy `test_poor_data_scores_low` está resuelto: el data quality gate en `src/decision_confidence/assessor.py` (`can_act = False` si DQ < 10 o TR < 12) hace que el test pase.
- **CI (`ci.yml`)** ejecuta además `ruff` bloqueante sobre los módulos mantenidos (F0–F7), `ruff` informativo sobre el resto (deuda de lint en reducción), import smoke y `py_compile` de los entry points.

---

## 9. Honestidad sobre limitaciones

Esta sección es deliberada: la transparencia metodológica es parte del valor académico del proyecto.

- **Pipeline A — profundidad temporal:** 2 imágenes Sentinel-2 reales (primavera 2026 + verano 2025, un único ciclo anual). El resultado real para el PNSG es el **ΔEHS estacional** (señal de alerta temprana de presión antrópica), que es válido con dos escenas. El test de tendencia **Mann-Kendall se demuestra sobre el Pipeline B** como capacidad del sistema, no como hallazgo multi-anual del PNSG; la serie real 2021–2026 vía Google Earth Engine es trabajo en curso (su andamiaje científico-técnico es la siguiente fase del roadmap).
- **Pipeline B — naturaleza de los datos:** opera sobre 20 activos sintéticos calibrados con anomalías documentadas de AEMET / Copernicus. La calibración no sustituye a una validación con datos satelitales reales multi-anuales.
- **Baselines EHS por hábitat:** el **framework** de baselines estratificados ya existe (`src/risk_engine/baselines.py`, con fallback a percentil de escena), pero la estratificación operativa por altitud/orientación requiere un **DEM aún no integrado** y el EHS operacional usa hoy percentiles de escena. Es una brecha de datos, no de método.
- **Serie temporal 2021–2026:** el andamiaje (spec, gate Mann-Kendall, manifiesto) está montado y probado; **falta la ingesta real vía Google Earth Engine** (credenciales + cómputo). Hasta entonces, sobre el PNSG solo se afirma el ΔEHS estacional, no la tendencia.
- **Validación de campo:** el esquema y las métricas de concordancia (`src/validation/`) están listos; **falta la campaña de terreno** (penetrómetro, parcelas, control) o, en su defecto, la pseudo-validación con puntos de control satelitales.
- **Costes unitarios de restauración (15,50 €/m):** calibrados con tarifas TRAGSA 2023; la cita de la resolución oficial por partida está pendiente de cierre y debe tratarse como estimación de orden de magnitud hasta entonces.

---

## 10. Fundamento científico

El SNTO se apoya en una cadena causal documentada: **pisoteo recreativo → compactación del suelo → estrés hídrico → firma espectral medible** (caída de NDVI y NDMI). La compactación reduce la macroporosidad un 15–40 %, suprimiendo la disponibilidad de agua en zona radicular con independencia del clima.

Referencias clave: Roovers et al. (2004); Pickering & Mount (2010); Marion & Leung (2001); Cole & Monz (2002); Duxbury et al. (2021); Sheldon (2020).

Marco regulatorio español aplicable: Ley 42/2007 (Patrimonio Natural y Biodiversidad), Ley 26/2007 (Responsabilidad Medioambiental), TRAGSA Tarifas 2023.

El detalle completo está en el [Whitepaper](WHITEPAPER_SNTO_Architecture_Blueprint.md).

---

## 11. Licencia / uso académico

Proyecto de investigación académica independiente desarrollado en la **Universidad Complutense de Madrid (UCM)**. Territorio real principal: **Parque Nacional Sierra de Guadarrama** (Red de Parques Nacionales — OAPN). Territorio de calibración metodológica: **Reserva de la Biosfera Sierra del Rincón** (Madrid). Territorio de demostración de la inteligencia territorial: **Villuercas-Ibores-Jara Geopark** (Extremadura). Uso académico y de investigación.

Supervisión académica: Carmen Mínguez · Susana Ramírez García (REGENERA) — Universidad Complutense de Madrid.

---

<div align="center">
<sub>SNTO v0.1.0 · Python ≥ 3.12 · 454 tests passing · junio 2026</sub>
</div>
