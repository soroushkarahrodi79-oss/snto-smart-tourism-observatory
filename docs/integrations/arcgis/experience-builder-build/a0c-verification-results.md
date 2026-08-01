# A0c — Resultados de verificación de permisos (OWNER_UI_VERIFIED)

> El propietario inspeccionó la UI de ArcGIS Online (2026-08-01) y aportó los
> estados. Categoría: `OWNER_UI_VERIFIED`. **No se infiere nada más allá de la
> evidencia.** Ninguna mutación se realiza en esta fase.

## Veredicto gobernante

- **`A0c_PERMISSION_VERIFICATION: COMPLETED_FOR_OWNER_OPERATED_BUILD`**
- **Global:** `READY_FOR_OWNER_OPERATED_EXPERIENCE_BUILDER_CREATION_WITH_APPROVED_HARDENING`
- **Pero:** ninguna mutación autorizada; QA multiusuario pendiente (no existe un
  segundo miembro no-owner); comportamiento efectivo no-owner no probado;
  continuidad/transferencia de cuenta pendiente.

## Grupo privado — «SNTO – Validación de campo DEMO»

Visibilidad: solo miembros del grupo · miembros elegibles: solo de mi
organización · unión: por invitación · contribución: todos los miembros ·
protección de borrado: **desactivada** · opción shared-update: **no observada** ·
miembros: **exactamente 1** (solo el owner; sin admins ni miembros ordinarios).

**Interpretación:** grupo privado, ligado a organización, por invitación, apto
para build operado por el owner; **no** apto todavía para QA multiusuario real
(no hay segunda cuenta no-owner); sin evidencia de shared-update; «todos los
miembros pueden contribuir» **no** prueba que puedan editar items de otros owners.
**Disposición:** `GROUP_READY_FOR_OWNER_OPERATED_BUILD`. Cautelas: protección de
borrado off, QA multiusuario pendiente, continuidad de cuenta pendiente.

## pilot_assets (Hosted Feature Layer)

Compartición: owner + grupo privado SNTO; no org-wide; no público. Protección de
borrado: **activada**. Edición: off · change tracking: off · editor tracking:
off · sync: off · export por otros: off · aprobación de compartición pública
editable: off · sin webhooks.
**Rol:** `READ_ONLY_ANALYTICAL_REFERENCE`. **Disposición: `A0c PASS`** — sin
cambios requeridos antes del build.

## Survey123 servicio principal

Compartición: owner + grupo privado; no org-wide; no público. Protección de
borrado: **off**. Edición: on · add: on · update: off · delete: off · editores
ven registros existentes: no · editor anónimo: add-only solo si fuera público ·
aprobación pública editable: off · editor tracking: on · change tracking: off ·
sync: off · export por otros: off.
**Rol:** `SURVEY123_CAPTURE_BACKEND / CAPTURE_ONLY / ADD_ONLY`. **Disposición:
`PASS_WITH_HARDENING`** (gap: protección de borrado off). **No** recomendar como
fuente de evidencia por defecto de Experience Builder.

## Survey123 results view

Compartición: owner + grupo privado; no org-wide; no público. Protección de
borrado: **off**. Edición: **off** · change tracking: off · editor tracking:
heredado/visible · sync: off · export por otros: **on** · aprobación pública
editable: off · caché: 30 s.
**Rol:** `READ_ONLY_EVIDENCE_DISPLAY`. **Disposición:
`PASS_WITH_GOVERNANCE_REVIEW`.** La UI confirma edición off → apta para mostrar
evidencia en Experience Builder; el **export sigue siendo una decisión de
gobernanza** porque el esquema puede exponer observador, notas, coordenadas
precisas y adjuntos; protección de borrado off. **No** se afirma riesgo cero de
extracción de datos.

## Survey123 form view

Compartición: owner + grupo privado; no org-wide; no público. Protección de
borrado: **off**. Edición: on · add: on · update: off · delete: off · editores
ven existentes: no · editor anónimo: add-only si fuera público · **aprobación de
compartición pública editable: on** · editor tracking: heredado/on · change
tracking: off · sync: off · export por otros: off · caché: 0 s.
**Rol:** `SURVEY123_CAPTURE_VIEW / CAPTURE_ONLY / ADD_ONLY`. **Disposición:
`PASS_WITH_HARDENING_RECOMMENDATION`.** Cautela: el item está actualmente
privado; que la aprobación de colección pública esté activada **no** lo hace
público por sí mismo, pero existe **riesgo de compartición pública accidental**
(la capacidad add-only anónima sería relevante si alguna vez se compartiera
públicamente). **Candidato de hardening:** desactivar la aprobación de
compartición pública editable salvo que se requiera explícitamente una encuesta
abierta/anónima.

## Survey123 form item

Compartición: owner + grupo privado; no org-wide; no público. Protección de
borrado: **off** · no obsoleto · sin URL personalizada · sin adjunto de código.
**Rol:** `PRIVATE_CAPTURE_ENTRY_POINT`. **Disposición: `PASS_WITH_HARDENING`**
(gap: protección de borrado off).

## Web Map

Compartición: owner + grupo privado; no org-wide; no público. Protección de
borrado: **off** · offline: off (sin áreas offline) · Save As: **on** · search:
on · search por capa: off · search por dirección: **on** · uso Field Maps:
on/visible · sin derecho de modificación directa observado para miembros
ordinarios del grupo.
**Rol:** `PRIVATE EXPERIENCE BUILDER MAP SOURCE`. **Disposición:
`PASS_WITH_HARDENING`.** Decisiones de gobernanza pendientes: activar protección
de borrado; decidir si Save As permanece on; decidir si se necesita búsqueda por
dirección (puede depender de locator/créditos de la organización — **sin
afirmación categórica de coste**); sin evidencia de derechos de edición directa
para miembros no-owner.

## Incógnitas restantes

- QA multiusuario (no existe segundo miembro no-owner).
- Comportamiento efectivo de un usuario no-owner (no probado).
- Continuidad/transferencia de la cuenta educativa.
- Política de locator/créditos de la organización para búsqueda por dirección.
