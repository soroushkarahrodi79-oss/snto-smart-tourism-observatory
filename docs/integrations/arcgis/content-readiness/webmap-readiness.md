# Disposición del Web Map — `SNTO_DEMO_PNSG_FieldValidation_Map`

> Ninguna edición realizada. **Clasificación formal tras el suplemento de
> verificación anónima (2026-07-31): `UNKNOWN — AUTHENTICATED_READ_REQUIRED`.**

## Suplemento de verificación anónima (2026-07-31)

El Item ID del Web Map fue aportado por el propietario (OWNER_UI_VERIFIED;
registrado en local). Lo verificado: existencia **OWNER_UI_VERIFIED** y acceso
anónimo a metadatos de item **ANONYMOUS_ACCESS_BLOCKED** (endpoint → `403`). Lo
**no** verificable sin sesión autenticada: capas operacionales, orden,
simbología, popups, filtros, bookmarks, extent, basemap, y el alcance de
compartición exacto (el `item/data` requiere token). Por tanto la clasificación
**es `UNKNOWN — AUTHENTICATED_READ_REQUIRED`**: existe (OWNER_UI) y su endpoint
bloquea acceso anónimo, pero su configuración interna no puede leerse. **No** se
afirma su alcance de compartición exacto a partir de `403`.

El `DERIVED_RISK` de cronología (reglas de `design-system.md` posteriores al
guardado del mapa) **sigue sin confirmar ni descartar**.

---

## Clasificación formal

**UNKNOWN — NOT LIVE-VERIFIED.**

No se usa `NOT_READY`, `READY` ni `READY_WITH_CONFIGURATION` porque ninguna
de esas clasificaciones puede sostenerse sin inspeccionar el mapa real. La
existencia y la compartición del mapa están `QUALITATIVELY_CONFIRMED`
(propietario) e `HISTORICALLY_VERIFIED` (roadmap 2026-07-13), pero su
configuración actual —capas, popups, simbología, filtros, extent,
bookmarks— es `UNKNOWN`.

## Criterios (todos UNKNOWN salvo lo históricamente verificado)

| Criterio | Estado |
|---|---|
| Capas operacionales correctas | UNKNOWN |
| Orden de capas correcto | UNKNOWN |
| Simbología correcta (por `trend`, patrón+etiqueta) | UNKNOWN — el roadmap solo confirmó históricamente "simbología por tendencia configurada" |
| Etiquetas correctas | UNKNOWN |
| Popups correctos (orden fijo `design-system.md` §6) | UNKNOWN |
| Filtros correctos | UNKNOWN |
| Rangos de visibilidad | UNKNOWN |
| Compartición correcta | HISTORICALLY_VERIFIED (roadmap 2026-07-13: solo grupo privado); estado **actual** UNKNOWN |
| Acceso de grupo correcto | UNKNOWN en detalle |
| Ninguna capa editable expuesta innecesariamente | HISTORICALLY_VERIFIED (roadmap 2026-07-13: edición desactivada); estado **actual** UNKNOWN |
| Ruta de integración Survey123/campo | UNKNOWN (depende del estado del feature service, también UNKNOWN) |
| Bookmarks | UNKNOWN |
| Extent | UNKNOWN |
| Idoneidad móvil/tablet | UNKNOWN |
| Etiquetas de evidencia visibles | UNKNOWN |
| Sello de fecha del snapshot | UNKNOWN |
| Visualización de proveniencia | UNKNOWN |

## DERIVED_RISK — hallazgo preliminar basado en repositorio (no confirmado)

**Hallazgo:** las reglas de presentación de evidencia aprobadas en Fase 2A
(`design-system.md`, popups de 3 dimensiones, patrón+etiqueta no-color) se
crearon **después** de la fecha histórica de guardado del Web Map
(2026-07-13). Es **plausible** que la configuración actual del mapa no
implemente esas reglas todavía.

**Esto es una hipótesis de planificación (`DERIVED_RISK`), no una
afirmación de que las reglas estén ausentes del Web Map real.** El mapa pudo
haberse actualizado en cualquier momento posterior sin que quede registro en
este repositorio.

## Siguiente paso (no ejecutar en Fase 3)

La Fase B2 del `build-playbook.md` ya prevé exactamente esta revisión
(simbología, popups). Este documento confirma que esa revisión **sigue
siendo necesaria como verificación**, no que el mapa esté necesariamente
desactualizado.
