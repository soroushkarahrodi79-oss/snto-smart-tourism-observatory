# Batch A — Registro de ejecución (hardening de bajo riesgo)

> **`BATCH_A_STATUS: OWNER_EXECUTED_AND_VERIFIED`** (2026-08-01).

## Atribución (distinción explícita)

| Campo | Valor |
|---|---|
| **EXECUTOR** | `OWNER_MANUAL_UI` — el propietario aplicó los cambios en su sesión autenticada de ArcGIS Online |
| **AUTHORIZATION** | `APPROVE ARCGIS HARDENING BATCH A` |
| **CLAUDE_DIRECT_ARCGIS_MUTATION** | `NONE` — Claude no operó la UI de ArcGIS ni cambió ningún ajuste |

Los Item IDs / URLs reales y los estados detallados se registran solo en el
registro local ignorado; aquí se documenta el hecho y las disposiciones.

## Estados aplicados (confirmados por el propietario)

| ID | Item | Estado previo (A0c) | Estado aplicado | Clase |
|---|---|---|---|---|
| A1 | Grupo privado | protección elim. OFF | **ON** | Recomendado |
| A2 | Survey123 servicio principal | protección elim. OFF | **ON** | Recomendado |
| A3 | Results view | protección elim. OFF | **ON** | Recomendado |
| A4 | Form view | protección elim. OFF | **ON** | Recomendado |
| A5 | Form item | protección elim. OFF | **ON** | Recomendado |
| A6 | Web Map | protección elim. OFF | **ON** | Recomendado |
| A7 | Results view · export de datos | ON | **OFF** | **Gobernanza (bloqueante)** |
| A8 | Form view · aprobación compartición pública editable | ON | **OFF** | **Gobernanza (bloqueante)** |
| A9 | Web Map · Guardar como (Save As) | ON | **OFF** | Opcional |
| A10 | Web Map · búsqueda por dirección | ON | **OFF** | Opcional |

## Invariantes confirmados (no-cambio)

- Results view · edición sigue **OFF**.
- Form view sigue **privado**.
- Form view sigue **add-only**.
- Web Map · búsqueda por **capa** sigue **OFF**.
- Compartición **NO cambiada** en ningún item.
- `pilot_assets` **NO cambiado** (ya estaba en su estado objetivo: protección ON,
  edición/export/sync OFF).

## Efecto de gobernanza

- **A7 (export OFF)** reduce el riesgo de extracción de datos potencialmente
  sensibles (observador, notas, coordenadas, adjuntos) por el ajuste de item de
  la results view. La visualización de evidencia en Experience Builder sigue
  siendo posible. **No** implica riesgo cero de extracción.
- **A8 (aprobación pública OFF)** elimina el riesgo de compartición pública
  accidental del form view; el item permanece privado y add-only para miembros
  autenticados del grupo.
- **A1–A6** protegen todos los items DEMO frente a borrado accidental.
- **A9/A10** endurecen el Web Map (sin copias no controladas; sin dependencia de
  geocoding/locator). **Sin afirmación categórica de coste.**

## Pendiente (sin cambio)

- **QA multiusuario:** el grupo tiene 1 solo miembro (el owner); comportamiento
  efectivo no-owner no probado (`multiuser-qa-plan.md`).
- **Continuidad/transferencia** de la cuenta educativa.

## Próxima puerta

`APPROVE WEB MAP CONFIGURATION BATCH B` — **no autorizada**. Batch B (popups y
filtros del Web Map) y Batch C (creación de Experience Builder) **no** se
ejecutan ni se autorizan automáticamente por este registro.
