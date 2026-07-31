# Decisiones de reutilización — por item (preliminar)

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
