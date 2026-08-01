# QA checklist — Fase 3 (preliminar → anónima → esquema autenticado)

## Suplemento de esquema autenticado (2026-08-01) — verificación de disciplina

- [x] Ninguna llamada a ArcGIS ni mutación en esta tarea; el esquema proviene
      de la inspección autenticada **del propietario**, no de este flujo.
- [x] `OWNER_AUTHENTICATED_SCHEMA_VERIFIED` se aplica **solo** a campos/config
      directamente respaldados por la evidencia aportada.
- [x] `LIVE_SCHEMA_VERIFIED` sigue sin usarse (reservado a inspección por este
      flujo, que no ocurrió).
- [x] No se afirma que la results view sea solo-lectura absoluta para todo
      usuario (root reporta *Is Updatable View*; permisos efectivos pendientes).
- [x] No se afirman permisos de usuario a partir de operaciones soportadas ni de
      `editable=true`; compartición/permisos siguen `AUTHENTICATED_READ_REQUIRED`.
- [x] `pilot_assets` no se recomienda recrear ahora (solo migrar/recrear antes de
      producción).
- [x] Experience Builder: existencia **`DOES_NOT_EXIST — OWNER_UI_VERIFIED`**
      (verificado por el propietario, 2026-08-01); decisión
      `CREATE_NEW_EXPERIENCE_BUILDER_APP`; creación no autorizada; no se crea.
- [x] A0c permisos: `COMPLETED_FOR_OWNER_OPERATED_BUILD` (OWNER_UI_VERIFIED);
      plan de mutación en 3 lotes con puertas separadas; ninguna mutación
      autorizada; QA multiusuario y continuidad de cuenta pendientes.
- [x] Estados `UNKNOWN` previos conservados solo como histórico, no como
      gobernantes.
- [x] Ningún Item ID real ni URL de servicio exacta en docs versionados: esos
      permanecen únicamente en el registro local ignorado. La documentación
      versionada **sí** conserva los hallazgos de esquema respaldados por
      evidencia, sus limitaciones y las decisiones gobernantes (sin esos
      identificadores ni URLs reales).
- [x] Ninguna coordenada GPS sensible ni contenido de adjunto copiado a docs.
- [x] `arcgis/demo/pnsg/item-registry.local.yaml` sigue ignorado y no staged.

---

> **Histórico.** Debajo, la disciplina del suplemento anónimo (2026-07-31).

## Suplemento de verificación anónima (2026-07-31) — verificación de disciplina

- [x] Todas las llamadas a ArcGIS fueron **anónimas y read-only** (solo
      `GET ...?f=json`); ningún endpoint administrativo ni de mutación.
- [x] No se usó ni solicitó ninguna credencial, token, cookie ni sesión.
- [x] Ningún item de ArcGIS fue creado, editado, publicado, compartido ni
      eliminado; ningún envío Survey123.
- [x] Cada afirmación `ANONYMOUS_REST_VERIFIED` cita su evidencia REST/HTTP
      (org: `sharing/rest/info`; servicios: `499 Token Required` vs
      `400 Invalid URL` calibrado). La existencia por UI del propietario se
      marca `OWNER_UI_VERIFIED`.
- [x] Ningún campo/esquema se marca `LIVE_SCHEMA_VERIFIED`; todo esquema queda
      `AUTHENTICATED_READ_REQUIRED`.
- [x] No se afirma "verificación en vivo" completa ni el alcance de
      compartición exacto a partir de `403`/`499`.
- [x] Ninguna decisión formal de reutilización cambió a un valor distinto de
      `UNKNOWN`.
- [x] Ninguna recreación se recomienda por indisponibilidad de metadatos.
- [x] Experience Builder no se declara existente ni inexistente
      (existencia `UNKNOWN`; estado `AUTHENTICATED_READ_REQUIRED`).
- [x] Los Item IDs/URLs reales están **solo** en el registro local ignorado;
      **no** en la documentación versionada.
- [x] `arcgis/demo/pnsg/item-registry.local.yaml` sigue ignorado y no staged.

---

> Verificación de que esta fase se mantuvo de solo lectura, sin fabricación
> de datos, y sin decisiones formales no respaldadas por metadatos reales.

## 1. Alcance de solo lectura

- [x] No se publicó, editó, sobrescribió, compartió, eliminó ni recreó ningún
      item de ArcGIS Online.
- [x] No se envió ningún dato a Survey123.
- [x] No se cambió ninguna configuración de compartición real.
- [x] No se intentó ninguna autenticación ArcGIS.

## 2. Integridad de identificadores

- [x] Ningún Item ID real fue fabricado; todos los campos de identificador en
      `item-registry.local.yaml` permanecen `REQUIRES_HUMAN_INPUT` o
      equivalentes.
- [x] Ninguna URL de servicio real fue inventada.

## 3. Honestidad de estado (corrección de Fase 3 aplicada)

- [x] Ninguna afirmación de esta versión describe inspección en vivo real.
- [x] Ningún item se describe como inexistente sin confirmación directa del
      propietario (el feature service de Survey123 y la app Experience
      Builder están marcados `UNKNOWN`, no "no existen").
- [x] Ninguna decisión formal de reutilización distinta de `UNKNOWN` se asigna
      a un item ArcGIS real (la única excepción es el archivo XLSForm en
      Git, que no es un item ArcGIS Online).
- [x] Ninguna afirmación de deriva de esquema real; toda hipótesis de deriva
      está etiquetada `DERIVED_RISK`.
- [x] Todo hallazgo inferido por cronología está etiquetado `DERIVED_RISK`,
      no presentado como hecho confirmado.
- [x] La disposición del Web Map es `UNKNOWN — NOT LIVE-VERIFIED`, no
      `NOT_READY`.
- [x] La disposición de Experience Builder a nivel ArcGIS es
      `LIVE_ARCGIS_READINESS_UNKNOWN`, separada de la disposición de
      repositorio (`PRELIMINARY_REPOSITORY_READY`).
- [x] La única severidad `BLOCKER` de la matriz de brechas es la ausencia de
      metadatos en vivo (brecha de proceso), no la existencia/inexistencia de
      ningún item de contenido.

## 4. Seguridad

- [x] Ningún token, contraseña, cookie, API key o secreto aparece en ningún
      documento de esta fase.
- [x] `item-registry.local.yaml` permanece ignorado por Git (`git
      check-ignore` confirmado) y no se ha añadido al índice.
- [x] Ninguna coordenada GPS sensible real aparece en los documentos de esta
      fase.

## 5. Registro local

- [x] `arcgis/demo/pnsg/item-registry.local.yaml` existe, está ignorado, y no
      aparece en `git status --short` como archivo a commitear.

## 6. Trazabilidad de hallazgos

- [x] Todo hallazgo de este paquete está respaldado por: (a) el contrato Git,
      (b) el roadmap ya auditado (`HISTORICALLY_VERIFIED`), (c) la
      confirmación cualitativa del propietario (`QUALITATIVELY_CONFIRMED`), o
      (d) una inferencia de cronología explícitamente etiquetada
      `DERIVED_RISK` — nunca presentada como hecho confirmado.

## 7. Alcance del paquete

- [x] El paquete se presenta explícitamente como *"Preliminary
      repository-based ArcGIS readiness assessment — live verification
      pending"*.
- [x] `owner-action-plan.md` define A0 (recolección de metadatos) como acción
      previa obligatoria; ninguna otra acción se prescribe como decidida.
- [x] Solo se modifican los nueve documentos de
      `docs/integrations/arcgis/content-readiness/`.
