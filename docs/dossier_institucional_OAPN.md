# SNTO — Observatorio de Inteligencia Territorial para el Parque Nacional Sierra de Guadarrama

**Dossier institucional · 2 páginas · v1.0 (junio 2026)**

Proyecto de investigación · Universidad Complutense de Madrid (UCM)
Autor: Soroush Karahrodi · Supervisión: Carmen Mínguez · Susana Ramírez García (REGENERA)
Repositorio: github.com/soroushkarahrodi79-oss/snto-smart-tourism-observatory · Dashboard en vivo: [URL Azure]

---

## 1. El problema

La mayoría de los espacios naturales protegidos gestionan el impacto del turismo de forma
**reactiva**: se actúa cuando la degradación de un sendero ya es visible sobre el terreno, cuando
la restauración es más cara y, a veces, cuando el daño es irreversible. Falta un instrumento que
(a) **detecte el estrés ecológico de forma temprana**, (b) **distinga si la causa es el uso
turístico o el clima** —porque la respuesta de gestión es distinta— y (c) traduzca cada hallazgo en
una **prioridad de inversión con presupuesto y nivel de confianza** que un gestor pueda defender.

## 2. La propuesta

El **SNTO (Smart Nature Tourism Observatory)** es un observatorio de código abierto que convierte
teledetección satelital **Sentinel-2** (programa Copernicus, datos abiertos) en inteligencia de
gestión accionable. No es un estudio externo sobre el Parque: se construye **sobre la cartografía
oficial OAPN del PNSG** (sendas y zonificación PRUG), por lo que es una **extensión analítica de
los propios datos del organismo**.

## 3. Qué hace, en concreto

| Capacidad | Qué resuelve |
|---|---|
| **Índice de Salud Ecológica (EHS)** calibrado por percentiles reales de cada escena (NDVI + NDMI) | Estado de cada sendero, comparable entre estaciones |
| **Atribución causal espacial (SCM)** — gradiente de impacto 0–50 / 50–200 / 200–1000 m | Separa degradación por **uso turístico** (localizada en la traza) de la **climática** (a escala de paisaje) |
| **Confianza de decisión (DCS)** con *data quality gate* | **No se emite recomendación de gasto sin evidencia suficiente** |
| **Priorización presupuestaria (TPI / TIS)** | Ordena dónde invertir y estima el coste de restauración y el de *no actuar* |
| **Capa socioeconómica (INE / ALMUDENA)** | Vincula el riesgo ambiental con empleo local en hostelería por municipio |

## 4. Resultados reales sobre el PNSG

Análisis ejecutado con **dos escenas Sentinel-2 reales** (primavera 2026-04-10 + verano 2025-08-10,
tile T30TVL) sobre **218 senderos** reconstruidos desde cartografía oficial:

- **17 de 73 senderos** muestran deterioro estacional activo (ΔEHS de degradación).
- Clasificación causal SCM: **27 localizados** (señal de uso) · **9 mixtos** · **37 a escala de paisaje** (señal climática).
- **Presupuesto indicativo de intervención: ~205.000 €**, modulado por el factor causal de cada tramo.
- Cobertura socioeconómica: **34 municipios** del entorno del Parque.

> **Honestidad metodológica:** con dos escenas se sostiene la señal estacional (ΔEHS), **no** una
> tendencia plurianual (Mann-Kendall requiere serie larga). El sistema lo declara explícitamente y
> trata estos resultados como **alerta temprana, no como intervención formal**. Las cifras
> socioeconómicas son **escenarios prospectivos**, no mediciones.

## 5. Madurez y rigor

- **474 tests automatizados** (suite verde), CI/CD separado del despliegue.
- Desplegado en la nube (Azure Container Apps), dashboard con tres vistas: técnica, gestor y
  auditoría científica.
- Etiquetado de procedencia visible en cada dato: **real / calibrado / sintético**.
- Documentación completa: arquitectura, whitepaper, protocolo de validación de campo, límites técnicos.

## 6. Alineación con el marco de gestión

El SNTO se diseña en sintonía con los marcos europeos de reporte de espacios protegidos
(Natura 2000 / EUROPARC / SISMOTUR) y con la **Carta Europea de Turismo Sostenible (CETS)**: cubre de
forma directa el **Principio 3** (protección del patrimonio natural) y el **Principio 10** (gestión de
flujos de visitantes), y de forma instrumental los Principios 1 y 2 (cooperación y elaboración de la
estrategia/plan de acción).

## 7. Qué pedimos / qué ofrecemos

**Ofrecemos** un observatorio funcional, abierto y documentado, ya operativo sobre el PNSG.
**Buscamos** una conversación con la Dirección del Parque y/o EUROPARC España para:

1. **Validar sobre el terreno** una muestra de los senderos señalados (campaña de campo ligera con
   penetrómetro/cobertura) que cierre la pseudo-validación.
2. Explorar el acceso a **series Sentinel-2 plurianuales** para activar la detección de tendencias.
3. Evaluar su encaje como instrumento de apoyo al **seguimiento del PRUG** y a una eventual
   candidatura/renovación **CETS**.

**Contacto:** Soroush Karahrodi · soroush.karahrodi79@gmail.com · vía UCM (REGENERA).
