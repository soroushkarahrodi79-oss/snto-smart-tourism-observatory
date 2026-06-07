# 🌍 Smart Tourism Observatory (SNTO)

## Gobernanza Inteligente y Transición Regenerativa para Destinos Turísticos

Smart Tourism Observatory (SNTO) es una plataforma de inteligencia territorial diseñada para monitorizar, analizar y apoyar la toma de decisiones sobre activos turísticos naturales mediante el uso combinado de teledetección satelital, análisis geoespacial, Open Data y modelos de evaluación ambiental.

El sistema permite evaluar el estado de senderos, miradores, áreas recreativas y otros recursos turísticos mediante indicadores ambientales derivados de imágenes Sentinel-2, análisis temporal multianual y modelos de interpretación espacial orientados a la gestión pública.

---

# 🎯 Objetivos del Proyecto

SNTO ha sido desarrollado para responder a preguntas clave de gestión territorial:

* ¿Qué activos turísticos presentan signos de deterioro ambiental?
* ¿Los cambios observados se deben a presión humana o a factores climáticos?
* ¿Qué lugares requieren seguimiento prioritario?
* ¿Dónde deberían concentrarse las inversiones públicas?
* ¿Qué activos pueden promocionarse de forma segura dentro de estrategias de turismo sostenible?

---

# 🛰️ Tecnologías y Fuentes de Datos

### Observación de la Tierra

* Sentinel-2 (Copernicus Programme)
* Índices espectrales:

  * NDVI (Vegetación)
  * NDMI (Humedad)
  * NBR (Riesgo de degradación e incendios)

### Datos Territoriales

* OpenStreetMap
* Modelos Digitales de Elevación (DEM)
* Cartografía de activos turísticos

### Datos Climáticos

* Series históricas y anomalías climáticas
* Indicadores de sequía y recuperación ambiental

---

# 🧠 Capacidades Actuales

## 1. Monitorización Ambiental Multianual

Reconstrucción histórica de indicadores ambientales mediante series temporales de hasta 5 años.

### Funcionalidades

* Tendencias temporales
* Detección de anomalías
* Evaluación de resiliencia ambiental
* Análisis de recuperación post-sequía

---

## 2. Environmental Health Score (EHS)

Indicador compuesto (0–100) que evalúa la salud ambiental de cada activo turístico considerando:

* Estado de la vegetación
* Tendencia temporal
* Frecuencia de anomalías
* Estabilidad ecológica
* Capacidad de recuperación

---

## 3. Spatial Causality Module (SCM)

Módulo diseñado para distinguir entre:

### Impacto Localizado

Posible influencia de actividades humanas o presión turística.

### Impacto de Escala Territorial

Cambios explicados por factores climáticos o ambientales regionales.

El análisis se realiza mediante la comparación de señales ambientales en diferentes zonas espaciales alrededor del activo.

---

## 4. Decision Confidence Score (DCS)

Sistema de evaluación de confianza para la toma de decisiones.

Cada recomendación emitida por SNTO incorpora una puntuación de confianza basada en:

* Calidad de los datos
* Robustez temporal
* Consistencia espacial
* Estabilidad del modelo
* Intensidad de la señal observada

Esto permite que las administraciones públicas conozcan no solo la recomendación, sino también el nivel de certeza asociado.

---

# 📊 Caso Piloto: Masatrigo Trail (Badajoz)

El activo piloto utilizado para la validación del sistema fue el sendero de Masatrigo (Extremadura).

### Principales hallazgos

* No existe evidencia estadísticamente significativa de degradación estructural.
* La disminución observada en 2022 estuvo asociada a una sequía extrema regional.
* El ecosistema mostró una recuperación completa durante 2023.
* El activo mantiene una buena integridad ambiental.

### Resultados

* Environmental Health Score (EHS): 77.7 / 100
* Clasificación: GOOD
* Tendencia: Sin deterioro significativo
* Recomendación: Monitorización periódica y promoción responsable

---

# 🏗️ Arquitectura del Proyecto

```text
src/
├── assets/
├── ingestion/
├── geospatial/
├── features/
├── time_series/
├── calibration/
├── risk_engine/
├── ranking/
├── alerts/
├── reporting/
├── api/
└── config/
```

---

# 📦 Scripts Principales

### Validación

```bash
python run_masatrigo_validation.py
```

Valida la consistencia de los resultados obtenidos con datos observados.

### Evaluación Fase 3

```bash
python run_phase3_report.py
```

Genera el informe de validación inicial y calibración del sistema.

### Evaluación Fase 4

```bash
python run_phase4_report.py
```

Reconstrucción multianual, análisis de tendencias y evaluación ambiental histórica.

### Spatial Causality Module

```bash
python run_scm_report.py
```

Analiza si los cambios observados tienen origen local o territorial.

### Decision Confidence Score

```bash
python run_dcs_report.py
```

Calcula el nivel de confianza asociado a las recomendaciones generadas.

---

# 🛠️ Instalación

Clonar el repositorio:

```bash
git clone <repository_url>
cd SNTO
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Configurar variables de entorno:

```bash
cp .env.example .env
```

---

# 🚀 Visión del Proyecto

SNTO no pretende ser únicamente una herramienta de análisis geoespacial.

La visión a largo plazo es construir una plataforma de inteligencia territorial capaz de apoyar la gestión sostenible de destinos turísticos mediante información objetiva, transparente y científicamente defendible.

El sistema está orientado a:

* Administraciones públicas
* Observatorios turísticos
* Gestores de espacios naturales
* Organismos de planificación territorial
* Iniciativas de turismo inteligente y regenerativo

---

# 📄 Licencia

Este proyecto se distribuye con fines académicos, de investigación y desarrollo de soluciones de inteligencia territorial para la gestión sostenible del turismo.
