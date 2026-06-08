# 🌍 Smart Natural Tourism Observatory (SNTO)

## Gobernanza Inteligente y Transición Regenerativa en la Reserva de la Biosfera Sierra del Rincón
### Hoja de Ruta para la Candidatura a la Fase I de la CETS

El **Smart Natural Tourism Observatory (SNTO)** es una plataforma abierta, espacialmente explícita y orientada a datos, diseñada para transitar la gestión de destinos turísticos naturales desde un paradigma de mantenimiento reactivo hacia un modelo proactivo de **Turismo Regenerativo**. Desarrollada en el contexto de la Reserva de la Biosfera Sierra del Rincón (Madrid, España) y su candidatura a la **Carta Europea de Turismo Sostenible (CETS) Fase I**, la plataforma operacionaliza el principio regenerativo central: la infraestructura turística debe restaurar activamente la capacidad de carga ecológica que consume.

> El documento de referencia técnica completo se encuentra en [`WHITEPAPER_SNTO_Architecture_Blueprint.md`](WHITEPAPER_SNTO_Architecture_Blueprint.md).

---

## 🎯 Objetivos del Proyecto

El SNTO responde a preguntas clave de gobernanza territorial:

- ¿Qué senderos presentan degradación ambiental atribuible a presión turística?
- ¿Los cambios observados por satélite se deben a impacto humano local o a forzamiento climático regional?
- ¿Qué activos requieren intervención inmediata y cuál es su presupuesto de restauración?
- ¿Dónde maximiza el retorno ecológico cada euro de inversión pública?
- ¿Qué activos pueden promocionarse con respaldo científico dentro de estrategias de turismo regenerativo?

---

## 🛰️ Fuentes de Datos y Stack Tecnológico

### Observación de la Tierra

| Fuente | Producto | Bandas utilizadas |
|--------|----------|-------------------|
| ESA Copernicus Sentinel-2 A/B | Nivel L2A (reflectancia superficial) | B4 (Rojo, 10 m) · B8 (NIR, 10 m) · B11 (SWIR1, 20 m→10 m) |

**Índices espectrales calculados:**
- **NDVI** — Normalized Difference Vegetation Index: capacidad fotosintética y biomasa aérea
- **NDMI** — Normalized Difference Moisture Index: contenido hídrico del dosel y compactación del suelo
- **NBR** — Normalized Burn Ratio: degradación por fuego e incidentes extremos

### Datos Territoriales y Vectoriales

- **OpenStreetMap** — geometrías de senderos, miradores y áreas recreativas
- **DEM SRTM** — elevación, pendiente y accesibilidad física
- **PostGIS** — almacenamiento espacial con índices GIST, consultas `ST_Length`, `ST_Buffer`

### Stack de Procesamiento

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Raster I/O | `rasterio` | ≥ 1.3 |
| Estadísticas zonales | `rasterstats` | ≥ 0.19 |
| DataFrames geoespaciales | `geopandas` + `shapely` | ≥ 1.0 / ≥ 2.0 |
| Base de datos | PostgreSQL + PostGIS | 16 + 3.4 |
| Dashboard interactivo | `streamlit` + `folium` | ≥ 1.35 / ≥ 0.16 |
| API REST | `fastapi` + `uvicorn` | ≥ 0.111 |
| Cómputo numérico | `numpy` | ≥ 1.26 |

---

## 🧪 Metodología Central

### Geometría espacial: buffers de 50 m en EPSG:25830

Todos los índices espectrales se agregan dentro de **buffers de 50 metros** generados alrededor de los ejes de los senderos, proyectados en **EPSG:25830 (ETRS89 / UTM Zona 30N)** — el sistema de referencia métrico oficial para la España peninsular. Este radio captura la zona de compactación del suelo inducida por el pisoteo (10–50 m desde el eje) y garantiza ≥ 250 píxeles por kilómetro de sendero para estadísticas zonales estables.

### Fórmulas de los índices

