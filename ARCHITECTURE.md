# SNTO — Arquitectura

Documento técnico de referencia. Lectura previa recomendada antes de entrar al
código. SNTO se compone de **dos pipelines arquitectónicamente separados** que
comparten los módulos analíticos de `src/`.

---

## 1. Vista de los dos pipelines

```
 PIPELINE A — GEOESPACIAL (datos reales)         PIPELINE B — INTELIGENCIA TERRITORIAL (demo)
 Sierra del Rincón (Madrid)                      Villuercas-Ibores-Jara (Extremadura)
 ───────────────────────────────────────         ─────────────────────────────────────────────
 ENTRADA                                          ENTRADA
   Sentinel-2 L2A (primavera + verano)              MultiYearAdapter (series calibradas con
   Capas vectoriales (senderos, ENP, MAB)           anomalías AEMET/Copernicus)
        │                                                │
        ▼                                                ▼
   etl_raster_processor   → NDVI/NDMI               run_phase3_report  → validación/calibración
   etl_vector_cleaner     → vectores limpios        run_phase4_report  → reconstrucción multi-anual
   etl_raster_intersection→ zonal stats             run_phase5_report  → TPI territorial
   calculate_delta_ehs    → EHS percentil           run_phase6_report  → escenarios TIS + contrafactual
   run_scm_operational    → SIG / SCM               run_phase7_report  → dashboard + 5 perfiles
   tis_engine             → presupuesto causal
        │                                                │
        ▼                                                ▼
 SALIDA                                           SALIDA
   EHS estacional, Delta EHS, clasificación         Informe estratégico 10 secciones,
   SCM, priority_score, presupuesto                 TPI/TIS, contrafactual, KPIs ejecutivos

                  ┌─────────────────────────────────────────────┐
 PUNTO DE         │  PostGIS: production_hiking_trails           │
 INTEGRACIÓN      │  (columnas avg_ndvi, avg_ndmi, ehs_spring,   │
 FUTURO           │   ehs_summer, delta_ehs, scm_classification, │
                  │   priority_score, presupuesto)               │
                  └─────────────────────────────────────────────┘
   El Pipeline A escribe indicadores reales aquí. Cuando esta tabla acumule
   series multi-anuales reales, el Pipeline B podrá consumirlas en lugar del
   MultiYearAdapter sintético.
```

---

## 2. Módulos `src/`

| Módulo | Descripción |
|---|---|
| `ingestion/` | Adaptadores de datos: `gee_adapter` (Google Earth Engine), `mock_generator`, `calibrated_adapter` (climatología calibrada por literatura), `multiyear_adapter` (reconstrucción multi-anual Extremadura). |
| `features/` | Índices espectrales (NDVI, NDMI) a partir de bandas. |
| `geospatial/` | Geometría (buffers, reproyección) y agregación zonal. |
| `time_series/` | Mann-Kendall + Sen's slope, descomposición armónica, climatología/anomalías, tendencia, volatilidad. |
| `risk_engine/` | EHS, componentes de riesgo, proxy de presión humana, `scorer`. |
| `spatial_causality/` | SCM: Spatial Impact Gradient y clasificación causal. |
| `decision_confidence/` | DCS de 5 dimensiones + data quality gate. |
| `territorial/` | Phase 5: TPI, portfolio, presupuesto, asignación. |
| `intervention/` | Phase 6: funciones de impacto, escenarios, TIS, reporter. |
| `platform/` | Phase 7: dashboard, madurez, stakeholders, playbooks, traductor, valor/ROI. |
| `calibration/` | Validador y rutinas de calibración. |
| `alerts/` | Motor de alertas y recomendaciones operativas. |
| `ranking/` | Ranker de activos. |
| `reporting/` | Constructor de informes. |
| `api/` | FastAPI: routers `evaluate`, `ranking`, `alerts`. |
| `assets/` | Modelos de dominio de los activos. |
| `config/` | `constants.py` (umbrales EHS/DCS/SCM) y `settings.py`. |

---

## 3. Decisiones de diseño

### 3.1 EHS operacional con percentiles de escena (P90/P10)

El EHS operacional ancla la referencia "sana" al **percentil 90** y el "suelo
degradado" al **percentil 10** de la distribución real de píxeles de **cada
escena Sentinel-2**, por estación e índice (`EHS_P_BASE=90`, `EHS_P_FLOOR=10` en
`src/config/constants.py`).

**Por qué, en lugar de un baseline universal:** un valor NDVI absoluto fijo no
es comparable entre escenas tomadas con distinta iluminación, fenología y
condiciones atmosféricas. Anclar a percentiles de la propia escena normaliza
frente a esas variaciones y mantiene la métrica interpretable y defendible para
comparación entre activos y entre estaciones. (La fórmula antigua basada en
NDVI×50 + NDMI×50 quedó reemplazada por este enfoque.)

