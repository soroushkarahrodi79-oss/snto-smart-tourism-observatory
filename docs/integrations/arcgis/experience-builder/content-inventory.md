# Inventario de contenido ArcGIS

> Fase 2A · documentación únicamente. **No se inventan Item IDs.** Todo Item ID
> real es **[Desconocido / Requiere input humano]** y se registra mediante
> placeholders en `item-registry.example.yaml`.

## 1. Existente y verificado

Evidencia: `docs/arcgis/field-validation-demo-roadmap.md` (fases 0–2 cerradas,
verificación 2026-07-13) y `arcgis/demo/pnsg/`.

| Elemento | Tipo ArcGIS | Estado | Nombre conocido | Compartición |
|---|---|---|---|---|
| Organización académica UCM | Org AGOL | **[Verificado]** confirmada 2026-07-13 | — | — |
| Grupo del piloto | Private Group | **[Verificado]** creado | `SNTO — Validación de campo DEMO` | Privado |
| Capa de activos | Hosted Feature Layer | **[Verificado]** publicada, edición desactivada, 2 entidades, simbología por tendencia | `SNTO_DEMO_PNSG_Assets` | Solo grupo |
| Mapa web | Web Map | **[Verificado]** guardado | `SNTO_DEMO_PNSG_FieldValidation_Map` | Solo grupo |
| Formulario de campo | Survey123 (XLSForm) | **[Verificado]** generado en Connect; **servicio aún no publicado** | `SNTO_DEMO_PNSG_FieldValidation.xlsx` | Solo grupo (previsto) |

**Nota de acceso [Verificado]:** la org confirma acceso a Survey123, Field Maps,
Field Maps Designer, Dashboards, Experience Builder, Data Pipelines, Hub,
QuickCapture, Instant Apps, StoryMaps y Map Viewer. Privilegio de crear grupos
privados y de publicar Hosted Feature Layers **confirmado por prueba funcional**.
Tipo de usuario y rol exactos: **[Desconocido]**.

## 2. Implícito pero no verificado

Existen porque el trabajo previo los produjo, pero **su metadato no está en el
repositorio**:

| Elemento | Por qué es implícito | Placeholder |
|---|---|---|
| Item ID de la capa de activos | La capa está publicada, pero el ID no se registró en Git | `assets_layer_item_id` |
| URL del servicio REST de activos + índice de capa | Necesario para el Web Map/EB | `assets_layer_service_url`, `assets_layer_index` |
| Item ID del Web Map | El mapa está guardado | `webmap_item_id` |
| Item ID del formulario Survey123 | Form generado | `field_survey_item_id` |
| Item ID + URL del feature service de campo | Se publica en Fase 3 | `field_service_item_id`, `field_service_url`, `field_layer_index` |
| ID del grupo privado y owner | Grupo creado | `private_group_id`, `owner_username_or_role` |

Todos: **[Desconocido / Requiere input humano]**.

## 3. Por crear

| Elemento | Tipo ArcGIS | Momento | Nota |
|---|---|---|---|
| Feature service de observaciones | Survey123 Hosted Feature Layer | Roadmap Fase 3 | Esquema en `data-contract.md` |
| Vista de solo lectura de activos | Hosted Feature Layer **View** | Antes de exponer a EB | Aísla la capa base de la vista compartida — **[Propuesto]** |
| App Experience Builder | Experience Builder | Fase 2 del build-playbook | 4 páginas + Asset Detail |
| Vista «solo QA reviewed» de observaciones | Hosted Feature Layer **View** con filtro | Cuando exista campaña | Separa `synthetic`/`draft` de `reviewed` — **[Propuesto]** |

## 4. Por esperar (Diferido)

| Elemento | Tipo ArcGIS | Condición de desbloqueo |
|---|---|---|
| Dashboard de seguimiento | Dashboard | Tras MVP EB estable + datos de campo reales |
| StoryMap metodológico | StoryMap | Tras QA de evidencia y decisión de compartición |
| Capa límite PNSG | Feature/Basemap | Licencia y procedencia OAPN documentadas |
| Capa zonas PRUG | Hosted Feature Layer | Licencia y procedencia OAPN documentadas |
| Cualquier vista pública | Sharing público | Superar Fase 7 del roadmap + aprobación explícita |

## 5. Regla de nomenclatura y gobernanza

**[Verificado]** (`arcgis/demo/pnsg/README.md`, roadmap §1.2):

- Prefijo obligatorio de todo item: `SNTO_DEMO_`.
- Descripción obligatoria: «Demostración académica; no usar para decisiones
  operativas».
- Compartición **solo con el grupo privado** durante el desarrollo.
- Prohibido compartir públicamente hasta superar la Fase 7.
- La capa de activos permanece **de solo lectura** para el personal de campo.

## 6. Riesgo de cuenta educativa y continuidad

**[Desconocido / Requiere input humano]** La organización está confirmada como
UCM, pero no constan en Git el tipo exacto de usuario, el propietario
institucional de continuidad, las reglas de transferencia ni la fecha de
caducidad de la cuenta educativa.

**[Propuesto] Antes del build:**

- identificar owner actual y owner institucional de respaldo;
- confirmar si grupo, capas, Web Map, Survey123 y app EB son transferibles;
- registrar fecha de expiración/revisión de la cuenta y un contacto responsable;
- acordar exportación/archivo y transferencia antes de cualquier baja;
- no tratar una cuenta de estudiante como custodia permanente de evidencia.