$$\text{NDVI} = \frac{\rho_{NIR} - \rho_{Red}}{\rho_{NIR} + \rho_{Red}} \qquad \text{NDMI} = \frac{\rho_{NIR} - \rho_{SWIR1}}{\rho_{NIR} + \rho_{SWIR1}}$$

---

## 📊 Environmental Health Score (EHS)

El **EHS** es el indicador operativo principal de SNTO. Convierte la señal espectral dual (NDVI + NDMI) en un **índice de degradación de 0 a 100** donde valores más altos indican mayor estrés ecológico — convenio inverso que alinea directamente el indicador con la lógica financiera del modelo de restauración.

### Fórmula operacional (`calculate_delta_ehs.py` + `tis_engine.py`)

$$D_{index} = \text{clamp}\!\left(\frac{\text{baseline}_{sano} - \text{observed}}{\text{baseline}_{sano} - \text{suelo}},\ 0,\ 1\right)$$

$$\boxed{\text{EHS} = 100 \times \left(W_{NDVI} \cdot D_{NDVI} + W_{NDMI} \cdot D_{NDMI}\right)}$$

Donde **baseline\_sano** = P90 y **suelo** = P10 de los píxeles válidos de la escena Sentinel-2, calculados excluyendo píxeles SCL no-vegetación y los propios buffers de sendero. EHS = 0 → observación igual o mejor que el baseline (sin estrés). EHS = 100 → degradación máxima (observación igual o peor que el suelo).

Los pesos ($W_{NDVI} = W_{NDMI} = 0.5$) y los percentiles (P90/P10) se configuran en `src/config/constants.py`.

### Motor EHS de investigación (implementación estadística completa — `src/risk_engine/ehs.py`)

$$\text{EHS}_{research} = 100 \times (1 - r_{composite})$$

| Componente de riesgo | Peso | Definición |
|---|---|---|
| Riesgo de baseline | 30 % | Distancia NDVI por debajo del baseline saludable (0.55) |
| Riesgo de tendencia | 25 % | Pendiente de Mann-Kendall significativa en declive (p < 0.05) |
| Riesgo de anomalía | 25 % | Fracción de meses con anomalía severa (\|z\| ≥ 1.5 σ) |
| Riesgo de recuperación | 10 % | Ratio NDVI post-sequía respecto al nivel pre-sequía |
| Riesgo de estabilidad | 10 % | Variabilidad residual interanual relativa a la media |

### Escala de clasificación EHS

| Rango EHS | Clase | Implicación de gestión |
|---|---|---|
| 0–39 | **Excelente** | Vegetación sobre baseline regional; elegible para promoción activa |
| 40–59 | **Buena** | Estrés estacional moderado; monitorización rutinaria |
| 60–74 | **Moderada** | Estrés crónico incipiente; monitorización anual recomendada |
| 75–89 | **Deficiente** | Degradación persistente; intervención preventiva activada |
| 90–100 | **Crítica** | Degradación severa; restauración inmediata mandatada |

### Delta EHS — Sistema de Alerta Temprana

$$\Delta\text{EHS} = \text{EHS}_{Verano} - \text{EHS}_{Primavera}$$

Un $\Delta\text{EHS}$ positivo por encima de la línea base climatológica indica que el estrés antropogénico está amplificando la sequía estacional — señal de alerta temprana antes de que se alcancen umbrales de degradación irreversible. Calculado por `calculate_delta_ehs.py`.

---

## 💰 Modelo Financiero-Ecológico (TIS Engine)

El **Tourism Impact Score Engine** (`tis_engine.py`) traduce el EHS en presupuestos de restauración accionables:

### Puntuación de prioridad

$$P_{score} = \text{EHS} \times 0.60 + \text{traffic\_index} \times 0.40$$

Ponderación que privilegia la urgencia ecológica (60 %) sobre la presión de visitantes (40 %).

### Presupuesto dinámico de restauración

$$\boxed{B_{restauración} = L_m \times 15{,}50 \frac{\text{EUR}}{m} \times \frac{P_{score}}{100}}$$

