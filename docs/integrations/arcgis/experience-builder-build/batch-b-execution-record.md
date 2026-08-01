# Batch B — Registro de ejecución (configuración del Web Map)

> **`BATCH_B_STATUS: OWNER_EXECUTED_AND_VERIFIED`** (2026-08-01).

## Atribución (distinción explícita)

| Campo | Valor |
|---|---|
| **EXECUTOR** | `OWNER_MANUAL_UI` — el propietario configuró el Web Map en su sesión autenticada de ArcGIS Online |
| **AUTHORIZATION** | `APPROVE WEB MAP CONFIGURATION BATCH B` |
| **CLAUDE_DIRECT_ARCGIS_MUTATION** | `NONE` — Claude no operó el Map Viewer ni guardó ningún cambio |

El Item ID del Web Map de backup y demás identificadores reales se registran
solo en el registro local ignorado; aquí se documenta el hecho y las
disposiciones.

## Backup / rollback (precondición) — confirmado

- Copia privada del Web Map **creada y verificada** (Map Viewer → Guardar y abrir
  → Guardar como; **solo owner**).
- La copia **abre** y **referencia las mismas capas existentes**.
- **No** se duplicaron Hosted Feature Layers (solo el item Web Map).
- Item ID del backup: registrado **solo** en `item-registry.local.yaml` si el
  propietario lo aporta; **nunca** en la documentación versionada.

## Cambios aplicados (confirmados por el propietario)

| ID | Cambio | Estado | Detalle |
|---|---|---|---|
| B1 | Popup de `Observaciones de campo · DEMO` | ✅ configurado y **guardado** | 12 campos legibles; oculta objectid/globalid/Creator/Editor/CreationDate/EditDate y lat/lon crudas; adjuntos accesibles; nulos **no** convertidos a 0; **sin Arcade** |
| B2 | Popup de `pilot_assets` | ✅ configurado y **guardado** | 15 campos; oculta ObjectId/campos técnicos; formatos numéricos/fecha revisados; `demo_status`/`decision_caveat`/`provenance` visibles; **sin Arcade** |
| B3 | Filtros | ✅ verificado sin cambios | sin filtro de capa, sin `definitionExpression`, sin display filter, sin time filter restrictivos |
| B4 | Orden / visibilidad / simbología | ✅ preservado | orden 1) Observaciones · DEMO 2) pilot_assets; ambas visibles; simbología evidencia/tendencia preservada; basemap/extent/escala sin cambios; solape y legibilidad verificados |

## Invariantes confirmados (no-cambio)

- Web Map **original sigue privado**.
- Compartición **sin cambios**.
- Capas alojadas **sin duplicar**.
- Esquema, campos, dominios y datos **sin modificar**.
- Experience Builder **no creado**.
- Batch C **no ejecutado**.

## Reglas de integridad preservadas

- Nulos → «Sin dato»/en blanco, **nunca 0**; `synthetic`/`missing` explícitos;
  no promocionar `synthetic` a `real`.
- Tendencia ≠ causalidad; punto provisional ≠ geometría autoritativa; `asset_id`
  es solo unión lógica (sin relationship class).
- **B3** confirmada como regla de integridad: el Web Map permanece ampliamente
  reutilizable; el filtrado interactivo se implementará en Experience Builder
  (Batch C).

## Pendiente (sin cambio)

- **QA multiusuario:** el grupo tiene 1 solo miembro (el owner); comportamiento
  efectivo no-owner no probado (`multiuser-qa-plan.md`).
- **Continuidad/transferencia** de la cuenta educativa.

## Próxima puerta

`APPROVE EXPERIENCE BUILDER CREATION BATCH C` — **no autorizada**. Batch C
(creación de la app privada de Experience Builder) **no** se ejecuta ni se
autoriza automáticamente por este registro.
