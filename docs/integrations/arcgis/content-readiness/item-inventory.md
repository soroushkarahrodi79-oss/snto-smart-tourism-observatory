# Inventario de items ArcGIS — Fase 3 (preliminar → anónima → esquema autenticado)

> Marco temporal: **estado histórico** (roadmap 2026-07-13) → **anónimo**
> (2026-07-31) → **esquema autenticado del propietario** (2026-08-01, gobernante).
> Ningún Item ID es fabricado. Los Item IDs reales, las URLs exactas de servicio
> y los metadatos locales detallados permanecen únicamente en el registro local
> ignorado `arcgis/demo/pnsg/item-registry.local.yaml`. La documentación
> versionada conserva los hallazgos de esquema respaldados por evidencia, sus
> limitaciones y las decisiones gobernantes, sin incluir esos identificadores ni
> URLs reales.

## Suplemento de esquema autenticado (2026-08-01) — GOBERNANTE

Evidencia `OWNER_AUTHENTICATED_SCHEMA_VERIFIED` aportada por el propietario
(REST autenticada + Map Viewer). Prevalece sobre la tabla anónima de más abajo.

| Item | Existencia | Esquema/config | Estado |
|---|---|---|---|
| Organización | ANONYMOUS_REST_VERIFIED | admin | AUTHENTICATED_READ_REQUIRED (sin cambio) |
| Grupo privado | OWNER_UI_VERIFIED | permisos/miembros | UNKNOWN (pendiente) |
| `pilot_assets` capa 0 `pilot_assets_points` | verificada | punto, WKID 102100, sin GlobalID, sin adjuntos, `asset_id` nullable, strings 4000, sin dominios | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** |
| Survey123 servicio principal capa 0 | verificada | punto, EPSG 4326, `globalid`, adjuntos, editor tracking, dominios en `plot_id`/`erosion_class`/`evidence_class` | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** |
| Survey123 form view | verificada | vista actualizable, punto, EPSG 4326, adjuntos | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** (rol: captura) |
| Survey123 results view | verificada | vista, ops de consulta + adjuntos; root reporta *Is Updatable View* | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** (rol: evidencia read-oriented) |
| Web Map | verificada (capas/leyenda/popup) | 2 capas operacionales, simbología por evidencia/tendencia, popup con adjuntos | **OWNER_AUTHENTICATED_SCHEMA_VERIFIED** (config parcial; faltan filtros/refinamiento) |
| Survey123 form item | OWNER_UI_VERIFIED | item/sharing | AUTHENTICATED_READ_REQUIRED (pendiente) |
| Experience Builder | **UNKNOWN** | — | no aportado; no se afirma existencia ni ausencia |

**Pendiente (sin cambio):** compartición exacta de items, permisos/miembros del
grupo, filtros ocultos/definition expressions, bookmarks/basemap, existencia de
Experience Builder, continuidad de cuenta, permisos de edición efectivos por
usuario. Detalle de campos/dominios/roles en `schema-comparison.md`.

---

> **Estado previo (histórico) — Suplemento de verificación anónima (2026-07-31).**

## Suplemento de verificación anónima (2026-07-31)

Metadatos aportados por el propietario (OWNER_UI) + inspección REST/HTTP anónima
(sin credenciales). Categorías: ver `README.md` §0. Tabla de estado:

| Item | Existencia | Evidencia | Acceso anónimo | Configuración/esquema |
|---|---|---|---|---|
| Organización `ucmadrid.maps.arcgis.com` | **ANONYMOUS_REST_VERIFIED** | `sharing/rest/info` → AGOL real, `isTokenBasedSecurity:true` | info público | config admin → AUTHENTICATED_READ_REQUIRED |
| Grupo privado | **OWNER_UI_VERIFIED** | ID aportado por owner | **ANONYMOUS_ACCESS_BLOCKED** (`403`) | owner, miembros, sharing exacto → AUTHENTICATED_READ_REQUIRED |
| `pilot_assets` FeatureServer | **ANONYMOUS_REST_VERIFIED** (endpoint resuelve) | URL exacta → `499`; inexistente → `400` (calibrado) | **ANONYMOUS_ACCESS_BLOCKED** | índice de capa, esquema, geometría, CRS → AUTHENTICATED_READ_REQUIRED |
| Survey123 FeatureServer | **ANONYMOUS_REST_VERIFIED** (endpoint resuelve) | URL exacta → `499 Token Required` | **ANONYMOUS_ACCESS_BLOCKED** | índices capa/tabla, 14 campos, dominios, adjuntos, editor tracking → AUTHENTICATED_READ_REQUIRED |
| Survey123 form item | **OWNER_UI_VERIFIED** | ID aportado + `403` | **ANONYMOUS_ACCESS_BLOCKED** | AUTHENTICATED_READ_REQUIRED |
| Survey123 results view | **OWNER_UI_VERIFIED** | ID aportado por owner | — | AUTHENTICATED_READ_REQUIRED |
| Survey123 form view | **OWNER_UI_VERIFIED** | ID aportado por owner | — | AUTHENTICATED_READ_REQUIRED |
| Web Map | **OWNER_UI_VERIFIED** | ID aportado + `403` | **ANONYMOUS_ACCESS_BLOCKED** | capas operacionales, popups, simbología → AUTHENTICATED_READ_REQUIRED |
| pilot_assets item | **OWNER_UI_VERIFIED** | ID aportado + `403` | **ANONYMOUS_ACCESS_BLOCKED** | AUTHENTICATED_READ_REQUIRED |
| Experience Builder | **UNKNOWN** | no aportado; contenidos de grupo → `403` | — | AUTHENTICATED_READ_REQUIRED (no se afirma existencia ni ausencia) |