El coste unitario de **15,50 €/m lineal** está calibrado sobre las tarifas oficiales TRAGSA 2023:

| Componente | Fuente | Coste |
|---|---|---|
| Descompactación del suelo (escarificación mecánica) | TRAGSA Cap. 15 — Trabajos forestales | 4,20 €/m |
| Control de erosión (fajinas y albarradas) | TRAGSA Cap. 8 — Obras hidráulicas | 6,80 €/m |
| Revegetación autóctona (*Quercus*, *Cistus*, *Rosmarinus*) | Plan Nacional de Transición Ecológica 2021–2025 | 4,50 €/m |
| **Total** | | **15,50 €/m** |

Los senderos con $P_{score} \leq 60$ reciben asignación €0; su estado se mantiene mediante monitorización rutinaria.

---

## 🧠 Módulos Analíticos Avanzados

### Spatial Causality Module (SCM) — `src/spatial_causality/analyzer.py`

Distingue degradación **antropogénica (localizada)** de estrés **climático (territorial)** mediante el análisis del Gradiente de Impacto Espacial (SIG) en tres zonas concéntricas:

| Zona | Radio | Interpretación |
|---|---|---|
| Core | 0–50 m | Huella directa del sendero |
| Near | 50–200 m | Entorno inmediato |
| Landscape | 200–1000 m | Background regional |

$$\text{SIG} = \frac{\text{NDVI}_{landscape} - \text{NDVI}_{core}}{\text{NDVI}_{landscape}}$$

- **SIG > 0.15** → `LOCALIZED_IMPACT` (presión turística dominante)
- **SIG < 0.07** → `LANDSCAPE_DRIVEN` (forzamiento climático dominante)
- **0.07–0.15** → `MIXED`

### Decision Confidence Score (DCS) — `src/decision_confidence/assessor.py`

Evalúa la **fiabilidad de cada recomendación** (0–100) antes de activar ninguna obligación presupuestaria. Activos con DCS < 55 son desviados a protocolos de recopilación de evidencia en lugar de restauración completa.

| DCS | Clasificación | Acción |
|---|---|---|
| 80–100 | Muy alta confianza | Presupuesto completo asignado |
| 60–79 | Alta confianza | Intervención aprobada |
| 40–59 | Confianza moderada | Monitorización adicional requerida |
| 0–39 | Baja confianza | Solo recopilación de evidencia |

### Territorial Priority Index (TPI) — `src/territorial/tpi.py`

Clasifica cada activo en una **cartera territorial de cuatro niveles** para la priorización de inversión:

$$\text{TPI} = U_{condition}\ [0\text{–}40] + S_{evidence}\ [0\text{–}25] + V_{strategic}\ [0\text{–}20] + C_{causality}\ [0\text{–}15]$$

| Nivel | Clasificación | Criterio |
|---|---|---|
| Tier 1 | Atención Inmediata | Alerta crítica/urgente O EHS < 45 |
| Tier 2 | Acción Preventiva | TPI ≥ 38 y EHS < 75 |
| Tier 3 | Monitorización Rutinaria | Resto de activos |
| Tier 4 | Oportunidad de Promoción | EHS ≥ 75, DCS ≥ 55, tendencia estable |

---

## 🔄 Pipeline de Datos: Del Satélite al Dashboard

```
[ETAPA 1: INGESTIÓN]    Sentinel-2 L2A ZIP (.SAFE) → B04, B08, B11 JP2
          ↓
[ETAPA 2: PROCESO]      Reproyección EPSG:25830 → NDVI/NDMI GeoTIFF (LZW)
          ↓
[ETAPA 3: INTEGRACIÓN]  Estadísticas zonales (50 m buffers) → PostGIS → TIS Engine
          ↓
[ETAPA 4: SERVICIO]     Dashboard Streamlit → Mapa + KPIs + Tabla de prioridades
```

