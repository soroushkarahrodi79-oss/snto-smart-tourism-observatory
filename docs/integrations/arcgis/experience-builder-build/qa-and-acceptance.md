# QA y criterios de aceptación — Experience Builder MVP

> Testables. Se ejecutan en la fase de build (no ahora).

## 1. Integridad de evidencia
- [ ] Ningún valor `simulated`/`estimated` como titular ejecutivo en Decidir.
- [ ] Ninguna parcela `planned`/`missing` etiquetada como «observada».
- [ ] `missing`/null nunca como `0` (popups usan «Sin dato»).
- [ ] `synthetic` nunca convertido a `real`.
- [ ] Ningún texto afirma acuerdo satélite↔campo ni «método validado».
- [ ] Tendencia presentada como no causal; caveats visibles.

## 2. Uniones e interacción
- [ ] Observaciones unidas a activos por `asset_id` string, no por `OBJECTID`.
- [ ] `asset_id` nulo no tratado como enlazado.
- [ ] No se asume relationship class formal.
- [ ] Sincronización List↔Map↔Feature Info↔indicadores funciona.

## 3. Fuentes de datos
- [ ] Evidencia mostrada desde la **results view** (no la form view).
- [ ] Captura vía enlace al **form item** con prefill (fuera de la app).
- [ ] Ninguna capa alojada duplicada creada.

## 4. Privacidad y permisos
- [ ] App + Web Map + capas + results view compartidos solo con el grupo privado.
- [ ] Viewers de EB **no** pueden editar (results view).
- [ ] Form item/view solo para contribuyentes.
- [ ] Nada público; GPS/fotos/adjuntos dentro del grupo.
- [ ] Ninguna credencial/URL/Item ID expuesta en la app.

## 5. Accesibilidad y responsive
- [ ] Simbología con etiqueta/patrón (no solo color).
- [ ] Contraste AA sobre navy `#1b2d42`.
- [ ] Usable en desktop, tablet y móvil; Evidenciar a pantalla completa en móvil.

## 6. Decisión
- [ ] Máximo 3–4 cifras de decisión en Decidir, cada una con `confidence`+evidencia.
- [ ] El usuario encuentra el activo prioritario (Maliciosa–Porrones) y su
      evidencia sin narrador.
- [ ] Limitaciones visibles antes de cifras en Gobernar.

## 7. Gobernanza y coste
- [ ] Sin herramientas de análisis/geocoding/routing/servicios premium usados.
- [ ] Sello snapshot/fecha visible; nada descrito como «en vivo».
- [ ] Aviso de continuidad de cuenta educativa presente.
- [ ] Protección de borrado activada en todos los items DEMO tras Batch A/C.

## 7b. QA multiusuario (PENDIENTE — bloqueante para audiencia ampliada)
- [ ] Existe una segunda cuenta UCM no-owner en el grupo privado.
- [ ] El usuario no-owner ve la app y sus fuentes; **no** puede editar
      `pilot_assets` ni la results view; captura add-only sin ver existentes.
- [ ] Nada visible fuera del grupo. Ver `multiuser-qa-plan.md`.

## 8. Reversibilidad
- [ ] Copia/ajustes del Web Map registrados antes de configurar.
- [ ] Procedimiento de rollback disponible (`rollback-plan.md`).
- [ ] El núcleo SNTO funciona sin dependencia de ArcGIS.
