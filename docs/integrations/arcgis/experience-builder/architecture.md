# Arquitectura de la integración ArcGIS Experience Builder

> Fase 2A · documentación únicamente. Marcadores: **[Verificado] / [Propuesto] /
> [Desconocido] / [Diferido]**.

## A. Límite de producto: Streamlit vs Experience Builder

### A.1 Qué hace ya Streamlit (no duplicar)

**[Verificado]** La app Streamlit (`app.py` + `src/ui/`) es composición y
navegación sobre la **gramática de 4 capas** definida en `src/ui/navigation.py`:

- **Decidir** — Panorama ejecutivo, Acciones urgentes, Simulador de presupuesto,
  Impacto socioeconómico.
- **Diagnosticar** — Diagnóstico espacial, Catálogo de activos y sendas, Presión
  y capacidad de carga, Proyección de tendencia.
- **Evidenciar** — Evidencia satelital, Confianza e incertidumbre, Proveniencia
  y linaje.
- **Gobernar** — Metodología y auditoría, Informes y exportaciones,
  Configuración territorial.

Streamlit es un **tablero de decisión denso**: cálculo científico (EHS, DCS,
SCM, TPI, TIS), modulación por audiencia (`src/platform/views.py`), consumo de
persistencia in-process (`src/ui/services/`). Su mapa es **secundario**.

### A.2 Qué hace Experience Builder que Streamlit no hace

**[Propuesto]** Experience Builder aporta lo que Streamlit no puede:

1. Un **lienzo espacial interactivo** donde selección en Map ↔ List ↔ Table se
   sincroniza mediante *data/message actions* nativas.
2. Superposición de **geometría oficial OAPN** y **zonas PRUG** como capas
   navegables.
3. **Captura de campo Survey123** integrada en el mismo lienzo (el ciclo
   `alerta satelital → visita → registro` se cierra dentro de ArcGIS).
4. Uso offline vía Field Maps para el trabajo de campo real.

**Regla de no duplicación [Propuesto]:** la app EB **no** reproduce el tablero
ejecutivo de Streamlit. Reutiliza la gramática de 4 capas como esqueleto de
información, pero cada capa se re-expresa en clave **map-centric**, no como
copia de los módulos Streamlit.

### A.3 Por qué map-centric

**[Verificado]** El valor único de ArcGIS Online es el motor cartográfico y de
edición (Hosted Feature Layers, Web Map, Survey123, Field Maps). **[Propuesto]**
Por tanto la página central del MVP (Diagnosticar) es un **mapa a pantalla
completa** con List/Table/Filter acoplados; las demás páginas orbitan alrededor
de la selección espacial y del objeto transversal **Asset Detail**.

## B. Elección de arquitectura de integración

**[Verificado]** Opciones evaluadas en el informe de Fase 1 (§7):

| Opción | Descripción | Veredicto |
|---|---|---|
| **A** | ArcGIS Online nativo / nocode | **Recomendada para el MVP** |
| B | AGOL + publicación/actualización por script | Diferida (evolución opcional) |
| C | Experience Builder Developer Edition / widget personalizado | **Rechazada** (deuda de mantenimiento; no hay limitación demostrada) |
| D | Integración en vivo contra `/api/v2` | **Rechazada ahora** (ADR-012 no disparado) |

**[Propuesto] Decisión para Fase 2+: Opción A (nocode).** Justificación:

- El trabajo ya iniciado (Hosted Feature Layer publicada, Web Map guardada,
  XLSForm generado) es 100 % nocode.
- Ningún flujo del MVP requiere un widget personalizado (ver
  `page-blueprints.md`; cualquier carencia se registra como **[Diferido]**).
- La ciencia de SNTO **no se recalcula** en ArcGIS: ArcGIS es capa de captura y
  presentación (roadmap §3: «ArcGIS será una capa de captura y operación. No
  recalculará la ciencia de SNTO»).

## C. Modelo de contenido (resumen)

**[Propuesto]** Tipos de item ArcGIS del MVP (detalle en `content-inventory.md`):

- **Hosted Feature Layer** de activos (`SNTO_DEMO_PNSG_Assets`) — **[Verificado]**
  ya publicada (2 puntos, edición desactivada).
- **Hosted Feature Layer View** de solo lectura para compartir sin exponer la
  capa base — **[Propuesto]**.
- **Web Map** (`SNTO_DEMO_PNSG_FieldValidation_Map`) — **[Verificado]** ya
  guardada.
- **Survey123 form + feature service** — **[Verificado]** form generado, servicio
  por publicar (roadmap Fase 3).
- **Experience Builder app** — **[Propuesto]** por crear.
- **Dashboard**, **StoryMap** — **[Diferido]**.
- **Grupo privado** `SNTO — Validación de campo DEMO` — **[Verificado]** creado.
- Capa **PRUG / límite PNSG** — **[Propuesto, condicionado]** a licencia y
  procedencia documentadas.

## D. Modelo de actualización (crítico para la integridad)

**[Propuesto]** Distinción explícita de mecanismos por dominio:

| Dominio | Mecanismo | Etiqueta obligatoria en UI |
|---|---|---|
| Activos + tendencia satelital | **Snapshot regenerado manualmente** (via `scripts/export_gis.py` → overwrite de la Hosted Feature Layer) | «Snapshot · <fecha> · vX.Y.Z» |
| Observaciones de campo | **Append-only** (edición de Hosted Feature Layer vía Survey123/Field Maps) | «Captura de campo · estado QA» |
| Informes / exportaciones GIS | **Una sola vez / bajo demanda** (item enlazado o Embed) | «Generado el <fecha>» |

**Regla dura [Verificado por política]:** ningún snapshot se etiqueta como «en
vivo». El sello de fecha/versión (`source_version`, `calculated_at`) viaja con
cada feature y se muestra siempre.

## E. Relación con ADR-012 (¿EB dispara el despliegue de `/api/v2`?)

**[Verificado]** `docs/decisions/ADR-012.md`: `/api/v2` **no está desplegado**;
el disparador es «un consumidor externo concreto (integración GIS/BI, parque
socio, o cualquier … )».

**[Propuesto] Conclusión:** una app Experience Builder que consume **Hosted
Feature Layers estáticas (snapshots)** **NO** dispara ADR-012. Solo una
dependencia **en vivo** de EB hacia `/api/v2` (p. ej. un widget que hiciera
fetch a la API en cada carga) constituiría el «consumidor externo». El MVP evita
esa dependencia deliberadamente. Por tanto: **no se recomienda desplegar la API
solo por usar ArcGIS.**

## F. Qué queda fuera del MVP

**[Diferido]**

- Dashboard operativo y StoryMap narrativo (Fases 6–7 de la implementación).
- Cualquier compartición pública (hasta superar la QA de la Fase 5 del roadmap).
- Publicación por script / actualización programada (Opción B).
- Cliente en vivo de `/api/v2` (Opción D).
- Capas PRUG/límite sin licencia confirmada.
- Widgets personalizados (salvo brecha demostrada y registrada).
- Cualquier afirmación de validación científica o de acuerdo satélite↔campo.
- Dependencia duradera de una cuenta educativa personal sin propietario
  institucional, plan de transferencia y fecha de revisión de caducidad.