**GeoTIFFs producidos en `data/clean_assets/`:**
- `clean_S2_B04_red.tif` · `clean_S2_B08_nir.tif` · `clean_S2_B11_swir.tif`
- `clean_S2_NDVI.tif` · `clean_S2_NDMI.tif`

---

## 📊 Dashboard Interactivo

```bash
streamlit run app.py
```

El dashboard (`app.py`) proporciona una interfaz de soporte a la decisión para gestores de parques y evaluadores de la CETS:

- **Tarjetas KPI:** senderos analizados · senderos críticos · presupuesto total de restauración · volumen máximo de visitantes
- **Mapa Folium:** senderos coloreados por estado de salud (verde: EHS ≤ 60 · rojo: EHS > 60), centrado en Sierra del Rincón (41.14°N, −3.52°E)
- **Tabla de intervención prioritaria:** top 10 senderos por puntuación de prioridad descendente con coloración gradiente RdYlGn
- **Panel temporal:** visualización de ΔEH (Verano − Primavera) por sendero

---

## 🏗️ Arquitectura del Proyecto

```
snto-smart-tourism-observatory/
├── src/
│   ├── ingestion/          # Adaptadores GEE, calibrado, multi-año, mock
│   ├── features/           # Extracción NDVI/NDMI/NBR (spectral.py)
│   ├── geospatial/         # Buffers, estadísticas zonales, geometría
│   ├── time_series/        # Mann-Kendall, z-score, descomposición armónica
│   ├── risk_engine/        # EHS, componentes de riesgo, presión humana
│   ├── spatial_causality/  # SCM — análisis de gradiente espacial (SIG)
│   ├── decision_confidence/# DCS — fiabilidad de recomendaciones
│   ├── territorial/        # TPI, asignador de presupuesto, cartera
│   ├── intervention/       # Modelado de impacto y escenarios
│   ├── platform/           # Dashboard ejecutivo, madurez, stakeholders
│   ├── api/                # Endpoints FastAPI (evaluate, ranking, alerts)
│   └── config/             # Constantes, settings, variables de entorno
├── data/
│   ├── raw_assets/raster_data/   # ZIP Sentinel-2 L2A
│   └── clean_assets/             # GeoTIFFs procesados
├── tests/                        # 27 módulos de test, 400+ casos
├── app.py                        # Dashboard Streamlit
├── db_production_seeder.py       # Inicialización PostgreSQL/PostGIS (paso 0)
├── etl_raster_processor.py       # Extracción de bandas, NDVI/NDMI (paso 1)
├── etl_vector_cleaner.py         # Limpieza de geometrías OSM (paso 2)
├── etl_raster_intersection.py    # Estadísticas zonales → PostGIS (paso 3)
├── calculate_delta_ehs.py        # EHS estacional percentil-anclado (paso 4)
├── run_scm_operational.py        # SIG espacial real → scm_classification (paso 5)
├── tis_engine.py                 # Motor TIS: prioridad + presupuesto causal (paso 6)
└── WHITEPAPER_SNTO_Architecture_Blueprint.md  # Documento de referencia técnica
```

---

## 📦 Scripts de Ejecución

### Pipeline ETL completo

Orden de ejecución obligatorio. Cada script depende de las salidas del anterior.

```bash
# 0. Inicializa la base de datos (una sola vez por entorno)
python db_production_seeder.py

# 1. Procesa los rasters Sentinel-2: bandas crudas → NDVI/NDMI GeoTIFF
python etl_raster_processor.py

# 2. Limpia y valida las geometrías vectoriales OSM
python etl_vector_cleaner.py

# 3. Estadísticas zonales (avg_ndvi, avg_ndmi) → PostGIS
python etl_raster_intersection.py

# 4. EHS estacional anclado a percentiles reales de cada escena
#    Escribe: ehs_spring, ehs_summer, delta_ehs
python calculate_delta_ehs.py

# 5. Gradiente de Impacto Espacial desde rasters reales
#    Escribe: scm_classification, scm_sig_spring, scm_sig_summer
python run_scm_operational.py

# 6. Motor TIS: prioridad + presupuesto bruto + presupuesto causal (SCM)
#    Escribe: priority_score, needs_intervention, tis_budget_eur, tis_budget_causal_eur
python tis_engine.py
```

