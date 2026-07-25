# SNTO — Observatorio de Inteligencia Territorial para el Parque Nacional Sierra de Guadarrama

**Dossier institucional · 2 páginas**

> Las secciones §4, §5 y §6 se **generan** desde los datos vivos del observatorio
> (`python scripts/build_dossier.py`); el resto es prosa editada a mano. CI
> verifica que las cifras publicadas siguen coincidiendo con el sistema.

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

<!-- SNTO:AUTO:resultados -->
- **46 de 218 senderos** muestran deterioro estacional activo (ΔEHS de degradación).
- Clasificación causal SCM: **24 localizados** (señal de uso) · **29 mixtos** · **165 a escala de paisaje** (señal climática).
- **Presupuesto indicativo de intervención: 1.435.721 €**, modulado por el factor causal de cada tramo.
- Salud ecológica media en verano: **88.5/100** sobre 1.035 km analizados.
- Zona PRUG de atención prioritaria (mayor protección con deterioro activo): **Zona de Uso Restringido**.
- Cobertura socioeconómica: **34 municipios** del entorno del Parque.
<!-- /SNTO:AUTO:resultados -->

> **Honestidad metodológica:** con dos escenas se sostiene la señal estacional (ΔEHS), **no** una
> tendencia plurianual (Mann-Kendall requiere serie larga). El sistema lo declara explícitamente y
> trata estos resultados como **alerta temprana, no como intervención formal**. Las cifras
> socioeconómicas son **escenarios prospectivos**, no mediciones.

## 5. Madurez y rigor

<!-- SNTO:AUTO:madurez -->
- Suite de tests automatizados **verde** en cada cambio, con CI/CD separado del despliegue (el conteo vivo está en el README del repositorio).
- Desplegado en la nube (Azure Container Apps), panel con cuatro capas de decisión y tres vistas por audiencia.
- Etiquetado de procedencia visible en cada dato: **real / calibrado / simulado / sintético**.
- Estado de las vías de dato real (comprobado en vivo): serie satelital sí · movilidad MITMA **aún no** · zonas SCM multiescala **aún no** · serie socioeconómica **aún no**.
- Parcelas de campo con medición registrada: **0** — la campaña de validación (#26) sigue pendiente, por lo que **no se afirma validación de campo**.
- Documentación completa: arquitectura, whitepaper, protocolo de validación de campo, límites técnicos.
<!-- /SNTO:AUTO:madurez -->

## 6. Alineación con el marco de gestión

<!-- SNTO:AUTO:marco -->
El SNTO se diseña en sintonía con los marcos europeos de reporte de espacios protegidos (Natura 2000 / EUROPARC / SISMOTUR) y con la **Carta Europea de Turismo Sostenible (CETS)**. La cobertura declarada por principio, con la evidencia que la respalda hoy:

- **Principio 3** (Proteger y potenciar el patrimonio natural y cultural): cubierto de forma directa.
- **Principio 10** (Controlar y seguir los flujos de turistas): cubierto de forma parcial — sin dato real hoy.
- **Principio 1** (Hacer partícipes a los implicados en el turismo): cubierto de forma instrumental — sobre dato calibrado.
- **Principio 2** (Elaborar y aplicar una estrategia y un plan de acción): cubierto de forma parcial — sobre dato calibrado.

La correspondencia completa con los componentes del dosier de la Fase I y los 10 principios —incluidos los que quedan **fuera del alcance** de un sistema de evidencia teledetectada— se genera desde el propio observatorio (módulo «Informes y exportaciones»).
<!-- /SNTO:AUTO:marco -->

## 7. Qué pedimos / qué ofrecemos

**Ofrecemos** un observatorio funcional, abierto y documentado, ya operativo sobre el PNSG.
**Buscamos** una conversación con la Dirección del Parque y/o EUROPARC España para:

1. **Validar sobre el terreno** una muestra de los senderos señalados (campaña de campo ligera con
   penetrómetro/cobertura) que cierre la pseudo-validación.
2. Explorar el acceso a **datos reales de afluencia** (aforos de sendero, conteos de visitantes o
   registros de uso público). Es hoy la brecha principal: la capacidad de carga y el seguimiento de
   flujos se apoyan en una estimación curada, no en una medición.
3. Evaluar su encaje como instrumento de apoyo al **seguimiento del PRUG** y a una eventual
   candidatura/renovación **CETS**.

**Contacto:** Soroush Karahrodi · soroush.karahrodi79@gmail.com · vía UCM (REGENERA).
