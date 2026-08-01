# Checklist de ejecución en la UI (operado por el propietario — FUTURO)

> **No ejecutar.** Secuencia futura, gobernada por puertas de aprobación. Cada
> bloque termina en una puerta explícita del propietario.

## Puerta 0 — A0c (permisos) ✅ COMPLETADA (2026-08-01)
Verificada por el owner (`a0c-verification-results.md`). La ejecución de las
puertas siguientes se reorganiza en **tres lotes con aprobaciones separadas**:
`hardening-batch-a.md` (`APPROVE ARCGIS HARDENING BATCH A`) →
`webmap-batch-b.md` (`APPROVE WEB MAP CONFIGURATION BATCH B`) →
`experience-builder-batch-c.md` (`APPROVE EXPERIENCE BUILDER CREATION BATCH C`).
QA multiusuario (`multiuser-qa-plan.md`) y continuidad de cuenta: **pendientes**.
Las puertas 1–7 de abajo se mantienen como guía de detalle dentro de esos lotes.

**Batch A: ✅ `OWNER_EXECUTED_AND_VERIFIED` (2026-08-01)** — ejecutado por el
propietario (`OWNER_MANUAL_UI`); ver `batch-a-execution-record.md`. **Batch B**
(configuración del Web Map, Puertas 1–2) y **Batch C** (creación de la app,
Puertas 3–7): **pendientes** de su aprobación separada.

## Puerta 1 — Copia de seguridad y registro previo
1. Guardar una copia del Web Map (si la UI lo permite).
2. Capturar simbología, popups, compartición y extent actuales.
**Puerta:** estado original documentado (rollback posible).

## Puerta 2 — Configuración del Web Map
1. Configurar popups de observaciones y de `pilot_assets` según
   `webmap-configuration-plan.md` (mostrar/ocultar campos; null→«Sin dato»).
2. Confirmar simbología por evidencia/tendencia con etiqueta/patrón.
3. **No** añadir definition expressions restrictivas.
**Puerta:** revisión visual del propietario.

## Puerta 3 — Crear la app Experience Builder
1. Crear Web Experience nueva; título `SNTO · Espacio de decisión PNSG — DEMO académico`; descripción DEMO obligatoria.
2. Fuente primaria: el Web Map existente.
3. Aplicar tema SNTO.
4. Definir 5 páginas: Decidir, Diagnosticar, Evidenciar, Gobernar, Asset Detail.
**Puerta:** estructura aprobada. **Requiere aprobación explícita de mutación.**

## Puerta 4 — Construir páginas y cablear widgets
Orden: Gobernar → Diagnosticar → Asset Detail → Decidir → Evidenciar
(`page-architecture.md` + `interaction-matrix.md`). Evidenciar usa el **results
view**; el botón de captura enlaza al **form item** con prefill.
**Puerta:** cada página revisada contra `qa-and-acceptance.md`.

## Puerta 5 — Vistas responsive
Configurar desktop/tablet/móvil; Evidenciar a pantalla completa en móvil.
**Puerta:** prueba en tres tamaños.

## Puerta 6 — Compartición
Aplicar `sharing-and-security.md`; probar con una cuenta miembro del grupo (no
owner); confirmar que **nada** queda público.
**Puerta:** revisión de permisos.

## Puerta 7 — QA
Ejecutar `qa-and-acceptance.md` completo.
**Puerta:** todos los criterios en verde.

## Reversión
Si se descarta: `rollback-plan.md`.
