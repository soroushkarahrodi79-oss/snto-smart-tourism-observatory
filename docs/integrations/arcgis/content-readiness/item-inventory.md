# Inventario de items ArcGIS — Fase 3 (preliminar)

> Cada item separa **estado histórico** (lo que el roadmap del 2026-07-13
> verificó), **confirmación cualitativa** (lo que el propietario reafirmó el
> 2026-07-30) y **estado en vivo** (lo que solo una inspección real
> confirmaría — hoy `UNKNOWN` en todos los casos). Ningún Item ID es
> fabricado. Ver `README.md` §3 para la terminología.

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