### Dashboard

```bash
streamlit run app.py
```

### API REST

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Informes de validación y análisis

```bash
python run_masatrigo_validation.py   # Validación caso piloto
python run_phase3_report.py          # Validación inicial y calibración
python run_phase4_report.py          # Reconstrucción multianual (4–5 años)
python run_scm_report.py             # Módulo de causalidad espacial
python run_dcs_report.py             # Puntuación de confianza de decisión
python run_phase5_report.py          # Análisis de inteligencia territorial
python run_phase6_report.py          # Impacto de intervención y escenarios
python run_phase7_report.py          # Plataforma estratégica completa
```

---

## 🚀 Instalación

```bash
git clone <repository_url>
cd snto-smart-tourism-observatory
pip install -r requirements.txt
cp .env.example .env
# Editar .env con credenciales PostgreSQL y, opcionalmente, Google Earth Engine
```

### Variables de entorno clave (`.env.example`)

```bash
SNTO_DB_HOST=localhost
SNTO_DB_PORT=5432
SNTO_DB_NAME=snto
SNTO_DB_USER=postgres
SNTO_DB_PASS=TU_CONTRASEÑA_AQUI
USE_MOCK_DATA=true          # false para usar Google Earth Engine real
```

### Inicializar la base de datos

```bash
python db_production_seeder.py
```

---

## 🧪 Tests

```bash
pytest tests/ -v --cov=src
```

El proyecto incluye 27 módulos de test con más de 400 casos que cubren: EHS, SCM, DCS, análisis temporal, scoring de riesgo, modelos de activos y endpoints de API.

---

## 📋 Caso Piloto: Sendero de Masatrigo (Badajoz, Extremadura)

| Indicador | Resultado |
|---|---|
| Environmental Health Score (EHS) | 77.7 / 100 |
| Clasificación | GOOD |
| Causalidad (SCM) | Degradación 2022 asociada a sequía regional extrema |
| Recuperación | Completa en 2023 |
| Tendencia | Sin deterioro estructural significativo |
| Recomendación | Monitorización periódica y promoción responsable |

---

## 🌿 Contribución a la CETS Fase I

El SNTO satisface directamente los tres requisitos de evidencia de la certificación CETS Fase I:

1. **Sistema de monitorización operacional:** el EHS derivado de satélite proporciona indicadores ambientales continuos, auditables y actualizables mensualmente.
2. **Minimización de la huella ecológica:** el modelo financiero-ecológico crea un vínculo jurídicamente defendible entre visitación turística, degradación medible e inversión de restauración obligatoria.
3. **Dashboard orientado a stakeholders:** la interfaz Streamlit traduce datos satelitales complejos en KPIs y mapas accesibles para gestores de parques, stakeholders municipales y evaluadores de la CETS.

---

## 🔭 Visión y Escalabilidad

La arquitectura del SNTO es directamente transferible a cualquier:
- Reserva de Biosfera europea con cobertura Sentinel-2
- Territorio certificado o candidato a la CETS
- Espacio natural protegido con infraestructura de senderos digitalizada en OpenStreetMap

El stack completo (Python, PostGIS, Streamlit) no requiere licencias propietarias y los datos Sentinel-2 son accesibles públicamente a través del Copernicus Open Access Hub.

**Usuarios objetivo:** administraciones públicas · observatorios turísticos · gestores de espacios naturales · organismos de planificación territorial · iniciativas de turismo inteligente y regenerativo.

---

## 📄 Licencia

Este proyecto se distribuye con fines académicos, de investigación y desarrollo de soluciones de inteligencia territorial para la gestión sostenible del turismo.

**Versión:** 0.1.0 | **Python:** ≥ 3.12 | **Contacto:** soroush.karahrodi79@gmail.com
