# QA checklist — MVP Experience Builder

> Fase 2A · documentación únicamente. Criterios **testables**. Se ejecutan en la
> fase de build (B7), no ahora.

## 1. Integridad de evidencia

- [ ] Ningún valor `simulated`/`estimated` aparece como titular ejecutivo en
      **Decidir**.
- [ ] Ninguna parcela `planned`/`missing` se etiqueta como «observada» en
      **Evidenciar**.
- [ ] Ningún campo `missing`/null se muestra como `0` (popups y fichas usan
      «Sin dato»).
- [ ] `unknown` no se interpreta como `false`; ausencia de observación no se
      presenta como «estable»; ausencia de registro de campo no se presenta
      como validación.
- [ ] Ningún dato `synthetic`/`simulated` cambia automáticamente a `real`.
- [ ] Ningún texto afirma acuerdo satélite↔campo ni «método validado».
- [ ] `agreement_status` solo contiene un resultado después de una comparación
      legítima con muestra suficiente; `field_verified` no implica acuerdo.
- [ ] Las tres dimensiones de evidencia (`evidence_level`, `qa_status`,
      `validation_status`) se muestran separadas, no fusionadas.
- [ ] `has_trend=false` es distinguible **sin** depender del color.

## 2. Sincronización e interacción

- [ ] Selección sincronizada **Map ↔ List ↔ Table** en Diagnosticar.
- [ ] Clic en entidad abre **Asset Detail** con el activo correcto.
- [ ] `Search` localiza un activo por nombre/`asset_id`.
- [ ] Los filtros vacíos muestran estado vacío honesto + reset.

## 3. Claves y uniones

- [ ] Las observaciones se unen a activos por **`asset_id` string**, no por
      `OBJECTID`.
- [ ] Los adjuntos/fotos se relacionan por `GlobalID`/`parentglobalid`.
- [ ] `plot_id` deduplica correctamente.
- [ ] La FK numérica de persistencia **no** se expone en ArcGIS.

## 4. Snapshot vs vivo

- [ ] Cada capa de snapshot muestra `source_version` + fecha.
- [ ] En ningún sitio un snapshot se describe como «en vivo».
- [ ] La página **Gobernar** explica qué es snapshot y qué sería «en vivo».

## 5. Privacidad y permisos

- [ ] App, Web Map y capas compartidos **solo con el grupo privado**.
- [ ] Nada compartido públicamente.
- [ ] GPS y fotos no expuestos fuera del grupo.
- [ ] Adjuntos y registros de observación no expuestos fuera del grupo ni antes
      de una revisión de compartición explícita.
- [ ] Ningún secreto/token/cookie en items ni en descripciones.
- [ ] Owner actual, owner de continuidad, transferibilidad y fecha de
      caducidad/revisión de la cuenta educativa están registrados.

## 6. Accesibilidad y responsive

- [ ] Toda simbología categórica lleva etiqueta/patrón (no solo color).
- [ ] Contraste AA en textos sobre navy `#1b2d42`.
- [ ] Usable en desktop, tablet y móvil (los tres layouts verificados).
- [ ] Evidenciar usable a pantalla completa en móvil (uso de campo).

## 7. Usabilidad de decisión

- [ ] El usuario encuentra el activo prioritario (Maliciosa–Porrones) y su
      evidencia **sin narrador**.
- [ ] Máximo 3–4 cifras de decisión en Decidir.
- [ ] Cada cifra lleva `confidence` + badge de evidencia.
- [ ] Las limitaciones son visibles antes que cualquier cifra en Gobernar.

## 8. Reversibilidad

- [ ] Existe procedimiento de archivo/rollback (build-playbook B8).
- [ ] El backup externo del material fuente está verificado.
- [ ] El núcleo SNTO funciona sin dependencia de ArcGIS.
- [ ] Existe un procedimiento de exportación/transferencia previo a la baja de
      la cuenta educativa.
