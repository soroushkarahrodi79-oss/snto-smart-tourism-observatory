# Plan de mutación operado por el propietario (maestro)

> **Ninguna mutación se ejecuta.** Plan preparado para ejecución futura del
> propietario, en tres lotes con **puertas de aprobación separadas**. No combinar
> las tres aprobaciones.

## Puertas de aprobación (separadas)

- `APPROVE ARCGIS HARDENING BATCH A` → ver [`hardening-batch-a.md`](hardening-batch-a.md)
- `APPROVE WEB MAP CONFIGURATION BATCH B` → ver [`webmap-batch-b.md`](webmap-batch-b.md)
- `APPROVE EXPERIENCE BUILDER CREATION BATCH C` → ver [`experience-builder-batch-c.md`](experience-builder-batch-c.md)

## Formato de cada mutación

Cada fila de cada lote documenta: item · estado actual · estado propuesto · ruta
exacta de la UI de ArcGIS · toggle/campo exacto · resultado esperado · riesgo ·
rollback · implicación de coste/crédito · evidencia a capturar tras el cambio ·
bloqueante/opcional.

## Estado de ejecución

- **Batch A: ✅ `OWNER_EXECUTED_AND_VERIFIED` (2026-08-01)** — ejecutado por el
  propietario (`OWNER_MANUAL_UI`); Claude no mutó ArcGIS. Ver
  [`batch-a-execution-record.md`](batch-a-execution-record.md).
- **Batch B:** pendiente de `APPROVE WEB MAP CONFIGURATION BATCH B` (no autorizado).
- **Batch C:** pendiente de `APPROVE EXPERIENCE BUILDER CREATION BATCH C` (no autorizado).

## Resumen de lotes

| Lote | Alcance | Riesgo | Precondición |
|---|---|---|---|
| **A — Hardening de bajo riesgo** ✅ ejecutado | protección de borrado; export de results view; aprobación pública del form view; Save As y búsqueda por dirección del Web Map | Bajo (toggles de gobernanza, reversibles) | A0c completado |
| **B — Configuración del Web Map** | popups; filtros; visibilidad/orden; sin definition expressions restrictivas permanentes salvo justificación | Bajo-medio | Batch A aprobado |
| **C — Creación de Experience Builder** | crear app; fuentes; páginas; widgets; interacciones; compartición privada; protección de borrado de la app | Medio (crea un item nuevo, no destructivo) | Batch B aprobado |

## Reglas transversales

- Ejecutar A → B → C en orden; cada lote requiere su propia aprobación.
- Antes de B: guardar copia/ajustes del Web Map (rollback).
- Ninguna acción destructiva sobre items existentes; solo el item EB nuevo puede
  eliminarse en rollback.
- Sin capas alojadas duplicadas; sin geocoding/routing/análisis/servicios premium.
- **Sin afirmación categórica de coste**; comprobar política de créditos de la
  organización (ver `credit-and-cost.md`).
- Tras cada lote: capturar evidencia (`post-mutation-evidence-checklist.md`).
- **QA multiusuario** y **continuidad de cuenta** siguen pendientes con
  independencia de los lotes (ver `multiuser-qa-plan.md`).