### 3.2 El SCM calcula SIG desde rásteres reales

`run_scm_operational.py` calcula el Spatial Impact Gradient directamente de los
GeoTIFFs Sentinel-2, comparando la zona *core* del sendero (0–50 m) con el fondo
*landscape* (200–1000 m) en EPSG:25830:

```
SIG = (NDVI_landscape − NDVI_core) / max(NDVI_landscape, 0.01)
  SIG > 0.15 → LOCALIZED_IMPACT
  SIG < 0.07 → LANDSCAPE_DRIVEN
  else       → MIXED
```

**Por qué desde rásteres reales y no desde el MultiYearAdapter:** el diagnóstico
causal (¿degradación por uso del sendero o por forzamiento climático regional?)
exige el gradiente espacial real entre el corredor del sendero y su entorno. Ese
contraste solo existe en los píxeles reales de la imagen; un adaptador de series
sintéticas no contiene la estructura espacial necesaria para discriminarlo.

### 3.3 El DCS tiene data quality gate

El DCS suma 5 dimensiones (DQ 0–25, TR 0–25, SC 0–20, MS 0–15, SS 0–15). Tras
clasificar, se aplica un gate: si **DQ < 10** o **TR < 12**
(`DCS_MIN_DQ_FOR_ACTION`, `DCS_MIN_TR_FOR_ACTION`), entonces `can_act = False` y
una clasificación HIGH/VERY HIGH se degrada a MODERATE.

**Por qué:** sin el gate, valores altos de consistencia espacial, estabilidad de
modelo o fuerza de señal podrían inflar el DCS total aunque el dato fundacional
(cobertura temporal y de observaciones) sea insuficiente para una decisión
formal. El gate impide recomendar acción sobre una base de evidencia débil.

### 3.4 Por qué dos pipelines separados

El Pipeline A es **producción con datos reales** sobre un territorio acotado: hoy
dispone de 2 escenas (un año), suficientes para indicadores estacionales pero no
para series temporales largas. El Pipeline B es la **demostración completa del
sistema de gobernanza** (7 fases) y requiere profundidad temporal multi-anual,
que aún no existe como dato real. Separarlos permite que A entregue valor real
inmediato y que B demuestre la capacidad analítica completa sin bloquearse a la
espera de años de adquisición satelital. La tabla PostGIS (§1) es el punto de
integración previsto cuando A acumule histórico real.

---

## 4. Flujo de datos del Pipeline A

```
Sentinel-2 L2A (ZIP)        Capas vectoriales (GeoJSON)
        │                              │
        ▼                              ▼
 etl_raster_processor          etl_vector_cleaner
   B04/B08/B11 → clip            reproyección EPSG:4326
   NDVI, NDMI (GeoTIFF)          filtro a AOI Sierra del Rincón
        │                              │
        └──────────────┬───────────────┘
                       ▼
            etl_raster_intersection
            buffer 50 m por sendero (EPSG:25830)
            zonal stats → avg_ndvi, avg_ndmi  ──► PostGIS
                       │
                       ▼
            calculate_delta_ehs
            EHS_spring, EHS_summer (percentiles P90/P10)
            delta_ehs  ──► PostGIS
                       │
                       ▼
            run_scm_operational
            SIG_spring, SIG_summer → scm_classification  ──► PostGIS
                       │
                       ▼
            tis_engine
            priority_score = EHS·0.60 + traffic_index·0.40
            presupuesto con factor causal (NULL→MIXED, 0.5)  ──► PostGIS
```

---

## 5. Dependencias entre módulos del Pipeline B (Phase 1 → 7)

```
Phase 1  Ingestión + features + EHS base
            ingestion/ · features/ · risk_engine/
                       │
Phase 2-4  Series temporales y reconstrucción multi-anual
            time_series/ (Mann-Kendall, descomposición, anomalías)
            spatial_causality/ (SCM)  +  decision_confidence/ (DCS)
                       │
Phase 5  Inteligencia territorial
            territorial/ (TPI, portfolio, presupuesto, asignación)
                       │  consume EHS/DCS/SCM/tendencias por activo
Phase 6  Intervención y escenarios
            intervention/ (impacto, escenarios TIS, contrafactual)
                       │  consume el ranking territorial de Phase 5
Phase 7  Plataforma estratégica
            platform/ (dashboard, madurez, stakeholders, playbooks, valor)
                       │  consume Phase 5 + Phase 6
            run_phase7_report.py ejecuta Phase 5 → 6 → 7 y emite el
            informe de 10 secciones.
```

Cada fase consume las salidas de la anterior; `run_phase7_report.py` orquesta la
cadena completa.
