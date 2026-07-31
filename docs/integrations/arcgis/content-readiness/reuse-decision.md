# Decisiones de reutilización — por item (preliminar + suplemento en vivo)

## Actualización del suplemento de verificación anónima (2026-07-31)

La verificación anónima confirmó **existencia** (OWNER_UI_VERIFIED /
ANONYMOUS_REST_VERIFIED) y **bloqueo de acceso anónimo** de la organización, los
dos FeatureServer y los items, pero **no** pudo leer sus esquemas ni verificar
el alcance de compartición exacto (sin credenciales). Por tanto:

- **Las decisiones formales siguen `UNKNOWN`** para todos los items ArcGIS
  reales. La verificación de existencia **no** basta para una decisión de
  reutilización: esa decisión depende del **esquema** (compatibilidad de
  campos/dominios/geometría), que permanece `AUTHENTICATED_READ_REQUIRED`.
- **Las hipótesis preliminares se refuerzan** (el item existe, no hay que
  crearlo desde cero, y ninguna evidencia sugiere `RECREATE`), pero siguen
  siendo **no vinculantes** hasta la lectura autenticada de esquema.
- **Ninguna recreación se justifica** por indisponibilidad de metadatos.

Estado formal tras el suplemento (sin cambios respecto a la regla anterior):

| Item | Decisión formal | Hipótesis (reforzada, no vinculante) |
|---|---|---|
| Grupo privado | UNKNOWN | reuse candidate (existencia OWNER_UI_VERIFIED) |
| `pilot_assets` layer | UNKNOWN | REUSE_WITH_CONFIGURATION (endpoint resuelve; esquema pendiente) |
| Web Map | UNKNOWN | configuration candidate (existencia OWNER_UI_VERIFIED) |
| Survey123 feature service | UNKNOWN | reuse candidate — endpoint **resuelve** (antes se dudaba); esquema pendiente |
| Survey123 results view | UNKNOWN | reuse candidate (OWNER_UI_VERIFIED) |
| Survey123 form view | UNKNOWN | reuse candidate (OWNER_UI_VERIFIED) |
| Survey123 form (item) | UNKNOWN | reuse candidate (OWNER_UI_VERIFIED) |
| Experience Builder | UNKNOWN | sin base — existencia AUTHENTICATED_READ_REQUIRED |

**Cambio destacable:** el endpoint del feature service de Survey123 **resuelve**
(ANONYMOUS_REST_VERIFIED), lo que retira la duda "no confirmado ni descartado"
de la fase preliminar. Aun así, su decisión formal permanece `UNKNOWN` hasta
verificar su esquema mediante lectura autenticada.

---

> Decisiones preliminares previas (históricas) conservadas abajo.

> **Regla de esta corrección:** ningún item real recibe una decisión formal
> distinta de `UNKNOWN` sin verificación en vivo. Donde es útil, se añade una
> **hipótesis preliminar no vinculante**, claramente separada de la decisión
> formal, junto con la evidencia que haría falta para confirmarla.

## Grupo privado `SNTO — Validación de campo DEMO`

**Decisión formal: UNKNOWN — requiere verificación en vivo.**
**Hipótesis preliminar (no vinculante):** likely reuse candidate.
**Evidencia necesaria:** Item ID del grupo, owner, `member_count`, alcance de
acceso real.

## Hosted Feature Layer `SNTO_DEMO_PNSG_Assets`

**Decisión formal: UNKNOWN — requiere verificación en vivo.**
**Hipótesis preliminar (no vinculante):** likely REUSE_WITH_CONFIGURATION —
la existencia y la protección básica (edición desactivada, compartición
privada) están respaldadas históricamente, y no hay evidencia real de
esquema incompatible; **recreation not currently justified** por ninguna
evidencia disponible.
**Evidencia necesaria:** esquema REST real, alcance de compartición actual,
capacidades del servicio, comparación campo por campo con
`data-contract.md` §1 (ver `schema-comparison.md`, DERIVED_RISK de deriva de
metadata Fase 2B, no confirmado).

## Web Map `SNTO_DEMO_PNSG_FieldValidation_Map`

**Decisión formal: UNKNOWN — requiere verificación en vivo.**
**Hipótesis preliminar (no vinculante):** likely configuration candidate —
existencia respaldada históricamente; la configuración de popups/simbología
conforme a `design-system.md` es plausible que necesite ajuste, pero esto es
una hipótesis, no un hallazgo confirmado.
**Evidencia necesaria:** ver `webmap-readiness.md`.

## Survey123 XLSForm (archivo)

**Decisión formal (sobre el archivo local en Git): VERIFIED / REUSE_AS_IS.**
Esta es la única decisión formal no condicionada a ArcGIS en vivo, porque se
refiere al **archivo del repositorio**, no a un item ArcGIS Online. Está
alineado con el contrato de 14 columnas y no requiere reconstrucción.
**Sobre su publicación en Connect:** UNKNOWN — no forma parte de esta
decisión.

## Survey123 feature service

**Decisión formal: UNKNOWN — requiere verificación en vivo.**
**Hipótesis preliminar (no vinculante):** no se puede formular una hipótesis
de reutilización porque no se sabe si el item existe. Si existe, sería
candidato a `REUSE_WITH_CONFIGURATION` o `REUSE_AS_IS` según su esquema; si
no existe, la acción sería crearlo (roadmap Fase 3, condicionado a §A0).
**Evidencia necesaria:** confirmación de existencia + Item ID/URL de servicio
+ esquema real.

## Experience Builder app

**Decisión formal: UNKNOWN — requiere verificación en vivo.**
**Hipótesis preliminar (no vinculante):** ninguna — no hay base suficiente
para hipotetizar sin saber si el item existe.
**Evidencia necesaria:** confirmación de existencia + Item ID si existe.

## Dashboard / StoryMap

**Decisión formal (alcance de producto): DEFERRED** — esto es una decisión de
arquitectura (`architecture.md` §F), independiente del estado de ArcGIS.
**Existencia real en ArcGIS: UNKNOWN**, no evaluada en esta fase.

## Capa PRUG / límite PNSG

**Decisión formal: DEFERRED** (condicionada a licencia/procedencia, no
resuelta).

## Resumen

| Item | Decisión formal | Hipótesis preliminar (no vinculante) |
|---|---|---|
| Grupo privado | UNKNOWN | likely reuse candidate |
| Capa de activos | UNKNOWN | likely REUSE_WITH_CONFIGURATION |
| Web Map | UNKNOWN | likely configuration candidate |
| XLSForm (archivo Git) | VERIFIED / REUSE_AS_IS | — (no aplica, no es un item ArcGIS) |
| Feature service Survey123 | UNKNOWN | sin base suficiente |
| Experience Builder app | UNKNOWN | sin base suficiente |
| Dashboard (alcance) | DEFERRED | — |
| StoryMap (alcance) | DEFERRED | — |
| Capa PRUG/límite | DEFERRED | — |

**Ningún item real recibe `RECREATE`.** No hay evidencia confirmada de
esquema incompatible, tipos de campo erróneos, relaciones rotas, exposición
pública indebida o inestabilidad de propiedad. Toda incertidumbre actual es
de **verificación pendiente**, no de reconstrucción necesaria — pero esa
misma falta de verificación impide también afirmar `REUSE_AS_IS` o
`REUSE_WITH_CONFIGURATION` como decisiones formales.
