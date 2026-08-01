# BATCH C — Creación de Experience Builder (preparado — NO ejecutar)

> Puerta de aprobación: **`APPROVE EXPERIENCE BUILDER CREATION BATCH C`**.
> Requiere Batch A y Batch B aprobados. Crea **un** item nuevo (no destructivo).
> Ninguna creación se realiza en esta fase.

## Mutaciones

| # | Acción | Estado actual | Estado propuesto | Ruta UI | Resultado | Riesgo | Rollback | Coste | Evidencia | Bloq/Opc |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Crear app | no existe (`DOES_NOT_EXIST — OWNER_UI_VERIFIED`) | 1 Web Experience privada, título `SNTO · Espacio de decisión PNSG — DEMO académico`, descripción DEMO | Experience Builder → Create → New | item EB nuevo | medio (no destructivo) | eliminar el item EB nuevo | crear app normalmente sin coste recurrente (comprobar org) | captura item | **Bloqueante** |
| C2 | Añadir fuentes | — | primaria: Web Map existente; secundaria: results view; opc. pilot_assets | EB → Data | fuentes conectadas | bajo | quitar fuente | ninguno | captura | **Bloqueante** |
| C3 | Crear páginas | — | Decidir, Diagnosticar, Evidenciar, Gobernar, Asset Detail | EB → Page | 5 páginas | bajo | eliminar página | ninguno | captura | **Bloqueante** |
| C4 | Configurar widgets | — | por `page-architecture.md` (widgets estándar) | EB → Widgets | UI funcional | bajo | quitar widget | ninguno | captura por página | Opcional |
| C5 | Configurar interacciones | — | por `interaction-matrix.md` (message actions) | EB → Actions | sincronización | bajo | quitar action | ninguno | prueba interacción | Opcional |
| C6 | Compartir | — | **solo grupo privado SNTO**; nada público; sin acceso anónimo | EB → Share | app privada | **alto si se comparte de más** | reducir compartición | ninguno | captura Share | **Bloqueante** |
| C7 | Protección de borrado de la app | — | **on** tras creación | Item → Settings → Delete protection | app no borrable | ninguno | desactivar | ninguno | captura | Recomendado |

## Reglas duras

- **No crear capas alojadas duplicadas.** Reutilizar Web Map + results view +
  pilot_assets.
- **Evidencia** desde la **results view** (no la form view); **captura** vía
  enlace al **form item** con prefill.
- `asset_id` = unión lógica; sin relationship class; `asset_id` nulo no enlazado.
- Compartir la app **no** concede acceso a las fuentes: confirmar
  `sharing-and-security.md` con una cuenta miembro (no owner).
- Sin publicar públicamente; sin acceso anónimo; sin geocoding/routing/análisis.

## Tras C

Ejecutar `post-mutation-evidence-checklist.md` y `qa-and-acceptance.md`. La **QA
multiusuario** requiere una segunda cuenta no-owner (`multiuser-qa-plan.md`),
pendiente.
