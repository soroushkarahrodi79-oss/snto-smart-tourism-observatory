# Build playbook — construcción de la app Experience Builder

> Fase 2A · documentación únicamente. **Este playbook NO se ejecuta ahora.** Es
> un plan futuro, operado por el propietario, con puertas de aprobación. Donde se
> requiere un Item ID real se usa un **placeholder** de
> `item-registry.example.yaml`.

## Convenciones

- Prefijo obligatorio de items: `SNTO_DEMO_`.
- Compartición: **solo grupo privado** hasta superar la QA.
- Cada fase termina en una **puerta de aprobación** explícita del propietario.
- **Nunca** compartir contraseña, token, clave ni cookie. Los Item IDs son
  identificadores, no credenciales, pero se registran solo tras aprobación
  explícita del propietario.

## Fase B0 · Preparación (aprobación previa)

1. Confirmar tipo de usuario, rol y créditos disponibles en la org UCM
   (**[Desconocido]** hoy).
2. Confirmar owner actual, owner institucional de respaldo, transferibilidad de
   todos los items y fecha de caducidad/revisión de la cuenta educativa
   (**[Desconocido]** hoy). Definir archivo/exportación antes de una baja.
3. Confirmar que el grupo privado `SNTO — Validación de campo DEMO`
   (`private_group_id`) existe. **[Verificado]** creado.
4. Regenerar un candidato de snapshot con `scripts/export_gis.py`.
   **[Verificado]** El exportador actual enriquece tendencia/evidencia, pero
   solo guarda la versión en metadata top-level y no añade por feature
   `source_version`, `calculated_at` ni `demo_status`. No publicar hasta que una
   preparación funcional separada y aprobada complete el contrato o se revise
   explícitamente el contrato. **Puerta:** revisión del diff y de todos los
   metadatos de snapshot.

## Fase B1 · Inventario de items

Verificar/registrar (en `item-registry.example.yaml`, con placeholders hasta
aprobación):

- `assets_layer_item_id`, `assets_layer_service_url`, `assets_layer_index`
  (capa `SNTO_DEMO_PNSG_Assets`, **[Verificado]** publicada);
- `webmap_item_id` (`SNTO_DEMO_PNSG_FieldValidation_Map`, **[Verificado]**);
- `field_survey_item_id`, `field_service_item_id`, `field_service_url`,
  `field_layer_index` (Survey123, se publican en roadmap Fase 3).

**Puerta:** el propietario confirma qué IDs pueden registrarse.

## Fase B2 · Configuración del Web Map

1. Abrir `SNTO_DEMO_PNSG_FieldValidation_Map`.
2. Simbología por `trend` con **patrón + etiqueta** (no solo color); `has_trend=0`
   con contorno discontinuo y etiqueta «Sin serie».
3. Configurar popups según `design-system.md` §6 (orden fijo, null → «Sin dato»).
4. Añadir capa PRUG/límite **solo si** su licencia/procedencia están documentadas
   (**[Diferido/condicionado]**).
5. **Puerta:** revisión visual de simbología y popups.

## Fase B3 · Creación de la app Experience Builder

1. Crear app EB en blanco; nombre `SNTO_DEMO_PNSG_EspacioDecision`; prefijo y
   descripción obligatoria.
2. Aplicar tema con la paleta SNTO (`design-system.md` §1).
3. Definir 4 páginas (Section/Views): Decidir, Diagnosticar, Evidenciar,
   Gobernar + panel Asset Detail.
4. **Puerta:** estructura de páginas aprobada.

## Fase B4 · Orden de construcción de páginas y cableado de widgets

Construir en este orden (de menor a mayor dependencia de datos):

1. **Gobernar** (estático: `Text`, `Button` de descarga, `Embed`).
2. **Diagnosticar** (`Map` + `List` + `Table` + `Filter` + `Search`; cablear
   sincronización Map↔List↔Table).
3. **Asset Detail** (`Feature Info` + `List` de observaciones + `Text`; parámetro
   de URL para selección).
4. **Decidir** (`Text` KPIs + `List` prioritaria + `Button` → Diagnosticar).
5. **Evidenciar** (`Map` de parcelas + `Feature Info` + `Chart` + botón Survey123
   con prefill de `asset_id`; ver `survey123-integration.md` §3).

**Puerta:** cada página revisada contra sus criterios de aceptación en
`page-blueprints.md`.

## Fase B5 · Vistas responsive

1. Configurar layouts desktop / tablet / móvil por página (`design-system.md` §8).
2. Verificar la hoja inferior deslizable en Diagnosticar y la ficha a pantalla
   completa en Evidenciar.
3. **Puerta:** prueba en los tres tamaños.

## Fase B6 · Compartición

1. Compartir app, Web Map y capas **solo con el grupo privado**.
2. Confirmar que **nada** queda público.
3. Mantener GPS, fotos, adjuntos y registros de observación privados hasta una
   revisión de compartición explícita y documentada.
4. Registrar `sharing_scope = group_private` y `last_verified_at`.
5. **Puerta:** revisión de permisos (checklist QA).

## Fase B7 · QA

Ejecutar `qa-checklist.md` completo. **Puerta:** todos los criterios en verde.

## Fase B8 · Rollback / archivo

Si se descarta la demo (roadmap §7):

1. **No** fusionar ninguna rama de código.
2. Eliminar o archivar los items `SNTO_DEMO_` en ArcGIS.
3. No alterar `main` ni los datos de producción.
4. El núcleo SNTO sigue funcionando sin dependencia de ArcGIS.
5. El backup externo
   (`SNTO_BACKUPS/arcgis-field-validation-demo-2026-07-29/`) conserva el material
   fuente.

## Fuera de este playbook (Diferido)

Dashboard y StoryMap: fases posteriores, con su propio playbook y aprobación. No
se pliegan silenciosamente en el primer alcance de Experience Builder.