**Hallazgo de control de acceso (no de privacidad global):** los endpoints
probados no exponen acceso anónimo — resultado positivo de control de acceso
**para esas rutas**. **No** sustituye la verificación autenticada del alcance de
compartición exacto, la pertenencia al grupo, el control de acceso basado en
propiedad ni los permisos de item. **No** se afirma que todos los items sean
privados a partir de `403`/`499`.

**Hallazgo incidental (no es item nuestro):** el directorio público de
servicios del host lista dos FeatureServer con prefijo `PNSG_` — posible
cartografía OAPN/PRUG pública, **no** parte del set DEMO suministrado; sin
verificar licencia/procedencia.

---

> Lo que sigue es el inventario preliminar previo (histórico), conservado. El
> suplemento de arriba prevalece donde hubo verificación anónima.

## Organización ArcGIS UCM

- **Existencia:** QUALITATIVELY_CONFIRMED (2026-07-30) + HISTORICALLY_VERIFIED
  (roadmap 2026-07-13: "organización académica de la Universidad Complutense
  de Madrid confirmada").
- **URL / configuración (tipo de usuario, rol, créditos):** UNKNOWN.

## Grupo privado `SNTO — Validación de campo DEMO`

- **Creación histórica:** HISTORICALLY_VERIFIED (roadmap 2026-07-13: "Grupo
  privado creado por el propietario del piloto").
- **Existencia actual:** QUALITATIVELY_CONFIRMED **solo si** la declaración
  del propietario ("sigue todo existe") se interpreta como que cubre este
  item; no fue identificado individualmente.
- **Item ID, owner, alcance de acceso, nº de miembros:** UNKNOWN.
- **Decisión de reutilización:** UNKNOWN (ver `reuse-decision.md`).

## Hosted Feature Layer `SNTO_DEMO_PNSG_Assets`

- **Publicación histórica:** HISTORICALLY_VERIFIED (roadmap 2026-07-13:
  "`pilot_assets.geojson` publicado correctamente como capa de entidades
  alojada… edición desactivada, dos entidades verificadas, simbología por
  tendencia configurada").
- **Existencia actual:** QUALITATIVELY_CONFIRMED.
- **Esquema actual, compartición actual, edición actual, capacidades del
  servicio:** UNKNOWN.
- **Decisión de reutilización:** UNKNOWN.
- **Nota:** candidato a reutilización, **pendiente de verificación en vivo**
  (ver `reuse-decision.md` para la hipótesis preliminar no vinculante).

## Web Map `SNTO_DEMO_PNSG_FieldValidation_Map`

- **Guardado histórico:** HISTORICALLY_VERIFIED (roadmap 2026-07-13: "mapa
  guardado… contenido compartido exclusivamente con el grupo privado del
  piloto").
- **Existencia actual:** QUALITATIVELY_CONFIRMED.
- **Capas operacionales, popups, filtros, compartición y disposición
  actuales:** UNKNOWN.
- **Clasificación de disposición:** UNKNOWN (ver `webmap-readiness.md`; **no**
  `NOT_READY`).

## Survey123 XLSForm `SNTO_DEMO_PNSG_FieldValidation`

- **XLSForm canónico en Git:** VERIFIED (archivo presente en
  `arcgis/demo/pnsg/SNTO_DEMO_PNSG_FieldValidation.xlsx`, hash confirmado en
  el backup externo).
- **Generación histórica:** HISTORICALLY_VERIFIED (roadmap: "XLSForm…
  generado con cuatro parcelas controladas… alineado con las catorce
  columnas canónicas").
- **Estado actual de publicación en Connect:** UNKNOWN.
- **Existencia del feature service:** UNKNOWN. El roadmap registró esto como
  "pendiente" el 2026-07-13, pero han pasado 17 días y la declaración
  cualitativa del propietario no distingue si ese paso pendiente se completó.
  **No se afirma que el servicio no exista** — se afirma que su estado es
  desconocido sin verificación adicional.
- **Envíos/submissions:** UNKNOWN salvo confirmación explícita del
  propietario (no recibida).

## Survey123 Feature Service

- **Existencia:** UNKNOWN. **No se afirma inexistencia.** El único dato
  histórico es que el roadmap, el 2026-07-13, lo marcó como pendiente de
  publicar; eso es un hecho histórico, no una prueba de su estado actual.
- **Metadatos (Item ID, URL, índices, dominios, adjuntos):** UNKNOWN.

## Experience Builder app

- **Existencia:** UNKNOWN. El `build-playbook.md` de Fase 2A la describía
  como "por crear" en ese momento, pero **no se afirma que siga sin crearse**
  sin confirmación explícita del propietario.
- **Item ID, título, configuración:** UNKNOWN.

## Dashboard / StoryMap

- **Alcance de producto:** DEFERRED (decisión de arquitectura, independiente
  del estado de ArcGIS).
- **Existencia real en ArcGIS Online:** UNKNOWN — no inspeccionada. Un item
  con ese propósito podría o no existir; no se ha verificado en ningún
  sentido.

## Capa PRUG / límite PNSG

- **Existencia:** UNKNOWN.
- **Licencia/procedencia:** UNKNOWN.
- **Alcance de producto:** condicionado (DEFERRED hasta confirmar licencia).

## Nota sobre "sigue todo existe"

Esta frase es una **confirmación cualitativa agregada**, no una identificación
item por item con metadatos verificables. No permite:

- concluir qué Item ID tiene cada elemento;
- concluir si el feature service de Survey123 fue publicado;
- concluir si existe ya un item de Experience Builder;
- asignar ninguna decisión formal de reutilización o de disposición.

Su único efecto documentado aquí es reforzar `QUALITATIVELY_CONFIRMED` para
los cuatro items que el roadmap ya había descrito individualmente
(organización, grupo, capa de activos, Web Map).
