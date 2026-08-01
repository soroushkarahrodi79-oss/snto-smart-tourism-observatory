# SNTO · Integración ArcGIS Experience Builder — Paquete de arquitectura (Fase 2A)

**Estado del paquete:** documentación únicamente (Fase 2A). No cambia código,
tests, despliegue, persistencia, API ni ningún item de ArcGIS Online.

**Rama:** `docs/arcgis-experience-builder-architecture` (worktree aislado).
**Base auditada:** HEAD `33e9041` (`feat/v3.0-postgis-geometry`), repo en
`2.1.0.dev0`, último tag `v2.0.0`.

---

## 1. Qué define este paquete

El MVP aprobado:

> **«SNTO · Espacio de decisión PNSG — DEMO académico»**

**Rol primario (Verificado como decisión de producto):** un **espacio de
trabajo GIS-facing privado** para el piloto PNSG y la evidencia de campo,
dirigido a personal técnico, investigadores y demostraciones controladas de
gestión.

**No es** (límites explícitos):

- ❌ un portal público de transparencia;
- ❌ un reemplazo de la aplicación Streamlit;
- ❌ un sistema de validación científica completado;
- ❌ un cliente de API en vivo (`/api/v2` sigue sin desplegar — ver ADR-012);
- ❌ un despliegue de producción empresarial;
- ❌ una aplicación con widget personalizado (Developer Edition).

## 2. Por qué existe (reconciliación con el trabajo previo)

Este paquete **extiende y normaliza** el trabajo ArcGIS ya auditado; **no lo
sustituye ni lo ignora**. Ese trabajo previo existe como material local
verificado (respaldado externamente en
`SNTO_BACKUPS/arcgis-field-validation-demo-2026-07-29/`):

| Archivo fuente auditado | Rol |
|---|---|
| `docs/arcgis/field-validation-demo-roadmap.md` | Hoja de ruta operativa por fases (0–7) de la **captura de campo**. Autoridad sobre el flujo Survey123 / Field Maps. |
| `arcgis/demo/pnsg/README.md` | Contrato de intercambio y advertencias de evidencia. |
| `arcgis/demo/pnsg/pilot_assets.geojson` | Capa de 2 activos piloto ya publicada como Hosted Feature Layer. |
| `arcgis/demo/pnsg/field_observations_seed.csv` | Semilla de 4 parcelas `planned`/`missing` (no observaciones). |
| `arcgis/demo/pnsg/SNTO_DEMO_PNSG_FieldValidation.xlsx` | XLSForm de Survey123 ya generado. |

**División de responsabilidades entre los dos documentos:**

- `docs/arcgis/field-validation-demo-roadmap.md` → **cómo se captura** la
  evidencia de campo (Survey123, Field Maps, importación a SNTO). Sigue siendo
  la autoridad de ese flujo.
- Este paquete (`docs/integrations/arcgis/experience-builder/`) → **cómo se
  presenta y decide** sobre la evidencia en una app Experience Builder
  nocode, y el contrato de datos que lo hace posible. La app EB corresponde a
  la **Fase 5** de aquella hoja de ruta, aquí desarrollada en profundidad.

No se crea una segunda estructura ArcGIS competidora: este paquete referencia
el roadmap existente y añade la capa de arquitectura EB que allí solo estaba
esbozada.

## 3. Contenido del paquete

| Documento | Propósito |
|---|---|
| [`README.md`](README.md) | Este índice, definición del MVP, leyenda de marcadores. |
| [`architecture.md`](architecture.md) | Límite de producto Streamlit↔EB, por qué es nocode y map-centric, modelo de actualización, relación con ADR-012, qué queda fuera del MVP. |
| [`content-inventory.md`](content-inventory.md) | Modelo de contenido ArcGIS: existente/verificado, implícito/no verificado, por crear, por esperar. |
| [`data-contract.md`](data-contract.md) | Campos canónicos, tipos, nulabilidad, alias, dominios; mapeo `asset_id` string ↔ FK numérica; `plot_id`/`GlobalID`/`OBJECTID`; CRS; null vs cero. |
| [`page-blueprints.md`](page-blueprints.md) | Blueprint por página (Decidir/Diagnosticar/Evidenciar/Gobernar) + Asset Detail. |
| [`design-system.md`](design-system.md) | Tipografía, jerarquía, badges de evidencia, popups, alternativas no basadas en color. |
| [`survey123-integration.md`](survey123-integration.md) | Estado conocido/desconocido, URL prefill, privacidad GPS/fotos, brecha de esquema con persistencia. |
| [`build-playbook.md`](build-playbook.md) | Plan click-by-click futuro, operado por el propietario, con puertas de aprobación. |
| [`qa-checklist.md`](qa-checklist.md) | Criterios de aceptación testables del MVP. |
| [`item-registry.example.yaml`](item-registry.example.yaml) | Placeholders seguros; **sin** Item IDs reales ni secretos. |

## 4. Leyenda de marcadores (usada en todo el paquete)

Cada afirmación relevante se marca como:

- **[Verificado]** — respaldado por un archivo/esquema real del repositorio o por
  el roadmap ya auditado.
- **[Propuesto]** — recomendación de diseño de esta fase, aún no implementada.
- **[Desconocido / Requiere input humano]** — metadato de ArcGIS Online que solo
  el propietario puede aportar (ver `item-registry.example.yaml` y §13 del
  informe de Fase 1).
- **[Diferido]** — fuera del MVP; trabajo de una fase posterior.

## 5. Reglas de integridad no negociables

- Un **snapshot** exportado nunca se describe como «en vivo».
- Una parcela `planned` nunca se describe como «observada».
- Un valor `missing` nunca se muestra como `0`.
- `unknown` nunca se interpreta como `false`; ausencia de observación no se
  presenta como «estable» y ausencia de registro de campo no se presenta como
  «validado».
- La evidencia `simulated`/`estimated` nunca se promociona a titular ejecutivo.
- La evidencia `synthetic`/`simulated` nunca se convierte automáticamente en
  `real`.
- Nunca se afirma acuerdo satélite↔campo antes de que exista la campaña.
- No se introduce ningún requisito de widget personalizado salvo que se
  demuestre y se registre como brecha **[Diferido]** una limitación concreta de
  los widgets estándar.
